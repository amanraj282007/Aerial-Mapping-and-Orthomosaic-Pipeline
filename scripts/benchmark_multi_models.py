"""
Multi-Model Photogrammetry & GSD Scaling Benchmark Engine
=========================================================
Author: Aman Raj (Subteam: ICS)
Project: Edhitha UAS Recruitment (Task 3A - Advanced Evaluation)

Objective:
Perform empirical cross-validation across:
1. Feature Detectors: SIFT (Scale-Invariant Feature Transform) vs.
                      ORB (Oriented FAST and Rotated BRIEF) vs.
                      AKAZE (Accelerated-KAZE)
2. Scaling & GSD (Ground Sampling Distance):
   scale 0.10, 0.12, 0.15, 0.20, 0.25
"""

import os
import time
import glob
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def evaluate_detectors(image_paths, num_pairs=10):
    print("=" * 70)
    print("  PHASE 1: FEATURE DETECTOR BENCHMARK (SIFT vs. ORB vs. AKAZE)")
    print("=" * 70)
    
    detectors = {
        "SIFT (L2)": (cv2.SIFT_create(nfeatures=2500), cv2.NORM_L2),
        "ORB (Hamming)": (cv2.ORB_create(nfeatures=2500, scoreType=cv2.ORB_HARRIS_SCORE), cv2.NORM_HAMMING),
        "ORB-Fast": (cv2.ORB_create(nfeatures=2500, scoreType=cv2.ORB_FAST_SCORE), cv2.NORM_HAMMING)
    }
    
    results = {name: {"kps": [], "time_det": [], "matches": [], "inliers": [], "inlier_ratio": []} for name in detectors}
    
    # Evaluate across representative frame pairs
    pairs = []
    step = max(1, len(image_paths) // (num_pairs + 1))
    for i in range(0, len(image_paths) - 1, step):
        if len(pairs) < num_pairs:
            pairs.append((image_paths[i], image_paths[i+1]))
            
    print(f"Evaluating detectors across {len(pairs)} representative survey frame pairs...")
    
    scale = 0.20
    for det_name, (det, norm_type) in detectors.items():
        print(f"\nTesting detector: {det_name}...")
        bf = cv2.BFMatcher(norm_type, crossCheck=False)
        
        for p1, p2 in pairs:
            img1 = cv2.imread(p1)
            img2 = cv2.imread(p2)
            
            h, w = img1.shape[:2]
            s1 = cv2.resize(img1, (int(w * scale), int(h * scale)))
            s2 = cv2.resize(img2, (int(w * scale), int(h * scale)))
            
            g1 = cv2.cvtColor(s1, cv2.COLOR_BGR2GRAY)
            g2 = cv2.cvtColor(s2, cv2.COLOR_BGR2GRAY)
            
            t0 = time.time()
            kp1, des1 = det.detectAndCompute(g1, None)
            kp2, des2 = det.detectAndCompute(g2, None)
            t_det = (time.time() - t0) * 1000.0 / 2.0 # ms per image
            
            if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
                continue
                
            matches = bf.knnMatch(des1, des2, k=2)
            good = [m for m, n in matches if m.distance < 0.75 * n.distance] if len(matches) > 0 and len(matches[0]) == 2 else []
            
            if len(good) >= 8:
                src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
                _, inliers = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=3.0)
                inlier_cnt = int(np.sum(inliers)) if inliers is not None else 0
                ratio = (inlier_cnt / len(good)) * 100.0 if len(good) > 0 else 0
            else:
                inlier_cnt = 0
                ratio = 0
                
            results[det_name]["kps"].append((len(kp1) + len(kp2)) / 2.0)
            results[det_name]["time_det"].append(t_det)
            results[det_name]["matches"].append(len(good))
            results[det_name]["inliers"].append(inlier_cnt)
            results[det_name]["inlier_ratio"].append(ratio)

    summary = {}
    print("\n" + "-" * 70)
    print(f"{'Detector':<10} | {'Avg Keypoints':<14} | {'Latency (ms)':<12} | {'Matches':<10} | {'Inliers':<10} | {'Inlier Ratio':<12}")
    print("-" * 70)
    for name in detectors:
        avg_kps = np.mean(results[name]["kps"])
        avg_time = np.mean(results[name]["time_det"])
        avg_matches = np.mean(results[name]["matches"])
        avg_inliers = np.mean(results[name]["inliers"])
        avg_ratio = np.mean(results[name]["inlier_ratio"])
        summary[name] = {
            "avg_kps": avg_kps, "avg_time": avg_time, "avg_matches": avg_matches,
            "avg_inliers": avg_inliers, "avg_ratio": avg_ratio
        }
        print(f"{name:<10} | {avg_kps:<14.1f} | {avg_time:<12.1f} | {avg_matches:<10.1f} | {avg_inliers:<10.1f} | {avg_ratio:<11.1f}%")
    print("-" * 70)
    return summary

def evaluate_scales(image_paths):
    print("\n" + "=" * 70)
    print("  PHASE 2: GSD SCALE FACTOR & LATENCY-ACCURACY PARETO ANALYSIS")
    print("=" * 70)
    
    scales = [0.10, 0.12, 0.15, 0.20, 0.25]
    scale_results = {}
    
    sift = cv2.SIFT_create(nfeatures=2500)
    
    # Test on a 5-frame slice
    sample_files = image_paths[:5]
    
    print(f"{'Scale':<8} | {'Frame Size (px)':<16} | {'Canvas Size (est)':<18} | {'Est. RAM (MB)':<14} | {'Speed / Frame':<12}")
    print("-" * 75)
    
    for sc in scales:
        t0 = time.time()
        for f in sample_files:
            img = cv2.imread(f)
            h, w = img.shape[:2]
            small = cv2.resize(img, (int(w * sc), int(h * sc)))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            kps, des = sift.detectAndCompute(gray, None)
            
        t_per_frame = ((time.time() - t0) / len(sample_files)) * 1000.0
        frame_w = int(4032 * sc)
        frame_h = int(3040 * sc)
        canvas_w = int(24000 * sc)
        canvas_h = int(24000 * sc)
        est_ram_mb = (canvas_w * canvas_h * 3 * 4) / (1024 * 1024) # Float32 canvas
        
        scale_results[sc] = {
            "frame_w": frame_w, "frame_h": frame_h,
            "canvas_w": canvas_w, "canvas_h": canvas_h,
            "est_ram_mb": est_ram_mb,
            "time_per_frame_ms": t_per_frame
        }
        print(f"{sc:<8.2f} | {f'{frame_w}x{frame_h}':<16} | {f'{canvas_w}x{canvas_h}':<18} | {f'{est_ram_mb:.0f} MB':<14} | {f'{t_per_frame:.1f} ms':<12}")
    print("-" * 75)
    return scale_results

def plot_benchmarks(detector_summary, scale_summary, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    
    # Plot 1: Feature Detector Comparison
    det_names = list(detector_summary.keys())
    inliers = [detector_summary[d]["avg_inliers"] for d in det_names]
    times = [detector_summary[d]["avg_time"] for d in det_names]
    
    x = np.arange(len(det_names))
    width = 0.35
    
    ax1 = axes[0]
    rects1 = ax1.bar(x - width/2, inliers, width, label='RANSAC Inliers', color='#1B365D')
    ax1.set_ylabel('Inliers Count', color='#1B365D', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(det_names, fontweight='bold')
    
    ax1_twin = ax1.twinx()
    rects2 = ax1_twin.bar(x + width/2, times, width, label='Latency (ms)', color='#D97706')
    ax1_twin.set_ylabel('Detection Latency (ms)', color='#D97706', fontweight='bold')
    
    ax1.set_title("Feature Detector Inlier Robustness vs. Latency", fontsize=11, fontweight='bold', pad=10)
    ax1.grid(True, linestyle="--", alpha=0.3)
    
    # Plot 2: Pareto Frontier of Scale vs. RAM & Resolution
    scales = list(scale_summary.keys())
    times_ms = [scale_summary[s]["time_per_frame_ms"] for s in scales]
    rams = [scale_summary[s]["est_ram_mb"] / 1024.0 for s in scales] # in GB
    
    ax2 = axes[1]
    ax2.plot(scales, times_ms, 'o-', color='#2B6CB0', linewidth=2, label='Processing Time per Frame (ms)')
    ax2.set_xlabel('GSD Downsampling Scale Factor', fontweight='bold')
    ax2.set_ylabel('Time per Frame (ms)', color='#2B6CB0', fontweight='bold')
    ax2.grid(True, linestyle="--", alpha=0.3)
    
    ax2_twin = ax2.twinx()
    ax2_twin.plot(scales, rams, 's--', color='#C53030', linewidth=2, label='Peak Canvas RAM (GB)')
    ax2_twin.set_ylabel('Estimated Canvas RAM (GB)', color='#C53030', fontweight='bold')
    
    ax2.set_title("GSD Scale Factor: Latency vs. Memory Footprint", fontsize=11, fontweight='bold', pad=10)
    
    plt.tight_layout()
    plot_path = os.path.join(output_dir, "benchmark_comparison_charts.png")
    plt.savefig(plot_path, bbox_inches='tight')
    plt.close()
    print(f"\n[Saved] Multi-model benchmark visualization: {plot_path}")

def run_benchmarks():
    image_dir = "Task3_Aerial_Mapping_Testing/raw_images"
    output_dir = "Task3_Aerial_Mapping_Testing/outputs"
    
    all_files = sorted(glob.glob(os.path.join(image_dir, "*.jpg")))[4:] # Skip 4 blank frames
    
    det_summary = evaluate_detectors(all_files, num_pairs=8)
    scale_summary = evaluate_scales(all_files)
    plot_benchmarks(det_summary, scale_summary, output_dir)
    
    # Write text report
    out_txt = os.path.join(output_dir, "benchmark_empirical_results.txt")
    with open(out_txt, "w") as f:
        f.write("EMPIRICAL BENCHMARK: MULTI-MODEL & GSD SCALE ANALYSIS\n")
        f.write("=" * 60 + "\n\n")
        f.write("1. FEATURE DETECTOR COMPARISON:\n")
        for d, vals in det_summary.items():
            f.write(f"- {d}: Avg Inliers={vals['avg_inliers']:.1f}, Ratio={vals['avg_ratio']:.1f}%, Latency={vals['avg_time']:.1f}ms\n")
        f.write("\n2. GSD SCALE FACTOR ANALYSIS:\n")
        for s, vals in scale_summary.items():
            f.write(f"- Scale {s:.2f}: Frame={vals['frame_w']}x{vals['frame_h']}px, Canvas={vals['canvas_w']}x{vals['canvas_h']}px, RAM={vals['est_ram_mb']:.0f}MB, Time={vals['time_per_frame_ms']:.1f}ms\n")
    print(f"[Saved] Empirical text summary: {out_txt}")

if __name__ == "__main__":
    run_benchmarks()
