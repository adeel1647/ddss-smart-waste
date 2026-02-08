\# Smart Waste Management DDSS



\## Project Overview

This project implements a Data-Driven Decision Support System (DDSS) for smart waste management.  

The system integrates computer vision, predictive analytics, and route optimisation to support

efficient and adaptive waste collection.



\## Dataset Description



\### Waste Image Dataset

This project uses the \*\*TrashNet\*\* dataset for waste image classification.



\- \*\*Source:\*\* Stanford University (CS229 Project)

\- \*\*Authors:\*\* Gary Thung and Mindy Yang

\- \*\*Public Repository:\*\* https://github.com/garythung/trashnet

\- \*\*Domain:\*\* Academic research and education



\### Dataset Characteristics

\- \*\*Number of classes:\*\* 6

&nbsp; - Cardboard

&nbsp; - Glass

&nbsp; - Metal

&nbsp; - Paper

  - Trash

&nbsp; - Plastic

\- \*\*Images per class:\*\* Approximately 400–600

\- \*\*Image format:\*\* JPEG

\- \*\*Labelling:\*\* Manually labelled



\### Rationale for Dataset Selection

TrashNet is widely cited in academic literature for waste classification tasks and has been used

as a benchmark dataset in multiple peer-reviewed studies. Its class structure and image quality

make it suitable for fine-tuning convolutional neural networks such as DenseNet121.



\### Dataset Structure

The dataset has been structured to align with standard Keras and TensorFlow data loaders:





