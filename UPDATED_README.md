# Smart Waste Management DDSS

## Overview

This project is an end-to-end **Data-Driven Decision Support System (DDSS)** for smart waste management. It combines:

- waste image classification using deep learning
- smart-bin telemetry ingestion
- short-term fill-level forecasting
- priority-based decision support
- route optimisation for waste collection
- backend API integration for frontend and operational workflows

The main goal is to turn raw image data and bin telemetry into operational decisions: which bins should be serviced first, why they are urgent, and how collection routes should be planned efficiently.

---

## High-Level System Flow

The full system follows this pipeline:

1. **Bin registration**
   - Smart bins are registered with geolocation and postcode.

2. **Telemetry ingestion**
   - The system stores fill level, collection delay, and timestamps.

3. **Image classification**
   - Waste images are sent to the backend and classified into one of six categories.

4. **Forecasting**
   - The system predicts the fill level 6 hours ahead using recent telemetry and engineered features.

5. **Decision support**
   - A weighted priority score is calculated from predicted fill, time since last collection, and uncertainty.

6. **Routing**
   - Priority-ranked bins are sent into routing logic to create collection trips.

A simple way to describe the system is:

**sense -> classify -> forecast -> rank -> route**

---

## Main Components

### 1. Computer Vision Layer

This layer classifies waste images.

**Model used**
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

**Typical inference flow**
1. image uploaded through API
2. image resized to `224 x 224`
3. pixel values normalized to `[0, 1]`
4. model returns class probabilities
5. top class and confidence are returned and optionally stored in the database

### 2. Telemetry Layer

This layer stores smart-bin operational data such as:
- fill level
- hours since last collection
- timestamp
- bin identifier

This data is used both for reporting and for forecasting / prioritisation.

### 3. Forecasting Layer

This layer predicts how full a bin will be after 6 hours.

**Model used**
- RandomForestRegressor

**Purpose**
- move from reactive collection to proactive planning
- identify bins that may become critical soon even if they are not yet full

### 4. Decision Support Layer

This layer combines perception and prediction into an operational urgency score.

It uses:
- current or recent fill level
- predicted fill in 6 hours
- hours since last collection
- classifier confidence / uncertainty

### 5. Routing Layer

This layer converts ranked bins into practical collection routes.

Routing strategies include:
- greedy priority-based routing
- priority + distance routing
- capacity-constrained multi-trip routing
- VRP-style optimisation using OR-Tools
- optional real-road path generation with OSRM / map-based logic, depending on environment setup

---

## Dataset

### Image Classification Dataset

The image dataset is stored in class-wise folders under `data/images/`.

Expected / confirmed structure:

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

This is a **TrashNet-style 6-class waste dataset structure**.

### Dataset Summary

Based on the reviewed project files, the dataset contains approximately:

- cardboard: 403
- glass: 501
- metal: 410
- paper: 594
- plastic: 482
- trash: 137

**Total images: 2527**

### Important note on data source

The project structure and README indicate a TrashNet-style dataset. If you need to claim the exact original public source in a report or viva, verify whether your local dataset was directly downloaded from the TrashNet repository or adapted from another source before making that claim formally.

---

## Image Classification Model

### Final Model

The main deployed classifier is based on **DenseNet121**.

Common project model files include:
- `densenet121_final.keras`
- `densenet121_final.h5`
- `densenet121_finetuned.h5`
- `densenet121_regularized.h5`

### Architecture Summary

The final model follows a transfer-learning design:
- DenseNet121 backbone with `include_top=False`
- input shape `224 x 224 x 3`
- GlobalAveragePooling2D
- Dense(256, activation='relu')
- Dropout(0.3)
- Dense(6, activation='softmax')

### Training Strategy

The training notebooks indicate the following approach:
- transfer learning from ImageNet
- initial freezing of the base model
- fine-tuning of the final layers
- last ~30 layers unfrozen during fine-tuning
- class weighting for class imbalance
- early stopping
- learning-rate reduction on plateau
- Adam optimizer

### Input Preprocessing

Images are:
- loaded as RGB
- resized to `224 x 224`
- normalized by dividing by 255

### Data Augmentation

The training pipeline uses augmentation such as:
- rotation
- width shift
- height shift
- zoom
- shear
- horizontal flip

### Train / Validation Split

The reviewed training setup uses an approximate 80/20 split:
- training images: 2024
- validation images: 503

### Classification Performance

From the reviewed evaluation outputs:
- accuracy: about **0.83**
- macro F1-score: about **0.81**
- weighted F1-score: about **0.83**

Per-class F1 values observed in evaluation:
- cardboard: 0.86
- glass: 0.81
- metal: 0.87
- paper: 0.91
- plastic: 0.76
- trash: 0.66

### Interpretation

The model performs strongly on paper, metal, and cardboard. The weakest class is usually **trash**, which is expected because:
- it has fewer examples
- it is visually more diverse
- it may overlap with other categories

---

## Forecasting Model

### Model Used

The short-term fill-level prediction component uses:
- `fill_forecast_rf.pkl`
- RandomForestRegressor

Reviewed model details indicate:
- around 400 trees
- max depth around 18
- 9 engineered input features

### Forecasting Features

The forecast model uses features such as:
- `fill_level`
- `hour_of_day`
- `day`
- `weekend`
- `growth_rate`
- `lag_1`
- `lag_2`
- `lag_3`
- `rolling_mean_3`

### Target

The forecasting task predicts:
- **fill level 6 hours ahead**

### Forecasting Data Source

Important: the forecasting notebook uses **synthetic / simulated telemetry data**, not real long-term production IoT sensor logs.

The simulated setup includes:
- multiple bins
- hourly progression
- growth trends
- day / weekend effects
- noise
- lag features
- occasional emptying/reset behaviour

### Forecasting Performance

From the reviewed notebook comparison:
- Random Forest: MAE ≈ **3.878**, R² ≈ **0.791**
- Gradient Boosting: MAE ≈ 4.530, R² ≈ 0.758
- Naive baseline: MAE ≈ 11.144, R² ≈ 0.137
- Linear Regression: MAE ≈ 13.059, R² ≈ 0.311

### Interpretation

Random Forest was selected because it performed best among the tested forecasting models and handled nonlinear relationships better than simpler baselines.

---

## Decision Support Logic

The DDSS computes a priority score for each eligible bin.

### Main Inputs
- predicted fill in 6 hours
- hours since last collection
- classification confidence
- derived uncertainty

### Uncertainty

Uncertainty is derived as:

```text
uncertainty = 1 - confidence
```

### Priority Score Formula

```text
priority_score =
    0.5 * predicted_fill_6h
  + 0.3 * last_collection_hours
  + 0.2 * uncertainty * 100
```

### Why this matters

This formula ensures the system does not only react to current fill. It also considers:
- near-future risk
- collection delay
- uncertainty in model prediction

This makes the system more realistic for operational planning.

---

## Alerts / Operational Rules

The reviewed code indicates alerts such as:
- `CRITICAL_FILL_PREDICTED` when predicted fill is very high
- `OVERDUE_COLLECTION` when a bin has not been serviced for too long
- `LOW_CLASSIFICATION_CONFIDENCE` when the image classifier is uncertain

These alerts support fast operational interpretation and explainability.

---

## Routing and Optimisation

### Supported Routing Approaches

#### 1. Priority-only routing
Bins are sorted by urgency only.

#### 2. Priority + distance routing
Bins are selected using both urgency and travel efficiency.

#### 3. Capacity-constrained routing
The truck has limited carrying capacity, so the algorithm:
- splits bins into feasible trips
- returns to depot when needed
- reduces overload risk

#### 4. VRP optimisation
A more formal vehicle-routing formulation is supported through **OR-Tools**.

### Routing Inputs
Typical routing inputs include:
- depot location
- bin coordinates
- predicted or current demand
- truck capacity
- ranked candidate bins

### Practical Purpose
This helps answer:
- which bins should be collected first
- how many trips are needed
- how route distance can be reduced

---

## Backend Architecture

The backend is implemented with **FastAPI** and related Python services.

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

### Likely Backend Responsibilities
- expose REST APIs for bins, telemetry, classification, DDSS, routing, and auth
- load trained ML models
- store operational data and decisions
- return structured results to the frontend

---

## Database Entities

The reviewed backend structure indicates core entities such as:

- `bins`
- `telemetry`
- `classifications`
- `decision_runs`
- `decision_items`
- `route_plans`
- `route_trips`
- `users`

### Meaning of Each

**bins**
- master bin metadata
- geolocation, postcode, active status

**telemetry**
- fill-level and time-based sensor-style records

**classifications**
- stored image prediction results

**decision_runs**
- one DDSS execution session

**decision_items**
- per-bin priority outputs and alerts

**route_plans**
- one routing plan execution

**route_trips**
- specific trips and route details

**users**
- authentication and profile data

---

## API Design

The backend exposes endpoints for operational workflows.

### Main API Areas

#### Bin APIs
- create bin
- list bins
- retrieve bin-related information

#### Telemetry APIs
- submit telemetry for a bin
- get latest telemetry

#### Classification API
- upload image
- run DenseNet121 inference
- optionally store result against a bin

#### DDSS APIs
- run decision-support pipeline
- retrieve latest decision outputs

#### Routing APIs
- generate route plan from latest DDSS output
- generate VRP-based route plan

#### Authentication APIs
- register
- login
- forgot/reset password
- logout
- current user profile
- update profile

### End-to-End API Flow Example

1. create a bin
2. post telemetry
3. post image to classify
4. run DDSS
5. fetch ranked bins
6. generate route plan
7. display route in frontend

---

## Frontend Integration

The system is designed to connect the frontend directly to backend APIs.

A typical frontend flow is:
- user registers / logs in
- dashboard lists bins and status
- telemetry and classifications are displayed
- DDSS results show urgent bins and scores
- routing output is shown as route summaries / maps

---

## Authentication and Security

### Authentication
- JWT bearer tokens

### Password Handling
- Argon2 hashing

### Why this matters
- JWT supports stateless authenticated API access
- Argon2 is a strong password hashing method suitable for production-style systems

---

## Strengths of the Project

1. Integrates multiple AI/ML components in one operational system.
2. Goes beyond classification by adding forecasting and optimisation.
3. Uses a realistic backend API architecture.
4. Includes explainable operational outputs like priority scores and alerts.
5. Demonstrates practical smart-city relevance.

---

## Known Limitations

### 1. Forecasting data is simulated
The forecasting model should ideally be retrained later on real sensor telemetry.

### 2. Dataset imbalance
The `trash` class has fewer samples, which affects class performance.

### 3. Documentation drift
Older README sections may not exactly match the newest code or saved model names.

### 4. Prototype vs production
The project is strong as an integrated prototype / academic system, but still benefits from further hardening, testing, and cleanup before full production use.

---

## Suggested Presentation Summary

You can describe the project like this:

> This project is an end-to-end smart waste management DDSS. It uses a DenseNet121 transfer-learning model to classify waste images, a Random Forest regressor to predict bin fill 6 hours ahead, a weighted decision-support engine to rank bin urgency, and routing optimisation to plan efficient waste collection trips.

---

## Suggested Viva Summary Answers

### What model are you using?
- DenseNet121 for image classification
- Random Forest regression for short-term fill forecasting

### What is the source of training data?
- Image classification uses a local 6-class waste image dataset in TrashNet-style folder format.
- Forecasting uses simulated telemetry generated in the notebook.

### What classes do you predict?
- cardboard, glass, metal, paper, plastic, trash

### What is your image accuracy?
- about 83% on the reviewed validation/evaluation outputs

### Why use DenseNet121?
- strong transfer-learning performance and efficient feature reuse

### Why use Random Forest?
- it performed best among the tested forecasting models in the project notebooks

### What is the main innovation?
- integration of classification, forecasting, decision support, and routing into one operational system

---

## Future Improvements

Potential next steps:
- retrain forecasting model on real IoT telemetry
- increase dataset size for underrepresented classes
- improve trash-class performance
- improve API and documentation consistency
- add automated tests
- deploy with monitoring and model-version control
- integrate live sensor communication such as MQTT or embedded hardware
- add richer frontend analytics and explainability dashboards

---

## Reproducibility Notes

To reproduce the project well, keep the following folders organised:

```text
backend/
models/
data/
notebooks/
README.md
requirements.txt
```

Recommended documentation to maintain:
- exact dataset source and version
- exact train / validation split method
- model hyperparameters
- saved model version used by backend
- API examples
- environment variables and database setup

---

## Final Note

This project is best understood as an **integrated smart-city waste management prototype** that combines deep learning, ML forecasting, operational decision support, and route optimisation into one backend-driven system.
