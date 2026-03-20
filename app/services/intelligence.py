from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.intelligence import (
    get_device_status_map,
    get_latest_classification_map,
    get_latest_telemetry_map,
    get_recent_telemetry_series,
    list_candidate_bins,
    list_model_metric_snapshots,
)
from app.services.forecaster import ForecastInput, ForecastService


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _round2(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


async def build_risk_scores(
    session: AsyncSession,
    *,
    forecaster: ForecastService,
    organisation_id: int | None = None,
    limit: int = 50,
) -> list[dict]:
    bins = await list_candidate_bins(session, organisation_id=organisation_id, limit=max(limit, 50))
    if not bins:
        return []
    bin_ids = [b.bin_id for b in bins]
    latest_tel = await get_latest_telemetry_map(session, bin_ids)
    latest_cls = await get_latest_classification_map(session, bin_ids)
    telemetry_series = await get_recent_telemetry_series(session, bin_ids, hours=48)
    device_map = await get_device_status_map(session, bin_ids)
    now = datetime.now(timezone.utc)
    items: list[dict] = []

    for bin_row in bins:
        telemetry = latest_tel.get(bin_row.bin_id)
        if telemetry is None:
            continue
        series = telemetry_series.get(bin_row.bin_id, [])
        fills = [float(x.fill_level) for x in series]
        history_mean = mean(fills) if fills else float(telemetry.fill_level)
        current_fill = float(telemetry.fill_level)
        growth_rate = 0.0
        if len(fills) >= 2:
            growth_rate = max(0.0, (fills[-1] - fills[0]) / max(1, len(fills) - 1))
        forecast_input = ForecastInput(
            bin_id=bin_row.bin_id,
            fill_level=current_fill,
            hour_of_day=now.hour,
            day=now.weekday(),
            weekend=1 if now.weekday() >= 5 else 0,
            growth_rate=growth_rate,
            lags=(fills[-3:] if len(fills) >= 3 else ([current_fill] * 3)),
            rolling_mean_3=(sum(fills[-3:]) / min(3, len(fills))) if fills else current_fill,
        )
        predicted_fill = float(forecaster.predict_6h(forecast_input))
        overflow_delta = max(0.0, 100.0 - current_fill)
        overflow_eta_hours = None if predicted_fill <= current_fill else _round2(6.0 * (overflow_delta / max(0.1, predicted_fill - current_fill)))
        stale_hours = max(0.0, (now - telemetry.ts).total_seconds() / 3600.0)
        anomaly_delta = abs(current_fill - history_mean)
        anomaly_score = _clamp(anomaly_delta / 35.0 + (0.25 if stale_hours >= 8 else 0.0))
        anomaly_flags: list[str] = []
        if stale_hours >= 8:
            anomaly_flags.append('STALE_TELEMETRY')
        if anomaly_delta >= 25:
            anomaly_flags.append('ABNORMAL_FILL_PATTERN')
        if len(fills) >= 2 and fills[-1] + 15 < fills[-2]:
            anomaly_flags.append('SUDDEN_DROP')
        classification = latest_cls.get(bin_row.bin_id)
        contamination_reasons: list[str] = []
        contamination_risk = 0.08
        if classification is None:
            contamination_reasons.append('No recent image classification available')
            contamination_risk += 0.1
        else:
            confidence = float(classification.confidence)
            if confidence < 0.55:
                contamination_reasons.append('Low classification confidence')
                contamination_risk += 0.22
            if classification.predicted_class == 'trash':
                contamination_reasons.append('Generic trash class often indicates mixed waste')
                contamination_risk += 0.18
        if current_fill >= 90:
            contamination_reasons.append('High fill level increases mixed-waste spill risk')
            contamination_risk += 0.12
        device_issues = device_map.get(bin_row.bin_id, [])
        if any(d.status in {'offline', 'maintenance'} for d in device_issues):
            anomaly_flags.append('DEVICE_HEALTH_RISK')
            contamination_reasons.append('Device health risk reduces sensing reliability')
            contamination_risk += 0.08
        overflow_risk = _clamp((predicted_fill / 100.0) * 0.55 + (current_fill / 100.0) * 0.25 + (float(telemetry.last_collection_hours) / 72.0) * 0.20)
        if overflow_eta_hours is not None and overflow_eta_hours <= 6:
            overflow_risk = _clamp(overflow_risk + 0.15)
        recommended_action = 'Monitor'
        if overflow_risk >= 0.85:
            recommended_action = 'Dispatch urgent collection'
        elif contamination_risk >= 0.5:
            recommended_action = 'Inspect for contamination'
        elif anomaly_score >= 0.55:
            recommended_action = 'Verify sensor / telemetry health'
        items.append({
            'bin_id': bin_row.bin_id,
            'organisation_id': bin_row.organisation_id,
            'site_id': bin_row.site_id,
            'zone_id': bin_row.zone_id,
            'current_fill': _round2(current_fill),
            'predicted_fill_6h': _round2(predicted_fill),
            'overflow_eta_hours': overflow_eta_hours,
            'overflow_risk_probability': _round2(overflow_risk),
            'anomaly_score': _round2(anomaly_score),
            'anomaly_flags': anomaly_flags,
            'contamination_risk_probability': _round2(_clamp(contamination_risk)),
            'contamination_reasons': contamination_reasons,
            'recommended_action': recommended_action,
            'generated_at': now,
        })
    items.sort(key=lambda x: (x['overflow_risk_probability'], x['anomaly_score'], x['contamination_risk_probability']), reverse=True)
    return items[:limit]


async def build_explainability(session: AsyncSession, *, forecaster: ForecastService, bin_id: str) -> dict | None:
    scores = await build_risk_scores(session, forecaster=forecaster, limit=500)
    target = next((item for item in scores if item['bin_id'] == bin_id), None)
    if target is None:
        return None
    factors = [
        {
            'factor': 'Predicted fill in next 6h',
            'impact': 'high' if target['predicted_fill_6h'] >= 85 else 'medium',
            'value': target['predicted_fill_6h'],
            'reason': 'Higher future fill directly raises overflow urgency.',
        },
        {
            'factor': 'Overflow risk probability',
            'impact': 'high' if target['overflow_risk_probability'] >= 0.75 else 'medium',
            'value': target['overflow_risk_probability'],
            'reason': 'Composite probability from current fill, forecast, and service delay.',
        },
        {
            'factor': 'Anomaly score',
            'impact': 'medium' if target['anomaly_score'] >= 0.4 else 'low',
            'value': target['anomaly_score'],
            'reason': 'Flags abnormal telemetry behaviour or stale device data.',
        },
        {
            'factor': 'Contamination risk probability',
            'impact': 'medium' if target['contamination_risk_probability'] >= 0.4 else 'low',
            'value': target['contamination_risk_probability'],
            'reason': 'Based on low-confidence waste class and operating conditions.',
        },
    ]
    summary = (
        f"Bin {bin_id} is prioritised because predicted fill is {target['predicted_fill_6h']}%, "
        f"overflow risk is {target['overflow_risk_probability']}, "
        f"and anomaly score is {target['anomaly_score']}."
    )
    return {
        'bin_id': bin_id,
        'generated_at': target['generated_at'],
        'summary': summary,
        'recommendation': target['recommended_action'],
        'contributing_factors': factors,
        'risk': target,
    }


async def build_anomaly_events(session: AsyncSession, *, organisation_id: int | None = None, hours: int = 48, limit: int = 50) -> list[dict]:
    bins = await list_candidate_bins(session, organisation_id=organisation_id, limit=max(limit, 50))
    if not bins:
        return []
    bin_ids = [b.bin_id for b in bins]
    telemetry_series = await get_recent_telemetry_series(session, bin_ids, hours=hours)
    items: list[dict] = []
    for row in bins:
        series = telemetry_series.get(row.bin_id, [])
        if len(series) < 2:
            continue
        latest = series[-1]
        expected = mean(float(x.fill_level) for x in series[:-1]) if len(series) > 1 else float(latest.fill_level)
        delta = float(latest.fill_level) - expected
        anomaly_score = _clamp(abs(delta) / 35.0)
        flags = []
        if delta >= 20:
            flags.append('SPIKE')
        if delta <= -20:
            flags.append('DROP')
        if (datetime.now(timezone.utc) - latest.ts).total_seconds() / 3600.0 >= 8:
            flags.append('STALE')
            anomaly_score = _clamp(anomaly_score + 0.25)
        if anomaly_score < 0.45:
            continue
        items.append({
            'bin_id': row.bin_id,
            'organisation_id': row.organisation_id,
            'site_id': row.site_id,
            'zone_id': row.zone_id,
            'latest_fill': _round2(float(latest.fill_level)),
            'expected_fill': _round2(expected),
            'delta': _round2(delta),
            'anomaly_score': _round2(anomaly_score),
            'flags': flags,
            'ts': latest.ts,
        })
    items.sort(key=lambda x: x['anomaly_score'], reverse=True)
    return items[:limit]


async def build_monitoring_summary(session: AsyncSession, *, model_name: str | None = None, days: int = 14) -> dict:
    rows = await list_model_metric_snapshots(session, model_name=model_name, days=days, limit=500)
    grouped: dict[tuple[str, str], list] = defaultdict(list)
    for row in rows:
        grouped[(row.model_name, row.metric_name)].append(row)
    metrics = []
    resolved_model_name = model_name
    for (group_model_name, metric_name), bucket in grouped.items():
        latest = bucket[0]
        resolved_model_name = resolved_model_name or group_model_name
        metrics.append({
            'metric_name': metric_name,
            'latest_value': round(float(latest.metric_value), 4),
            'status': latest.status,
            'sample_size': latest.sample_size,
            'model_version': latest.model_version,
            'last_created_at': latest.created_at,
        })
    metrics.sort(key=lambda x: x['metric_name'])
    return {
        'model_name': resolved_model_name or 'all_models',
        'days': days,
        'metrics': metrics,
    }
