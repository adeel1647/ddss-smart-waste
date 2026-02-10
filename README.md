\# Smart Waste Management DDSS



\## Project Overview



This project implements a \*\*Data-Driven Decision Support System (DDSS)\*\*

for smart waste management. The system integrates \*\*computer vision\*\*,

\*\*predictive analytics\*\*, and \*\*route optimisation\*\* to support

efficient and adaptive waste collection operations in smart-city

environments.



The overall aim is to reduce unnecessary waste collection trips, prevent

bin overflow, and improve operational efficiency through data-driven

decision-making.



------------------------------------------------------------------------



\## Dataset Description



\### Waste Image Dataset



This project uses the \*\*TrashNet\*\* dataset for waste image

classification.



\-   \*\*Source:\*\* Stanford University (CS229 Project)

\-   \*\*Authors:\*\* Gary Thung and Mindy Yang

\-   \*\*Public Repository:\*\* https://github.com/garythung/trashnet

\-   \*\*Domain:\*\* Academic research and education



\### Dataset Characteristics



\-   \*\*Number of classes:\*\* 6

&nbsp;   -   Cardboard

&nbsp;   -   Glass

&nbsp;   -   Metal

&nbsp;   -   Paper

&nbsp;   -   Plastic

&nbsp;   -   Trash

\-   \*\*Images per class:\*\* Approximately 400--600

\-   \*\*Image format:\*\* JPEG

\-   \*\*Labelling:\*\* Manually labelled



\### Rationale for Dataset Selection



TrashNet is widely cited in academic literature for waste classification

tasks and has been used as a benchmark dataset in multiple peer-reviewed

studies. Its class structure, image quality, and public availability

make it suitable for transfer learning experiments using convolutional

neural networks such as \*\*DenseNet121\*\*.



\### Dataset Structure



The dataset has been structured to align with standard Keras and

TensorFlow data loaders:



&nbsp;   data/

&nbsp;   └── images/

&nbsp;       ├── cardboard/

&nbsp;       ├── glass/

&nbsp;       ├── metal/

&nbsp;       ├── paper/

&nbsp;       ├── plastic/

&nbsp;       └── trash/



All preprocessing steps (resizing, normalisation, and augmentation) are

performed within the training pipeline to preserve the integrity of the

original dataset.



------------------------------------------------------------------------

## Dataset Exploration
Initial dataset exploration was conducted using Jupyter Notebook to:
- Verify directory structure and image readability
- Confirm consistency between labels and visual content
- Visually inspect random samples (5–10 images per class)

---

## Model Development

### Baseline Model
- Architecture: **DenseNet121**
- Pretrained on **ImageNet**
- Custom classification head added
- Base model layers frozen

**Training configuration:**
- Image size: 224 × 224
- Batch size: 16
- Optimizer: Adam
- Learning rate: 1e-4
- Epochs: 5

### Baseline Results
- Training accuracy: ~83%
- Validation accuracy: ~72%

---

## Fine-Tuning
- Total layers in DenseNet121: 427
- Top 53 layers unfrozen for fine-tuning
- Reduced learning rate applied

### Fine-Tuned Results
- Training accuracy: ~85%
- Validation accuracy: ~75%

---

## Model Evaluation
Evaluation was performed on a held-out test set using:
- Accuracy
- Precision
- Recall
- F1-score
- Classification report

**Overall test accuracy:** ~78%

Strong performance was observed across most classes. Lower performance on the “trash” category
is expected due to visual ambiguity and class overlap.

---

## Decision Support System (DDSS)
A rule-based DDSS layer combines:
- Waste classification output
- Prediction confidence
- Simulated IoT bin fill-level data

**Example decisions:**
- High confidence + high fill level → Urgent collection
- Low confidence → Manual inspection
- Normal fill level → Scheduled collection

This transforms raw predictions into actionable operational decisions.

---

## Current Project Status
✔ Dataset selection and verification completed  
✔ Baseline and fine-tuned DenseNet121 models trained  
✔ Model evaluation completed  
✔ DDSS decision logic implemented  

---

## Next Steps
1. IoT data simulation or hardware integration
2. Real-time inference pipeline
3. End-to-end DDSS system demonstration
4. Dissertation writing and final analysis

---

## Reproducibility
All experiments use publicly available datasets and standard machine learning libraries to ensure
transparency, reproducibility, and academic integrity.
