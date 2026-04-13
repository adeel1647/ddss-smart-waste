# DDSS Smart Waste Management — Backend Update (Address-First UK Geocoding)

## What changed

This backend update changes the platform from **manual latitude/longitude entry** to an **address-first UK workflow**.

Users can now create and update sites, bins, and route depots using:

- postcode
- address text
- selected search suggestion (`place_id`)
- optional manual coordinate override for controlled admin cases

The backend still stores **resolved `lat` / `lon` internally** because they are still required for:

- map rendering
- route optimisation
- VRP planning
- distance calculations
- any future spatial analytics

So the new model is:

**user enters postcode/address → backend geocodes → backend stores normalized address + resolved coordinates**

---

## New backend capabilities

### 1. Geocoding endpoints
New routes under `/api/v1/geo`:

- `GET /geo/search?q=...`
- `GET /geo/postcode/{postcode}`
- `POST /geo/resolve`

These endpoints provide UK-focused postcode and address search plus full resolution into normalized address fields and coordinates.

### 2. Address-first bins
`POST /bins` and `PATCH /bins/{bin_id}` now support:

- `postcode`
- `address_line_1`
- `address_line_2`
- `city`
- `county`
- `country`
- `formatted_address`
- `geocode_place_id`

The backend resolves and stores `lat` / `lon` automatically.

### 3. Address-first enterprise sites
`POST /enterprise/sites` and `PATCH /enterprise/sites/{site_id}` now support the same address-first workflow.

### 4. Address-first routing depot
These routing endpoints now accept either coordinates **or** address-based depot input:

- `POST /routing/optimize`
- `POST /routing/plan-latest`
- `POST /routing/plan-latest-vrp`

Supported depot fields:

- `depot_lat`, `depot_lon`
- `depot_postcode`
- `depot_address`
- `depot_place_id`
- `depot_address_line_1`
- `depot_address_line_2`
- `depot_city`
- `depot_county`
- `depot_country`

---

## Why this is the correct design

Do **not** remove coordinates completely from the backend.

Routing, map views, and spatial calculations still need geometry.  
The improvement is to remove **manual coordinate entry from frontend/API usage**, not to remove coordinates from the internal data model.

This update therefore gives you:

- easier bin/site data entry
- better UK operational addressing
- support for shops, houses, offices, apartments, and named depots
- no breakage in map/routing/DDSS downstream logic

---

## Updated location fields

### Bin model additions
The `bins` table now stores:

- `address_line_1`
- `address_line_2`
- `city`
- `county`
- `country`
- `formatted_address`
- `geocode_place_id`
- `geocode_source`
- `geocode_confidence`

Existing fields kept:

- `postcode`
- `sector`
- `lat`
- `lon`

### Site model additions
The `sites` table now stores:

- `postcode`
- `address_line_1`
- `address_line_2`
- `city`
- `county`
- `country`
- `formatted_address`
- `geocode_place_id`
- `geocode_source`
- `geocode_confidence`

Existing fields kept:

- `address`
- `lat`
- `lon`

---

## Backend files changed

Replace these backend files:

- `app/core/config.py`
- `app/db/models.py`
- `app/schemas/common.py`
- `app/schemas/enterprise.py`
- `app/schemas/routing.py`
- `app/services/geocoding.py` **(new)**
- `app/schemas/geo.py` **(new)**
- `app/api/routes/geo.py` **(new)**
- `app/api/routes/bins.py`
- `app/api/routes/enterprise.py`
- `app/api/routes/routing.py`
- `app/api/routes/routing_vrp.py`
- `app/repositories/bins.py`
- `app/main.py`

Also apply the migration:

- `alembic/versions/20260408_address_first_geo.py`

---

## Important migration note

Because the data model changed, you should run a database migration before using the updated frontend.

This update adds new columns to:

- `sites`
- `bins`

It does **not** remove existing `lat/lon`.

That keeps old rows valid while allowing new address-first rows.

---

## Existing ML models

### Image classification
No retraining needed.  
The image classifier is unaffected by the address-first workflow.

### Fill forecasting
No retraining needed for the deployed model.  
The forecasting features are still based on telemetry/time features rather than raw address text.

### Integration notebooks
Your routing/integration/seed notebooks may need small updates if they currently assume that a human manually enters `lat/lon`.

Likely files to review:

- `src/train_densenet.ipynb` only if any UI demo references manual coordinates
- any integration or routing notebooks/scripts that create sample bins/sites directly from `lat/lon`

The ML core does **not** need redesign for this backend change.

---

## Recommended frontend follow-up

After replacing the backend files, update the frontend to:

- search postcode/address using `/geo/search`
- let the user pick one suggestion
- store/display normalized address
- stop asking users to manually type latitude/longitude
- send depot postcode/address for routing forms

That frontend work should be done after the backend and migration are in place.

---

## Example new flows

### Create bin
1. user types `LS1 6BR`
2. frontend calls `/geo/search?q=LS1 6BR`
3. user selects `12 Briggate, Leeds, LS1 6BR`
4. frontend posts selected address info to `/bins`
5. backend stores:
   - full address
   - resolved `lat/lon`
   - postcode/sector

### Create site
1. user types office/depot postcode
2. frontend selects exact address
3. backend stores site address + resolved coordinates

### Plan route
1. user enters depot postcode/address
2. backend resolves depot coordinates
3. existing routing logic continues unchanged

---

## New API summary

### Geocoding
- `GET /api/v1/geo/search`
- `GET /api/v1/geo/postcode/{postcode}`
- `POST /api/v1/geo/resolve`

### Updated location-aware APIs
- `POST /api/v1/bins`
- `PATCH /api/v1/bins/{bin_id}`
- `POST /api/v1/enterprise/sites`
- `PATCH /api/v1/enterprise/sites/{site_id}`
- `POST /api/v1/routing/optimize`
- `POST /api/v1/routing/plan-latest`
- `POST /api/v1/routing/plan-latest-vrp`

---

## Practical implementation note

This update uses an OpenStreetMap / Nominatim-compatible geocoding service through a dedicated backend service layer.  
That means the provider can later be swapped without changing every route or frontend component.

This is the safest enterprise-ready approach for your UK rollout.
