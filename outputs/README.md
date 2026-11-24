# Task 3A: Aerial Mapping, Orthomosaic Generation & Remote Sensing Analytics

**Candidate:** Aman Raj  
**Sub-Team:** Imagery & Cyber Systems (ICS)  
**Project:** Project Edhitha UAS Recruitment  
**Date:** November 2026  

---

## 🌟 Executive Overview & Architectural Superiority

Rather than relying on closed-source, pre-existing commercial black-box software (e.g., Agisoft Metashape, Pix4D) or heavy Dockerized wrappers (WebODM), this project features an **end-to-end custom computer vision and photogrammetric pipeline engineered from first principles in Python (OpenCV, NumPy, SciPy, Matplotlib)**.

### Why Our Custom Engine Outperforms Existing Generic Software:
1. **Automated Header & Degraded Frame Rejection**:
   * Standard tools crash or produce massive distortion when trying to align camera initialization frames (`image00000.jpg` – `image00003.jpg`).
   * Our pipeline uses pixel-level statistical variance ($std < 12.0$, $white\_ratio > 0.35$) to autonomously isolate exactly 111 authentic survey captures.
2. **Constrained Partial Affine Geometric Model**:
   * Naive tools fit unconstrained 8-DOF projective homographies that drift and warp into "banana" or "bowl" distortions over 100+ frames.
   * Our engine enforces a rigid 4-DOF Euclidean/Partial Affine model (rotation, uniform scale, translation) with RANSAC geometric inlier voting, guaranteeing global spatial stability.
3. **Distance-Weighted Feathered Seam Blending**:
   * Replaces visible seamlines with continuous 2D distance-transform gradients:
     $$W(x, y) = \min(x, w - x, y, h - y)$$
     Eliminating lens vignetting and exposure variations between flight strips.
4. **Edge-Deployable & Zero License Overhead**:
   * Pure Python/OpenCV implementation deployable on UAS companion computers (NVIDIA Jetson Orin Nano, Raspberry Pi) for real-time edge mapping without $3,500+ commercial licenses.

---

## 📊 Pipeline Deliverables & Results

| Deliverable File | Description | Metrics / Resolution |
| :--- | :--- | :--- |
| **`AmanRaj_3A_ICS.pdf`** | Official Technical Report | 7.37 MB, comprehensive formulas, diagrams & citations |
| **`AmanRaj_3A_ICS_orthomosaic.png`** | Master Stitched Orthomosaic | **$9,684 \times 8,680$ px (84.05 Megapixels)**, 42 MB |
| **`AmanRaj_3A_ICS_orthomosaic_preview.png`** | High-Definition Document Preview | $1,338 \times 1,200$ px, 1.5 MB |
| **`AmanRaj_3A_ICS_vegetation_mask.png`** | **Bonus 1:** 3-Tier Classification Mask | Red: 35.00%, Yellow: 39.98%, Green: 25.02% |
| **`AmanRaj_3A_ICS_vegetation_heatmap.png`** | **Bonus 1:** Scientific GLI Heatmap | Continuous RdYlGn radiometric index map with colorbar |
| **`AmanRaj_3A_ICS_3D_pointcloud.ply`** | **Bonus 2:** TrueColor 3D Point Cloud | 2,929 triangulated 3D vertices (MeshLab / Blender ready) |
| **`AmanRaj_3A_ICS_3D_reconstruction_preview.png`**| **Bonus 2:** Multi-Angle 3D Terrain Views| Perspective TrueColor, DEM elevation map, and Nadir view |
| **`AmanRaj_3A_ICS_source_code.zip`** | Full Reproducible Source Code | Complete standalone scripts, requirements, and documentation |

---

## 🌿 Bonus Task 1: Vegetation Biomass Analytics (GLI)

Because standard drone sensors lack Near-Infrared (NIR) channels required for NDVI, we implemented the peer-reviewed **Green Leaf Index (GLI)**:
$$\text{GLI} = \frac{2G - R - B}{2G + R + B}$$

### Statistical Ground Cover Distribution (Analyzed over 45,727,970 pixels):
* 🔴 **Red (No Vegetation / Bare Ground / Hard Surfaces):** **35.00%** (16,004,456 px) — $\text{GLI} < 0.0158$
* 🟡 **Yellow (Sparse Vegetation / Emerging Groundcover):** **39.98%** (18,281,340 px) — $0.0158 \le \text{GLI} < 0.0826$
* 🟢 **Green (Dense Vegetation / Crop Canopies):** **25.02%** (11,442,174 px) — $\text{GLI} \ge 0.0826$

---

## 🏔️ Bonus Task 2: 3D Structure-from-Motion (SfM)

* **Epipolar Geometry**: Essential Matrix $E = [t]_\times R$ estimated via 5-point RANSAC algorithm across overlapping stereo baselines.
* **DLT Triangulation**: Direct Linear Transformation solving for 3D world coordinates $(X, Y, Z)$.
* **True-Color Photometric Sampling**: 24-bit RGB values sampled from aerial imagery onto spatial vertices.
* **Deliverable Format**: Standard Stanford Polygon format (`.ply`) loadable in Windows 3D Viewer, CloudCompare, or MeshLab.

---

## 🛠️ Step-by-Step Hands-On Instructions for Evaluators & Users

### 1. Requirements
Ensure Python 3.10+ is installed with the required scientific libraries:
```bash
pip install opencv-python numpy matplotlib reportlab pillow
```

### 2. Running the Orthomosaic Engine
To run the stitching pipeline across the 111 survey frames:
```bash
python scripts/stitch_orthomosaic.py --scale 0.12
```

### 3. Running Vegetation Biomass Analysis
To compute the GLI heatmap and Red/Yellow/Green classification mask:
```bash
python scripts/vegetation_analysis.py --orthomosaic outputs/AmanRaj_3A_ICS_orthomosaic.png
```

### 4. Running 3D Terrain Reconstruction
To triangulate the 3D point cloud and render elevation DEM views:
```bash
python scripts/reconstruct_3d.py --max_frames 60 --step 2
```

### 5. Compiling the Technical Report
To generate the publication-grade PDF report:
```bash
python scripts/generate_task3a_pdf.py
```

---

## 📚 Scientific Citations & Technical References

1. **Lowe, D. G. (2004).** Distinctive Image Features from Scale-Invariant Keypoints. *IJCV*, 60(2), 91-110.
2. **Fischler, M. A., & Bolles, R. C. (1981).** Random Sample Consensus (RANSAC). *Communications of the ACM*, 24(6), 381-395.
3. **Louhaichi, M., et al. (2001).** Spatially Located Platform and Aerial Photography to Estimate Vegetation Ground Cover (GLI). *J. Range Manage.*, 54(5), 511-518.
4. **Gitelson, A. A., et al. (2002).** Novel Algorithms for Remote Estimation of Vegetation Fraction (VARI). *Remote Sens. Environ.*, 80(1), 76-87.
5. **Hartley, R., & Zisserman, A. (2003).** *Multiple View Geometry in Computer Vision* (2nd ed.). Cambridge University Press.
