"""
Drone Aerial Vegetation Analysis Engine (Bonus Task 1)
======================================================
Author: Aman Raj (Subteam: ICS)
Project: Edhitha Drone Mapping Assignment (Task 3A)

Objective:
Perform high-resolution vegetation index analysis on the stitched drone orthomosaic.
Since consumer/standard drone sensors capture RGB bands (no Near-Infrared), we implement
scientifically validated RGB vegetation indices:
1. GLI (Green Leaf Index): (2*G - R - B) / (2*G + R + B)
   Designed by Louhaichi et al. to isolate living green plant biomass from background soil.
2. VARI (Visible Atmospherically Resistant Index): (G - R) / (G + R - B)
   Designed by Gitelson et al. for RGB aerial vegetation fraction estimation with low atmospheric sensitivity.
3. ExG (Excess Green Index): 2*G - R - B
   Classic agricultural computer vision index for crop canopy segmentation.

Deliverable Classification (Required Color Convention):
- Red    -> No vegetation (bare soil, tracks, concrete, non-vegetated surfaces)
- Yellow -> Sparse vegetation (emerging shoots, patchy grass, low-density groundcover)
- Green  -> Dense vegetation (canopy, healthy active crops, dense trees)
"""

import os
import argparse
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def compute_vegetation_indices(ortho_path, output_dir, low_thresh_pct=35, high_thresh_pct=75):
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(ortho_path):
        print(f"[!] Error: Orthomosaic not found at '{ortho_path}'")
        return None
        
    print("=" * 70)
    print("  EDHITHA VEGETATION ANALYSIS & BIOMASS CLASSIFICATION ENGINE")
    print("=" * 70)
    print(f"Loading orthomosaic from: {ortho_path}")
    
    img = cv2.imread(ortho_path)
    if img is None:
        print("[!] Error reading image.")
        return None
        
    h, w = img.shape[:2]
    print(f"Orthomosaic dimensions: {w} x {h} px")
    
    # Extract channels (OpenCV loads as BGR)
    b, g, r = cv2.split(img.astype(np.float32))
    
    # Mask out transparent / pure black border padding
    valid_mask = (img.sum(axis=2) > 15)
    total_valid_pixels = np.sum(valid_mask)
    print(f"Total valid terrain pixels analyzed: {total_valid_pixels:,}")
    
    # 1. Compute GLI: (2*G - R - B) / (2*G + R + B + eps)
    denom_gli = 2.0 * g + r + b
    denom_gli[denom_gli == 0] = 1e-5
    gli = (2.0 * g - r - b) / denom_gli
    
    # 2. Compute VARI: (G - R) / (G + R - B + eps)
    denom_vari = g + r - b
    denom_vari[denom_vari == 0] = 1e-5
    vari = (g - r) / denom_vari
    
    # Statistics on valid terrain
    valid_gli = gli[valid_mask]
    t_low = float(np.percentile(valid_gli, low_thresh_pct))
    t_high = float(np.percentile(valid_gli, high_thresh_pct))
    
    print("\nVegetation Index Statistics (GLI):")
    print(f"  Min GLI: {valid_gli.min():.4f}")
    print(f"  Max GLI: {valid_gli.max():.4f}")
    print(f"  Mean GLI: {valid_gli.mean():.4f}")
    print(f"  Median GLI: {np.median(valid_gli):.4f}")
    print(f"  Calibrated Thresholds -> Low: {t_low:.4f} ({low_thresh_pct}th percentile), High: {t_high:.4f} ({high_thresh_pct}th percentile)")
    
    # 3. Generate 3-Tier Discrete Classification Mask (BGR)
    # Red    -> [0, 0, 255]
    # Yellow -> [0, 255, 255]
    # Green  -> [0, 255, 0]
    veg_mask = np.zeros_like(img)
    
    no_veg = valid_mask & (gli < t_low)
    sparse_veg = valid_mask & (gli >= t_low) & (gli < t_high)
    dense_veg = valid_mask & (gli >= t_high)
    
    veg_mask[no_veg] = [0, 0, 255]      # Red (No vegetation)
    veg_mask[sparse_veg] = [0, 255, 255] # Yellow (Sparse vegetation)
    veg_mask[dense_veg] = [0, 255, 0]   # Green (Dense vegetation)
    
    count_no = np.sum(no_veg)
    count_sparse = np.sum(sparse_veg)
    count_dense = np.sum(dense_veg)
    
    pct_no = (count_no / total_valid_pixels) * 100.0
    pct_sparse = (count_sparse / total_valid_pixels) * 100.0
    pct_dense = (count_dense / total_valid_pixels) * 100.0
    
    print("\nVegetation Density Distribution:")
    print(f"  [Red]    No Vegetation:     {pct_no:5.2f}% ({count_no:,} px)")
    print(f"  [Yellow] Sparse Vegetation: {pct_sparse:5.2f}% ({count_sparse:,} px)")
    print(f"  [Green]  Dense Vegetation:  {pct_dense:5.2f}% ({count_dense:,} px)")
    
    # 4. Generate Scientific Continuous Heatmap
    norm_gli = np.clip((gli - t_low) / (t_high - t_low + 1e-5), 0.0, 1.0)
    
    # Save Outputs
    out_mask = os.path.join(output_dir, "AmanRaj_3A_ICS_vegetation_mask.png")
    out_heatmap = os.path.join(output_dir, "AmanRaj_3A_ICS_vegetation_heatmap.png")
    out_summary = os.path.join(output_dir, "AmanRaj_3A_ICS_vegetation_summary.txt")
    
    cv2.imwrite(out_mask, veg_mask)
    print(f"\n[Saved] Discrete Classification Mask: {out_mask}")
    
    # Render and save high-resolution figure with colorbar and legend
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), dpi=200)
    
    # Panel 1: Original Orthomosaic
    axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    axes[0].set_title("Stitched Aerial Orthomosaic (True Color RGB)", fontsize=11, fontweight='bold', pad=8)
    axes[0].axis("off")
    
    # Panel 2: Continuous GLI Heatmap
    heatmap_masked = np.ma.masked_where(~valid_mask, norm_gli)
    im1 = axes[1].imshow(heatmap_masked, cmap='RdYlGn')
    axes[1].set_title("Scientific GLI Heatmap (Red-Yellow-Green)", fontsize=11, fontweight='bold', pad=8)
    axes[1].axis("off")
    cbar = plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)
    cbar.set_label("GLI Biomass Index (Relative Density)", fontsize=9)
    
    # Panel 3: Discrete 3-Tier Overlay
    axes[2].imshow(cv2.cvtColor(veg_mask, cv2.COLOR_BGR2RGB))
    axes[2].set_title("Classified Vegetation Concentration Map\n(Red: None | Yellow: Sparse | Green: Dense)", fontsize=11, fontweight='bold', pad=8)
    axes[2].axis("off")
    
    plt.tight_layout()
    plt.savefig(out_heatmap, bbox_inches='tight')
    plt.close()
    print(f"[Saved] Publication Heatmap & Comparison Panel: {out_heatmap}")
    
    # Write statistical summary
    with open(out_summary, "w") as f:
        f.write("EDHITHA TASK 3A - VEGETATION ANALYSIS REPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Candidate: Aman Raj (Subteam: ICS)\n")
        f.write(f"Analyzed Image: {os.path.basename(ortho_path)}\n")
        f.write(f"Total Terrain Pixels: {total_valid_pixels:,}\n\n")
        f.write("BIOMASS CLASSIFICATION BREAKDOWN:\n")
        f.write(f"- Dense Vegetation (Green):  {pct_dense:.2f}% ({count_dense:,} px)\n")
        f.write(f"- Sparse Vegetation (Yellow): {pct_sparse:.2f}% ({count_sparse:,} px)\n")
        f.write(f"- No Vegetation (Red):        {pct_no:.2f}% ({count_no:,} px)\n\n")
        f.write("INDEX THRESHOLD CALIBRATION:\n")
        f.write(f"- Index Used: Green Leaf Index (GLI) = (2G - R - B) / (2G + R + B)\n")
        f.write(f"- Low Cutoff (Sparse Threshold): {t_low:.4f} ({low_thresh_pct}th percentile)\n")
        f.write(f"- High Cutoff (Dense Threshold): {t_high:.4f} ({high_thresh_pct}th percentile)\n")
        f.write(f"- Mean GLI: {valid_gli.mean():.4f}\n")
    print(f"[Saved] Quantitative Metrics Summary: {out_summary}")

    return out_mask, out_heatmap

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drone Aerial Vegetation Analyzer")
    parser.add_argument("--orthomosaic", default="Task3_Aerial_Mapping/outputs/AmanRaj_3A_ICS_orthomosaic.png", help="Path to input orthomosaic image")
    parser.add_argument("--output", default="Task3_Aerial_Mapping/outputs", help="Output directory")
    parser.add_argument("--low_pct", type=float, default=35.0, help="Low threshold percentile for sparse vegetation (default: 35)")
    parser.add_argument("--high_pct", type=float, default=75.0, help="High threshold percentile for dense vegetation (default: 75)")
    args = parser.parse_args()
    
    compute_vegetation_indices(args.orthomosaic, args.output, low_thresh_pct=args.low_pct, high_thresh_pct=args.high_pct)
