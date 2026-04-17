from __future__ import annotations
from app.services.model_store import ModelStore
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


async def build_anomaly_events(
    session: AsyncSession,
    *,
    forecaster: ForecastService,
    organisation_id: int | None = None,
    hours: int = 48,
    limit: int = 50,
    ) -> list[dict]:
    bins = await list_candidate_bins(session, organisation_id=organisation_id, limit=max(limit, 100))
    if not bins:
        return []

    bin_ids = [b.bin_id for b in bins]
    telemetry_series = await get_recent_telemetry_series(session, bin_ids, hours=hours)
    device_map = await get_device_status_map(session, bin_ids)
    now = datetime.now(timezone.utc)

    items: list[dict] = []

    for row in bins:
        series = telemetry_series.get(row.bin_id, [])
        if len(series) < 2:
            continue

        latest = series[-1]
        previous = series[:-1]

        expected = mean(float(x.fill_level) for x in previous) if previous else float(latest.fill_level)
        latest_fill = float(latest.fill_level)
        delta = latest_fill - expected

        stale_hours = max(0.0, (now - latest.ts).total_seconds() / 3600.0)
        anomaly_score = _clamp(abs(delta) / 35.0)

        flags: list[str] = []

        if delta >= 15:
            flags.append("SPIKE")
        if delta <= -15:
            flags.append("DROP")

        if stale_hours >= 8:
            flags.append("STALE")
            anomaly_score = _clamp(anomaly_score + 0.25)

        device_issues = device_map.get(row.bin_id, [])
        if any(d.status in {"offline", "maintenance"} for d in device_issues):
            flags.append("DEVICE_HEALTH_RISK")
            anomaly_score = _clamp(anomaly_score + 0.15)

        # Lower threshold so page is useful
        if anomaly_score < 0.25:
            continue

        items.append({
            "bin_id": row.bin_id,
            "organisation_id": row.organisation_id,
            "site_id": row.site_id,
            "zone_id": row.zone_id,
            "latest_fill": _round2(latest_fill),
            "expected_fill": _round2(expected),
            "delta": _round2(delta),
            "anomaly_score": _round2(anomaly_score),
            "flags": flags,
            "ts": latest.ts,
        })

    items.sort(key=lambda x: (x["anomaly_score"], abs(x["delta"])), reverse=True)
    return items[:limit]


async def build_monitoring_summary(
    session: AsyncSession,
    *,
    model_name: str | None = None,
    days: int = 14,
    organisation_id: int | None = None,
    forecaster: ForecastService | None = None,
) -> dict:
    rows = await list_model_metric_snapshots(session, model_name=model_name, days=days, limit=500)

    # Existing snapshot-based behavior
    if rows:
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

    # Live fallback when no snapshots exist
    bins = await list_candidate_bins(session, organisation_id=organisation_id, limit=300)
    bin_ids = [b.bin_id for b in bins]
    latest_cls = await get_latest_classification_map(session, bin_ids)
    telemetry_series = await get_recent_telemetry_series(session, bin_ids, hours=max(48, min(days * 24, 24 * 14)))
    health = ModelStore.get_health()
    now = datetime.now(timezone.utc)

    risk_items: list[dict] = []
    if forecaster is not None and ModelStore.get_forecaster() is not None:
        try:
            risk_items = await build_risk_scores(
                session,
                forecaster=forecaster,
                organisation_id=organisation_id,
                limit=300,
            )
        except Exception:
            risk_items = []

    def status_from_thresholds(
        value: float,
        *,
        warning: float,
        critical: float,
        higher_is_worse: bool = True,
    ) -> str:
        if higher_is_worse:
            if value >= critical:
                return "critical"
            if value >= warning:
                return "warning"
            return "ok"
        else:
            if value <= critical:
                return "critical"
            if value <= warning:
                return "warning"
            return "ok"

    metrics: list[dict] = []

    def add_metric(
        group_model_name: str,
        metric_name: str,
        latest_value: float,
        status: str,
        sample_size: int | None = None,
        model_version: str | None = None,
    ) -> None:
        metrics.append({
            "model_name": group_model_name,
            "metric_name": metric_name,
            "latest_value": round(float(latest_value), 4),
            "status": status,
            "sample_size": sample_size,
            "model_version": model_version,
            "last_created_at": now,
        })

    total_bins = len(bin_ids)

    # waste_classifier (real loaded model)
    classifier_meta = health.get("classifier", {})
    classifier_loaded = 1.0 if classifier_meta.get("loaded") else 0.0
    cls_confidences = [float(x.confidence) for x in latest_cls.values()]
    avg_confidence = mean(cls_confidences) if cls_confidences else 0.0
    cls_coverage = (len(latest_cls) / total_bins) if total_bins else 0.0

    add_metric(
        "waste_classifier",
        "model_loaded",
        classifier_loaded,
        "ok" if classifier_loaded == 1.0 else "critical",
        sample_size=len(latest_cls),
        model_version=classifier_meta.get("version"),
    )
    add_metric(
        "waste_classifier",
        "avg_confidence",
        avg_confidence,
        status_from_thresholds(avg_confidence, warning=0.65, critical=0.45, higher_is_worse=False),
        sample_size=len(cls_confidences),
        model_version=classifier_meta.get("version"),
    )
    add_metric(
        "waste_classifier",
        "coverage_rate",
        cls_coverage,
        status_from_thresholds(cls_coverage, warning=0.50, critical=0.20, higher_is_worse=False),
        sample_size=total_bins,
        model_version=classifier_meta.get("version"),
    )

    # fill_predictor (real loaded model)
    forecaster_meta = health.get("forecaster", {})
    forecaster_loaded = 1.0 if forecaster_meta.get("loaded") else 0.0
    risk_coverage = (len(risk_items) / total_bins) if total_bins else 0.0
    avg_predicted_fill = (
        mean([(float(item["predicted_fill_6h"]) / 100.0) for item in risk_items])
        if risk_items else 0.0
    )

    add_metric(
        "fill_predictor",
        "model_loaded",
        forecaster_loaded,
        "ok" if forecaster_loaded == 1.0 else "critical",
        sample_size=len(risk_items),
        model_version=forecaster_meta.get("version"),
    )
    add_metric(
        "fill_predictor",
        "coverage_rate",
        risk_coverage,
        status_from_thresholds(risk_coverage, warning=0.50, critical=0.20, higher_is_worse=False),
        sample_size=total_bins,
        model_version=forecaster_meta.get("version"),
    )
    add_metric(
        "fill_predictor",
        "avg_predicted_fill_rate",
        avg_predicted_fill,
        status_from_thresholds(avg_predicted_fill, warning=0.70, critical=0.90, higher_is_worse=True),
        sample_size=len(risk_items),
        model_version=forecaster_meta.get("version"),
    )

    # overflow_risk (derived intelligence component)
    avg_overflow_risk = (
        mean([float(item["overflow_risk_probability"]) for item in risk_items])
        if risk_items else 0.0
    )
    high_overflow_rate = (
        sum(1 for item in risk_items if float(item["overflow_risk_probability"]) >= 0.7) / len(risk_items)
        if risk_items else 0.0
    )

    add_metric(
        "overflow_risk",
        "avg_overflow_risk",
        avg_overflow_risk,
        status_from_thresholds(avg_overflow_risk, warning=0.50, critical=0.75, higher_is_worse=True),
        sample_size=len(risk_items),
        model_version="heuristic-v1",
    )
    add_metric(
        "overflow_risk",
        "high_risk_rate",
        high_overflow_rate,
        status_from_thresholds(high_overflow_rate, warning=0.15, critical=0.30, higher_is_worse=True),
        sample_size=len(risk_items),
        model_version="heuristic-v1",
    )

    # anomaly_detector (derived intelligence component)
    avg_anomaly_score = (
        mean([float(item["anomaly_score"]) for item in risk_items])
        if risk_items else 0.0
    )
    anomaly_rate = (
        sum(1 for item in risk_items if float(item["anomaly_score"]) >= 0.5) / len(risk_items)
        if risk_items else 0.0
    )

    add_metric(
        "anomaly_detector",
        "avg_anomaly_score",
        avg_anomaly_score,
        status_from_thresholds(avg_anomaly_score, warning=0.45, critical=0.70, higher_is_worse=True),
        sample_size=len(risk_items),
        model_version="heuristic-v1",
    )
    add_metric(
        "anomaly_detector",
        "anomaly_rate",
        anomaly_rate,
        status_from_thresholds(anomaly_rate, warning=0.15, critical=0.35, higher_is_worse=True),
        sample_size=len(risk_items),
        model_version="heuristic-v1",
    )

    # contamination_classifier (derived intelligence component)
    avg_contamination_risk = (
        mean([float(item["contamination_risk_probability"]) for item in risk_items])
        if risk_items else 0.0
    )
    contamination_high_risk_rate = (
        sum(1 for item in risk_items if float(item["contamination_risk_probability"]) >= 0.5) / len(risk_items)
        if risk_items else 0.0
    )

    add_metric(
        "contamination_classifier",
        "avg_contamination_risk",
        avg_contamination_risk,
        status_from_thresholds(avg_contamination_risk, warning=0.35, critical=0.60, higher_is_worse=True),
        sample_size=len(risk_items),
        model_version="heuristic-v1",
    )
    add_metric(
        "contamination_classifier",
        "high_risk_rate",
        contamination_high_risk_rate,
        status_from_thresholds(contamination_high_risk_rate, warning=0.10, critical=0.25, higher_is_worse=True),
        sample_size=len(risk_items),
        model_version="heuristic-v1",
    )

    if model_name:
        metrics = [m for m in metrics if m["model_name"] == model_name]

    metrics.sort(key=lambda x: (x["model_name"], x["metric_name"]))

    return {
        "model_name": model_name or "all_models",
        "days": days,
        "metrics": [
            {
                "metric_name": m["metric_name"],
                "latest_value": m["latest_value"],
                "status": m["status"],
                "sample_size": m["sample_size"],
                "model_version": m["model_version"],
                "last_created_at": m["last_created_at"],
            }
            for m in metrics
        ],
    }