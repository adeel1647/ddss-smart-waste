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



\## Dataset Exploration and Verification



An initial dataset exploration phase was conducted using Jupyter

Notebook to verify:



\-   Correct directory structure

\-   Image readability

\-   Consistency between class labels and visual content



A random subset of images (5 per class) was visually inspected to

confirm dataset validity.



------------------------------------------------------------------------



\## Baseline Model Implementation



\### Model Architecture



A \*\*DenseNet121\*\* convolutional neural network pretrained on

\*\*ImageNet\*\* was used as the baseline classification model. Transfer

learning was applied by freezing all pretrained layers and training a

custom classification head.



\### Training Configuration



\-   Input size: 224 × 224 RGB images

\-   Batch size: 16

\-   Optimizer: Adam

\-   Learning rate: 1e-4

\-   Loss function: Categorical Cross-Entropy

\-   Epochs: 5



------------------------------------------------------------------------



\## Baseline Model Results



\-   Training accuracy: \\~83%

\-   Validation accuracy: \\~72%

\-   Validation loss: \\~0.68



These results provide a strong baseline for further fine-tuning and

optimisation.



------------------------------------------------------------------------



\## Current Project Status



✔ Dataset selection and verification completed\\

✔ Baseline DenseNet121 model trained and evaluated\\

✔ Model saved for further experimentation



------------------------------------------------------------------------



\## Next Steps



1\.  Fine-tune DenseNet121

2\.  Edge optimisation

3\.  IoT simulation and prediction

4\.  Routing optimisation

5\.  Full DDSS integration



------------------------------------------------------------------------



\## Reproducibility



All experiments are conducted using publicly available datasets and

standard deep learning libraries to ensure reproducibility and

transparency.



