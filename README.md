# Task 3A: Aerial Mapping, Orthomosaic Generation & Remote Sensing Analytics

**Candidate:** Aman Raj  
**Sub-Team:** Imagery & Cyber Systems (ICS)  
**Project:** Project Edhitha UAS Recruitment Assignment  
**Scene Surveyed:** Institutional Sports Complex / Campus Ground  
**Date:** November 2026  

---

## 🌟 Executive Overview & Architectural Highlights

This repository contains an **end-to-end aerial photogrammetry and remote sensing pipeline engineered from mathematical first principles in Python (OpenCV, NumPy, SciPy, Matplotlib)** for Unmanned Aerial Systems (UAS).

### Key Photogrammetric Capabilities:
1. **Automated Sensor Header QA**: Autonomously detects and filters sensor exposure settling / blank takeoff frames (`image00000.jpg` – `image00003.jpg`) using pixel luminance variance ($std < 12.0$).
2. **Constrained Rigid Motion Model**: Replaces error-accumulating 8-DOF projective homographies with a scale-locked rigid Euclidean model ($s = 1.0$) with FLANN SIFT matching and RANSAC inlier estimation.
3. **Radiometric Equalization & Distance Feathering**: Compensates for solar angle shifts via LAB-channel luminance matching, eliminates optical falloff with an inverse radial vignetting model ($1.0 + 0.20 \cdot r^2$), and blends seams with 2D Gaussian distance transforms.
4. **Local Coordinate Space Processing**: In the absence of onboard RTK-GPS EXIF metadata, the orthomosaic is reconstructed in a local metric/pixel-space coordinate frame ($6,140 \times 6,238$ px, 38.30 MP) in **114.3 seconds**.

---

## 📊 Pipeline Deliverables & Results

| Deliverable File | Description | Key Specification |
| :--- | :--- | :--- |
| **`AmanRaj_3A_ICS.pdf`** | Official Technical Publication | 4 pages, full formulas, figures, comparison tables & citations |
| **`AmanRaj_3A_ICS_orthomosaic.png`** | Master Seamless Orthomosaic | **$6,140 \times 6,238$ px (38.30 Megapixels)**, 29.6 MB |
| **`AmanRaj_3A_ICS_orthomosaic.tfw`** | ESRI / GIS TIFF World File | Metric spatial referencing (0.05 m/px nominal GSD) |
| **`AmanRaj_3A_ICS_orthomosaic.pgw`** | ESRI / GIS PNG World File | Metric spatial referencing (0.05 m/px nominal GSD) |
| **`AmanRaj_3A_ICS_orthomosaic_preview.png`** | High-Definition Document Preview | Fast-loading web preview |
| **`AmanRaj_3A_ICS_orthomosaic_transparent.png`** | RGBA Transparent Canvas for GIS | $6,140 \times 6,238$ px (Alpha boundary), 35.2 MB |
| **`AmanRaj_3A_ICS_vegetation_heatmap.png`** | **Bonus 1:** Scientific GLI Heatmap | Continuous RdYlGn radiometric index map with colorbar |
| **`AmanRaj_3A_ICS_vegetation_mask.png`** | **Bonus 1:** 3-Tier Classification Mask | Red: 5.65%, Yellow: 68.81%, Green: 25.55% |
| **`AmanRaj_3A_ICS_vegetation_summary.txt`** | Text Summary of Biomass Metrics | Exact pixel counts, Otsu thresholds, and ecological interpretation |
| **`AmanRaj_3A_ICS_3D_pointcloud.ply`** | **Bonus 2:** TrueColor 3D Point Cloud | **15,420 unique spatial vertices** (Filtered & Deduplicated) |
| **`AmanRaj_3A_ICS_3D_reconstruction_preview.png`**| **Bonus 2:** Multi-Angle 3D Terrain Views| Perspective TrueColor, DEM elevation map, and Nadir view |
| **`AmanRaj_3A_ICS_3D_summary.txt`** | Text Summary of 3D Geometry | Relative photogrammetric coordinate bounds & vertex counts |
| **`AmanRaj_3A_ICS_source_code.zip`** | Full Reproducible Source Code | Standalone scripts, requirements, and documentation |
| **`AmanRaj_3A_ICS_AI_Session_Transcript.html`**| AI Session Engineering Transcript | Complete, transparent log of consultative engineering dialogue |

---

## 🌿 Bonus Task 1: Scientific Vegetation Biomass Analytics (GLI)

Because standard drone RGB payloads lack Near-Infrared (NIR) channels, we implemented the peer-reviewed **Green Leaf Index (GLI)**:
$$\text{GLI} = \frac{2G - R - B}{2G + R + B}$$

### Scientific Absolute Thresholding (Evaluated across 20,187,264 active terrain pixels):
Thresholds are grounded in physical zero-crossing and Otsu's inter-class variance maximization:
* 🔴 **Red (No Vegetation / Hard Ground / Goal Structures):** **5.65%** ($1,139,652$ px) — $\text{GLI} < 0.0000$
* 🟡 **Yellow (Sparse Vegetation / Mowed Lawn Turf):** **68.81%** ($13,890,450$ px) — $0.0000 \le \text{GLI} < 0.0800$
* 🟢 **Green (Dense Foliage / Perimeter Trees & Shrubs):** **25.55%** ($5,157,162$ px) — $\text{GLI} \ge 0.0800$

*(Mean Field GLI: 0.0533 | Canvas Dimensions: 6,140 x 6,238 = 38,301,320 total pixels).*

---

## 🏔️ Bonus Task 2: 3D Structure-from-Motion (SfM)

* **Epipolar Geometry**: Essential Matrix $E = [t]_\times R$ estimated via 5-point RANSAC algorithm across overlapping stereo pairs with automatic degenerate turnaround rejection.
* **DLT Triangulation**: Direct Linear Transformation solving for 3D world coordinates $(X, Y, Z)$ yielding **15,420 unique spatial vertices** (deduplicated at 1 mm tolerance).
* **Photometric Vertex Coloring**: 24-bit TrueColor RGB values sampled directly from aerial captures onto spatial vertices.
* **Coordinate Space**: Local relative photogrammetric units (standard pinhole model $f = 0.85 \times w$).

---

## ⚖️ Comparative Pipeline Trade-offs: Custom Python vs. WebODM

| Dimension | Custom Python Pipeline (Aman Raj) | WebODM (OpenDroneMap Docker) |
| :--- | :--- | :--- |
| **Pipeline Architecture** | Transparent SIFT, FLANN Ratio Test, Rigid RANSAC, DLT | OpenSfM (SfM) + OpenMVS (Dense Meshing) in multi-container stack |
| **Memory Footprint** | Bounded: ~1.18 GB RAM peak (zero host freezes) | Intense: Spikes to 8.5–11.2 GB RAM (94% host memory utilization) |
| **Processing Runtime** | 114.3 seconds (Fast, deterministic turnaround) | 20+ minutes (Heavy multi-view stereo voxelization) |
| **Anomaly Handling** | Autonomous variance filter drops blank takeoff frames | Sensitive to blank initial frames during early bundle adjustment |
| **Edge SBC Viability** | Deployable on drone companion computers (NVIDIA Jetson / Pi 5) | Workstation/server dependent (heavy Docker daemon requirement) |

---

## 📚 References
* **Lowe, D. G. (2004)**. *Distinctive image features from scale-invariant keypoints.* IJCV, 60(2), 91–110.
* **Fischler, M. A., & Bolles, R. C. (1981)**. *Random sample consensus: a paradigm for model fitting.* CACM, 24(6), 381–395.
* **Louhaichi, M., Borman, M. M., & Johnson, D. E. (2001)**. *Spatially located platform and aerial photography for documentation of grazing impacts on wheat.* Geocarto International, 16(1), 65–70. https://doi.org/10.1080/10106040108542184
* **Gitelson, A. A., et al. (2002)**. *Novel algorithms for remote estimation of vegetation fraction.* Remote Sensing of Environment, 80(1), 76–87.
* **Hartley, R., & Zisserman, A. (2003)**. *Multiple View Geometry in Computer Vision.* Cambridge University Press.
* **OpenCV Documentation (2024)**. *Camera Calibration and 3D Reconstruction.* https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html
