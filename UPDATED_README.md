# Smart Waste Management DDSS

## Overview

This project is an end-to-end **Data-Driven Decision Support System (DDSS)** for smart waste management. It combines:

- waste image classification using deep learning
- smart-bin telemetry ingestion
- short-term fill-level forecasting
- priority-based decision support
- route optimisation for waste collection
- backend API integration for frontend dashboards and operations

The system turns raw image and telemetry inputs into operational outputs: **which bins are urgent, why they are urgent, which alerts are active, and how routes should be planned**.

A concise flow is:

**sense -> classify -> forecast -> rank -> alert -> route -> monitor**

---

## Core System Flow

1. **Register bins**
   - Each smart bin is stored with geolocation, postcode, and optional sector.

2. **Ingest telemetry**
   - Fill level, hours since last collection, and timestamps are stored.

3. **Classify waste images**
   - Waste images are uploaded and classified into one of six categories.

4. **Forecast future fill**
   - A Random Forest model predicts fill level 6 hours ahead.

5. **Run DDSS**
   - The system combines forecast, collection delay, and uncertainty into a priority score.

6. **Generate alerts**
   - Alert rules convert DDSS outputs into operational warnings and critical events.

7. **Plan routes**
   - Ranked bins are converted into optimized trips.

8. **Visualise operations**
   - Frontend dashboards use analytics, map, alerts, latest DDSS, and routing outputs.

---

## Main Functional Layers

### 1. Computer Vision Layer

This layer classifies waste images.

**Main deployed classifier**
- DenseNet121
- ImageNet pretrained backbone
- transfer learning + fine-tuning
- 6-class softmax output

**Predicted classes**
- cardboard
- glass
- metal
- paper
- plastic
- trash

**Inference pipeline**
1. user uploads an image
2. image is resized to `224 x 224`
3. pixel values are normalized
4. the classifier returns probabilities
5. top prediction and top-k classes are returned
6. if `bin_id` is supplied, the result can be stored in the database

---

### 2. Telemetry Layer

This layer stores operational smart-bin measurements.

**Key values**
- `fill_level`
- `last_collection_hours`
- `ts`
- `bin_id`

This supports:
- current operational state
- forecasting features
- dashboard metrics
- stale data checks
- route demand estimation

---

### 3. Forecasting Layer

This layer predicts future fill.

**Model**
- `RandomForestRegressor`

**Backend model file**
- `fill_forecast_rf.pkl`

**Prediction target**
- fill level in the next **6 hours**

**Typical features**
- `fill_level`
- `hour_of_day`
- `day`
- `weekend`
- `growth_rate`
- lag features
- rolling mean

**Practical value**
- moves routing from reactive collection to proactive collection
- identifies bins that are not critical now but will become critical soon

---

### 4. Decision Support Layer

This layer creates a ranked list of bins.

**Main DDSS inputs**
- predicted fill in 6 hours
- hours since last collection
- image classifier confidence
- uncertainty derived from confidence

**Uncertainty**
```text
uncertainty = 1 - confidence
```

**Priority score**
```text
priority_score =
    0.5 * predicted_fill_6h
  + 0.3 * last_collection_hours
  + 0.2 * uncertainty * 100
```

**Meaning**
- bins closer to full get higher urgency
- bins uncollected for longer get higher urgency
- uncertain classifications add caution weight

---

### 5. Alerts Layer

The alert layer makes DDSS results easier to interpret operationally.

**Alert types present in the codebase**
- `CRITICAL_FILL_PREDICTED`
- `OVERDUE_COLLECTION`
- `LOW_CLASSIFICATION_CONFIDENCE`
- `STALE_TELEMETRY`
- `NO_RECENT_CLASSIFICATION`
- `ROUTE_CAPACITY_RISK`

**Severity mapping**
- **critical**
  - `CRITICAL_FILL_PREDICTED`
  - `OVERDUE_COLLECTION`
  - `ROUTE_CAPACITY_RISK`
- **warning**
  - `LOW_CLASSIFICATION_CONFIDENCE`
  - `STALE_TELEMETRY`
  - `NO_RECENT_CLASSIFICATION`
- **info**
  - any future non-critical/non-warning type

**Current DDSS-generated alerts**
The active DDSS run currently creates these directly from ranking inputs:
- `CRITICAL_FILL_PREDICTED`
- `OVERDUE_COLLECTION`
- `LOW_CLASSIFICATION_CONFIDENCE`

**Alert lifecycle**
- newly active alert -> `open`
- acknowledged by operator -> `acknowledged`
- no longer active or manually resolved -> `resolved`

**Stored alert metadata**
Typical metadata saved with an alert includes:
- `priority_score`
- `predicted_fill_6h`
- `confidence`

This is useful for explainability and auditability.

---

### 6. Routing Layer

This layer turns ranked bins into actual collection trips.

**Supported route modes in the backend**
1. **Manual optimize**
   - client submits explicit points and route settings

2. **Plan from latest DDSS**
   - system reads latest DDSS-ranked bins and builds trips

3. **VRP plan**
   - system solves a vehicle-routing formulation using OR-Tools

**Current strategy values**
- `priority_only`
- `priority_distance`
- `vrp` (stored on VRP-generated route plans)

**Routing details**
- depot latitude / longitude are required
- vehicle capacity is required
- top-ranked bins can be limited with `top_n`
- total route distance and trips are returned
- each trip contains a stop list and trip distance
- VRP response may also include geometry in the response payload

---

### 7. Monitoring / Dashboard Layer

The backend exposes several operational dashboard endpoints:

- **ops summary** for top operational KPIs
- **alerts summary** and **latest alerts**
- **latest DDSS**
- **latest route**
- **route impact metrics**
- **analytics overview**
- **fill trend analytics**
- **class distribution analytics**
- **map bins view**

This is what makes the system a real DDSS rather than just an ML model API.

---

## Dataset

### Image Dataset Structure

The image dataset follows a TrashNet-style 6-class folder structure:

```text
data/
  images/
    cardboard/
    glass/
    metal/
    paper/
    plastic/
    trash/
```

### Approximate Dataset Counts

- cardboard: 403
- glass: 501
- metal: 410
- paper: 594
- plastic: 482
- trash: 137

**Total images: 2527**

### Important note
The forecasting pipeline is based on **simulated telemetry data**, not long-term real sensor telemetry. This is acceptable for academic prototyping, but production-grade forecasting should later be retrained on real sensor logs.

---

## Model Summary

### Image Classification Model
- DenseNet121
- transfer learning from ImageNet
- input shape `224 x 224 x 3`
- dropout regularisation
- softmax output over 6 classes

### Forecasting Model
- Random Forest Regressor
- predicts fill level 6 hours ahead
- uses engineered features from recent telemetry

### Model Artifacts Used by Backend
- `models/densenet121_final.keras`
- `models/fill_forecast_rf.pkl`

---

## Backend Architecture

### Main Technologies
- FastAPI
- PostgreSQL
- SQLAlchemy async
- asyncpg
- TensorFlow / Keras
- scikit-learn
- joblib
- OR-Tools
- JWT authentication
- Argon2 password hashing
- httpx

### API prefix
All mounted endpoints are served under:

```text
/api/v1
```

### App startup behavior
At startup the backend:
- verifies DB connectivity
- ensures DB sequence safety
- loads the image classifier model if the file exists
- loads the forecast model if the file exists

---

## Authentication and Access

### Auth style
The backend supports bearer-style JWT authentication and also sets a cookie on login.

**Token sources accepted by protected endpoints**
- `Authorization: Bearer <token>`
- OAuth2 bearer token
- access cookie using the configured cookie name

### Current protected endpoints
The following route groups currently use `get_current_user`:
- bins
- telemetry
- classify
- ddss run
- routing optimize / plan-latest
- alerts
- users `/me`

### Important note
Some dashboard-oriented endpoints in the current mounted code do **not** explicitly require auth in the route function:
- analytics
- map
- ops
- latest DDSS
- latest routing
- routing impact
- public stats
- health
- forecast

If this project is deployed publicly, these should be reviewed carefully behind proper access control.

---

## Current Config / Operational Thresholds

Based on backend settings:

- image size: `224`
- top-k output: `3`
- max upload size: `10 MB`
- truck capacity default: `300`
- critical fill threshold: `90`
- overdue collection threshold: `36 hours`
- low classification confidence threshold: `0.6`

**Priority weights**
- predicted fill: `0.5`
- last collection delay: `0.3`
- uncertainty: `0.2`

---

## Database Entities

Core entities in the backend include:

- `bins`
- `telemetry`
- `classifications`
- `decision_runs`
- `decision_items`
- `alerts`
- `route_plans`
- `route_trips`
- `users`
- password reset related records

### Entity meanings

**bins**
- master bin metadata
- location, postcode, sector, active flag

**telemetry**
- timestamped fill data and collection delay data

**classifications**
- stored image predictions per bin

**decision_runs**
- one DDSS execution session

**decision_items**
- one ranked output record per eligible bin in a run

**alerts**
- operational warnings / critical events with status

**route_plans**
- one route-planning execution result

**route_trips**
- trip-by-trip route outputs

**users**
- login and profile records

---

## Active Mounted API Groups

The backend currently mounts these functional groups:

- health
- public stats
- auth
- users
- bins
- telemetry
- classify
- forecast
- DDSS run
- latest DDSS
- routing optimize
- routing latest
- VRP routing
- route impact metrics
- alerts
- ops summary
- analytics
- map view

### Note on codebase vs mounted routes
There is also a `ddss.py` file in the route folder containing `/ddss/process-bin`, but in the current `main.py` this router is **not mounted**, so it is **not part of the live API unless you explicitly include it**.

---

## Alerts, Analytics, Map, and Ops Details

### Alerts
The alerts module supports:
- listing alerts with optional filters
- fetching latest alerts
- getting summary counts
- updating alert status to `acknowledged` or `resolved`

### Analytics
The analytics module currently provides:
- overview KPIs
- average fill trend over time
- class distribution for recent classification data

**Overview fields**
- average fill today
- max fill today
- critical alerts today
- total open alerts
- latest route distance
- top waste class today

### Map
The map endpoint merges:
- bin master data
- latest telemetry
- latest classification
- latest DDSS item
- latest route membership

**Map output per bin includes**
- current fill
- predicted fill in 6 hours
- last collection hours
- predicted class
- confidence
- priority score
- alerts
- computed status
- whether it appears in the latest route

**Current map statuses**
- `inactive`
- `critical`
- `warning`
- `healthy`

### Ops summary
The ops summary endpoint gives a single operational snapshot including:
- total bins
- active / inactive bins
- critical / warning / healthy bins
- stale bins
- open and critical alerts
- latest DDSS run id
- latest route plan id
- average current fill
- average predicted fill in 6 hours

---

## Route Impact Metrics

The routing impact endpoint derives extra metrics from the latest route plan.

**Returned metrics include**
- latest plan id
- total distance
- baseline distance
- saved distance
- saved percentage
- trip count
- total stops
- average stops per trip
- estimated duration
- estimated fuel usage
- estimated CO2
- capacity utilization

**Important modeling note**
The baseline distance is currently estimated using a simple heuristic:
- baseline assumed as **25% worse** than optimized distance

So these values are useful for demonstration and comparative analytics, but should not be presented as exact logistics audit values.

---

## End-to-End Example Workflow

A standard operational sequence is:

1. register a bin
2. submit telemetry for that bin
3. optionally classify an uploaded waste image for that bin
4. run DDSS
5. inspect alerts and latest ranked bins
6. generate route plan from latest DDSS
7. inspect map, analytics, ops summary, and route impact

---

## Strengths of the Project

1. Integrates ML, rules, routing, and dashboards into one system.
2. Goes beyond image classification by adding proactive forecasting.
3. Produces explainable urgency using scores and alerts.
4. Exposes clean operational APIs for frontend integration.
5. Demonstrates strong applied AI / smart-city value.

---

## Current Limitations / Honest Notes

1. Forecasting is trained on simulated telemetry.
2. The `trash` class remains the weakest class due to imbalance and visual diversity.
3. Some route groups in the currently mounted code do not enforce auth yet.
4. Route-impact baseline is heuristic, not a measured real-world baseline.
5. The unmounted `ddss/process-bin` file may confuse maintainers unless clearly labeled as legacy or experimental.
6. Documentation should stay synchronized with code when endpoints evolve.

---

## Suggested Dissertation Positioning

A strong and accurate description is:

> This project is an integrated smart waste management DDSS that combines DenseNet121-based waste image classification, Random Forest fill forecasting, weighted decision support, alert generation, and route optimisation into one backend-driven operational platform.

---

## Suggested Future Improvements

- retrain forecasting on real IoT telemetry
- expand underrepresented classes, especially `trash`
- add stricter role-based access control across all dashboard endpoints
- add model health and model version metadata endpoints
- add automated API and integration tests
- persist VRP route geometry if needed
- support richer alert rule expansion such as stale telemetry and no recent classification triggers inside DDSS execution
- add audit logs and monitoring dashboards
- integrate live IoT ingestion such as MQTT or embedded sensors

---

## Reproducibility / Project Structure

Suggested top-level structure:

```text
backend/
frontend/
models/
data/
notebooks/
README.md
requirements.txt
```

Recommended items to keep documented:
- exact dataset source
- train/validation split
- final model filenames
- API examples
- environment variables
- DB migration steps
- frontend environment configuration

---

## Final Summary

This project is not only a waste-classification backend. It is a broader **smart waste management decision platform** that combines:

- perception
- forecasting
- prioritisation
- alerting
- routing
- monitoring

That broader systems view is one of the strongest parts of the project.


---

## Phase 4 Completed — Operations Layer

The current backend now includes an operations-facing layer around the core DDSS pipeline:

- alert generation and alert status management
- work order creation from alerts
- work order creation from latest route plans
- operational summary endpoints
- latest route / latest DDSS retrieval for dashboard consumption
- analytics and routing impact endpoints

### Phase 4 entities already in the codebase

- `alerts`
- `work_orders`
- `decision_runs`
- `decision_items`
- `route_plans`
- `route_trips`

### Phase 4 delivery value

This layer upgrades the platform from a prediction-only backend to an operations-support backend by enabling:

- triage of urgent bins
- acknowledgement / resolution workflows
- task generation from decision outputs
- route execution planning support
- dashboard-ready operational state summaries

---

## Phase 5 — Enterprise Readiness Layer

To move the project closer to market level, the backend should now support multi-organisation deployment, team permissions, device fleet management, notification orchestration, and scheduled reporting.

The recommended Phase 5 backend modules are:

1. **Multi-tenant organisation model**
2. **Granular RBAC**
3. **Notification service skeleton**
4. **Device management**
5. **Scheduled reports and exports**
6. **Audit logging**

### Phase 5 data model added in the update bundle

#### Multi-tenant structure
- `organisations`
- `sites`
- `zones`
- `organisation_memberships`

#### Device fleet operations
- `devices`
- `device_heartbeats`

#### Notifications
- `notification_channels`
- `notification_events`

#### Reporting
- `scheduled_reports`

#### Auditability
- `audit_logs`

### Recommended RBAC roles

- `viewer`
- `operator`
- `manager`
- `owner`
- platform-level `is_admin`

### Example permission design

- viewers can read organisation data
- operators can read and send operational heartbeats
- managers can manage devices, sites, zones, notifications, and reports
- owners can additionally manage organisation memberships
- platform admins can manage everything across tenants

### New enterprise endpoints in the Phase 5 bundle

Under `/api/v1/enterprise`:

- `GET /organisations`
- `POST /organisations`
- `GET /sites`
- `POST /sites`
- `GET /zones`
- `POST /zones`
- `GET /memberships`
- `POST /memberships`
- `GET /devices`
- `POST /devices`
- `POST /devices/{device_id}/heartbeat`
- `GET /notification-channels`
- `POST /notification-channels`
- `GET /notification-events`
- `POST /notification-events`
- `GET /reports`
- `POST /reports`
- `GET /audit-logs`

### Why this matters commercially

This is the layer buyers usually care about most in a real deployment:

- managing multiple customer estates
- isolating one organisation from another
- proving who changed what and when
- tracking device health over time
- notifying real teams and escalation channels
- scheduling operational reporting for contracts and SLAs

---

## Important codebase issues found during deep review

### 1. `app/db/models.py` contains a broken `Organisation / Site / Zone` section

The current file mixes SQLAlchemy 2.0 typed models with legacy `Column(...)` usage but does not import `Column`. In its present state, that section is structurally inconsistent and should be replaced with a unified SQLAlchemy 2.0 style model definition.

### 2. Tenancy is not yet connected to existing core entities

The original `Bin`, `WorkOrder`, `Alert`, and route entities do not yet fully encode tenant ownership. For real production use, `organisation_id`, `site_id`, and `zone_id` should become first-class operational filters.

### 3. Auth is still mostly single-tenant

The existing login/auth flow supports authentication, but not tenant selection, tenant-scoped permission checks, or membership-aware role resolution.

### 4. Notifications are not yet operationally executable

Email/password reset email exists, but the platform does not yet have a dedicated notification orchestration layer for alerts, escalations, report delivery, or webhook fan-out.

### 5. Device fleet support is missing from the current production path

Your project already acts like an IoT operational platform, but there is no formal device registration / last-seen / heartbeat / battery / maintenance model in the original codebase.

### 6. Auditability is partial

The README mentions explainability and auditability, but there was no dedicated audit log table and no reusable audit service attached to mutating enterprise actions.

---

## Frontend deep-review findings

The frontend is already a strong dashboard shell, but for Phase 5 it still needs a business-operations layer.

### Frontend strengths already present

- clean dashboard routing structure
- central API helper (`lib/api.ts`)
- consistent React Query data fetching layer
- existing operational pages for alerts, analytics, bins, telemetry, routing, and DDSS outputs
- configurable API base and API key management in settings

### Frontend gaps for Phase 5

1. there is no tenant switcher or organisation context
2. there are no enterprise CRUD screens for sites / zones / memberships
3. there is no device fleet page
4. there is no notification channel management UI
5. there is no scheduled report UI
6. there is no audit log viewer
7. there are no hooks/types yet for enterprise endpoints
8. route/data access is not tenant-scoped in the UI layer yet

### Recommended next frontend sprint after backend Phase 5

1. organisation selector in top bar
2. enterprise admin pages:
   - organisations
   - sites
   - zones
   - memberships
3. fleet management page:
   - devices
   - heartbeat status
   - maintenance due
4. notification management page
5. reports scheduler page
6. audit log explorer page
7. RBAC-aware navigation hiding / showing

---

## Migration guidance for your dissertation-to-market transition

### Immediate technical priorities

1. replace the current broken org/site/zone model block
2. add enterprise tables via Alembic migration
3. backfill `organisation_id` / `site_id` / `zone_id` where possible
4. enforce tenant filters in all read/write routes
5. add audit log writes on every important mutation
6. start notification delivery with email first, then webhook, then SMS
7. add device heartbeat ingestion from real sensor agents or simulator jobs
8. add scheduled-report runner as a background job or external scheduler

### What not to over-invest in first

Do not spend the next sprint only on more sophisticated ML unless the market story requires it.

For a market-level platform, the missing value is primarily:

- tenancy
- permissions
- workflows
- audit trail
- notificationing
- fleet operations
- scheduled reporting
- deployment reliability

These usually matter more than a slightly more complex model.


---

## Phase 6 — Intelligence Expansion

Phase 6 extends the platform beyond operational workflows into higher-value intelligence features that buyers expect from a market-level system.

### New backend capabilities added in this phase

1. **Overflow ETA + risk probability**
   - composite risk scoring API for each active bin
   - includes `predicted_fill_6h`, `overflow_eta_hours`, and `overflow_risk_probability`
   - supports site and organisation level prioritisation

2. **Anomaly detection**
   - detects abnormal telemetry spikes, drops, stale readings, and device-health-linked sensing risk
   - returns explainable flags such as `SPIKE`, `DROP`, `STALE`, and `DEVICE_HEALTH_RISK`

3. **Contamination workflows**
   - dedicated `contamination_cases` table
   - create, list, and update contamination investigations
   - supports severity, probability, notes, evidence payload, and lifecycle states

4. **Explainability API**
   - human-readable reasons for why a bin is risky
   - returns contributing factors and recommended action text suitable for UI cards and reports

5. **Model monitoring dashboard support**
   - dedicated `model_metric_snapshots` table
   - stores MAE, drift, latency, precision-like metrics, window labels, status, and metadata
   - supports summarised monitoring views for the frontend

### New Phase 6 tables

- `contamination_cases`
- `model_metric_snapshots`

### New Phase 6 API group

All new intelligence routes are exposed under:

```text
/api/v1/intelligence
```

Main endpoints added:
- `/risk/latest`
- `/anomalies`
- `/explain/bin/{bin_id}`
- `/contamination/cases`
- `/monitoring/snapshots`
- `/monitoring/summary`

### Why this phase matters

This phase moves the platform from an operations dashboard toward a more complete intelligent operations product. It introduces:
- predictive risk scoring instead of simple thresholding only
- investigation workflows for contamination
- explainability for trust and operator confidence
- monitoring hooks for ML reliability over time

### Recommended next step after Phase 6

After integrating this phase, the next improvement should be full tenant-scoping of all legacy operational modules so that alerts, DDSS runs, routes, analytics, and work orders are organisation-aware end-to-end.


---

# RBAC Phase: Roles, Rights, and Expected Behaviour

This section extends the previous README. Existing phases and features remain in place. The RBAC phase does not remove previous code; it adds role-aware access control on top of the current application.

## Roles added

### Owner
Full organisation control.

Can:
- create and manage organisation structure
- create and manage sites and zones
- add and remove members
- assign any role including owner
- manage devices
- manage notification channels and events
- manage reports
- read audit logs
- manage work orders
- access all intelligence endpoints
- create model monitoring snapshots

Cannot:
- bypass platform-level restrictions unless also a legacy platform admin

### Admin
Almost full operational control inside an organisation.

Can:
- manage sites and zones
- manage members except promoting someone to owner
- assign admin, manager, operator, viewer
- manage devices
- manage notifications and reports
- read audit logs
- manage work orders
- read intelligence and analytics

Cannot:
- delete organisation
- promote another member to owner

### Manager
Operations management role.

Can:
- view dashboard and enterprise data
- view alerts
- read analytics and intelligence
- create and manage work orders
- manage reports
- read audit logs
- create and update contamination cases

Cannot:
- manage members
- change organisation structure deeply
- manage notification channels
- create devices or change device registry structure

### Operator
Field worker role.

Can:
- view dashboard and bin status
- view alerts
- view devices
- submit device heartbeats if needed
- read assigned work orders
- update only work orders assigned to them

Cannot:
- manage users
- create sites or zones
- manage reports
- access full analytics and intelligence dashboards
- update work orders assigned to other people

### Viewer
Read-only role.

Can:
- view dashboard
- view organisations, sites, zones, bins, devices
- view alerts
- view reports

Cannot:
- change anything
- manage members
- manage work orders
- access advanced analytics and intelligence

## How RBAC is used in the system
1. User logs in.
2. Frontend calls `/api/v1/users/me`.
3. Backend returns `active_organisation_id`, `active_role`, and `memberships`.
4. Frontend hides or shows pages and actions based on role.
5. Backend also enforces permissions, so hidden buttons are not the only protection.

## Main backend files updated for RBAC
- `app/api/deps.py`
- `app/api/routes/users.py`
- `app/api/routes/enterprise.py`
- `app/api/routes/alerts.py`
- `app/api/routes/analytics.py`
- `app/api/routes/work_orders.py`
- `app/api/routes/intelligence.py`
- `app/repositories/work_orders.py`
- `app/services/alerts.py`
- `app/services/analytics.py`
- `app/schemas/enterprise.py`
- `app/schemas/work_orders.py`

## Frontend files updated for RBAC
- `lib/types.ts`
- `lib/queries.ts`

## Important implementation note
This phase is additive. Previous APIs and earlier phases remain in place. The RBAC layer is designed to preserve your earlier project structure and add access control with the least disruption possible.


## Role and Access Update (Added)

This update adds structured user-management on top of the previous system without removing older endpoints.

### What was added
- role-aware user creation workflow
- `/users` admin/owner management endpoints
- membership assignment per organisation
- optional site and bin assignment storage
- viewer/operator bin scoping on `/bins` endpoints
- login redirect support for role-based frontend landing pages

### Important note for existing databases
Because `user_site_assignments` and `user_bin_assignments` tables were added, an existing database must be migrated or recreated before using the new assignment features.


## What changed

This update makes the system follow these rules:

### Global roles
- `owner` → full platform access
- `admin` → full platform operational access

Global users do **not** need an organisation membership.

### Scoped roles
- `manager` → organisation-scoped manager
- `operator` → assigned site/bin operational user
- `viewer` → read-only user

## New intended workflow

1. First registered user becomes global `owner`.
2. Owner/Admin can create organisations.
3. Owner/Admin can create Managers for a specific organisation.
4. Manager can create Sites and Zones only inside their own organisation.
5. Manager can create Operators/Viewers only inside their own organisation.
6. Manager can assign Operators/Viewers to specific sites/bins.
7. Bins must be linked to:
   - `organisation_id`
   - `site_id`
   - optional `zone_id`

## Role responsibilities

### Owner
- full platform access
- create organisations
- create global admins
- see all organisations and all data

### Admin
- full platform operational access
- create organisations
- create managers/operators/viewers
- manage enterprise structure

### Manager
- scoped to their organisation only
- create sites
- create zones
- create bins only within their organisation/site/zone
- create operators/viewers in their organisation
- assign sites/bins to operators/viewers
- run DDSS/routing within their own organisation scope

### Operator
- daily operational role
- see assigned sites/bins
- see important alerts
- see routing/DDSS results relevant to their scope
- update assigned work/tasks
- mark collection work complete

### Viewer
- read-only role
- see scoped dashboards, bins, alerts, analytics
- cannot create or modify enterprise data

## Backend files updated
- `app/api/deps.py`
- `app/api/routes/auth.py`
- `app/api/routes/bins.py`
- `app/api/routes/enterprise.py`
- `app/api/routes/users.py`
- `app/repositories/bins.py`
- `app/repositories/users.py`
- `app/schemas/common.py`
- `app/schemas/enterprise.py`
- `app/schemas/users.py`
- `app/db/models.py`

## Frontend files updated
- `lib/types.ts`
- `lib/queries.ts`
- `lib/rbac-context.tsx`
- `components/app-sidebar.tsx`
- `app/dashboard/users/page.tsx`
- `app/dashboard/bins/page.tsx`

## API behavior summary

### Create organisation
`POST /api/v1/enterprise/organisations`
- Owner/Admin allowed
- creator is attached to org as `owner`/`admin`

### Create site
`POST /api/v1/enterprise/sites`
- Owner/Admin/Manager allowed
- Manager can only create inside own organisation

### Create zone
`POST /api/v1/enterprise/zones`
- Owner/Admin/Manager allowed
- Manager can only create inside own organisation via site ownership

### Create user with access
`POST /api/v1/users`
- Owner can create global owner/admin and scoped users
- Admin can create global admin and scoped users
- Manager can create only `operator` or `viewer` in own organisation

### Create bin
`POST /api/v1/bins`
- Owner/Admin/Manager allowed
- requires `organisation_id`, `site_id`, optional `zone_id`
- validates site belongs to organisation
- validates zone belongs to site

## Recommended test flow

1. Register first owner
2. Create Hull / Leeds / Bradford organisations
3. Create Hull manager attached to Hull organisation
4. Login as Hull manager
5. Create Hull sites
6. Create Hull zones
7. Create Hull operators/viewers
8. Assign Hull operators to Hull sites/bins
9. Create Hull bins linked to Hull org/site/zone
10. Verify Hull manager does not manage Leeds/Bradford bins


## 2026-03-20 RBAC and UI update
- Owner: global strategic role; organisation create/delete/edit allowed.
- Admin: global operational role; organisation edit allowed, organisation delete not allowed.
- Manager: organisation-scoped role; can create sites, zones, users (manager/operator/viewer) inside own organisation and manage bins in own organisation.
- Operator/Viewer: site-scoped assignments; direct bin assignment removed from UI flow. Bins are inherited from assigned sites.
- Bin registry now stores optional `name` and supports edit/delete.
- Enterprise tables now support edit/delete actions for organisations, sites and zones subject to role permissions.
- Audit logs can be inspected in a details modal on the frontend.
