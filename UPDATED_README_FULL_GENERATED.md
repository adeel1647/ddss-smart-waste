# DDSS Smart Waste Management — Updated Project README
## 1. Executive Overview
DDSS Smart Waste Management is an end-to-end smart waste operations platform that combines IoT telemetry, deep-learning image classification, short-horizon fill forecasting, decision support, alerting, route planning, enterprise management, and role-based dashboards. The codebase contains both a FastAPI backend and a Next.js frontend. The operational loop implemented in the project is: **register bins → ingest telemetry → classify waste → forecast future fill → run DDSS → generate alerts → plan routes → dispatch work → monitor outcomes**.
The uploaded source includes **26 SQLAlchemy models**, **75 API endpoints**, **19 dashboard pages**, ML notebooks, pretrained model artifacts, Alembic migrations, and basic automated tests.
## 2. Technology Stack
- **Backend:** FastAPI, SQLAlchemy async ORM, PostgreSQL, Alembic, Pydantic, jose JWT, OR-Tools, scikit-learn, TensorFlow/Keras.
- **Frontend:** Next.js App Router, TypeScript, React Query, Tailwind/shadcn UI, lucide-react icons.
- **ML artifacts:** `models/densenet121_final.keras`, `models/densenet121_final.h5`, `models/densenet121_regularized.h5`, `models/fill_forecast_rf.pkl`.
- **DevOps:** Dockerfile, docker-compose, `.env` / `.env.example`, pytest, notebooks for experimentation and integration.
## 3. System Architecture
### 3.1 Functional Layers
1. **Enterprise layer** — organisations, sites, zones, memberships, devices, notification channels, scheduled reports, audit logs.
2. **Operational layer** — bins, telemetry, classifications, alerts, work orders.
3. **Decision layer** — DDSS run generation, decision items, latest rankings.
4. **Routing layer** — heuristic routing plus VRP route planning.
5. **Intelligence layer** — risk scores, anomalies, contamination cases, model monitoring.
6. **Presentation layer** — role-aware Next.js dashboards for owner/admin/manager/operator/viewer.
### 3.2 Data Hierarchy
**Organisation → Site → Zone → Bin** is the main physical hierarchy. Devices can also be linked at organisation/site/zone/bin level. Users are either platform-level (`platform_role`) or organisation-scoped through memberships and site assignments.
## 4. Data & Model Inventory
| Model | Purpose |
|---|---|
| `Organisation` | Top-level client / council entity with slug, active flag, sites, memberships, devices, reports, and audit logs. |
| `Site` | Sub-area within an organisation; stores code, address, map coordinates, and owns zones/bins/devices. |
| `Zone` | Sub-division inside a site; used for service-level grouping and finer operational scope. |
| `Bin` | Physical smart bin registry record; stores organisation/site/zone linkage, name, postcode/sector, coordinates, active flag, and collection schedule. |
| `Telemetry` | Time-series operational readings: fill level and hours since last collection. |
| `Classification` | Image classifier outputs per bin with predicted class and confidence. |
| `DecisionRun` | A DDSS execution event timestamped and optionally filtered by postcode. |
| `DecisionItem` | Per-bin DDSS outcome including confidence, uncertainty, predicted fill, service delay, and priority score. |
| `RoutePlan` | Stored route plan metadata with strategy, capacity, depot, and total distance. |
| `RouteTrip` | Trip-level route result with serialized stop list and trip distance. |
| `User` | Authenticated account with email, password hash, display name, active flag, admin flag, and platform_role. |
| `OrganisationMembership` | Organisation-scoped role assignment for a user. |
| `UserSiteAssignment` | Site-level access control used especially for operator/viewer scoping. |
| `UserBinAssignment` | Direct bin-level assignment table (present in schema, though current UX prefers site-level assignment). |
| `PasswordResetCode` | Email reset code lifecycle storage. |
| `Alert` | Operational alert record linked to a bin and optionally a DDSS run. |
| `WorkOrder` | Actionable task linked to a bin and optionally an alert/route plan. |
| `Device` | Sensor/edge device registry record. |
| `DeviceHeartbeat` | Heartbeat / health payload from a registered device. |
| `NotificationChannel` | Configured outbound alert/report channel. |
| `NotificationEvent` | Individual event queued/sent through a channel. |
| `ScheduledReport` | Recurring report schedule definition. |
| `AuditLog` | Immutable business action log for enterprise actions. |
| `ContaminationCase` | Intelligence/field issue record for contamination incidents. |
| `ModelMetricSnapshot` | Monitoring snapshot for deployed model metrics. |

## 5. Machine Learning Components
### 5.1 Waste Classification Model
- **Architecture:** DenseNet121 transfer learning model.
- **Input:** RGB image resized to `224x224`.
- **Output classes:** cardboard, glass, metal, paper, plastic, trash.
- **Training notebook:** `notebooks/train_densenet.ipynb`.
- **Evaluation notebook:** `notebooks/evaluation.ipynb`.
- **Saved artifacts:** `densenet121_final.keras`, `densenet121_final.h5`, `densenet121_regularized.h5`, `densenet121_finetuned.h5`.
**Observed training/evaluation facts from notebooks:**
- Dataset loader found **2527 images across 6 classes**.
- Train/validation split observed in notebook: **2024 train / 503 validation**.
- Validation accuracy reported in evaluation notebook: **0.83** on 503 validation images.
- Classification report excerpt from notebook: cardboard F1 **0.86**, glass **0.81**, metal **0.87**, paper **0.91**, plastic **0.76**, trash **0.66**; weighted average F1 **0.83**.
### 5.2 Fill Forecasting Model
- **Model type:** `RandomForestRegressor`.
- **Notebook:** `notebooks/predictive_model.ipynb`.
- **Artifact:** `models/fill_forecast_rf.pkl`.
- **Feature set used in code:** `fill_level`, `hour_of_day`, `day`, `weekend`, `growth_rate`, `lag_1`, `lag_2`, `lag_3`, `rolling_mean_3`.
- **Forecast horizon:** 6 hours ahead.
**Observed notebook results:**
- Train size: **2544**, test size: **636**.
- Random Forest MAE: **3.878**.
- Random Forest R²: **0.791**.
- Gradient Boosting MAE/R²: **4.530 / 0.758**.
- Naive baseline MAE/R²: **11.144 / 0.137**.
This justifies the Random Forest choice in the deployed forecaster.
### 5.3 Integration Notebooks
The integration notebooks demonstrate the full smart-bin pipeline by loading both models, simulating IoT inputs, generating DDSS rankings, and comparing route planning methods. Notable notebook outputs include:
- `integration.ipynb`: full smart bin report generation and coordinate assignment.
- `integration_test.ipynb`: routing comparison where **priority+distance (13.34 km)** improves on **priority-only (18.99 km)**, saving **5.65 km** in the sample run.
## 6. DDSS Logic
The production DDSS route is `/ddss/run` in `app/api/routes/ddss_run.py`. The flow is: 
1. fetch active bins (optionally by postcode/sector, limited by `limit`)
2. fetch latest telemetry and latest classifications
3. fetch recent lag telemetry for forecasting features
4. predict fill 6h ahead via `ForecastService`
5. evaluate service interval status via `evaluate_service_window()`
6. compute normalized priority via `compute_priority_score()`
7. generate DDSS decision items and alerts
8. persist run + items and return ranked bins
**Current priority function from `app/services/priority.py`:**
```text
fill_score       = predicted_fill_6h / 100
overdue_score    = due_ratio versus collection_interval_days
uncertainty      = 1 - confidence
priority_score   = (0.55 * fill_score + 0.30 * overdue_score + 0.15 * uncertainty) * 100
```
This is stronger than a simple overflow-only ranking because it blends predicted urgency, service delay, and uncertainty.
## 7. Routing Logic
The backend exposes three routing modes:
- `/routing/optimize` — optimize an explicit set of input points using `priority_only` or `priority_distance`.
- `/routing/plan-latest` — create a plan directly from the latest DDSS run.
- `/routing/plan-latest-vrp` — build a VRP plan using OR-Tools with vehicle capacity, max vehicles, and optional OSRM geometry.
The route plans are stored in `RoutePlan` and `RouteTrip`, allowing dashboards to show latest route results and impact metrics.
## 8. Alerts, Intelligence, and Operations
- **Alerts** convert DDSS and operational states into triage-ready events with status (`open`, `acknowledged`, `resolved`) and severity (`info`, `warning`, `critical`).
- **Ops summary** aggregates total bins, stale bins, critical bins, alert counts, and latest DDSS/routing references.
- **Intelligence** adds risk scores, anomaly surfacing, explainability, contamination case tracking, and model monitoring snapshots.
- **Work orders** translate route plans or alerts into actionable tasks for operators.
## 9. Role Model and Restrictions
### 9.1 Role Types
- **Platform roles (`users.platform_role`)**: `owner`, `admin`. These are global roles.
- **Organisation roles (`organisation_memberships.role`)**: `viewer`, `operator`, `manager`, `admin`, `owner`.
### 9.2 Permissions from `app/api/deps.py`
- **viewer**: read dashboard, bins, alerts, reports, organisations/sites/zones, analytics, intelligence, routing, DDSS, telemetry.
- **operator**: all viewer capabilities plus device read/heartbeat, assigned work-order updates, and contamination write.
- **manager**: write access for bins, alerts, reports, sites, zones, devices, limited membership management, routing/DDSS/telemetry/classification write, audit read, work-order write.
- **admin**: broad full-system management including org write, notifications, memberships, routing/DDSS/telemetry/classification write, model monitoring read.
- **owner**: admin-level access plus organisation delete, owner assignment, model monitoring write, and highest-level control.
### 9.3 Current Practical Behaviour
- Managers are intended to operate within their organisation and usually create sites, zones, bins, and scoped users.
- Operators are field users focused on assigned sites, bins, work orders, alerts, and contamination cases.
- Viewers are read-only users.
- Platform owner/admin can operate across organisations.
## 10. Backend–Frontend Integration
### 10.1 API client
The frontend calls the backend through `frontend/lib/api.ts`. It resolves the base URL from `NEXT_PUBLIC_API_BASE_URL` or local storage, attaches `Authorization: Bearer <token>` if present, includes cookies, and surfaces backend errors consistently.
### 10.2 React Query data layer
`frontend/lib/queries.ts` wraps most backend routes in React Query hooks such as `useBins`, `useCreateBin`, `useLatestDDSS`, `usePlanLatestRouteVrp`, `useMe`, `useAlertsSummary`, and enterprise/user hooks. Mutations invalidate the correct caches so dashboards refresh after writes.
### 10.3 Role-aware UI
`frontend/lib/types.ts` and `frontend/lib/rbac-context.tsx` centralize role checks used by the UI. `components/app-sidebar.tsx` builds a navigation menu based on those checks. This is how the frontend hides or reveals sections like Enterprise, Users, Devices, Notifications, Audit, Intelligence, Telemetry, and Classify.
## 11. Frontend Dashboard Structure
The dashboard area includes **19 pages**. Major pages include:
- `dashboard/page.tsx` — landing dashboard summary.
- `dashboard/enterprise/page.tsx` — organisations, sites, zones, devices, members, audit-adjacent management.
- `dashboard/users/page.tsx` — user management and assignments.
- `dashboard/bins/page.tsx` — bin registry and operational list.
- `dashboard/telemetry/page.tsx` — latest telemetry reads and ingest workflows.
- `dashboard/classify/page.tsx` — upload image, classify waste, optionally store against a bin.
- `dashboard/ddss/page.tsx` — run DDSS and inspect ranked bins.
- `dashboard/routing/page.tsx` — latest routes, heuristic planning, VRP planning.
- `dashboard/map/page.tsx` — map visualization of bins/status/routes.
- `dashboard/alerts/page.tsx` — alert triage and state updates.
- `dashboard/analytics/page.tsx` — charts and KPI views.
- `dashboard/intelligence/*` — anomalies, contamination, monitoring.
- `dashboard/devices/page.tsx`, `dashboard/notifications/page.tsx`, `dashboard/audit/page.tsx`.
## 12. Current Data Model Usage in the Product
- **Organisations** represent council or client tenants.
- **Sites** represent areas inside an organisation (for example Leeds City Centre or Headingley Area).
- **Zones** refine sites for service or routing use (for example Retail Core or Station District).
- **Bins** are linked to organisation/site/zone and carry postcode, sector, lat/lon, active state, and schedule settings.
- **Telemetry** gives the operational state of bins.
- **Classification** adds waste type context.
- **DDSS decisions** prioritize bins for collection.
- **Route plans** operationalize the ranking into trips.
- **Alerts/work orders** turn rankings into actionable operations.
## 13. Testing & Validation Assets
The repository contains baseline async tests in `tests/` covering auth, bins, DDSS, routing, and telemetry smoke behaviour. These are useful for regression checks but are not yet a full enterprise RBAC test suite.
## 14. Files and Folders of Interest
- `app/main.py` — backend app bootstrap and router registration.
- `app/db/models.py` — database schema.
- `app/api/routes/*` — all API endpoints.
- `app/services/*` — business logic (priority, forecasting, routing, audit, analytics, alerts).
- `notebooks/*` — experimentation, evaluation, integration.
- `models/*` — trained model artifacts.
- `frontend/app/dashboard/*` — role-aware UI pages.
- `frontend/lib/*` — API client, hooks, RBAC helpers, shared types.
## 15. Recommended Presentation Narrative
For presentation, a strong story is: 
1. introduce the waste management problem and why reactive collection is inefficient
2. show the data hierarchy (organisation/site/zone/bin)
3. explain telemetry + image classification
4. show the forecasting model and notebook metrics
5. explain DDSS priority scoring and alert generation
6. show route planning and the distance-saving comparison from notebooks
7. explain enterprise roles and role-based dashboards
8. end with the live operational UI and latest analytics/alerts/routes.
## 16. Appendix: API Inventory
A full machine-readable API inventory with example payloads is provided separately in **`DDSS_Backend_API_Reference_Updated.json`**.
