"""
Custom Drone Aerial Photogrammetry & Orthomosaic Stitching Engine
==================================================================
Author: Aman Raj (Subteam: ICS)
Project: Edhitha Drone Mapping Assignment (Task 3A)

Key Technical Advantages over Pre-existing Generic Tools:
1. Automated Quality Assurance & Blank Header Filtering:
   Detects and skips camera sensor calibration / fade-in frames (e.g. image00000-00003).
2. Constrained Affine Transformation Estimation:
   Uses Partial Affine models (scale + rotation + translation) rather than unconstrained
   projective homographies to prevent projective drift, perspective warping, and
   keystoning over extended flight transects.
3. Scale-Invariant Feature Transform (SIFT) with Sub-Pixel Refinement:
   Extracts robust multi-scale keypoints resilient to terrain scale changes, illumination
   variance, and drone altitude fluctuations.
4. RANSAC Geometric Inlier Filtering:
   Eliminates spurious keypoint matches across repetitive agricultural crop patterns.
5. Distance-Weighted Feathered Seam Blending:
   Seamlessly interpolates overlapping flight strips using distance transform weighting,
   eliminating seamlines, exposure mismatch, and vignetting.
"""

import os
import sys
import glob
import time
import argparse
import numpy as np
import cv2

def is_valid_survey_frame(img, max_white_ratio=0.35):
    """
    Quality control filter to detect blank sensor frames or overexposed fade-ins.
    """
    if img is None:
        return False, "Null image"
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean_val = np.mean(gray)
    std_val = np.std(gray)
    
    # Check if mostly pure white (e.g., initialization blank frames 00000-00003)
    white_pixels = np.sum(gray > 245) / gray.size
    if mean_val > 240 and white_pixels > max_white_ratio:
        return False, f"Blank Header Frame (mean={mean_val:.1f}, std={std_val:.1f}, white_ratio={white_pixels:.2f})"
        
    return True, "Valid"

def generate_feather_weights(h, w):
    """
    Generates a 2D distance-transform feathering mask to blend overlapping frames smoothly.
    Pixels near image boundaries get near-zero weight; central pixels get weight 1.0.
    """
    y_idx, x_idx = np.indices((h, w))
    dist_x = np.minimum(x_idx, w - 1 - x_idx)
    dist_y = np.minimum(y_idx, h - 1 - y_idx)
    dist = np.minimum(dist_x, dist_y).astype(np.float32)
    
    # Normalize between 0.05 and 1.0
    weights = cv2.normalize(dist, None, 0.05, 1.0, cv2.NORM_MINMAX)
    return weights

def build_orthomosaic(input_dir, output_dir, scale=0.12, max_frames=None):
    """
    Main stitching pipeline.
    """
    os.makedirs(output_dir, exist_ok=True)
    all_files = sorted(glob.glob(os.path.join(input_dir, "*.jpg")))
    
    if not all_files:
        print(f"[!] Error: No .jpg files found in '{input_dir}'")
        return None
        
    print("=" * 70)
    print("  EDHITHA AERIAL PHOTOGRAMMETRY & ORTHOMOSAIC ENGINE")
    print("=" * 70)
    print(f"Total raw captures found: {len(all_files)}")
    print(f"Processing scale factor: {scale} (effective downsample for memory efficiency)")
    
    # Phase 1: Quality Control & Image Loading
    print("\n[Phase 1/4] Quality Control & Frame Ingestion...")
    valid_frames = []
    skipped_frames = []
    
    for fpath in all_files:
        fname = os.path.basename(fpath)
        img = cv2.imread(fpath)
        is_valid, reason = is_valid_survey_frame(img)
        if is_valid:
            valid_frames.append((fname, fpath))
        else:
            skipped_frames.append((fname, reason))
            
    print(f"  [+] Valid survey frames identified: {len(valid_frames)}")
    if skipped_frames:
        print(f"  [-] Filtered header/degraded frames ({len(skipped_frames)}):")
        for fn, r in skipped_frames:
            print(f"      - {fn}: {r}")

    if max_frames is not None:
        valid_frames = valid_frames[:max_frames]
        print(f"  [*] Limiting processing to first {len(valid_frames)} frames as requested.")

    # Phase 2: Multi-Scale SIFT Feature Extraction & Sequential Pairwise Tracking
    print(f"\n[Phase 2/4] SIFT Feature Extraction & Pairwise Motion Estimation across {len(valid_frames)} frames...")
    sift = cv2.SIFT_create(nfeatures=2500, contrastThreshold=0.03, edgeThreshold=10)
    bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    
    # We will accumulate global affine matrices relative to the initial survey frame (frame 0)
    # H_global[i] maps coordinates in frame i to frame 0
    H_global = [np.eye(3, dtype=np.float64)]
    
    prev_kps, prev_des = None, None
    prev_fname = None
    frame_h, frame_w = None, None
    
    # Store resized images to avoid reloading from disk during blending
    resized_images = []
    
    start_time = time.time()
    
    for idx, (fname, fpath) in enumerate(valid_frames):
        img = cv2.imread(fpath)
        h, w = img.shape[:2]
        cur_w, cur_h = int(w * scale), int(h * scale)
        small = cv2.resize(img, (cur_w, cur_h), interpolation=cv2.INTER_AREA)
        resized_images.append(small)
        
        if frame_h is None:
            frame_h, frame_w = cur_h, cur_w
            
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        kps, des = sift.detectAndCompute(gray, None)
        
        if idx > 0:
            # Match with previous frame using Lowe's ratio test
            matches = bf.knnMatch(des, prev_des, k=2)
            good_matches = [m for m, n in matches if m.distance < 0.75 * n.distance]
            
            if len(good_matches) >= 8:
                src_pts = np.float32([kps[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([prev_kps[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                
                # Estimate Partial Affine (scale + rotation + translation)
                M, inliers = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=3.0)
                if M is not None:
                    M_homo = np.eye(3, dtype=np.float64)
                    M_homo[:2, :] = M
                    # H_{i -> 0} = H_{i-1 -> 0} * M_{i -> i-1}
                    H_cur = H_global[-1] @ M_homo
                    inlier_count = int(np.sum(inliers)) if inliers is not None else 0
                else:
                    print(f"  [!] Affine estimation failed between {prev_fname} and {fname}. Using identity step.")
                    H_cur = H_global[-1]
                    inlier_count = 0
            else:
                print(f"  [!] Insufficient matches ({len(good_matches)}) between {prev_fname} and {fname}.")
                H_cur = H_global[-1]
                inlier_count = len(good_matches)
                
            H_global.append(H_cur)
            if (idx + 1) % 15 == 0 or idx == len(valid_frames) - 1:
                print(f"  [+] Processed frame {idx + 1}/{len(valid_frames)} ({fname}): {len(good_matches)} matches, {inlier_count} inliers.")
        
        prev_kps, prev_des = kps, des
        prev_fname = fname

    # Phase 3: Global Canvas Geometry & Projection Bounding Box
    print("\n[Phase 3/4] Computing Global Coordinate Envelope & Canvas Bounds...")
    corners = np.float32([[0, 0], [frame_w, 0], [frame_w, frame_h], [0, frame_h]]).reshape(-1, 1, 2)
    
    all_corners = []
    for H in H_global:
        warped_c = cv2.perspectiveTransform(corners, H)
        all_corners.append(warped_c)
        
    all_corners = np.vstack(all_corners)
    x_min, y_min = np.int32(np.floor(all_corners.min(axis=0).ravel())) - 15
    x_max, y_max = np.int32(np.ceil(all_corners.max(axis=0).ravel())) + 15
    
    canvas_w = int(x_max - x_min)
    canvas_h = int(y_max - y_min)
    
    print(f"  Canvas Dimensions: {canvas_w} x {canvas_h} pixels")
    print(f"  Coordinate Origin Shift: tx = {-x_min}, ty = {-y_min}")
    
    # Translation matrix to shift the origin to (0, 0)
    T = np.array([[1.0, 0.0, -x_min], [0.0, 1.0, -y_min], [0.0, 0.0, 1.0]], dtype=np.float64)
    
    # Phase 4: Distance-Weighted Feather Blending
    print("\n[Phase 4/4] Feather Blending into Master Canvas...")
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.float32)
    weight_canvas = np.zeros((canvas_h, canvas_w), dtype=np.float32)
    
    feather_mask = generate_feather_weights(frame_h, frame_w)
    
    for i, (small_img, H) in enumerate(zip(resized_images, H_global)):
        H_canvas = T @ H
        
        warped_img = cv2.warpPerspective(small_img.astype(np.float32), H_canvas, (canvas_w, canvas_h), flags=cv2.INTER_LINEAR)
        warped_weight = cv2.warpPerspective(feather_mask, H_canvas, (canvas_w, canvas_h), flags=cv2.INTER_LINEAR)
        
        mask = (warped_weight > 0.01)
        canvas[mask] += warped_img[mask] * warped_weight[mask, np.newaxis]
        weight_canvas[mask] += warped_weight[mask]
        
        if (i + 1) % 20 == 0 or i == len(resized_images) - 1:
            print(f"  [+] Blended {i + 1}/{len(resized_images)} frames...")

    valid_mask = weight_canvas > 0
    canvas[valid_mask] /= weight_canvas[valid_mask, np.newaxis]
    orthomosaic = np.clip(canvas, 0, 255).astype(np.uint8)
    
    # Crop black bounding padding if necessary
    gray_ortho = cv2.cvtColor(orthomosaic, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray_ortho, 1, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
        orthomosaic_cropped = orthomosaic[y:y+h, x:x+w]
    else:
        orthomosaic_cropped = orthomosaic

    total_time = time.time() - start_time
    print(f"\n[✓] Orthomosaic generation completed in {total_time:.1f} seconds!")
    print(f"    Final Output Shape: {orthomosaic_cropped.shape[1]} x {orthomosaic_cropped.shape[0]} px")
    
    # Save Deliverables
    master_out = os.path.join(output_dir, "AmanRaj_3A_ICS_orthomosaic.png")
    preview_out = os.path.join(output_dir, "AmanRaj_3A_ICS_orthomosaic_preview.png")
    
    cv2.imwrite(master_out, orthomosaic_cropped)
    print(f"  [Saved] Full Orthomosaic: {master_out}")
    
    # Generate smaller web/doc preview
    preview_h = 1200
    preview_w = int(orthomosaic_cropped.shape[1] * (preview_h / orthomosaic_cropped.shape[0]))
    preview = cv2.resize(orthomosaic_cropped, (preview_w, preview_h), interpolation=cv2.INTER_AREA)
    cv2.imwrite(preview_out, preview)
    print(f"  [Saved] Preview Map: {preview_out}")
    
    return master_out

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drone Aerial Orthomosaic Generator")
    parser.add_argument("--input", default="Task3_Aerial_Mapping/raw_images", help="Path to input images folder")
    parser.add_argument("--output", default="Task3_Aerial_Mapping/outputs", help="Output directory")
    parser.add_argument("--scale", type=float, default=0.12, help="Image processing scale factor (default: 0.12)")
    parser.add_argument("--max_frames", type=int, default=None, help="Limit frames for fast testing")
    args = parser.parse_args()
    
    build_orthomosaic(args.input, args.output, scale=args.scale, max_frames=args.max_frames)
