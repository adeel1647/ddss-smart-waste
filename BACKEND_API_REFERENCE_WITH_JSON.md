# Backend API Reference with JSON Examples

Base URL:

```text
/api/v1
```

## Authentication Notes

Protected endpoints accept either:

```http
Authorization: Bearer <access_token>
```

or the login cookie set by the backend.

Login returns JSON and also sets a cookie.

---

## 1) Health

### GET `/health`
**Purpose:** simple backend liveness check.

**Request body:** none

**Example response**
```json
{
  "status": "ok"
}
```

---

## 2) Public platform stats

### GET `/public/stats`
**Purpose:** simple public summary of platform capabilities.

**Request body:** none

**Example response**
```json
{
  "platform": "DDSS Smart Waste",
  "supported_classes": 6,
  "features": [
    "Image classification",
    "Fill forecasting",
    "Decision support",
    "Route optimization",
    "Operational alerts",
    "Analytics"
  ]
}
```

---

## 3) Authentication

### POST `/auth/register`
**Purpose:** create a new user.

**JSON request**
```json
{
  "email": "admin@example.com",
  "password": "StrongPass123!",
  "display_name": "Adeel"
}
```

**Example response**
```json
{
  "id": 1,
  "email": "admin@example.com",
  "display_name": "Adeel",
  "is_active": true,
  "is_admin": false
}
```

### POST `/auth/login`
**Purpose:** authenticate and receive access token.

**JSON request**
```json
{
  "email": "admin@example.com",
  "password": "StrongPass123!"
}
```

**Example response**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

### POST `/auth/forgot-password/request-code`
**Purpose:** send verification code email if account exists.

**JSON request**
```json
{
  "email": "admin@example.com"
}
```

**Example response**
```json
{
  "message": "If an account exists for that email, a verification code has been sent."
}
```

### POST `/auth/forgot-password/verify-code`
**Purpose:** verify email + code and receive reset token.

**JSON request**
```json
{
  "email": "admin@example.com",
  "code": "123456"
}
```

**Example response**
```json
{
  "message": "Code verified successfully",
  "reset_token": "eyJhbGciOi..."
}
```

### POST `/auth/forgot-password/reset`
**Purpose:** reset password using verified reset token.

**JSON request**
```json
{
  "reset_token": "eyJhbGciOi...",
  "new_password": "NewStrongPass123!",
  "confirm_password": "NewStrongPass123!"
}
```

**Example response**
```json
{
  "message": "Password reset successful"
}
```

### POST `/auth/logout`
**Purpose:** clear auth cookie.

**Request body:** none

**Example response**
```json
{
  "ok": true
}
```

---

## 4) User profile

### GET `/users/me`
**Purpose:** get current logged-in user.

**Request body:** none

**Example response**
```json
{
  "id": 1,
  "email": "admin@example.com",
  "display_name": "Adeel",
  "is_active": true,
  "is_admin": true
}
```

### PATCH `/users/me`
**Purpose:** update current user display name.

**JSON request**
```json
{
  "display_name": "Adeel Khan"
}
```

**Example response**
```json
{
  "id": 1,
  "email": "admin@example.com",
  "display_name": "Adeel Khan",
  "is_active": true,
  "is_admin": true
}
```

---

## 5) Bins

### POST `/bins`
**Purpose:** create a smart bin record.

**JSON request**
```json
{
  "postcode": "HU6 7RX",
  "sector": "North",
  "lat": 53.8142,
  "lon": -0.3671,
  "active": true
}
```

**Example response**
```json
{
  "bin_id": "BIN-0001",
  "postcode": "HU6 7RX",
  "sector": "North",
  "lat": 53.8142,
  "lon": -0.3671,
  "active": true,
  "created_at": "2026-03-18T10:30:00Z"
}
```

### GET `/bins`
**Purpose:** list bins.

**Query params**
- `postcode` optional
- `sector` optional
- `active` optional, defaults to `true`
- `limit` optional, defaults to `200`

**Example URL**
```text
/bins?postcode=HU6%207RX&sector=North&active=true&limit=50
```

**Example response**
```json
[
  {
    "bin_id": "BIN-0001",
    "postcode": "HU6 7RX",
    "sector": "North",
    "lat": 53.8142,
    "lon": -0.3671,
    "active": true,
    "created_at": "2026-03-18T10:30:00Z"
  }
]
```

### GET `/bins/{bin_id}`
**Purpose:** get one bin.

**Example response**
```json
{
  "bin_id": "BIN-0001",
  "postcode": "HU6 7RX",
  "sector": "North",
  "lat": 53.8142,
  "lon": -0.3671,
  "active": true,
  "created_at": "2026-03-18T10:30:00Z"
}
```

---

## 6) Telemetry

### POST `/bins/{bin_id}/telemetry`
**Purpose:** store telemetry for one bin.

**JSON request**
```json
{
  "ts": "2026-03-18T09:00:00Z",
  "fill_level": 72.5,
  "last_collection_hours": 18
}
```

**Example response**
```json
{
  "id": 101,
  "bin_id": "BIN-0001",
  "ts": "2026-03-18T09:00:00Z",
  "fill_level": 72.5,
  "last_collection_hours": 18.0
}
```

### GET `/bins/{bin_id}/telemetry/latest`
**Purpose:** get latest telemetry for one bin.

**Example response**
```json
{
  "id": 101,
  "bin_id": "BIN-0001",
  "ts": "2026-03-18T09:00:00Z",
  "fill_level": 72.5,
  "last_collection_hours": 18.0
}
```

---

## 7) Waste image classification

### POST `/classify`
**Purpose:** classify an uploaded waste image and optionally store the result against a bin.

**Content type**
```text
multipart/form-data
```

**Form fields**
- `file` required image file
- `bin_id` optional query parameter or form-compatible parameter depending on client usage

**Example cURL**
```bash
curl -X POST "http://localhost:8000/api/v1/classify?bin_id=BIN-0001"   -H "Authorization: Bearer YOUR_TOKEN"   -F "file=@sample.jpg"
```

**Example response**
```json
{
  "predicted_class": "plastic",
  "confidence": 0.91,
  "top_k": [
    {
      "label": "plastic",
      "confidence": 0.91
    },
    {
      "label": "trash",
      "confidence": 0.06
    },
    {
      "label": "metal",
      "confidence": 0.03
    }
  ],
  "stored": true
}
```

---

## 8) Forecasting

### POST `/forecast`
**Purpose:** predict fill level 6 hours ahead for one input record.

**JSON request**
```json
{
  "bin_id": "BIN-0001",
  "fill_level": 72.5,
  "hour_of_day": 9,
  "day": 2,
  "weekend": 0,
  "growth_rate": 1.1,
  "lags": [66.0, 69.5, 72.5],
  "rolling_mean_3": 69.33
}
```

**Example response**
```json
{
  "bin_id": "BIN-0001",
  "predicted_fill_6h": 88.4,
  "model": "random_forest"
}
```

**Note**
The model expects lag-like recent fill values. In practice, use realistic recent telemetry history.

---

## 9) DDSS run

### POST `/ddss/run`
**Purpose:** run the full decision-support pipeline on eligible bins.

**JSON request**
```json
{
  "postcode": "HU6 7RX",
  "sector": "North",
  "limit": 50
}
```

**Example response**
```json
{
  "run_id": 15,
  "ts": "2026-03-18T10:45:00Z",
  "postcode_filter": "HU6 7RX",
  "ranked_bins": [
    {
      "bin_id": "BIN-0001",
      "predicted_class": "plastic",
      "confidence": 0.91,
      "uncertainty": 0.09,
      "current_fill": 72.5,
      "predicted_fill_6h": 92.1,
      "last_collection_hours": 18.0,
      "priority_score": 57.45,
      "alerts": [
        "CRITICAL_FILL_PREDICTED"
      ],
      "meta": {
        "postcode": "HU6 7RX",
        "sector": "North"
      }
    }
  ]
}
```

**What this endpoint does**
- loads active bins
- reads latest telemetry
- gets latest classification if available
- predicts fill in 6 hours
- computes priority score
- stores decision items
- generates/updates alerts

---

## 10) Latest DDSS results

### GET `/ddss/latest`
**Purpose:** fetch the most recent DDSS run and ranked bins.

**Example response**
```json
{
  "run_id": 15,
  "ts": "2026-03-18T10:45:00Z",
  "postcode_filter": "HU6 7RX",
  "ranked_bins": [
    {
      "bin_id": "BIN-0001",
      "predicted_class": "plastic",
      "confidence": 0.91,
      "uncertainty": 0.09,
      "current_fill": 72.5,
      "predicted_fill_6h": 92.1,
      "last_collection_hours": 18.0,
      "priority_score": 57.45,
      "alerts": [
        "CRITICAL_FILL_PREDICTED"
      ],
      "meta": {
        "postcode": "HU6 7RX"
      }
    }
  ]
}
```

---

## 11) Routing - manual optimize

### POST `/routing/optimize`
**Purpose:** optimize trips for points supplied directly by the client.

**JSON request**
```json
{
  "depot_lat": 53.7716,
  "depot_lon": -0.3672,
  "capacity": 300,
  "strategy": "priority_distance",
  "points": [
    {
      "id": "BIN-0001",
      "lat": 53.8142,
      "lon": -0.3671,
      "priority": 57.45,
      "demand": 92.1
    },
    {
      "id": "BIN-0002",
      "lat": 53.799,
      "lon": -0.35,
      "priority": 43.2,
      "demand": 71.5
    }
  ]
}
```

**Example response**
```json
{
  "strategy": "priority_distance",
  "total_distance_km": 14.8,
  "trips": [
    {
      "stops": ["BIN-0001", "BIN-0002"],
      "trip_distance_km": 14.8
    }
  ]
}
```

---

## 12) Routing - plan from latest DDSS

### POST `/routing/plan-latest`
**Purpose:** create a route plan from the latest DDSS run.

**JSON request**
```json
{
  "depot_lat": 53.7716,
  "depot_lon": -0.3672,
  "capacity": 300,
  "strategy": "priority_distance",
  "decision_run_id": 15,
  "top_n": 25
}
```

**Example response**
```json
{
  "plan_id": 9,
  "ts": "2026-03-18T11:00:00Z",
  "decision_run_id": 15,
  "strategy": "priority_distance",
  "total_distance_km": 21.4,
  "trips": [
    {
      "stops": ["BIN-0001", "BIN-0003", "BIN-0002"],
      "trip_distance_km": 21.4
    }
  ]
}
```

**Important implementation note**
The current code still fetches the **latest** DDSS run internally. The `decision_run_id` field exists in the schema but is not currently used in the route logic.

---

## 13) Routing - latest plan

### GET `/routing/latest`
**Purpose:** fetch the latest stored route plan.

**Example response**
```json
{
  "plan_id": 9,
  "ts": "2026-03-18T11:00:00Z",
  "decision_run_id": 15,
  "strategy": "priority_distance",
  "total_distance_km": 21.4,
  "trips": [
    {
      "stops": ["BIN-0001", "BIN-0003", "BIN-0002"],
      "trip_distance_km": 21.4
    }
  ]
}
```

---

## 14) Routing - latest impact metrics

### GET `/routing/impact/latest`
**Purpose:** return summary performance metrics for the latest route plan.

**Example response**
```json
{
  "plan_id": 9,
  "strategy": "priority_distance",
  "total_distance_km": 21.4,
  "baseline_distance_km": 26.75,
  "distance_saved_km": 5.35,
  "distance_saved_pct": 20.0,
  "trip_count": 1,
  "total_stops": 3,
  "avg_stops_per_trip": 3.0,
  "estimated_duration_minutes": 51.36,
  "estimated_fuel_liters": 2.68,
  "estimated_co2_kg": 7.18,
  "capacity_utilization_pct": 1.0
}
```

**Note**
The baseline distance is derived using a simple heuristic, not a true real-world baseline route.

---

## 15) Routing - VRP plan

### POST `/routing/plan-latest-vrp`
**Purpose:** solve a vehicle-routing problem using latest DDSS-ranked bins.

**JSON request**
```json
{
  "depot_lat": 53.7716,
  "depot_lon": -0.3672,
  "capacity": 300,
  "max_vehicles": 6,
  "top_n": 50,
  "priority_weight": 10.0,
  "use_osrm": true
}
```

**Example response**
```json
{
  "plan_id": 10,
  "ts": "2026-03-18T11:10:00Z",
  "decision_run_id": 15,
  "strategy": "vrp",
  "total_distance_km": 18.9,
  "trips": [
    {
      "stops": ["BIN-0001", "BIN-0005"],
      "trip_distance_km": 9.4,
      "geometry": null
    },
    {
      "stops": ["BIN-0002", "BIN-0003"],
      "trip_distance_km": 9.5,
      "geometry": null
    }
  ]
}
```

---

## 16) Alerts

### GET `/alerts`
**Purpose:** list alerts with optional filters.

**Query params**
- `status` optional
- `severity` optional
- `limit` optional, default `50`

**Example URL**
```text
/alerts?status=open&severity=critical&limit=20
```

**Example response**
```json
{
  "items": [
    {
      "id": 7,
      "bin_id": "BIN-0001",
      "decision_run_id": 15,
      "alert_type": "CRITICAL_FILL_PREDICTED",
      "severity": "critical",
      "message": "Predicted fill exceeds critical threshold within 6 hours.",
      "status": "open",
      "meta": {
        "priority_score": 57.45,
        "predicted_fill_6h": 92.1,
        "confidence": 0.91
      },
      "created_at": "2026-03-18T10:45:10Z",
      "resolved_at": null
    }
  ]
}
```

### GET `/alerts/latest`
**Purpose:** fetch latest alerts.

**Query params**
- `limit` optional, default `10`

**Example response**
```json
{
  "items": [
    {
      "id": 7,
      "bin_id": "BIN-0001",
      "decision_run_id": 15,
      "alert_type": "CRITICAL_FILL_PREDICTED",
      "severity": "critical",
      "message": "Predicted fill exceeds critical threshold within 6 hours.",
      "status": "open",
      "meta": {
        "priority_score": 57.45,
        "predicted_fill_6h": 92.1,
        "confidence": 0.91
      },
      "created_at": "2026-03-18T10:45:10Z",
      "resolved_at": null
    }
  ]
}
```

### GET `/alerts/summary`
**Purpose:** get summary counts of alert status and severity.

**Example response**
```json
{
  "open_total": 8,
  "critical_total": 3,
  "warning_total": 5,
  "info_total": 0,
  "acknowledged_total": 2,
  "resolved_total": 9
}
```

### PATCH `/alerts/{alert_id}`
**Purpose:** acknowledge or resolve an alert.

**JSON request**
```json
{
  "status": "acknowledged"
}
```

**Allowed values**
- `acknowledged`
- `resolved`

**Example response**
```json
{
  "id": 7,
  "bin_id": "BIN-0001",
  "decision_run_id": 15,
  "alert_type": "CRITICAL_FILL_PREDICTED",
  "severity": "critical",
  "message": "Predicted fill exceeds critical threshold within 6 hours.",
  "status": "acknowledged",
  "meta": {
    "priority_score": 57.45,
    "predicted_fill_6h": 92.1,
    "confidence": 0.91
  },
  "created_at": "2026-03-18T10:45:10Z",
  "resolved_at": null
}
```

---

## 17) Ops summary

### GET `/ops/summary`
**Purpose:** return one operational KPI snapshot.

**Example response**
```json
{
  "total_bins": 120,
  "active_bins": 114,
  "inactive_bins": 6,
  "critical_bins": 12,
  "warning_bins": 25,
  "healthy_bins": 77,
  "stale_bins": 4,
  "open_alerts": 8,
  "critical_alerts": 3,
  "latest_ddss_run_id": 15,
  "latest_route_plan_id": 9,
  "avg_fill_level": 61.23,
  "avg_predicted_fill_6h": 74.81
}
```

---

## 18) Analytics

### GET `/analytics/overview`
**Purpose:** overview KPI metrics for dashboard cards.

**Example response**
```json
{
  "avg_fill_today": 58.41,
  "max_fill_today": 97.0,
  "critical_alerts_today": 4,
  "open_alerts_total": 8,
  "latest_route_distance_km": 21.4,
  "top_waste_class_today": "plastic"
}
```

### GET `/analytics/fill-trend`
**Purpose:** average fill trend bucketed by hour.

**Query params**
- `hours` optional, default `24`, allowed range `1..168`

**Example URL**
```text
/analytics/fill-trend?hours=48
```

**Example response**
```json
{
  "points": [
    {
      "ts": "2026-03-18T08:00:00+00:00",
      "value": 54.2
    },
    {
      "ts": "2026-03-18T09:00:00+00:00",
      "value": 57.9
    }
  ]
}
```

### GET `/analytics/class-distribution`
**Purpose:** predicted class distribution over recent time window.

**Query params**
- `hours` optional, default `24`, allowed range `1..168`

**Example response**
```json
{
  "items": [
    {
      "label": "plastic",
      "count": 25
    },
    {
      "label": "paper",
      "count": 18
    }
  ]
}
```

---

## 19) Map view

### GET `/map/bins`
**Purpose:** return map-ready bin data merged from multiple sources.

**Example response**
```json
{
  "items": [
    {
      "bin_id": "BIN-0001",
      "postcode": "HU6 7RX",
      "lat": 53.8142,
      "lon": -0.3671,
      "active": true,
      "current_fill": 72.5,
      "predicted_fill_6h": 92.1,
      "last_collection_hours": 18.0,
      "predicted_class": "plastic",
      "confidence": 0.91,
      "priority_score": 57.45,
      "alerts": [
        "CRITICAL_FILL_PREDICTED"
      ],
      "status": "critical",
      "in_latest_route": true
    }
  ]
}
```

**Status meanings**
- `inactive`: bin inactive
- `critical`: critical predicted fill or critical alert
- `warning`: high predicted fill but not critical
- `healthy`: no current warning signal

---

## Extra Notes

### Unmounted route file
There is also a route file in the codebase for:

```text
/ddss/process-bin
```

but it is not included in `main.py` right now, so it is not part of the live mounted API unless you add that router.

### Recommended testing order
A practical order for testing the backend is:
1. `/auth/register`
2. `/auth/login`
3. `/bins`
4. `/bins/{bin_id}/telemetry`
5. `/classify`
6. `/ddss/run`
7. `/alerts/latest`
8. `/routing/plan-latest`
9. `/routing/latest`
10. `/analytics/overview`
11. `/map/bins`
12. `/ops/summary`


---

## 16) Enterprise / Multi-tenant / Phase 5

These endpoints introduce the enterprise-readiness layer.

### GET `/enterprise/organisations`
**Purpose:** list organisations visible to the current user.

**Example response**
```json
[
  {
    "id": 1,
    "name": "Hull City Council",
    "slug": "hull-city-council",
    "description": "Primary municipal tenant",
    "is_active": true,
    "created_at": "2026-03-19T08:00:00Z",
    "updated_at": "2026-03-19T08:00:00Z"
  }
]
```

### POST `/enterprise/organisations`
**Purpose:** create an organisation. Platform admin only.

**JSON request**
```json
{
  "name": "Hull City Council",
  "slug": "hull-city-council",
  "description": "Primary municipal tenant"
}
```

### GET `/enterprise/sites?organisation_id=1`
**Purpose:** list sites inside an organisation.

### POST `/enterprise/sites`
**JSON request**
```json
{
  "organisation_id": 1,
  "name": "Hull Central Depot",
  "code": "HCD-01",
  "address": "Example Street, Hull",
  "lat": 53.7443,
  "lon": -0.3321
}
```

### GET `/enterprise/zones?site_id=1`
**Purpose:** list zones under a site.

### POST `/enterprise/zones`
**JSON request**
```json
{
  "site_id": 1,
  "name": "City Centre",
  "code": "CENTRE",
  "service_level": "high-frequency"
}
```

### GET `/enterprise/memberships?organisation_id=1`
**Purpose:** list membership assignments.

### POST `/enterprise/memberships`
**JSON request**
```json
{
  "organisation_id": 1,
  "user_id": 7,
  "role": "manager",
  "is_default": true
}
```

### GET `/enterprise/devices?organisation_id=1`
**Purpose:** list tenant devices.

### POST `/enterprise/devices`
**JSON request**
```json
{
  "organisation_id": 1,
  "site_id": 1,
  "zone_id": 2,
  "bin_id": "BIN-HU1-001",
  "serial_number": "SENSOR-2026-0001",
  "device_type": "ultrasonic_fill_sensor",
  "firmware_version": "1.0.4",
  "battery_pct": 97,
  "meta": {
    "vendor": "Acme Sensors",
    "connectivity": "LoRaWAN"
  }
}
```

### POST `/enterprise/devices/{device_id}/heartbeat`
**Purpose:** ingest device heartbeat and update last-seen state.

**JSON request**
```json
{
  "battery_pct": 94,
  "rssi": -71,
  "temperature_c": 18.5,
  "payload": {
    "firmware_ok": true,
    "sensor_status": "healthy"
  }
}
```

### GET `/enterprise/notification-channels?organisation_id=1`
**Purpose:** list configured channels.

### POST `/enterprise/notification-channels`
**JSON request**
```json
{
  "organisation_id": 1,
  "name": "Ops Email",
  "channel_type": "email",
  "target": "ops@example.com",
  "enabled": true,
  "severity_filter": "critical",
  "event_types": ["alert.created", "route.capacity_risk"]
}
```

### GET `/enterprise/notification-events?organisation_id=1`
**Purpose:** list queued / sent events.

### POST `/enterprise/notification-events`
**JSON request**
```json
{
  "organisation_id": 1,
  "channel_id": 3,
  "alert_id": 42,
  "event_type": "alert.created",
  "payload": {
    "message": "Predicted overflow in 4 hours",
    "severity": "critical"
  }
}
```

### GET `/enterprise/reports?organisation_id=1`
**Purpose:** list scheduled reports.

### POST `/enterprise/reports`
**JSON request**
```json
{
  "organisation_id": 1,
  "name": "Weekly Operations Summary",
  "report_type": "ops_summary",
  "cron_expr": "0 8 * * MON",
  "format": "csv",
  "recipients": ["manager@example.com", "ops@example.com"],
  "enabled": true
}
```

### GET `/enterprise/audit-logs?organisation_id=1`
**Purpose:** query audit trail for enterprise actions.

**Example response**
```json
[
  {
    "id": 101,
    "organisation_id": 1,
    "actor_user_id": 7,
    "action": "device.create",
    "entity_type": "device",
    "entity_id": "22",
    "status": "success",
    "details": {
      "serial_number": "SENSOR-2026-0001"
    },
    "created_at": "2026-03-19T08:30:00Z"
  }
]
```


---

## Phase 6) Intelligence Expansion

### GET `/intelligence/risk/latest`
**Purpose:** return latest composite risk scores including overflow ETA, anomaly score, and contamination risk.

**Query params**
- `organisation_id` optional
- `limit` optional, default `25`

**Example response**
```json
{
  "items": [
    {
      "bin_id": "BIN-001",
      "organisation_id": 2,
      "site_id": null,
      "zone_id": null,
      "current_fill": 81.4,
      "predicted_fill_6h": 96.8,
      "overflow_eta_hours": 4.2,
      "overflow_risk_probability": 0.91,
      "anomaly_score": 0.34,
      "anomaly_flags": ["DEVICE_HEALTH_RISK"],
      "contamination_risk_probability": 0.48,
      "contamination_reasons": [
        "Low classification confidence",
        "High fill level increases mixed-waste spill risk"
      ],
      "recommended_action": "Dispatch urgent collection",
      "generated_at": "2026-03-19T09:00:00Z"
    }
  ]
}
```

### GET `/intelligence/anomalies`
**Purpose:** return bins with abnormal telemetry behaviour.

**Query params**
- `organisation_id` optional
- `hours` optional, default `48`
- `limit` optional, default `50`

**Example response**
```json
{
  "items": [
    {
      "bin_id": "BIN-009",
      "organisation_id": 2,
      "site_id": null,
      "zone_id": null,
      "latest_fill": 92.0,
      "expected_fill": 61.3,
      "delta": 30.7,
      "anomaly_score": 0.88,
      "flags": ["SPIKE"],
      "ts": "2026-03-19T08:40:00Z"
    }
  ]
}
```

### GET `/intelligence/explain/bin/{bin_id}`
**Purpose:** provide human-readable reasoning for why a bin is risky.

**Example response**
```json
{
  "bin_id": "BIN-001",
  "generated_at": "2026-03-19T09:00:00Z",
  "summary": "Bin BIN-001 is prioritised because predicted fill is 96.8%, overflow risk is 0.91, and anomaly score is 0.34.",
  "recommendation": "Dispatch urgent collection",
  "contributing_factors": [
    {
      "factor": "Predicted fill in next 6h",
      "impact": "high",
      "value": 96.8,
      "reason": "Higher future fill directly raises overflow urgency."
    }
  ],
  "risk": {
    "bin_id": "BIN-001",
    "organisation_id": 2,
    "site_id": null,
    "zone_id": null,
    "current_fill": 81.4,
    "predicted_fill_6h": 96.8,
    "overflow_eta_hours": 4.2,
    "overflow_risk_probability": 0.91,
    "anomaly_score": 0.34,
    "anomaly_flags": ["DEVICE_HEALTH_RISK"],
    "contamination_risk_probability": 0.48,
    "contamination_reasons": ["Low classification confidence"],
    "recommended_action": "Dispatch urgent collection",
    "generated_at": "2026-03-19T09:00:00Z"
  }
}
```

### GET `/intelligence/contamination/cases`
**Purpose:** list contamination investigation cases.

### POST `/intelligence/contamination/cases`
**Purpose:** create a contamination case.

**JSON request**
```json
{
  "organisation_id": 2,
  "bin_id": "BIN-001",
  "source": "manual",
  "contamination_type": "mixed_waste",
  "severity": "high",
  "probability": 0.72,
  "status": "open",
  "notes": "Plastic contamination seen in paper stream",
  "evidence": {
    "photo_count": 2
  }
}
```

**Example response**
```json
{
  "id": 1,
  "organisation_id": 2,
  "site_id": null,
  "zone_id": null,
  "bin_id": "BIN-001",
  "source": "manual",
  "contamination_type": "mixed_waste",
  "severity": "high",
  "probability": 0.72,
  "status": "open",
  "notes": "Plastic contamination seen in paper stream",
  "evidence": {
    "photo_count": 2
  },
  "created_at": "2026-03-19T09:10:00Z",
  "updated_at": "2026-03-19T09:10:00Z",
  "resolved_at": null
}
```

### PATCH `/intelligence/contamination/cases/{case_id}`
**Purpose:** update contamination case status, severity, or notes.

### POST `/intelligence/monitoring/snapshots`
**Purpose:** ingest model monitoring metrics for dashboarding and drift visibility.

**JSON request**
```json
{
  "model_name": "fill_forecaster",
  "model_version": "rf-v1",
  "metric_name": "mae",
  "metric_value": 4.21,
  "window_label": "rolling_7d",
  "sample_size": 1240,
  "status": "ok",
  "meta": {
    "threshold_warning": 6.0,
    "threshold_critical": 8.0
  }
}
```

### GET `/intelligence/monitoring/summary`
**Purpose:** latest model monitoring metrics grouped by model + metric.

**Example response**
```json
{
  "model_name": "fill_forecaster",
  "days": 14,
  "metrics": [
    {
      "metric_name": "mae",
      "latest_value": 4.21,
      "status": "ok",
      "sample_size": 1240,
      "model_version": "rf-v1",
      "last_created_at": "2026-03-19T09:20:00Z"
    }
  ]
}
```


---

# RBAC Phase Addendum

This section extends the previous API reference. Existing APIs remain in place. The RBAC phase adds organisation-aware role enforcement on top of the current backend without removing previous endpoints.

## Supported organisation roles
- `owner`
- `admin`
- `manager`
- `operator`
- `viewer`
- `platform_admin` is the effective label used by the frontend when legacy `users.is_admin=true`.

## Updated `/users/me`

### GET `/api/v1/users/me`
Returns the authenticated user plus active organisation context and memberships.

Example response:
```json
{
  "id": 1,
  "email": "owner@example.com",
  "display_name": "Owner User",
  "is_active": true,
  "is_admin": false,
  "active_organisation_id": 2,
  "active_role": "owner",
  "memberships": [
    {
      "organisation_id": 2,
      "role": "owner",
      "is_default": true,
      "created_at": "2026-03-19T08:10:24+00:00"
    }
  ]
}
```

## RBAC-protected enterprise endpoints

### Organisations
- `GET /api/v1/enterprise/organisations` → all authenticated members can read their own organisations
- `POST /api/v1/enterprise/organisations` → platform admin only

### Sites
- `GET /api/v1/enterprise/sites?organisation_id=2` → viewer and above
- `POST /api/v1/enterprise/sites` → admin or owner

### Zones
- `GET /api/v1/enterprise/zones?site_id=1` → viewer and above
- `POST /api/v1/enterprise/zones` → admin or owner

### Memberships
- `GET /api/v1/enterprise/memberships?organisation_id=2` → admin or owner
- `POST /api/v1/enterprise/memberships` → admin or owner
  - owner assignment can only be done by an owner
  - admin cannot promote another member to owner

Example membership create payload:
```json
{
  "organisation_id": 2,
  "user_id": 7,
  "role": "manager",
  "is_default": false
}
```

### Devices
- `GET /api/v1/enterprise/devices?organisation_id=2` → viewer and above
- `POST /api/v1/enterprise/devices` → admin or owner
- `POST /api/v1/enterprise/devices/{device_id}/heartbeat` → operator and above

### Notifications and reports
- `GET /api/v1/enterprise/notification-channels?organisation_id=2` → admin or owner
- `POST /api/v1/enterprise/notification-channels` → admin or owner
- `GET /api/v1/enterprise/notification-events?organisation_id=2` → admin or owner
- `POST /api/v1/enterprise/notification-events` → admin or owner
- `GET /api/v1/enterprise/reports?organisation_id=2` → viewer and above
- `POST /api/v1/enterprise/reports` → manager, admin, owner

### Audit logs
- `GET /api/v1/enterprise/audit-logs?organisation_id=2` → manager, admin, owner

## RBAC-protected alerts and analytics

### Alerts
- `GET /api/v1/alerts?organisation_id=2` → viewer and above
- `GET /api/v1/alerts/latest?organisation_id=2` → viewer and above
- `GET /api/v1/alerts/summary?organisation_id=2` → viewer and above
- `PATCH /api/v1/alerts/{alert_id}` → admin or owner

### Analytics
- `GET /api/v1/analytics/overview?organisation_id=2` → manager, admin, owner
- `GET /api/v1/analytics/fill-trend?organisation_id=2&hours=24` → manager, admin, owner
- `GET /api/v1/analytics/class-distribution?organisation_id=2&hours=24` → manager, admin, owner

## RBAC-protected work orders

### Work order access model
- owner/admin/manager can create and manage work orders within their organisation
- operator can read only assigned work orders and update only assigned work orders
- viewer cannot modify work orders

### Endpoints
- `GET /api/v1/work-orders?organisation_id=2`
- `POST /api/v1/work-orders/from-alerts?organisation_id=2`
- `POST /api/v1/work-orders/from-latest-route?organisation_id=2`
- `PATCH /api/v1/work-orders/{work_order_id}`

Example operator-safe update payload:
```json
{
  "status": "completed",
  "resolution_notes": "Collection completed successfully"
}
```

## RBAC-protected intelligence endpoints

### Read access
- risk, anomalies, explainability → manager, admin, owner

### Write access
- contamination cases → manager, admin, owner
- model monitoring snapshots → owner or platform admin

Endpoints:
- `GET /api/v1/intelligence/risk/latest?organisation_id=2`
- `GET /api/v1/intelligence/anomalies?organisation_id=2`
- `GET /api/v1/intelligence/explain/bin/BIN-001?organisation_id=2`
- `GET /api/v1/intelligence/contamination/cases?organisation_id=2`
- `POST /api/v1/intelligence/contamination/cases`
- `PATCH /api/v1/intelligence/contamination/cases/{case_id}`
- `GET /api/v1/intelligence/monitoring/summary?organisation_id=2`
- `POST /api/v1/intelligence/monitoring/snapshots?organisation_id=2`

## Frontend role contract
The frontend should call `GET /api/v1/users/me` after login and drive route access, button visibility, and form availability from: `active_role`, `active_organisation_id`, and `memberships`.


## 4) User management and role assignment (Added)

### GET `/users/me`
Returns the authenticated user, active role, memberships, and assignments.

### GET `/users?organisation_id=1&role=viewer`
Lists users for admin/owner dashboards.

### POST `/users`
Create a user from the frontend and immediately assign a role.

```json
{
  "email": "viewer1@example.com",
  "password": "StrongPass123!",
  "display_name": "Viewer One",
  "organisation_id": 1,
  "role": "viewer",
  "is_default_membership": true,
  "site_ids": [1],
  "bin_ids": ["BIN-0001", "BIN-0002"]
}
```

### POST `/users/{user_id}/memberships`
Add another organisation membership to an existing user.

### POST `/users/{user_id}/assignments`
Replace site/bin assignments for an existing user.

```json
{
  "site_ids": [1, 2],
  "bin_ids": ["BIN-0001"],
  "replace_existing": true
}
```

### Updated `/auth/register` request body
Public registration still defaults to a safe viewer flow, but the schema now shows optional `role` and `organisation_id` fields for admin-assisted registration flows.
