"""
Drone Aerial 3D Terrain & Surface Reconstruction Engine (Bonus Task 2)
======================================================================
Author: Aman Raj (Subteam: ICS)
Project: Edhitha Drone Mapping Assignment (Task 3A)

Objective:
Generate a 3D visualization and point cloud model of the surveyed terrain
using Structure-from-Motion (SfM) photogrammetry on overlapping drone captures.

Methodology & Algorithms:
1. Multiview Feature Correspondence:
   Extracts invariant SIFT keypoints and tracks correspondences across overlapping frames.
2. Epipolar Geometry & Essential Matrix Estimation:
   Computes the Essential Matrix E = [t]_x * R using the Five-Point / Eight-Point
   algorithm wrapped in RANSAC to reject moving or ambiguous vegetation matches.
3. Camera Pose Recovery:
   Decomposes E via Singular Value Decomposition (SVD) to retrieve relative rotation (R)
   and translation (t) vectors satisfying the cheirality condition (points in front of both cameras).
4. Direct Linear Transformation (DLT) Triangulation:
   Solves for 3D world coordinates X = (x, y, z) by minimizing reprojection error
   across ray intersections from nominal pinhole camera projection matrices P1 and P2
   (utilizing standard uncalibrated focal scaling f ~ 0.85 * w).
5. True-Color Photometric Sampling:
   Interpolates RGB pixel values from original high-resolution aerial imagery onto
   triangulated 3D spatial points.
6. Polygon File Format (.PLY) Export:
   Generates standard industry-compatible 3D files loadable in MeshLab, CloudCompare,
   Blender, or Windows 3D Viewer.
"""

import os
import glob
import argparse
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def save_ply(filename, points_3d, colors_rgb):
    """
    Saves a 3D point cloud with RGB vertex colors to ASCII PLY format.
    """
    num_points = len(points_3d)
    header = [
        "ply",
        "format ascii 1.0",
        f"element vertex {num_points}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar red",
        "property uchar green",
        "property uchar blue",
        "end_header\n"
    ]
    with open(filename, "w") as f:
        f.write("\n".join(header))
        for pt, col in zip(points_3d, colors_rgb):
            f.write(f"{pt[0]:.4f} {pt[1]:.4f} {pt[2]:.4f} {int(col[0])} {int(col[1])} {int(col[2])}\n")

def run_3d_reconstruction(input_dir, output_dir, step=2, max_frames=50):
    os.makedirs(output_dir, exist_ok=True)
    all_files = sorted(glob.glob(os.path.join(input_dir, "*.jpg")))
    
    # Filter header frames
    survey_files = all_files[4:]
    if max_frames:
        survey_files = survey_files[:max_frames]
        
    # Subsample by step to ensure healthy stereo baseline (disparity)
    sampled_files = survey_files[::step]
    
    print("=" * 70)
    print("  EDHITHA 3D TERRAIN & STRUCTURE-FROM-MOTION (SfM) ENGINE")
    print("=" * 70)
    print(f"Total survey frames available: {len(survey_files)}")
    print(f"Sampled frames for stereo baseline (step={step}): {len(sampled_files)}")
    
    # Pre-load and resize images for feature matching
    scale = 0.25
    images = []
    fnames = []
    for f in sampled_files:
        img = cv2.imread(f)
        if img is not None:
            h, w = img.shape[:2]
            small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            images.append(small)
            fnames.append(os.path.basename(f))
            
    h, w = images[0].shape[:2]
    # Approximate camera intrinsic matrix K (field of view ~ 65-70 deg)
    focal_length = 0.85 * w
    K = np.array([
        [focal_length, 0.0, w / 2.0],
        [0.0, focal_length, h / 2.0],
        [0.0, 0.0, 1.0]
    ], dtype=np.float64)
    
    print(f"Nominal Pinhole Camera Intrinsics Matrix (scaled):\n{K}")
    
    # SIFT feature extraction
    print("\n[Phase 1/3] Extracting SIFT Keypoints across sampled frames...")
    sift = cv2.SIFT_create(nfeatures=3000)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    
    kps_list = []
    des_list = []
    for img in images:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kp, des = sift.detectAndCompute(gray, None)
        kps_list.append(kp)
        des_list.append(des)
        
    all_3d_points = []
    all_colors = []
    camera_positions = [[0.0, 0.0, 0.0]]
    
    R_accum = np.eye(3, dtype=np.float64)
    t_accum = np.zeros((3, 1), dtype=np.float64)
    
    print("\n[Phase 2/3] Sequential Epipolar Geometry & 3D Triangulation...")
    for i in range(len(images) - 1):
        if des_list[i] is None or des_list[i+1] is None:
            continue
            
        matches = bf.knnMatch(des_list[i], des_list[i+1], k=2)
        good = [m for m, n in matches if m.distance < 0.72 * n.distance]
        
        if len(good) < 15:
            continue
            
        pts1 = np.float32([kps_list[i][m.queryIdx].pt for m in good])
        pts2 = np.float32([kps_list[i+1][m.trainIdx].pt for m in good])
        
        # Estimate Essential Matrix with RANSAC
        try:
            E, mask_e = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
            if E is None or E.shape != (3, 3):
                continue
            
            # Recover relative pose
            _, R_rel, t_rel, mask_pose = cv2.recoverPose(E, pts1, pts2, K)
        except Exception:
            # Skip degenerate frames during sharp drone turns
            continue
        
        # Compute projection matrices
        P1 = K @ np.hstack([R_accum, t_accum])
        
        R_next = R_accum @ R_rel
        t_next = t_accum + R_accum @ t_rel
        P2 = K @ np.hstack([R_next, t_next])
        
        camera_positions.append(t_next.ravel().tolist())
        
        # DLT Triangulation
        pts4d = cv2.triangulatePoints(P1, P2, pts1.T, pts2.T)
        pts3d = pts4d[:3] / (pts4d[3] + 1e-7)
        pts3d = pts3d.T
        
        # Filter valid points (in front of camera, reasonable depth)
        valid = (pts4d[3] > 0) & (np.abs(pts3d[:, 2]) < 150) & (np.abs(pts3d[:, 0]) < 150) & (np.abs(pts3d[:, 1]) < 150)
        pts3d_valid = pts3d[valid]
        
        # Color sampling
        img_rgb = cv2.cvtColor(images[i], cv2.COLOR_BGR2RGB)
        for pt2d, pt3d in zip(pts1[valid], pts3d_valid):
            x, y = int(round(pt2d[0])), int(round(pt2d[1]))
            if 0 <= x < w and 0 <= y < h:
                color = img_rgb[y, x]
                all_3d_points.append(pt3d)
                all_colors.append(color)
                
        R_accum, t_accum = R_next, t_next
        if (i + 1) % 5 == 0 or i == len(images) - 2:
            print(f"  [+] Triangulated pair {i + 1}/{len(images) - 1}: {len(pts3d_valid)} 3D points added.")

    all_3d_points = np.array(all_3d_points, dtype=np.float32)
    all_colors = np.array(all_colors, dtype=np.uint8)
    camera_positions = np.array(camera_positions, dtype=np.float32)
    
    print(f"\n[Phase 3/3] Point Cloud Filtering & Deliverable Export...")
    print(f"  Total raw 3D points triangulated: {len(all_3d_points):,}")
    
    # Statistical Outlier Removal (cull extreme 2% tails)
    if len(all_3d_points) > 100:
        z_vals = all_3d_points[:, 2]
        z_low, z_high = np.percentile(z_vals, 2), np.percentile(z_vals, 98)
        filter_mask = (z_vals >= z_low) & (z_vals <= z_high)
        clean_points = all_3d_points[filter_mask]
        clean_colors = all_colors[filter_mask]
    else:
        clean_points = all_3d_points
        clean_colors = all_colors
        
    print(f"  Clean 3D points after outlier rejection: {len(clean_points):,}")
    
    # Save PLY File
    out_ply = os.path.join(output_dir, "AmanRaj_3A_ICS_3D_pointcloud.ply")
    save_ply(out_ply, clean_points, clean_colors)
    print(f"  [Saved] 3D Point Cloud (.PLY format): {out_ply}")
    
    # Multi-Angle 3D Visualization Renders
    out_render = os.path.join(output_dir, "AmanRaj_3A_ICS_3D_reconstruction_preview.png")
    fig = plt.figure(figsize=(18, 6), dpi=200)
    
    # Subsample points for smooth rendering
    max_plot_pts = min(8000, len(clean_points))
    sub_idx = np.random.choice(len(clean_points), max_plot_pts, replace=False)
    sub_pts = clean_points[sub_idx]
    sub_cols = clean_colors[sub_idx] / 255.0
    
    # View 1: Perspective True-Color Point Cloud
    ax1 = fig.add_subplot(131, projection='3d')
    ax1.scatter(sub_pts[:, 0], sub_pts[:, 1], sub_pts[:, 2], c=sub_cols, s=1.8, alpha=0.85)
    ax1.plot(camera_positions[:, 0], camera_positions[:, 1], camera_positions[:, 2], 'r^-', markersize=4, label='Drone Trajectory')
    ax1.set_title("3D True-Color Surface Model\n(Photogrammetric Point Cloud)", fontsize=10, fontweight='bold', pad=8)
    ax1.set_xlabel("X (m)", fontsize=8)
    ax1.set_ylabel("Y (m)", fontsize=8)
    ax1.set_zlabel("Elevation Z (m)", fontsize=8)
    ax1.view_init(elev=32, azim=-45)
    ax1.legend(loc='upper right', fontsize=8)
    
    # View 2: Elevation Heatmap (Digital Elevation Model view)
    ax2 = fig.add_subplot(132, projection='3d')
    sc = ax2.scatter(sub_pts[:, 0], sub_pts[:, 1], sub_pts[:, 2], c=sub_pts[:, 2], cmap='terrain', s=1.8, alpha=0.85)
    ax2.set_title("Digital Elevation Model (DEM)\n(Colored by Height Z)", fontsize=10, fontweight='bold', pad=8)
    ax2.set_xlabel("X (m)", fontsize=8)
    ax2.set_ylabel("Y (m)", fontsize=8)
    ax2.set_zlabel("Elevation Z (m)", fontsize=8)
    ax2.view_init(elev=45, azim=-60)
    cbar = plt.colorbar(sc, ax=ax2, shrink=0.5, aspect=10)
    cbar.set_label("Relative Elevation (m)", fontsize=8)
    
    # View 3: Top-Down Orthogonal View
    ax3 = fig.add_subplot(133, projection='3d')
    ax3.scatter(sub_pts[:, 0], sub_pts[:, 1], sub_pts[:, 2], c=sub_cols, s=1.8, alpha=0.85)
    ax3.set_title("Nadir / Top-Down 3D Perspective\n(Orthogonal Surface Overview)", fontsize=10, fontweight='bold', pad=8)
    ax3.set_xlabel("X (m)", fontsize=8)
    ax3.set_ylabel("Y (m)", fontsize=8)
    ax3.set_zlabel("Elevation Z (m)", fontsize=8)
    ax3.view_init(elev=85, azim=-90)
    
    plt.tight_layout()
    plt.savefig(out_render, bbox_inches='tight')
    plt.close()
    print(f"  [Saved] Multi-View 3D Visualization: {out_render}")
    
    # Save Metrics Summary
    out_summary = os.path.join(output_dir, "AmanRaj_3A_ICS_3D_summary.txt")
    with open(out_summary, "w") as f:
        f.write("EDHITHA TASK 3A - 3D RECONSTRUCTION REPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Candidate: Aman Raj (Subteam: ICS)\n")
        f.write(f"Total Triangulated 3D Points: {len(clean_points):,}\n")
        f.write(f"Stereo Baseline Camera Poses: {len(camera_positions)}\n")
        f.write(f"Elevation Range (Z): {clean_points[:, 2].min():.2f}m to {clean_points[:, 2].max():.2f}m (Span: {clean_points[:, 2].max() - clean_points[:, 2].min():.2f}m)\n")
        f.write("Methodology: Structure-from-Motion (SfM) via SIFT feature matching, Essential Matrix RANSAC, SVD Pose Recovery, and DLT Triangulation.\n")
        f.write("Output Deliverable Format: Stanford Triangle Mesh / Point Cloud (.PLY) with 24-bit TrueColor RGB vertices.\n")
    print(f"  [Saved] 3D Summary: {out_summary}")
    
    # Mirror to Edhitha submission folder
    sub_dir = "C:/Users/amanr/Downloads/drone assignment/Edhitha_Google_Drive_Submission/Task_3A"
    os.makedirs(sub_dir, exist_ok=True)
    import shutil
    shutil.copy2(out_ply, os.path.join(sub_dir, "AmanRaj_3A_ICS_3D_pointcloud.ply"))
    shutil.copy2(out_render, os.path.join(sub_dir, "AmanRaj_3A_ICS_3D_reconstruction_preview.png"))
    shutil.copy2(out_summary, os.path.join(sub_dir, "AmanRaj_3A_ICS_3D_summary.txt"))
    print(f"  [Synced] Mirrored full-field 3D model to submission folder: {sub_dir}")
    
    return out_ply, out_render

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drone Aerial 3D Reconstruction")
    parser.add_argument("--input", default="Task3_Aerial_Mapping/raw_images", help="Path to input images folder")
    parser.add_argument("--output", default="Task3_Aerial_Mapping/outputs", help="Output directory")
    parser.add_argument("--step", type=int, default=2, help="Frame step interval for stereo baseline")
    parser.add_argument("--max_frames", type=int, default=60, help="Max frames for 3D reconstruction")
    args = parser.parse_args()
    
    run_3d_reconstruction(args.input, args.output, step=args.step, max_frames=args.max_frames)
