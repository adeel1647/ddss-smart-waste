# DDSS Smart Waste Management

## 1. Project Overview

DDSS Smart Waste Management is an end-to-end **Data-Driven Decision Support System (DDSS)** for smart waste operations. It combines:

- smart-bin telemetry ingestion
- waste image classification using a DenseNet-based computer vision model
- short-horizon fill forecasting using a Random Forest regressor
- DDSS scoring and prioritisation
- operational alerting
- route planning and VRP-style optimisation
- enterprise hierarchy management
- intelligence features such as anomaly surfacing, contamination workflows, and model monitoring
- role-aware frontend dashboards
- a demo-user mode for safe presentation of the full system

A simple system flow is:

**register bins → ingest telemetry → classify waste → forecast fill → run DDSS → generate alerts → plan routes → monitor operations**

---

## 2. High-Level Architecture

### 2.1 Backend
- **Framework:** FastAPI
- **ORM / DB:** SQLAlchemy async + PostgreSQL
- **Validation:** Pydantic
- **Auth:** JWT / bearer token, with frontend support for token storage and session lookup
- **Routing / Optimisation:** custom route planners plus VRP/OR-Tools style planning logic
- **ML inference:** TensorFlow/Keras classifier + scikit-learn forecasting model
- **Async workers:** notification and report worker entrypoints exist for queued processing

### 2.2 Frontend
- **Framework:** Next.js App Router
- **Language:** TypeScript
- **Data layer:** React Query
- **UI:** Tailwind CSS + shadcn/ui + lucide-react
- **RBAC:** frontend role-aware page gating with additional demo-user restrictions
- **Dashboard structure:** sidebar + top bar + page-level role-aware actions

### 2.3 Functional Layers
1. **Enterprise Layer** — organisations, sites, zones, memberships, devices, reports, notifications, audit logs
2. **Operational Layer** — bins, telemetry, classifications, alerts, work orders
3. **Decision Layer** — DDSS runs and ranked decision items
4. **Routing Layer** — latest route plans, route metrics, optimise routes, VRP planning
5. **Intelligence Layer** — risk scoring, anomalies, explainability, contamination cases, model monitoring
6. **Presentation Layer** — frontend dashboards for enterprise, operations, analytics, intelligence, and admin workflows

---

## 3. Core Data Hierarchy

The project uses a layered physical hierarchy:

**Organisation → Site → Zone → Bin**

Supporting structures include:

- **Users** with either platform-level role or organisation-scoped memberships
- **UserSiteAssignment** and **UserBinAssignment** for scoped operational access
- **Devices** attachable to organisation, site, zone, or bin contexts
- **Telemetry / Classification / Alerts / Work Orders** linked to bins
- **Decision runs** and **route plans** linked to organisation-level operations

---

## 4. Current Model Inventory

The current uploaded backend contains **26 SQLAlchemy model classes** in `app/db/models.py`.

| Model | Purpose |
|---|---|
| `Organisation` | Top-level client/council entity |
| `Site` | Addressed operational site inside an organisation |
| `Zone` | Lower-level grouping inside a site |
| `Bin` | Physical smart-bin registry record |
| `Telemetry` | Fill-level and collection-delay time series |
| `Classification` | Image classification result per uploaded sample/bin |
| `DecisionRun` | A DDSS run event |
| `DecisionItem` | Ranked DDSS output per bin |
| `RoutePlan` | Stored route plan metadata |
| `RouteTrip` | Individual trip inside a route plan |
| `User` | Account, credentials, platform role, and active status |
| `OrganisationMembership` | Organisation-scoped user role |
| `UserSiteAssignment` | Site-level user scope |
| `UserBinAssignment` | Bin-level direct user scope |
| `PasswordResetCode` | Password reset lifecycle support |
| `Alert` | Operational alert linked to a bin and possibly a DDSS run |
| `WorkOrder` | Action/task generated from operations or routing context |
| `Device` | Device registry record |
| `DeviceHeartbeat` | Device health / heartbeat submissions |
| `NotificationChannel` | Notification destination configuration |
| `NotificationEvent` | Individual queued/sent notification item |
| `ScheduledReport` | Saved recurring report definition |
| `AuditLog` | Audit trail of important business actions |
| `ContaminationCase` | Contamination issue/investigation record |
| `ModelMetricSnapshot` | Stored model monitoring metric snapshot |
| `Base` | Declarative base |

---

## 5. Machine Learning Components

### 5.1 Waste Image Classification
The backend loads a classification model via `ClassifierService` and `ModelStore`.

**Current deployed class names:**
- cardboard
- glass
- metal
- paper
- plastic
- trash

**Inference behavior:**
- input image is processed
- top prediction and top-k probabilities are returned
- optional bin-linked persistence is supported
- frontend classify page is intentionally left writable for the demo user so the model can be tested live

**Referenced training/evaluation assets from earlier project files:**
- `notebooks/train_densenet.ipynb`
- `notebooks/evaluation.ipynb`
- `models/densenet121_final.keras`
- `models/densenet121_final.h5`
- `models/densenet121_regularized.h5`

### 5.2 Fill Forecasting
The backend loads a forecasting model via `ForecastService` and `ModelStore`.

**Current artifact path referenced in code/docs:**
- `fill_forecast_rf.pkl`

**Typical deployed feature pattern described in project files:**
- current fill level
- hour of day
- day / weekend signal
- growth rate
- lag features
- rolling mean features

**Forecast horizon used by the project:**
- short-term prediction focused on the next **6 hours**

### 5.3 Model Loading on Startup
At application startup:
- database initialisation runs
- demo user is ensured
- bin sequence is ensured
- classifier model path is checked and loaded into `ModelStore`
- forecast model path is checked and loaded into `ModelStore`

---

## 6. Address-First UK Geocoding Workflow

One of the major backend updates is the move from manual coordinate entry toward an **address-first UK workflow**.

### 6.1 Why this matters
Users should not need to manually enter raw latitude/longitude for common site/bin workflows. Instead, they can submit:
- postcode
- address text
- selected geocode place id
- resolved address components

The backend still stores **resolved `lat` / `lon` internally** because routing, maps, and spatial logic still need coordinates.

### 6.2 Current geocoding support
Routes under `/geo` provide:
- address search
- postcode lookup
- direct resolution of address input into normalized address + coordinates

### 6.3 Address-first adoption
This workflow is used across:
- bins
- enterprise sites
- routing depot input

### 6.4 Stored location fields
The project now supports richer address metadata such as:
- postcode
- address_line_1
- address_line_2
- city
- county
- country
- formatted_address
- geocode_place_id
- geocode_source
- geocode_confidence
- lat / lon

---

## 7. Site Boundary Support

The current codebase also includes **site boundary polygon support**, which is not consistently described in the older READMEs.

### 7.1 Backend support
- `Site.boundary_geojson` exists in the data model
- enterprise schemas validate that the boundary is a valid **GeoJSON Polygon**
- helper functions exist for point-in-polygon checks

### 7.2 Frontend support
The enterprise page includes a **Site Boundary** UI with a map-based component:
- `components/site-boundary-map.tsx`
- create/edit site forms allow an optional polygon boundary

This is important because it improves:
- site-level operational grouping
- map clarity
- future geofencing or automatic site association logic

---

## 8. DDSS Logic

The DDSS engine is centered around `POST /ddss/run` and related latest-result views.

### 8.1 Current production flow
1. fetch active bins, optionally filtered
2. fetch latest telemetry
3. fetch latest classifications
4. fetch lag telemetry where needed
5. generate forecasted fill values
6. compute urgency / service-window / confidence-aware prioritisation
7. persist DDSS run and decision items
8. generate alerts
9. expose latest results to dashboards and downstream routing

### 8.2 Priority concept
The project documentation describes the score as a blended function of:
- predicted fill urgency
- overdue collection/service pressure
- uncertainty / confidence penalty

This is stronger than a simple static threshold system because it ranks operational urgency rather than only detecting overflow.

---

## 9. Routing Logic

The codebase contains:
- explicit route optimisation endpoints
- latest-DDSS route planning endpoints
- VRP-style planning support
- route metrics / impact support

### 9.1 Current routing capabilities
- optimise supplied route input directly
- generate a route plan from latest DDSS results
- generate a VRP route plan from latest DDSS results
- fetch latest stored route plan
- fetch latest route impact metrics

### 9.2 Why routing still needs coordinates
Even after the address-first UX shift, the routing layer still depends on:
- depot coordinates
- bin coordinates
- distance calculations
- route geometry / map rendering

So the documentation should continue to explain that the system is **address-first for users**, but still **coordinate-backed internally**.

---

## 10. Alerts, Operations, and Work Orders

### 10.1 Alerts
Alerts represent operational issues tied to bins and DDSS state.

Typical alert attributes:
- alert type
- severity
- status (`open`, `acknowledged`, `resolved`)
- message
- bin linkage
- timestamps

### 10.2 Ops / dashboard summaries
Operational summaries aggregate:
- total bins
- stale telemetry
- critical bins
- alert counts
- latest DDSS run info
- latest route info

### 10.3 Work orders
Work orders provide an action layer for operational teams and can be connected to:
- alerts
- route planning
- bin-specific intervention tasks

---

## 11. Intelligence Layer

The intelligence layer is one of the most important evolved areas of the project.

### 11.1 Risk scoring
The backend exposes latest intelligence risk outputs through:
- `/intelligence/risk/latest`

These are built using the forecasting model plus telemetry/classification context.

### 11.2 Anomaly detection
The backend exposes:
- `/intelligence/anomalies`

The current implementation uses recent telemetry history and related heuristics to surface unusual behavior.

### 11.3 Explainability
The backend exposes:
- `/intelligence/explain/bin/{bin_id}`

This supports per-bin reasoning views in the frontend intelligence dashboard.

### 11.4 Contamination workflows
The backend exposes:
- list contamination cases
- create contamination case
- update contamination case

These are surfaced in the contamination page and are role-restricted for demo users.

### 11.5 Model monitoring
The backend exposes:
- snapshot creation endpoint
- monitoring summary endpoint

The project now supports:
- stored monitoring snapshots
- monitoring summary generation
- model name / version metadata in monitoring payloads

---

## 12. Analytics Layer

The analytics page and related backend services provide:
- overview KPIs
- fill trend time-series
- waste class distribution

These are separate from the intelligence layer:
- **analytics** focuses on current/aggregate operational metrics
- **intelligence** focuses on risk, anomalies, explainability, contamination, and model monitoring

---

## 13. Enterprise Layer

The enterprise layer now includes more than just organisations/sites/zones.

### 13.1 Core enterprise entities
- organisations
- sites
- zones
- memberships
- users and user role assignment
- devices and device heartbeats
- notification channels
- notification events
- scheduled reports
- audit logs

### 13.2 Audit logging
The current code uses an audit service to log important mutations, especially inside enterprise and intelligence mutations.

This is important for:
- traceability
- explainability of administrative changes
- future compliance/reporting needs

---

## 14. Notification and Report System

This area has evolved beyond simple CRUD models.

### 14.1 What the notification panel represents
- **Channels** = where notifications should go
- **Events** = what happened
- **Reports** = what recurring outputs should be generated

### 14.2 Current backend entities
- `NotificationChannel`
- `NotificationEvent`
- `ScheduledReport`

### 14.3 New backend service additions in current code
The current uploaded code contains:
- `app/services/notifiers.py`
- `app/services/notifications_dispatcher.py`
- `app/services/reports_scheduler.py`
- `app/workers/notification_worker.py`
- `app/workers/report_worker.py`

This means the documentation should now reflect that the project has:
- placeholder notifier implementations for email/SMS/webhook/in-app
- a queued notification dispatch flow
- a report scheduler that can create `report.ready` notification events
- manual worker entrypoints for event/report processing

### 14.4 Current limitation
These notifier implementations are still **simulation/placeholder-style integrations**, not full production-grade provider integrations. The documentation should explain that:
- the architecture for dispatch exists
- real provider integration can be added later
- worker execution can be manual, scheduled, or moved to a queue system later

---

## 15. Authentication, RBAC, and Demo User

### 15.1 Auth model
The project supports:
- bearer token login
- frontend token storage
- current-user session lookup
- password reset code workflow

### 15.2 Role model
The backend uses a mixture of:
- platform-level roles
- organisation-scoped memberships

Typical organisation roles:
- viewer
- operator
- manager
- admin
- owner

### 15.3 Demo user mode
A major recent addition is a **safe demo user flow**.

**Current demo credentials:**
- Email: `demo@ddss.com`
- Password: `Demo123.`
- Display name: `Demo User`

### 15.4 How demo user is created
The current backend startup uses:
- `app/services/demo_user.py`
- startup hook in `app/main.py`

If the user does not exist and at least one organisation exists, the backend automatically ensures a demo user with a default membership.

### 15.5 Demo user permission behavior
The current code explicitly grants the demo user:
- broad **read access across the app**
- **classify read/write**
- no broad mutating access for sensitive operational features

This is implemented in `app/api/deps.py` via:
- `DEMO_USER_EMAIL`
- `DEMO_ALLOWED_PERMISSIONS`
- `is_demo_user(...)`
- `user_has_permission(...)`

### 15.6 Demo user frontend behavior
The frontend now includes:
- pre-filled demo login credentials on the login page
- “Continue as Demo User” behavior
- full sidebar visibility for exploration
- demo-user restrictions to hide or disable write actions on sensitive pages

### 15.7 Demo user page restrictions
The code now restricts or hides mutating actions for the demo user on pages such as:
- dashboard DDSS run actions
- DDSS page execution
- routing plan execution
- alerts write/update actions
- contamination writes/updates
- telemetry ingest
- bins management
- notifications/report creation

The classify page remains available for active testing of the model.

---

## 16. Frontend Dashboard Pages (Current Uploaded Code)

The current frontend contains the following dashboard pages:

- `app/dashboard/alerts/page.tsx`
- `app/dashboard/analytics/page.tsx`
- `app/dashboard/audit/page.tsx`
- `app/dashboard/bins/page.tsx`
- `app/dashboard/classify/page.tsx`
- `app/dashboard/ddss/page.tsx`
- `app/dashboard/devices/page.tsx`
- `app/dashboard/enterprise/page.tsx`
- `app/dashboard/intelligence/anomalies/page.tsx`
- `app/dashboard/intelligence/contamination/page.tsx`
- `app/dashboard/intelligence/monitoring/page.tsx`
- `app/dashboard/intelligence/page.tsx`
- `app/dashboard/map/page.tsx`
- `app/dashboard/notifications/page.tsx`
- `app/dashboard/page.tsx`
- `app/dashboard/routing/page.tsx`
- `app/dashboard/settings/page.tsx`
- `app/dashboard/telemetry/page.tsx`
- `app/dashboard/users/page.tsx`


This confirms the frontend now goes well beyond the earliest simplified dashboard and includes:
- enterprise management
- user management
- notifications/report management
- devices
- audit log viewing
- dedicated intelligence sub-pages
- demo-aware login and access behavior

---

## 17. Frontend-Side Implementation Notes That Should Be Documented

Several older README statements are now outdated and should be updated.

### 17.1 Login is no longer purely client-side demo only
The older frontend README says the login page has “No API call -- purely client-side for demo purposes”.

That is no longer accurate. The current login page:
- calls the real backend login mutation
- stores the token
- fetches `/users/me`
- supports both demo login and normal login

### 17.2 Frontend now includes stronger RBAC
The project now contains:
- `lib/rbac-context.tsx`
- `components/rbac-gate.tsx`
- demo-aware restrictions
- page-level control over mutating UI

### 17.3 React Query integration is broader than older docs suggest
The current frontend uses React Query wrappers in `lib/queries.ts` for a broad set of:
- enterprise
- notifications
- intelligence
- analytics
- auth
- device
- user
- routing
- DDSS
- contamination
- monitoring
- and other operational endpoints

---

## 18. Current Backend Route Inventory

The current uploaded backend contains **82 route handlers** across the route modules below.

### alerts
- `GET /alerts`
- `GET /alerts/latest`
- `GET /alerts/summary`
- `PATCH /alerts/{alert_id}`

### analytics
- `GET /analytics/overview`
- `GET /analytics/fill-trend`
- `GET /analytics/class-distribution`

### auth
- `GET /auth/session`
- `POST /auth/login`
- `POST /auth/register`
- `POST /auth/forgot-password/request-code`
- `POST /auth/forgot-password/verify-code`
- `POST /auth/forgot-password/reset`
- `POST /auth/logout`

### bins
- `POST /bins`
- `GET /bins`
- `GET /bins/{bin_id}`
- `PATCH /bins/{bin_id}`
- `DELETE /bins/{bin_id}`

### classify
- `POST /classify`

### ddss
- `POST /ddss/process-bin`

### ddss_latest
- `GET /ddss/latest`

### ddss_run
- `POST /ddss/run`

### enterprise
- `GET /enterprise/organisations`
- `POST /enterprise/organisations`
- `GET /enterprise/sites`
- `POST /enterprise/sites`
- `GET /enterprise/zones`
- `POST /enterprise/zones`
- `PATCH /enterprise/organisations/{organisation_id}`
- `DELETE /enterprise/organisations/{organisation_id}`
- `PATCH /enterprise/sites/{site_id}`
- `DELETE /enterprise/sites/{site_id}`
- `PATCH /enterprise/zones/{zone_id}`
- `DELETE /enterprise/zones/{zone_id}`
- `GET /enterprise/memberships`
- `POST /enterprise/memberships`
- `GET /enterprise/devices`
- `POST /enterprise/devices`
- `POST /enterprise/devices/{device_id}/heartbeat`
- `GET /enterprise/notification-channels`
- `POST /enterprise/notification-channels`
- `GET /enterprise/notification-events`
- `POST /enterprise/notification-events`
- `GET /enterprise/reports`
- `POST /enterprise/reports`
- `GET /enterprise/audit-logs`

### forecast
- `POST /forecast`

### geo
- `GET /geo/search`
- `GET /geo/postcode/{postcode}`
- `POST /geo/resolve`

### health
- `GET /health`
- `GET /health/models`

### intelligence
- `GET /intelligence/risk/latest`
- `GET /intelligence/anomalies`
- `GET /intelligence/explain/bin/{bin_id}`
- `GET /intelligence/contamination/cases`
- `POST /intelligence/contamination/cases`
- `PATCH /intelligence/contamination/cases/{case_id}`
- `POST /intelligence/monitoring/snapshots`
- `GET /intelligence/monitoring/summary`

### map
- `GET /map/bins`

### ops
- `GET /ops/summary`

### public
- `GET /public/stats`

### routing
- `POST /routing/optimize`
- `POST /routing/plan-latest`

### routing_latest
- `GET /routing/latest`

### routing_metrics
- `GET /routing/impact/latest`

### routing_vrp
- `POST /routing/plan-latest-vrp`

### telemetry
- `POST /bins/{bin_id}/telemetry`
- `GET /bins/{bin_id}/telemetry/latest`

### users
- `GET /users/me`
- `PATCH /users/me`
- `GET /users`
- `POST /users`
- `DELETE /users/{user_id}`
- `POST /users/{user_id}/memberships`
- `POST /users/{user_id}/assignments`

### work_orders
- `GET /work-orders`
- `POST /work-orders/from-alerts`
- `POST /work-orders/from-latest-route`
- `PATCH /work-orders/{work_order_id}`

---

## 19. API Reference Corrections and Additions Required

The existing `DDSS_Backend_API_Reference_Updated.json` is valuable, but it is not fully aligned with the current code. It should be **updated, not replaced**.

### 19.1 Prefix corrections required
Several enterprise and intelligence endpoints in the JSON are documented without their full route prefixes.

Examples of paths that should be corrected:

| Current JSON style | Actual current route |
|---|---|
| `/organisations` | `/enterprise/organisations` |
| `/sites` | `/enterprise/sites` |
| `/zones` | `/enterprise/zones` |
| `/devices` | `/enterprise/devices` |
| `/notification-channels` | `/enterprise/notification-channels` |
| `/notification-events` | `/enterprise/notification-events` |
| `/reports` | `/enterprise/reports` |
| `/audit-logs` | `/enterprise/audit-logs` |
| `/memberships` | `/enterprise/memberships` |
| `/risk/latest` | `/intelligence/risk/latest` |
| `/anomalies` | `/intelligence/anomalies` |
| `/explain/bin/{bin_id}` | `/intelligence/explain/bin/{bin_id}` |
| `/contamination/cases` | `/intelligence/contamination/cases` |
| `/monitoring/snapshots` | `/intelligence/monitoring/snapshots` |
| `/monitoring/summary` | `/intelligence/monitoring/summary` |
| `/impact/latest` | `/routing/impact/latest` |

### 19.2 Newer implementation details that should be added to the API reference notes
Add notes covering:
- demo user creation and permission behavior
- startup model loading and model readiness checks
- telemetry write permission enforcement
- placeholder notification dispatch + report scheduler services
- worker entrypoints for notifications and reports
- site boundary GeoJSON support in enterprise sites
- frontend demo login now uses real backend auth, not fake local-only auth
- model monitoring includes snapshot and summary routes under `/intelligence/monitoring/...`

### 19.3 Frontend/UX notes worth adding to the API companion
Add practical notes such as:
- demo user can explore the full app but is blocked from sensitive POST/PATCH/DELETE operations
- classify remains writable for demo/testing
- enterprise and intelligence pages now have broader coverage than earlier docs
- notification management UI now exists, but real provider delivery is still placeholder-based unless workers/providers are configured

---

## 20. Recommended Single-File Documentation Strategy

To avoid maintaining multiple overlapping files, use this merged document as the new primary project file.

Recommended approach:
1. keep this file as the **main project README / technical companion**
2. keep the JSON API reference for structured endpoint lookup
3. update the JSON paths and notes rather than deleting it
4. treat the older README files as historical drafts that fed into this merged version

---

## 21. Practical “What Has Been Done in This Project” Summary

This project now includes, in one integrated stack:

- enterprise hierarchy management (organisation, site, zone, bin)
- address-first UK geocoding for bins, sites, and depot input
- optional site boundary polygons
- telemetry ingestion and latest telemetry retrieval
- image classification with stored model loading
- fill forecasting with stored model loading
- DDSS ranking and latest-run retrieval
- alert generation and status workflows
- routing optimisation, latest planning, and route impact metrics
- analytics dashboards
- intelligence risk scoring
- anomaly surfacing
- contamination case workflows
- explainability endpoints
- model monitoring snapshots and summaries
- device registry and heartbeat endpoints
- audit logging
- notification channels/events/report scheduling
- worker-based notification/report processing scaffolding
- frontend dashboards for enterprise, operations, analytics, routing, and intelligence
- RBAC-aware user experience
- safe demo-user mode with one-click-style demo login behavior

---

## 22. Suggested Next Documentation Step

If you also want the structured API reference file updated, the safest workflow is:

1. keep `DDSS_Backend_API_Reference_Updated.json`
2. correct the route prefixes listed above
3. add a “Current Code Additions” note block for:
   - demo user
   - notification/report workers
   - site boundaries
   - intelligence monitoring summary/snapshot paths
   - frontend demo restrictions
4. optionally regenerate endpoint examples using the current schemas

---

## 23. Closing Note

This merged file is intended to help a professor, collaborator, supervisor, or friend quickly understand:

- what the system does
- how the architecture is structured
- what models and APIs exist
- what has been added recently
- how demo mode works
- which documentation areas needed correction as the app evolved

It is specifically written to **preserve and extend** the previous documentation rather than replace it with a shorter or simpler summary.
