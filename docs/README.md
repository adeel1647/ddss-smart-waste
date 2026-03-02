Smart Waste Management DDSS
Project Overview

This project implements a full Data-Driven Decision Support System (DDSS) for intelligent waste management in smart-city environments.

The system integrates:

Computer Vision (Deep Learning-based waste classification)

Transfer Learning using DenseNet121

Fine-tuning and regularisation techniques

IoT-based bin simulation

Multi-factor priority scoring

Distance-aware route optimisation

Capacity-constrained vehicle routing

Route visualisation

The objective is to transform raw image predictions and simulated IoT data into actionable operational decisions that optimise waste collection efficiency, reduce travel distance, and improve resource utilisation.

System Architecture

The DDSS consists of four integrated layers:

1️⃣ Computer Vision Layer

Classifies waste type using DenseNet121.

2️⃣ IoT Simulation Layer

Simulates real-world bin sensor data:

Fill level (%)

Location (postcode)

Time since last collection

3️⃣ Decision Support Layer

Computes a weighted priority score based on:

Fill level (50%)

Time since last collection (30%)

Prediction uncertainty (20%)

4️⃣ Route Optimisation Layer

Generates:

Distance-aware collection routes

Capacity-constrained truck trips

Optimised travel paths

Comparative routing analysis

This layered architecture mirrors real smart-city waste management systems.

Dataset Description
TrashNet Dataset

Source: Stanford University (CS229 Project)

Authors: Gary Thung and Mindy Yang

Repository: https://github.com/garythung/trashnet

Classes: 6 (Cardboard, Glass, Metal, Paper, Plastic, Trash)

Total Images: ~2,500

Format: JPEG

Labeling: Manually annotated

Dataset structure:

data/
 └── images/
      ├── cardboard/
      ├── glass/
      ├── metal/
      ├── paper/
      ├── plastic/
      └── trash/


All preprocessing (resizing, normalization, augmentation) is performed dynamically during training.

Model Development
Baseline Model

Architecture: DenseNet121 (ImageNet pretrained)

Base model frozen

Custom classification head added

Training configuration:

Image size: 224 × 224

Batch size: 16

Optimizer: Adam

Learning rate: 1e-4

Epochs: 5

Baseline Results:

Training Accuracy: ~87%

Validation Accuracy: ~79%

Fine-Tuning Strategy

Total layers: 427

Last 30 layers unfrozen

Learning rate reduced to 3e-5

Early stopping applied

Learning rate scheduling enabled

Class weights applied for imbalance handling

Fine-Tuned Results:

Training Accuracy: ~92–93%

Validation Accuracy: ~84–85%

Best Validation Accuracy: 85%

The fine-tuning process significantly reduced overfitting and improved generalisation.

Final Model

Final deployed model:

densenet121_final.h5


Includes:

Transfer learning

Controlled fine-tuning

Regularisation

Learning rate scheduling

Early stopping

Class-weight balancing

This model is used for all subsequent DDSS integration stages.

Model Evaluation

Evaluation metrics used:

Accuracy

Precision

Recall

F1-score

Confusion Matrix

Classification Report

Final Evaluation Results:

Test Accuracy: 85%

Macro F1-score: 0.84

Weighted F1-score: 0.85

Strong performance across most classes.
Improved recall observed for the “Trash” category after class weighting.



IoT Bin Integration

Simulated smart bins generate:

Fill level (%)

postcode location

Hours since last collection

This simulates ultrasonic sensor data and time-based monitoring systems.

Priority Scoring Model

A weighted scoring formula determines bin urgency:

Priority Score =
0.5 × Fill Level
+ 0.3 × Collection Time
+ 0.2 × Prediction Uncertainty


This transforms classification output into a quantitative decision metric.

Route Optimisation

Two routing strategies were compared:

1️⃣ Priority-Only Routing

Bins sorted purely by urgency.

2️⃣ Priority + Distance Routing

Score = Distance / (Priority + ε)

This balances urgency and travel cost.

Results

Priority-only route distance: 16.85 km

Priority + Distance route distance: 12.35 km

Distance reduction: 4.50 km (~27% improvement)

This demonstrates that distance-aware routing significantly reduces operational travel cost.

Capacity-Constrained Vehicle Routing

Truck capacity constraint: 300 units

The algorithm automatically:

Splits collection into multiple trips

Returns to depot when full

Minimises total travel distance

Example Output:

Total Trips Required: 3

Total Travel Distance: 16.17 km

High load utilisation in Trip 1 and Trip 2

This mimics real-world waste collection logistics.

Route Visualisation

The system visualises:

Depot location

Smart bin coordinates

Route paths with arrows

Separate colours for each trip

This provides clear operational insight and supports presentation and analysis.

Experimental Comparison

Distance-aware routing achieved:

27% reduction in total travel distance

Maintained capacity constraints

Balanced urgency and logistics cost

This validates the effectiveness of integrating AI classification with logistics optimisation.

Current Project Status

✔ Dataset validated
✔ Baseline model trained
✔ Fine-tuned model optimised
✔ Final model selected (85% accuracy)
✔ Evaluation pipeline implemented
✔ IoT simulation integrated
✔ Priority scoring implemented
✔ Distance-aware routing completed
✔ Capacity-constrained VRP completed
✔ Route visualisation implemented

System prototype is fully operational.



## System Architecture (5-Layer Integrated Framework)

### 1️⃣ Computer Vision Layer

-   DenseNet121 (ImageNet pretrained)
-   Controlled fine-tuning (last 30 layers unfrozen)
-   Class-weight balancing
-   Early stopping + LR scheduling

Performance: - Test Accuracy: 85% - Macro F1-score: 0.84 - Weighted
F1-score: 0.85

Classes: Cardboard, Glass, Metal, Paper, Plastic, Trash

------------------------------------------------------------------------

### 2️⃣ Predictive Forecasting Layer (ML-Based)

Random Forest regression model predicting bin fill level 6 hours ahead.

Features: - fill_level - hour_of_day - day - weekend

Performance: - MAE: 2.59 - R²: 0.98

Model saved as: fill_forecast_rf_weekend.pkl

This enables proactive collection planning instead of threshold-based
reactive scheduling.

------------------------------------------------------------------------

### 3️⃣ IoT Simulation Layer

Simulates smart bin sensor data including: - Fill level (%) -
postcode-based location - Time since last collection - Dynamic waste
accumulation - Simulated collection reset events

------------------------------------------------------------------------

### 4️⃣ Decision Support Layer

Priority Score = 0.5 × Predicted Fill Level\
+ 0.3 × Time Since Collection\
+ 0.2 × Prediction Uncertainty

This transforms AI predictions into operational urgency metrics.

------------------------------------------------------------------------

### 5️⃣ Route Optimisation Layer

Implements:

-   Priority-only routing
-   Hybrid Priority + Distance routing
-   Capacity-constrained vehicle routing
-   Depot-based trip splitting
-   Real road-network routing using OSMnx
-   Multi-run statistical validation

Score function: Score = Distance / (Priority + ε)

------------------------------------------------------------------------

## Routing Performance

### Single Run Example

-   Priority-only: 16.85 km
-   Priority + Distance: 12.35 km
-   Improvement: \~27%

### Multi-Run Statistical Validation (10 runs)

-   Priority-only Mean Distance: 20.06 km
-   Priority + Distance Mean Distance: 11.79 km
-   Average Distance Reduction: 40.24%
-   Standard Deviation: 8.25%

This demonstrates statistically robust improvement.

------------------------------------------------------------------------

## Capacity-Constrained Vehicle Routing

Truck capacity: 300 units

System: - Splits routes into multiple trips - Returns to depot when
full - Maximises load utilisation

Example: - Total Trips: 3 - Total Distance: 16.17 km

------------------------------------------------------------------------

## Environmental Impact Modelling

Distance savings converted into fuel and CO₂ savings.

Assumptions tested: 30, 45, 60 L per 100 km

Mean CO₂ Saved Per Run: - 30 L/100km → 6.15 kg - 45 L/100km → 9.22 kg -
60 L/100km → 12.29 kg

Annual CO₂ Savings (1 route/day):

-   30 L/100km → 2.24 tonnes/year
-   45 L/100km → 3.36 tonnes/year
-   60 L/100km → 4.49 tonnes/year

Environmental savings remain robust under sensitivity analysis.

------------------------------------------------------------------------

## Real-Time Adaptive Simulation

The system dynamically:

-   Updates fill levels over time
-   Forecasts future fill
-   Recalculates priorities
-   Displays Top 3 urgent bins
-   Triggers critical alerts (\>90%)
-   Simulates collection reset

Demonstrates fully adaptive DDSS behaviour.

------------------------------------------------------------------------

## Road-Network Routing (OSMnx Integration)

-   Uses real road graph
-   Shortest path routing
-   Realistic street-level routes
-   Capacity-constrained trip visualisation

Adds real-world operational realism.

------------------------------------------------------------------------

## Current System Status

✔ DenseNet121 trained & fine-tuned\
✔ ML forecasting implemented\
✔ Multi-factor priority scoring\
✔ Distance-aware routing\
✔ Capacity-constrained VRP\
✔ Real road-network routing\
✔ Statistical validation\
✔ Environmental impact modelling\
✔ Real-time adaptive simulation\
✔ Full route visualisation

System prototype is fully operational and MSc-level complete.



Future Work

Real IoT hardware integration (Raspberry Pi / Jetson Nano)

Real-time MQTT-based communication

Predictive bin fill-level forecasting (LSTM/XGBoost)

Reinforcement learning-based routing

Web dashboard deployment

Reproducibility

Public dataset (TrashNet)

TensorFlow / Keras framework

Structured training pipeline

Fixed random seed for consistent experimental results

Modular notebook-based implementation

All experiments are reproducible and aligned with academic research standards.

