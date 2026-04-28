---
title: "Imagen Product Recontextualization at Scale"
---

This repository contains Jupyter notebooks and tools to perform large-scale product image recontextualization using Google's Gemini and Imagen Product Recontext models. It includes both the generation pipeline and an evaluation framework.

**Authors**: Layolin Jesudhass & Isidro De Loera

## Contents

### Notebooks

- **`imagen_product_recontext_at_scale.ipynb`**  
  Scales up product image recontextualization using Imagen. Handles:
  - Batch generation of recontextualized product images
  - Prompt engineering for diverse product contexts
  - Sequential and Parallel execution options.

- **`evaluation_imagen_product_recontext_at_scale.ipynb`**  
  Evaluates the generated images on various axes, such as:
    - Product Fidelity
    - Scene Realism
    - Aesthetic Quality
    - Brand Integrity
    - Policy Compliance
    - Imaging Quality
  - Sequential and Parallel execution options.

## Getting Started

### Requirements

- Python 3.8+
- Jupyter or VSCode
- Google Cloud Vertex AI and access to Imagen Product Recontext API
- Required Python libraries are listed in `requirements.txt`.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio.git
   ```
2. Navigate to the experiment directory:
   ```bash
   cd vertex-ai-creative-studio/experiments/Imagen_Product_Recontext
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

1.  **Generate Images:** Open and run the `imagen_product_recontext_at_scale.ipynb` notebook to generate recontextualized product images.
2.  **Evaluate Images:** Open and run the `evaluation_imagen_product_recontext_at_scale.ipynb` notebook to evaluate the generated images.