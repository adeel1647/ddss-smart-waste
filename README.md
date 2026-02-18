# Smart Waste Management DDSS

## Project Overview

This project implements a **Data-Driven Decision Support System (DDSS)**
for intelligent waste classification in smart-city environments.

The system integrates:

-   Computer Vision (Deep Learning-based waste classification)
-   Transfer Learning using DenseNet121
-   Fine-tuning and regularisation techniques
-   Rule-based Decision Support Logic

The objective is to improve waste sorting accuracy and transform model
predictions into actionable waste management decisions.

------------------------------------------------------------------------

## Dataset Description

### TrashNet Dataset

-   **Source:** Stanford University (CS229 Project)
-   **Authors:** Gary Thung and Mindy Yang
-   **Repository:** https://github.com/garythung/trashnet
-   **Classes:** 6 (Cardboard, Glass, Metal, Paper, Plastic, Trash)
-   **Total Images:** \~2,500
-   **Format:** JPEG
-   **Labeling:** Manually annotated

Dataset structure:

data/ └── images/ ├── cardboard/ ├── glass/ ├── metal/ ├── paper/ ├──
plastic/ └── trash/

All preprocessing (resizing, normalization, augmentation) is handled
during training.

------------------------------------------------------------------------

## Model Development

### Baseline Model

-   Architecture: DenseNet121 (ImageNet pretrained)
-   Base model frozen
-   Custom classification head added

**Training Configuration** - Image size: 224 × 224 - Batch size: 16 -
Optimizer: Adam - Learning rate: 1e-4 - Epochs: 5

**Baseline Results** - Training Accuracy: \~87% - Validation Accuracy:
\~79%

------------------------------------------------------------------------

## Fine-Tuning

-   Total layers: 427
-   Last 30 layers unfrozen
-   Learning rate reduced to 3e-5
-   Early stopping applied
-   Learning rate scheduling enabled
-   Class weights applied to handle imbalance

**Fine-Tuned Results** - Training Accuracy: \~92--93% - Validation
Accuracy: \~84--85% - Best Validation Accuracy: 85%

------------------------------------------------------------------------

## Final Model

Final deployed model:

densenet121_final.h5

Includes: - Transfer learning - Controlled fine-tuning -
Regularisation - Learning rate scheduling - Early stopping

------------------------------------------------------------------------

## Model Evaluation

Evaluation metrics: - Accuracy - Precision - Recall - F1-score -
Confusion Matrix - Classification Report

**Final Test Accuracy:** 85%\
**Macro F1-score:** 0.84\
**Weighted F1-score:** 0.85

Strong performance across most classes, with improved recall for the
Trash category.

------------------------------------------------------------------------

## Decision Support System (DDSS)

A rule-based layer converts predictions into operational waste handling
decisions.

### Confidence Rule

-   Confidence ≥ 0.60 → Automatic action
-   Confidence \< 0.60 → Manual inspection required

### Waste Handling Actions

  Class       Action
  ----------- -------------------------------
  Cardboard   Send to recycling facility
  Paper       Send to recycling facility
  Glass       Glass recycling process
  Metal       Metal recovery process
  Plastic     Plastic sorting and recycling
  Trash       Landfill disposal

------------------------------------------------------------------------

## Current Project Status

✔ Dataset validated\
✔ Baseline model trained\
✔ Fine-tuned model optimized\
✔ Final model selected (85% accuracy)\
✔ Evaluation pipeline implemented\
✔ DDSS logic integrated

------------------------------------------------------------------------

## Next Steps

1.  IoT bin fill-level integration\
2.  Route optimisation modeling\
3.  Real-time inference pipeline\
4.  Full DDSS architecture integration\
5.  Dissertation finalization

------------------------------------------------------------------------

## Reproducibility

-   Public dataset (TrashNet)
-   TensorFlow / Keras framework
-   Structured training pipeline
-   Standard evaluation metrics

All experiments are reproducible and aligned with academic research
standards.
