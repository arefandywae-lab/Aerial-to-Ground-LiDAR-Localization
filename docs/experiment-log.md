# Experiment log

Running record of what was built, what was measured, and what failed. Numbers are copied from `results/*.json`
(never retyped from memory). Status of each entry: **done** = result file exists; **pending** = running or not started.
All results are **simulation only** (Gazebo Harmonic); claims do not transfer to real sensors without further evidence.

## 0. Setup (shared by all runs)

| Item | Value |
| --- | --- |
| Simulator | Gazebo Harmonic, ROS 2, `ogre2` renderer |
| Dev machine | Windows 10 host, WSL2 Ubuntu 24.04, RTX 4060 Ti 8 GB |
| World (current) | 30 x 20 m room, 18 random boxes, procedural blob+shape textures (`worlds/gen_world.py`) |
| Robot | diff-drive; 32-beam LiDAR (range 40 m, sigma 0.01 m), IMU, 640x480 camera (HFOV 1.2 rad, fx = 467.7) |
| LiDAR mapping | FAST-LIO2 -> map in `camera_init` frame, aligned to world with GT (`ros/eval_ate.align`) |
| Map cleaning | radius outlier removal (0.3 m, >= 4 neighbours), PCA normals (k = 12) -> 124,989 points |
| Map colour | mean colour of mapping images that see the point (z-buffer test); **uses GT camera poses** |
| Mapping session | `s0`: 287 images + GT poses |
| Query session | `q1`: 154 images + GT poses (different path from `s0`) |
| Success thresholds | (0.25 m, 2 deg), (0.5 m, 5 deg), (5 m, 10 deg) - Aachen-style, fixed before running; to be confirmed after experiment 1 |
| Harness | `vps/harness.py`: same query set for every method, GT from Gazebo; reports recall, median error, latency, prepare time, VRAM peak (device-wide, includes other GPU apps) |

Reproduce a run (inside WSL):

```bash
cd SlamProject/vps
python3 harness.py --method m0 --map /root/data/s0_img --queries /root/data/q1_img --out ../results/m0_q1.json
```

## 1. M0 - visual-only reference (done)

**What:** SIFT map triangulated from mapping images using **GT poses** (known-pose SfM, so no COLMAP pose error), descriptor-voting
retrieval over keyframes, 2D-3D matching in the top-5 keyframes, PnP + RANSAC + LM refinement. File: `vps/m0.py`.
It is the visual ceiling for this sim, not a LiDAR method.

| Metric | Value |
| --- | --- |
| Localized | 61.0 % (94 / 154) |
| Recall @ (0.25 m, 2 deg) | 50.0 % |
| Recall @ (0.5 m, 5 deg) | 55.8 % |
| Recall @ (5 m, 10 deg) | 59.7 % |
| Median error (localized only) | 0.043 m, 0.26 deg |
| Latency (median) | 52.5 ms / query |
| Prepare | 12.2 s |

Source: `results/m0_q1.json`.

## 2. M1 - LiDAR map rendered as images, SIFT matching (done, negative result)

**Idea (own implementation, borrowing the concept of rendering a LiDAR map into searchable images with 2D-3D provenance):**
render the coloured LiDAR map from virtual viewpoints, keep the map-point index per pixel, run SIFT on the render, and take each
keypoint's metric 3D position from the provenance. Retrieval and PnP are M0's, so only the map source differs. File: `vps/m1.py`.

Renderer: painter's-order point splatting (radius from depth), hole fill from the nearest rendered pixel (<= 12 px, provenance follows
the neighbour), grey sky, 1 px Gaussian blur. Virtual viewpoints = the 287 mapping poses.

| Variant | Localized | Recall @ (0.25 m, 2 deg) | Notes |
| --- | --- | --- | --- |
| Raw splat, radius 0.06 m, no hole fill | 0.0 % | 0.0 % | render had see-through holes and a dot-grid pattern |
| + hole fill, radius 0.06 m | 1.3 % | 0.6 % | median 11 m / 86 deg error: wrong poses |
| + hole fill, radius 0.03 m (final) | 0.6 % (1 / 154) | 0.6 % | the one success: 0.18 m / 0.72 deg |

Source: `results/m1_q1.json` (final variant).

**Diagnosis.** Render and real image at the *identical* pose have matching geometry, but SIFT finds few correspondences: about 24 of 695
real keypoints matched within 3 px at one test pose; summed over 4 test poses (ratio test 0.9), splat radius 0.03 m gave 217 good matches vs 144 at 0.06 m.
Cause: the sim textures are small blobs and hard-edged shapes; the coloured map (point spacing roughly 5 cm, estimated from a 1/20 subsample, not measured exactly) cannot
reproduce that detail, so the render is a low-pass version of the real image.

**Conclusion (scoped to this sim and this renderer):** SIFT on a colour render of a LiDAR map does not localize here; PnP itself is
sound. This is a negative result for RQ1, not evidence against the general idea.

## 3. M1 + LoFTR (done)

Same renders and provenance as M1, but query<->render matching with LoFTR (Kornia, `outdoor` weights, confidence > 0.5). Retrieval =
LoFTR match count against every 3rd render (96 renders); PnP + RANSAC + LM from the top-5 renders' matches. File: `vps/m1l.py`.

| Metric | M0 (visual ref.) | M1 + SIFT | **M1 + LoFTR** |
| --- | --- | --- | --- |
| Localized | 61.0 % | 0.6 % | **91.6 %** (141 / 154) |
| Recall @ (0.25 m, 2 deg) | 50.0 % | 0.6 % | **68.2 %** (105 / 154) |
| Recall @ (0.5 m, 5 deg) | 55.8 % | 0.6 % | **72.1 %** |
| Recall @ (5 m, 10 deg) | 59.7 % | 0.6 % | **73.4 %** (113 / 154) |
| Median error (localized only) | 0.043 m, 0.26 deg | 0.18 m, 0.72 deg (n = 1) | 0.082 m, 0.39 deg |
| Latency (median) | 52.5 ms | 35.6 ms | **9,397 ms** |
| Peak VRAM over baseline | 0 | 209 MiB (sampled, device-wide) | 1,457 MiB |
| Prepare | 12.2 s | 25.6 s | 12.7 s |

Source: `results/m0_q1.json`, `results/m1_q1.json`, `results/m1l_q1.json`.

**Reading the result (scoped to this sim, one world, one query session):**
- With a learned matcher the same renders work: recall at the strictest threshold is 68 % vs 50 % for the SIFT visual reference.
  The render/real texture gap that broke SIFT is not fatal for LoFTR.
- 18 % of queries (141 localized vs 113 within 5 m / 10 deg) returned a pose that was **wrong**, not "no pose". A confidence/inlier
  gate is needed before these poses can be trusted; the inlier count is already returned by `localize` but not yet used.
- Median error of correct poses is higher than M0 (0.082 m vs 0.043 m): render-based 3D points are less precise than triangulated ones.
- **Latency is not usable as is:** 9.4 s/query comes from brute-force LoFTR against all 96 renders. A global-descriptor retrieval
  step would cut this by orders of magnitude; the number above is a worst case, not a property of the approach.
- Caveats: M0 uses GT-pose triangulation (a fair ceiling for SIFT, not a deployed pipeline); LoFTR is a pretrained model that may have
  seen similar textures; single run, no seeds repeated yet; the queries share the world and textures with the mapping session.

## 3b. Audit follow-up: post-fix baseline, speed-up ablation, failure analysis (done, seed 0, q1)

**Supersedes the numbers in section 3.** Section 3 was produced with a renderer whose painter's order was reversed (near points
overwritten by far ones, `m1.py`). After the fix, M1-LoFTR seed 0 (`results/m1l_q1_s0.json`): localized 91.6 %, recall@(0.25 m, 2 deg) 70.8 %,
recall@(5 m, 10 deg) 75.3 %, p50 latency 9.3 s. All rows below are single runs (seed 0) on 154 queries; 1 query = 0.65 points, and RANSAC-seed
variance alone moved M0 by 4 points (50.0 % vs 53.9 %), so differences of 1-3 points are noise.

Speed-up variants (`vps/m1lf.py`; GPU exact z-buffer renderer, fp16 LoFTR, coarse-to-fine retrieval; `scripts/run_ablation.sh`), paired per query against the baseline:

| Variant | fp16 | coarse retrieval | Correct @0.25 m,2 deg (of 154) | Baseline-only / variant-only | p50 latency | Speed-up |
| --- | --- | --- | --- | --- | --- | --- |
| baseline (CPU painter) | no | no | 109 | - | 9.3 s | 1.0x |
| f0c0 (renderer only) | no | no | 106 | 11 / 8 | 9.4 s | 1.0x |
| f0c1 | no | yes | 107 | 11 / 9 | 3.3 s | 2.8x |
| f1c0 | yes | no | 104 | 13 / 8 | 6.1 s | 1.5x |
| f1c1 | yes | yes | 99 | 14 / 4 | 2.0 s | 4.6x |

Only f1c1 differs from the baseline beyond noise (14 vs 4 discordant queries, two-sided sign test p ~ 0.03, uncorrected for 4 comparisons, one seed).
Recommended default: f0c1. Renderer facts: the CPU painter differs from the exact z-buffer on 3-29 % of pixels (up to ~1 m in 3D at depth edges) but this
did not change accuracy (f0c0 vs baseline within noise); the GPU renderer matches a float64 reference exactly and is 4.3x faster at 1.2 M points
(82 vs 354 ms), no faster at the current 125 k points. Latency/VRAM were measured on an otherwise idle GPU; VRAM is the PyTorch allocator peak only.

**Failure analysis of the baseline's wrong poses (25 of 154, scripts in `scripts/diag/`).** Wrong poses are not low-inlier: median 204 inliers (p90 1,067) vs 758
for good poses, so an inlier gate does not remove them (precision of returned poses stays 82-85 % at gates 12-40 even at the lax (5 m, 10 deg)).
Inlier points are in front of the camera (0 % behind), so it is not a PnP flip. Instead position error = 2 x distance from the room centre (median ratio 1.00, 80 % within
0.9-1.1) and rotation error ~180 deg (80 % within 170-180): the returned pose is the **point reflection of the true camera through the room centre**.
Cause: `worlds/gen_world.py` textures all four perimeter walls with one image, making the room 180-deg symmetric (perceptual aliasing). This is a
world-design artefact; section 5 of the spec (repeating structure) should treat it as a deliberate variable, not leave it in the baseline.

**Task-difficulty caveat.** Every query lies 1.06 m (median; max 1.46 m) from its nearest mapping pose with a median yaw difference of 0.4 deg, so q1 retraces s0
almost exactly. All numbers here are best-case for viewpoint change.

## 3c. Dataset v2: clean textures, FAST-LIO2 map, reversed-direction queries (done)

Everything in sections 1-3b used dataset v1 (one texture shared by all four walls). v2 re-records the room with a unique texture per wall and per box
(`worlds/gen_world.py --distinct 1`), same layout and waypoints (recovered from v1 GT). Recorded with `scripts/collect_v2.sh`, evaluated by
`scripts/pipeline_v2.sh` / `scripts/finish_v2.sh`, summarised by `scripts/summarize_v2.py` (raw results in `results/v2/`).

| Session | Role | Images | Path |
| --- | --- | --- | --- |
| `s0v2` | mapping | 349 | rectangle at |x|<=12, |y|<=8, clockwise |
| `q1v2` | query | 380 | 1 m outside the map path, same direction (median 1.00 m from nearest map pose, yaw diff 0 deg) |
| `q2v2` | query | 394 | 1 m outside, **reversed direction** (median 1.15 m, yaw diff median 179 deg) |

**Map (FAST-LIO2 on `s0v2`).** ATE rmse 0.026 m, max 0.056 m, RPE(10 %) 0.017 m, drift 0.05 % of 78.7 m. 146,185 points in the world frame (extent matches the
room), 90 % of points coloured by at least one camera. Colours still use GT camera poses (as in v1).

Results (mean +- sample std over 3 RANSAC seeds, M1 = M1-LoFTR variant f0c1: fp32, coarse retrieval, 96-render-equivalent density):

| Queries | Method | Localized | Recall (0.25 m, 2 deg) | Recall (5 m, 10 deg) | Median error | p50 latency |
| --- | --- | --- | --- | --- | --- | --- |
| q1v2 | M0 | 85.9 +- 0.4 % | 72.4 +- 1.5 % | 82.8 +- 0.2 % | 0.046 m, 0.36 deg | 35 ms |
| q1v2 | M1-LoFTR | 93.4 % | **86.1 %** | **91.8 %** | 0.068 m, 0.25 deg | 3.7 s |
| q2v2 | M0 | 13.2 +- 0.8 % | 0.0 % | 0.0 % | 17.5 m, 135 deg | 34 ms |
| q2v2 | M1-LoFTR | 63.7 % | 13.7 % | 40.4 % | 1.03 m, 5.0 deg | 3.6 s |

**What the numbers support**
- The aliasing diagnosis (3b) is confirmed: M1-LoFTR wrong poses on q1v2 are 6 / 380 (1.6 %, v1: 25 / 154 = 16 %) and the point-reflection signature is gone
  (pos error / (2 x distance from centre) median 0.03, v1 1.00; none rotated > 170 deg). With the aliasing removed the inlier gate works: precision 99.7 % at 40 inliers (v1 ~85 %).
- Same-direction queries (q1v2): the LiDAR-map method beats the GT-posed visual reference at the strict threshold (86.1 % vs 72.4 %), at ~100x the latency.
- Reversed-direction queries (q2v2): the image-based map **cannot** serve a camera looking the other way (0 % at every threshold; its 13 % "localized" are all wrong poses).
  M1-LoFTR degrades to 13.7 % / 40.4 %. Note the M1 map is queried only through renders at the mapping poses, which all face the loop direction.

**What they do not support / caveats**
- The +- is RANSAC-seed variance only. M1-LoFTR gives bit-identical per-query results for all seeds (stable because LoFTR yields hundreds of inliers), so its +-0.0 is not evidence of low variance across worlds or sessions; M0 differs on 43-46 queries between seeds. World/trajectory/mapping-run variance is still unmeasured (TODO A11).
- One room, one layout, one texture set; queries are 1 m from the map path. M0 is a GT-pose upper bound for SIFT, not a deployable pipeline; map colours and the LiDAR-to-world alignment also use GT.
- q2v2 recovered from an unclean VM shutdown (bag metadata rebuilt with `ros2 bag reindex`, images re-dumped); bag contents verified readable (118 s, 87 m).

### 3d. Yawed virtual viewpoints (done, seed 0, deterministic across seeds)

Motivation: the M1 map is queried only through renders, and in 3c every render sits at a mapping pose, so all renders face the loop direction although the LiDAR map has 360 deg
of geometry. `vps/m1lf.py` (`M1LF_YAWS`) can add renders at the same positions with the camera yawed about world z. Run with `scripts/run_yaw.sh`; position density fixed
(`M1L_STEP=6`, 59 poses) so only the yaw set changes. fp32, coarse retrieval, seed 0.

| Queries | Virtual yaws | Renders | Localized | Recall (0.25 m, 2 deg) | Recall (5 m, 10 deg) | Wrong poses | p50 latency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| q2v2 (reversed) | 0 (control) | 59 | 59.6 % | 13.7 % | 39.6 % | 79 | 2.5 s |
| q2v2 (reversed) | 0, 90, 180, 270 | 236 | 83.8 % | **53.3 %** | **82.5 %** | **5** | 6.4 s |
| q1v2 (same dir.) | 0, 90, 180, 270 | 236 | 92.9 % | 85.0 % | 91.6 % | 5 | 6.4 s |

(q1v2 reference at 96 renders, yaw 0: 93.4 % / 86.1 % / 91.8 %, 6 wrong; the 1.1-point difference is 4 queries and the position density also differs, so no regression is claimed or excluded.)
The inlier gate stays reliable (precision at 40 inliers: 99.7 % on q2v2, 100 % on q1v2).

**Reading.** Yawed renders turn the reversed-direction case from mostly failing (13.7 % at the strict threshold, 79 wrong poses) to mostly working (53.3 %, 5 wrong poses). The image-based map
(M0) has no equivalent: it can only be matched from the viewpoints it was photographed from (0 % on q2v2). Cost: latency 2.5 s -> 6.4 s (retrieval scales with the number of renders).
Residual failures concentrate near the loop corners (q2v2: 75 % not-good within 3 m of a corner vs 33 % elsewhere; q1v2: 47 % vs 2 %), where the robot turns and sees close,
oblique walls; 90-deg yaw spacing leaves up to 45 deg of mismatch. A finer yaw set is a hypothesis, not tested.

**Caveat that limits this result.** The yaw set was chosen after seeing q2v2 fail, and q2v2's yaw difference (179 deg) coincides exactly with one of the added yaws. A fair test needs a
held-out query set with other yaw offsets (e.g. 45 and 135 deg) and ideally a second world (TODO A26).

### 3e. Held-out yaw test on q3v2 (done, seed 0)

`q3v2` (`scripts/collect_q3.sh`, 619 images): the robot drives a lane 0.5 m outside the map path and makes a full in-place 360 deg turn at 8 spots (`drive_waypoints.py`, waypoint
suffix `,s`). Median distance to the nearest map pose 0.61 m (max 1.00 m). **Design flaw, stated up front:** yaw is not uniform, because the legs between spots run
counter-clockwise (opposite to the map loop) and make up most of the images (348 of 619 within 150-180 deg of the nearest map pose's yaw); only ~84 images come from the spins. Results are therefore
stratified by the query's misalignment from the virtual yaws {0, 90, 180, 270} (distance in degrees to the nearest multiple of 90 of its yaw difference to the nearest map pose;
`scripts/summarize_q3.py`). The yaw set (and the idea) were fixed before this set was recorded, so it is a fair test of non-aligned viewpoints.

| Method | Misalignment | n | Correct (0.25 m, 2 deg) | OK (5 m, 10 deg) | Wrong poses | No pose |
| --- | --- | --- | --- | --- | --- | --- |
| M0 | all | 619 | 10.8 % | 12.6 % | 116 | 425 |
| M1-LoFTR, yaw 0 only (control) | all | 619 | 26.5 % | 46.8 % | 100 | 229 |
| M1-LoFTR, yaws 0/90/180/270 | all | 619 | **56.9 %** | **77.2 %** | **13** | 128 |
| yaw 0 / 4 yaws | 0-15 deg | 406 | 24.4 % / 63.8 % | 49.3 % / 84.7 % | 67 / 1 | 139 / 61 |
| yaw 0 / 4 yaws | 15-30 deg | 112 | 25.0 % / 42.0 % | 36.6 % / 58.0 % | 17 / 7 | 54 / 40 |
| yaw 0 / 4 yaws | 30-45 deg | 101 | 36.6 % / 45.5 % | 48.5 % / 68.3 % | 16 / 5 | 36 / 27 |

**Reading.** The yawed renders help at every misalignment, but the gain shrinks as the query yaw moves away from the rendered ones: +39 points (strict threshold) when aligned, +17 at 15-30 deg, +9 at 30-45 deg;
wrong poses fall 100 -> 13 overall. This supports the earlier hypothesis that a finer yaw spacing (e.g. 45 deg) is needed for arbitrary headings, which is not yet tested (it multiplies renders and latency).
M0 collapses (10.8 % / 12.6 %) because an image map can only be matched from the headings it was photographed from.

**Caveats.** One seed (results are seed-invariant for M1); bins mix positions and path types, so differences between bins within one run are confounded and only the paired yaw-0 vs 4-yaw comparison per bin is clean;
consecutive frames are highly correlated (a spin gives ~10 near-identical views), so the effective sample is much smaller than n; lane is 0.5-1 m from the map path, same room and textures.

### 3f. Vector retrieval, stage 1 without any download (done)

`scripts/retrieval_recall.py`: global descriptor = LoFTR coarse-backbone features (256 channels at 1/8 resolution) average-pooled over a grid, L2-normalised per cell, cosine search over the 236 renders
(room map, 59 positions x 4 yaws). A database view counts as correct if within 1.5 m and 45 deg of the query's GT pose; recall is computed over queries that have at least one such view (upper bound
97.1 % / 94.9 % / 100 % for q1v2 / q2v2 / q3v2).

| Queries | Grid | R@1 | R@5 | R@10 | R@20 | R@50 |
| --- | --- | --- | --- | --- | --- | --- |
| q1v2 | 1x1 | 5.4 | 21.7 | 42.0 | 56.9 | 86.2 |
| q1v2 | 3x4 | 8.4 | 34.7 | 50.4 | 79.1 | 95.4 |
| q2v2 | 1x1 | 3.7 | 7.8 | 11.8 | 17.6 | 35.8 |
| q2v2 | 3x4 | 4.0 | 18.4 | 27.3 | 50.8 | 76.7 |
| q3v2 | 1x1 | 2.9 | 8.9 | 15.2 | 24.7 | 47.0 |
| q3v2 | 3x4 | 6.0 | 21.0 | 32.1 | 57.8 | 76.7 |

**Reading.** Spatial grid pooling helps (1x1 -> 3x4), but a pooled matcher backbone is a weak place-recognition descriptor: a 50-view shortlist (21 % of this small database) still misses 23 % of the hard queries.
The urban database would have ~3,360 views, so a trained global descriptor is required (MegaLoc / DINOv2-based; needs a weights download, not yet approved). The per-query backbone time printed by the script (~0.6 s) includes reading PNGs
over the NTFS mount and is not a model latency. Single run; descriptors are deterministic.

### 3g. Vector retrieval, stage 2: MegaLoc (done)

Same database (236 renders), same queries and same correctness criterion as 3f; descriptor = MegaLoc (DINOv2-B backbone + optimal-transport aggregator, 228.6 M parameters, 915 MB weights, 8448-d L2-normalised;
GitHub gmberton/MegaLoc MIT + Hugging Face gberton/MegaLoc; code reviewed before running); input 238x322 RGB, ImageNet normalisation (`scripts/megaloc_recall.py`).

| Queries | R@1 | R@5 | R@10 | R@20 | R@50 | (3f pooled LoFTR 3x4: R@20 / R@50) |
| --- | --- | --- | --- | --- | --- | --- |
| q1v2 | 37.4 | 65.9 | 72.9 | 82.9 | 94.6 | 79.1 / 95.4 |
| q2v2 | 16.3 | 38.0 | 50.5 | 65.2 | 90.4 | 50.8 / 76.7 |
| q3v2 | 24.7 | 47.7 | 58.6 | 71.1 | 90.3 | 57.8 / 76.7 |

Forward time ~8.5 ms per image (batch of 32, RTX 4060 Ti, GPU-synchronised, image decoding excluded). The recall criterion is strict (1.5 m and 45 deg); views slightly outside it can still be matchable,
so recall@k is a lower bound on usefulness and the end-to-end numbers (below, `scripts/run_megaloc_e2e.sh`) are what counts.

### 3h. Learned confidence gate ("System One" head), first attempt: not good enough (done, CPU)

Features logged per query by `vps/m1l.py` for the MegaLoc runs (`results/v2/mega_q{1,2,3}v2_feat.npy`: inliers, inlier ratio, matches, top-1/top-2 retrieval counts and margin, distinct renders used, inlier spread, reprojection error,
median depth, position/heading distance between the PnP pose and the retrieved render). Logistic regression (ridge 10), **leave-one-session-out** over q1v2 / q2v2 / q3v2 (`scripts/confidence_gate.py`, `scripts/run_gate_variants.sh`).
Label = pose usable at (0.5 m, 5 deg); among returned poses 96.6 % / 82.1 % / 89.1 % are usable (q1v2 / q2v2 / q3v2). A first run with the strict label (0.25 m, 2 deg) was misleading (it mixes "imprecise" with "wrong"); two bugs of mine
(inlier count missing from the feature set; a shadowed loop variable) were fixed.

| Held-out session | AUROC inlier count (the plain gate) | AUROC learned (all features) | learned, reduced features | precision keeping top 50 % / 70 % of returned (learned vs inliers) |
| --- | --- | --- | --- | --- |
| q1v2 same direction | **0.994** | 0.976 | 0.77 | 1.00 / 1.00 vs 1.00 / 1.00 |
| q2v2 reversed | 0.506 (chance) | 0.748 | 0.72 | 0.93 / 0.90 vs 0.80 / 0.80 (all returned: 0.82) |
| q3v2 spins | 0.816 | 0.849 | 0.90 | 0.975 / 0.968 vs 0.963 / 0.956 (all returned: 0.89) |

**Findings.** (1) The inlier count, the standard confidence signal, is excellent when the viewpoint matches the map (0.994) and **no better than chance for reversed-direction queries (0.506)**: wrong poses there are confident.
(2) The learned head helps on the hard sessions but loses to the plain inlier count on the easy one when trained on the others; no variant wins everywhere, because the relation between the features and correctness differs between failure types.
(3) Against the deployment target (accepted poses >= 95 % usable, false accepts <= 1 % of queries) it fails on q2v2: keeping the top 50 % still leaves ~7 % wrong poses accepted (~2.8 % of all queries). Probabilities are only calibrated (Brier ~ constant rate) with the reduced feature set, and then no better than the base rate; with all features they are badly miscalibrated on q2v2 (Brier 0.74 vs 0.147).
(4) Three sessions from one room (two used for training) are too little to learn a transferable rule; this does not show that a learned gate cannot work, only that this one does not.

**What the data point to.** The missing information is not in per-pose statistics but in *consistency*: do independent candidate renders agree on the pose (consensus of PnP solutions from separate retrieved views), and does the pose agree with odometry over time (exp 8). Next: log per-candidate poses and a consensus feature, add sessions/worlds (TODO R3), then re-test; keep the plain inlier gate only for same-direction conditions.

### Recording-pipeline findings (audit 4)
A loaded `ros2 bag record` delivered ~2 % of messages up to 0.54 s late, so receive order was shuffled although the stamped data is intact (sort by stamp gives a clean 4 ms ramp).
`/gt/poses` is unstamped after the Pose_V -> TFMessage bridge, so GT time was previously inferred from receive order. Fixes: stamped `/gt/model` (PosePublisher),
`eval_ate.gt_track()` (refuses non-monotone legacy bags), image sort by stamp in `dump_session.py`, `ros/resort_bag.py` so FAST-LIO replays in sim-time order.
v1 bags verified identical under the new code. Windows ran out of virtual memory several times that day (WSL VM was killed once, losing buffered writes);
the pagefile was moved to C: (8 GB) and no run since has lost data.

## 4. Environment problems worth knowing (for reproducibility)

- The C: drive filled up (0 GB free) because Windows grew `pagefile.sys` to 30 GB under WSL memory pressure. Fixed by moving the
  pagefile to the A: drive; project data and the WSL distro live on A:.
- torch/kornia install into WSL needed a retry; installed `torch 2.6.0+cu124` and `kornia 0.8.3`, CUDA available.
- LoFTR `outdoor` weights (~45 MB) are downloaded by Kornia on first use from the original authors' host.

## 4. Series B (aerial map -> ground camera), first results: urban world, drone map (done, partial)

World `worlds/gen_urban.py` (200 x 200 m, 50 buildings, streets 10 m wide, alleys 3 m, facade textures from only 4 repeating variants), RTF 1.0 with sensors rendering. Recorded by `scripts/urban_record.sh`,
mapped by `scripts/urban_map.sh`. Drone: LiDAR (64 x 1024, 100 m) + camera (pitched 0.7 rad down) + IMU, 4 lanes at z = 45 m, 4 m/s, yaw following the travel direction
(VelocityControl linear commands are in the body frame: verified). Ground robot: camera only, street centre lines.

| Item | Value |
| --- | --- |
| Drone session `ud0` | 479 images (every 5th), 841 m path, GT frames incl. sensors from the bag |
| FAST-LIO2 on the drone flight | ATE rmse **0.083 m**, max 0.241 m, RPE(10 %) 0.107 m, drift 0.01 % of 841 m (config `ros/fastlio_drone.yaml`) |
| World-frame LiDAR map | 2,370,307 points (voxel 0.25 m), extent +-100 m, z up to 33.9 m (tallest building 35 m) |
| Ground session `ug1` | 819 images (every 6th), street grid x in +-50 m, y from -85 to 50 m, camera height 0.44 m |
| Map points seen by the drone camera | **60 %** (room: 90 %) |
| Uncoloured by class | ground/roof 35.4 %, facade 43.8 %; facade z<0.5 m: 72.7 %, 0.5-5 m: 61.9 %, 15-40 m: 26.7 %; **street-level facade (z<3 m): 64.8 % uncoloured** |

Facade-orientation statistics were **discarded**: PCA normals have arbitrary sign (only 1,607 points "faced -x"), so orientation classes carry no meaning.

**M0 (drone image map, GT-posed) on ground queries `ug1`: 0 % localized of 819** (every threshold). Plumbing control: M0 with the drone images as both map and queries localizes
95.4 % with 4.5 mm median error, so poses/extrinsics/frames of the drone data are consistent and the zero is a genuine cross-view failure of an image map photographed from 45 m.

Alignment check (`docs/figures/urban_alignment_check.png`, visual inspection of 6 pairs): at ground poses the rendered map lines up with the real image (building edges, sky gap, road perspective);
at drone poses the render is mostly blank because `render()` clipped depth at 25 m, a constant tuned for the 30 x 20 m room. Fixed: `M1_ZFAR` (default 25, use ~120 for the urban map).
Street-level render quality is poor (grey uncoloured road with sparse large splats, patchy facade colours), consistent with the coverage numbers.

**Not yet done for series B:** M1-LoFTR on `ug1` (needs ground-level virtual viewpoints and a vector-database retrieval: ~1,000 positions x several yaws is far too many renders for brute-force LoFTR), alleys, repeating-facade
analysis, tile streaming.
- Second unclean WSL shutdown while two GPU jobs ran side by side: Windows "low virtual memory" (vmmem 14.2 GB, WSL page cache ~10 GB after multi-GB bag I/O, other host programs ~22 GB committed). Nothing was lost this time (integrity check `scripts/diag/integrity.sh`); only the running jobs. Rules adopted: one heavy job at a time, drop the page cache after large-bag steps. A `.wslconfig` memory cap / `autoMemoryReclaim` would be a user-approved system change (not done).

### 4b. Headline test: M1-LoFTR on the urban ground queries (done; weak result, decision gate triggered)

Map: drone LiDAR map `map_ud0.npz` (2.37 M points, 60 % coloured), 3,360 ground-level virtual views (`vps/viewpoints.py`: 420 positions on a 6 m grid in free space x 8 yaws, camera height 0.44 m),
render far clip 120 m (`M1_ZFAR`), MegaLoc shortlist 50 -> coarse LoFTR -> full LoFTR on 12 -> PnP (`scripts/urban_m1_test.sh`). Queries: every 4th image of `ug1` (205 of 819), ground camera along the street grid.

| Metric | Value |
| --- | --- |
| Pose returned | 21.5 % |
| Within (0.25 m, 2 deg) | **0.0 %** |
| Within (0.5 m, 5 deg) | **2.0 %** |
| Within (5 m, 10 deg) | **9.8 %** |
| Median error of returned poses | 7.7 m, 5.7 deg |
| p50 latency | 2.26 s |
| (M0 on all 819, drone-image map) | 0 % |

**Decision gate (set before the run):** below ~20 % at (5 m, 10 deg) -> stop optimisation work and diagnose. Triggered. Honest status: the claim "a drone-built LiDAR map lets a camera-only ground robot localize in a city" is **not supported by this
run**; it is better than the image-map baseline (0 %) but nowhere near usable. Causes are being separated (retrieval vs matching/render quality vs the 65 % uncoloured street-level facades): see 4c when done.

### 4c. Why the urban test is weak: diagnosis (done; 205 queries `ug1s`, `scripts/urban_diag.py`, `scripts/urban_d0.py`)

| Test | What it isolates | Result |
| --- | --- | --- |
| D2 retrieval (MegaLoc over 3,360 views; "close" view = within 4 m and 30 deg) | retrieval | 88.8 % of queries have a close view; R@1 7.7, R@10 37.4, R@50 62.6, R@100 74.7 % |
| D1 oracle: LoFTR + PnP against the view nearest the GT pose (gap: median 2.55 m, max 8.8 m, yaw median 0) | matching if retrieval were perfect | pose returned 2.4 %, within (5 m,10 deg) 2.4 %, median confident matches 6, median inliers 0 |
| D0 zero gap: render at the query's own GT pose, LoFTR + PnP | render/appearance gap alone | confident matches median 7 (p90 19), inliers median 0, within (5 m,10 deg) **8.8 %**, (0.5 m,5 deg) 2.9 % |
| D3 colour fraction of oracle views | colour coverage | median 0.25; success does not rise with colour fraction (10 % / 3 % / 1 % in the three populated bins, small n) |
| D0 after filling unseen points from coloured neighbours (`scripts/fill_colors.py`, 0.75 m, k 5; unseen 40 % -> 5.2 %) | causal test of the grey-speckle hypothesis | matches median 13 (p90 73), within (5 m,10 deg) **35.1 %**, (0.5 m,5 deg) 17.1 % |

**Conclusion.** The geometry is fine (building silhouettes, sky gaps and road perspective line up in the render at GT poses; FAST-LIO ATE 8 cm); the failure is **appearance**: even with zero viewpoint gap only 8.8 % localize, and retrieval is a second, smaller problem.
Visual inspection (`docs/figures/urban_d0_examples*.png`): facades are speckled (coloured and grey points interleaved) with no window rectangles, near road is a set of large grey/colour blobs, road markings are missing.
Filling unseen colours raised D0 from 8.8 % to 35.1 %, so colour coverage is a large part of the gap but not all: remaining defects seen in the filled renders are colour bleeding (road points next to facades take facade colours because the fill ignores surface type),
speckled facades and sparse near-field ground. Even a zero-gap 35 % is far from usable, so polishing alone may not be enough; geometry-based matching is the alternative (see TODO C-geo).

### 4d. Render fidelity ladder (done; D0 benchmark, `scripts/run_c_render.sh`)

Class-aware colour fill (`scripts/fill_colors2.py`: neighbours within 1 m whose |n.n'| > 0.8; unseen 40 % -> 4.6 %) and splat size. The default splat radius (0.03 m) had been tuned for the 0.1 m room map; the urban map uses 0.25 m voxels.

| D0 (render at the query's GT pose, 205 queries) | Confident matches (median) | Within (5 m,10 deg) | Within (0.5 m,5 deg) |
| --- | --- | --- | --- |
| original map, splat 0.03 m / 4 px | 7 | 8.8 % | 2.9 % |
| naive colour fill (4c) | 13 | 35.1 % | 17.1 % |
| class-aware fill, 0.03 m / 4 px | 12 | 32.2 % | 14.6 % |
| class-aware fill, splat 0.12 m / 4 px | 59 | 69.8 % | 21.5 % |
| class-aware fill, splat 0.12 m / 8 px | 68 | 73.2 % | 24.4 % |

**Reading.** Matching the splat size to the map's voxel size is the dominant fix (32 % -> 70 %); the class-aware fill is not measurably better than the naive one on this metric (32.2 vs 35.1 %, within noise at n = 205) although it avoids visible bleeding.
Even at zero viewpoint gap only ~22-24 % are within (0.5 m, 5 deg): the precision of the 3D points taken from the render (0.25 m voxels, hole-filled pixels, range amplification) limits fine accuracy; this is what render-and-refine (TODO A28) targets.
Budget set in advance (stop if D0 within (5 m,10 deg) < 70 % after these steps): met at 69.8 % (4 px) / 73.2 % (8 px); end-to-end re-test (C-decide) below.

### 4e. Urban end-to-end re-test after the render fixes (C-decide; same 205 queries; `scripts/urban_m1_test2.sh`)

Map `map_ud0_f2.npz` (class-aware fill), splat 0.12 m / 4 px, far clip 120 m, 3,360 ground-level views, MegaLoc shortlist 50 -> LoFTR -> PnP.

| Metric | before (4b) | after |
| --- | --- | --- |
| Pose returned | 21.5 % | **88.8 %** |
| Within (5 m, 10 deg) | 9.8 % | **50.2 %** |
| Within (0.5 m, 5 deg) | 2.0 % | **23.4 %** |
| Within (0.25 m, 2 deg) | 0.0 % | 2.0 % |
| Median error of returned poses | 7.7 m, 5.7 deg | **0.94 m, 0.90 deg** |
| p50 latency | 2.26 s | 2.34 s |
| Inlier gate >= 40: returned / precision at (5 m,10 deg) | 1.5 % / 100 % | 73.7 % / **63.6 %** |

Decision gate (>= 30 % within (5 m,10 deg)): passed, so the appearance-based path continues (C-geo not triggered). **Still far from the proposed acceptance criteria** (accepted poses >= 95 % usable, false accepts <= 1 %).
Warning sign: among poses with >= 40 inliers (74 % of queries) only 63.6 % are within (5 m, 10 deg), i.e. the standard confidence signal accepts many confident wrong poses in the city; the four repeating facade textures make aliasing likely (not yet verified by the signature test used in the room).
A single run (n = 205, one session, one map, quarter of the ground queries, seed-invariant method); the same queries were used to choose the render fixes (class-aware fill, splat size) so the comparison is within one set, not held out.

### 4f. Where the remaining urban failures come from (diagnosis repeated with the fixed render; same 205 queries)

| Stage | Within (5 m,10 deg) | Notes |
| --- | --- | --- |
| render at the query's own GT pose, matched (D0, 4d) | ~70-73 % | zero viewpoint gap; ~27 % still fail to match |
| nearest of the 3,360 views to the GT pose (D1; gap median 2.55 m, max 8.8 m, yaw median 0) | 62.4 % (strict 21.0 %) | the 6 m x 45 deg view grid costs ~8-10 points |
| MegaLoc retrieval over all views (D2, "close" = 4 m and 30 deg) | R@1 18.7, R@10 48.9, **R@50 69.8**, R@100 76.9 % | was R@50 62.6 % before the render fix |
| full pipeline (4e) | **50.2 %** | retrieval is the largest single loss, then grid gap, then matching |

Colour fraction of the oracle view: the success rate does not rise with it (bins 0.25-0.5: 66.4 %, 0.5-1.0: 52.2 %; n = 131 / 69), so more colour is not simply better (wide-open views probably contain more distant, ambiguous structure; not tested).
Levers, each addressing one measured loss: a denser view grid (needs tiling: 13 k views would not fit in memory at once), a stronger or position-aware retrieval (a position prior removes the global-search problem: tested in 4g), render-and-refine for the strict threshold (A28).

### 4g. Position-prior ("tracking") mode on the urban queries (done; same 205 queries; `scripts/run_prior_test.sh`, `scripts/gate_curve.py`)

A robot that has odometry knows roughly where it is after the first fix; global search over the whole city is the hard case only for start-up and kidnapping. Simulated prior: GT xy + Gaussian noise per query (sigma 5 or 10 m);
candidate views limited to a radius around it (20 / 35 m); everything else as 4e (MegaLoc shortlist 50 within that set -> LoFTR -> PnP).

| | no prior | prior sigma 5 m, radius 20 m | prior sigma 10 m, radius 35 m |
| --- | --- | --- | --- |
| Within (5 m,10 deg) | 50.2 % | **81.5 %** | 71.7 % |
| Within (0.5 m,5 deg) | 23.4 % | 31.7 % | 28.3 % |
| Median error (returned) | 0.94 m | 0.55 m | 0.61 m |
| p50 latency | 2.34 s | 2.32 s (K and top-N unchanged) | 2.33 s |

Accepted-pose quality by inlier gate (accepted = fraction of ALL queries):

| Run, gate | accepted | within (5 m,10 deg) | within (1 m,5 deg) | within (0.5 m,5 deg) | gross-wrong accepted (% of all queries) |
| --- | --- | --- | --- | --- | --- |
| no prior, >= 40 | 73.7 % | 63.6 % | 59.6 % | 31.1 % | 26.8 % |
| prior 5 m, >= 40 | 71.7 % | 97.3 % | 85.0 % | 43.5 % | 2.0 % |
| prior 5 m, >= 80 | 59.0 % | 98.3 % | 88.4 % | 47.9 % | **1.0 %** |
| prior 5 m, >= 150 | 46.3 % | 98.9 % | 89.5 % | 46.3 % | 0.5 % |
| prior 10 m, >= 80 | 60.0 % | 91.9 % | 81.3 % | 41.5 % | 4.9 % |

**Reading.** With a +-5 m prior the plain inlier gate becomes usable: gross errors among accepted poses drop from 36 % to ~2 % (1 % at gate 80, 59 % of queries accepted), which suggests that most confident wrong poses in the no-prior case came from searching the
whole city (aliasing between similar streets), not from bad matching. Against the proposed criteria: gross-wrong accepted <= 1 % of queries is met at gate 80; fine accuracy is NOT: only 48 % of accepted poses are within (0.5 m, 5 deg) (88 % within 1 m), so the
render-based 3D points limit precision (render-and-refine, A28). A +-10 m prior is clearly worse than +-5 m (gross-wrong 4.9 % at gate 80), so the benefit depends on prior quality.
Caveats: the prior is iid Gaussian around GT (real odometry errors are correlated and can exceed 10 m after a kidnapping); same 205 queries that were used to choose the render fixes (held-out re-test: 4h); one session, one map, four repeating facade textures.

### 4h. Re-test on disjoint queries (done; `scripts/urban_heldout.sh`, 205 queries `ug1h` = every 4th frame, offset 2; no re-tuning)

| | tuned set (ug1s) | disjoint set (ug1h) |
| --- | --- | --- |
| prior 5 m: within (5 m,10 deg) | 81.5 % | 80.5 % |
| prior 5 m: within (0.5 m,5 deg) | 31.7 % | 35.6 % |
| prior 5 m, gate >= 80: accepted / within (5 m,10 deg) / within (1 m,5 deg) / within (0.5 m,5 deg) / gross-wrong (% of all) | 59.0 / 98.3 / 88.4 / 47.9 / 1.0 % | 59.0 / 98.3 / 85.1 / 52.9 / 1.0 % |
| no prior: within (5 m,10 deg) | 50.2 % | 54.6 % |
| no prior, gate >= 40: precision at (5 m,10 deg) | 63.6 % | 68.2 % |

The disjoint set reproduces the tuned-set numbers, so the render fixes were not over-fitted to those exact frames. **Limit of this check:** the two sets are interleaved frames of the same route (neighbours ~0.2 s apart), not an independent route or world;
generalisation to unseen streets and to a second world is still untested (TODO C-heldout stays open).

### 4i. Render-and-refine (A28): no gain (done; prior 5 m / radius 20 m; `scripts/urban_refine_test.sh`)

After the first PnP, render the map at the estimated pose, match the query to that render and re-solve (2 iterations, result kept only if inliers >= half of the first solution's).

| | ug1h no refine | ug1h refine x2 | ug1s no refine | ug1s refine x2 |
| --- | --- | --- | --- | --- |
| Within (5 m,10 deg) | 80.5 % | 80.5 % (identical per query) | 81.5 % | 81.5 % (identical) |
| Within (0.5 m,5 deg) | 35.6 % | 33.7 % | 31.7 % | 34.1 % |
| Median error | 0.543 m | 0.546 m | 0.552 m | 0.554 m |
| p50 latency | 2.32 s | 2.44 s | 2.32 s | 2.45 s |

**Reading.** No improvement (one set up, one down, within noise), +0.13 s latency. The fine-accuracy limit is therefore not the viewpoint gap that refinement removes but the quality of the 3D points taken from the render: the provenance point is the voxel centre
(0.25 m voxels) of the nearest map point, up to ~0.12 m off the true surface along the pixel ray, amplified at the 20-40 m ranges of a street canyon; refinement reuses the same provenance. Test of that explanation: intersect each pixel ray with the plane
of its provenance point (map normals): 4j.

### 4j. Plane-corrected provenance: worse (done; held-out ug1h, prior 5 m; `scripts/urban_plane_test.sh`)

Each correspondence's 3D point replaced by the intersection of the pixel's viewing ray with the plane through the provenance point (map normals) where the ray is not grazing and the correction is < 0.5 m (`M1_PLANE=1`).

| ug1h | voxel-centre provenance | plane-corrected |
| --- | --- | --- |
| Within (0.5 m,5 deg) | 35.6 % | 27.3 % |
| Within (0.25 m,2 deg) | 3.9 % | 0.5 % |
| Within (5 m,10 deg) | 80.5 % | 80.5 % |
| Median translation error, accepted (>= 80 inliers, n = 121) | 0.484 m (IQR 0.40-0.66) | 0.575 m (IQR 0.44-0.80) |
| Median rotation error, accepted | 0.40 deg | 0.38 deg |

The hypothesis "per-point 3D precision of the voxel-centre provenance limits fine accuracy" is **not supported** (worse). The accepted poses have a narrow translation-error band (0.40-0.66 m) with small rotation error (0.4 deg): a consistent offset of ~0.5 m rather than random per-query noise,
which points at the reference frame (map vs GT world) or a systematic effect, not at matching. Next: save predicted poses and analyse the error vectors (4k).

### 4k. Where the ~0.5 m urban translation error comes from (done; ug1h, prior 5 m, accepted = >= 80 inliers and not gross-wrong, n = 119; `scripts/error_field.py`, `scripts/map_bias.py`, `scripts/rot_trans_coupling.py`)

1. **The map is registered to the world within ~1 cm** where it matters: checked against exact SDF geometry (ground median z -0.007 m, ground-plane tilt 0.002 deg, wall planes of all four orientations within +-0.01 m median, IQR +-4 cm). Roofs read +0.27 m but that is a 98th percentile of
   0.25 m voxel centres, not representative of street level. So the error is **not** a map-to-GT frame offset (my earlier suspicion was wrong).
2. Mean world-frame error (0.08, 0.13, **+0.38**) m; in the camera frame (right, down, forward) (0.04, **-0.39**, 0.21) m; it is spatially smooth (median error 0.484 -> 0.220 m after removing the mean of other poses within 12 m).
3. **Rotation-translation coupling explains the scatter:** translation error down vs pitch error: correlation **+0.95**, slope +34.6 m/rad; right vs yaw: **-0.92**, -39.6 m/rad. A slope of 35-40 m/rad matches the depth of the street-canyon structure: with distant points, PnP cannot separate a
   0.5 deg pitch/yaw error from a ~0.3 m shift. Rotation errors per axis (deg): mean (-0.13, 0.03, -0.14), std (0.51, 0.41, 0.32); a constant vertical offset of about 0.3 m remains at zero pitch error (regression intercept), cause not identified.
4. Things that did **not** help: render-and-refine (4i), plane-corrected provenance (4j).

Implication: fine accuracy in deep streets is limited by weak conditioning of the pose from far structure, which a gravity direction from the robot's IMU can remove (fixes pitch and roll; only yaw and position are solved): tested in 4l.

### 4l. Gravity-aided 4-DoF refinement (done; ug1h, prior 5 m; `scripts/urban_gravity_test.sh`, `scripts/diag/patch_gravity.py`)

Simulated IMU gravity direction (GT + rotation noise per axis) fixes pitch and roll; yaw and position are solved by Huber-weighted reprojection error over the PnP inliers (`m1l.grav_refine`).

| ug1h, prior 5 m | no IMU | IMU noise 0.1 deg | IMU noise 0.5 deg |
| --- | --- | --- | --- |
| Within (0.5 m,5 deg), all queries | 35.6 % | 40.0 % | 29.3 % |
| Accepted (>= 80 inliers), n = 119/120/120: within 0.5 m / 1 m | 53.8 % / 86.6 % | 58.3 % / 91.7 % | 40.8 % / 85.8 % |
| Median translation error, accepted | 0.484 m | 0.456 m | 0.553 m |
| Median rotation error, accepted | 0.38 deg | 0.22 deg | 0.74 deg |
| Within (5 m,10 deg) | 80.5 % | 79.5 % | 79.5 % |

**Reading.** A gravity direction good to 0.1 deg helps only a little (+4-5 points at 0.5 m; median 0.484 -> 0.456 m) and a 0.5 deg IMU is **worse than no IMU**. The translation-pitch correlation of 0.95 (4k) is a symptom, not the root cause: once rotation is constrained, the underlying
systematic error (a constant ~0.3 m vertical offset, cause not identified) is absorbed by the translation. Three attempts to improve fine accuracy (render-and-refine 4i, plane-corrected provenance 4j, gravity prior 4l) each moved the 0.5 m figure by at most ~5 points (two of them down or flat).
Decision: stop chasing sub-0.5 m accuracy; state the measured level (accepted poses at gate >= 80: ~54-58 % within 0.5 m, ~87-92 % within 1 m, median ~0.46-0.48 m) and leave the offset as an open problem (TODO C-const). Remaining untested candidates: bias of the provenance points of near-field ground (two voxel layers at +-0.125 m),
a depth-dependent weighting of correspondences, and the 0.25 m voxel size itself (a finer map).

### 4m. Independent route (route 2) and drone coverage of what the ground robot sees (done; `scripts/urban_route2.sh`, `route2_segments.py`, `obs_count.py`)

Route 2 (`ug2`, 285 evaluated queries = every 2nd dumped frame): street y=0 (never driven) plus the opposite direction on y=-50, x=50, x=-50; evaluated with the SAME settings as 4g/4h, no re-tuning.

| prior 5 m / radius 20 m | interleaved frames of the tuned route (4h) | **route 2** |
| --- | --- | --- |
| Within (5 m,10 deg), all queries | 80.5 % | **72.3 %** |
| Within (0.5 m,5 deg) | 35.6 % | 27.4 % |
| Median error | 0.543 m | 0.645 m |
| Gate >= 80: accepted / within (5 m,10 deg) / within (1 m,5 deg) / within (0.5 m,5 deg) | 59.0 / 98.3 / 85.1 / 52.9 % | 62.1 / **90.4** / 85.9 / 37.9 % |
| **Gross-wrong accepted at gate >= 80 (% of all queries)** | 1.0 % | **6.0 %** (2.8 % at gate >= 150, 41.8 % accepted) |
| No prior: within (5 m,10 deg) | 54.6 % | 46.0 % |

**Correction of earlier wording:** "98 % of accepted poses correct, 1 % gross-wrong" (4g/4h) is **not** reproduced on an independent route (90.4 % / 6.0 %); the earlier figure was inflated by tuning/evaluating on interleaved frames of one route. The acceptance target (gross-wrong <= 1 %) is not met.
Per street segment (prior, no gate; within (5 m,10 deg) / gross-wrong): y=-50 east 97.6 % / 0 %; x=50 north 92.9 % / 4.8 %; **y=0 west, a street never driven: 92.9 % / 7.1 %** (in the 67 queries >5 m from any ug1 pose: 100 % within, 0 gross-wrong);
**x=-50 south 28.6 % / 54.8 %**; second y=-50 east pass 74.4 % / 23.3 %; start segment (x=0 north, y -85..-50) only 15.6 % returned a pose. Failures concentrate in specific streets, not in "unseen" or "reversed" streets as such.

Drone coverage of what a ground robot sees (observation counts, same z-buffer visibility test as the colouring): street-level facade points (z < 3 m): **seen by 0 drone images 64.8 %, by >= 3 images 19.2 %, median count 0**; facade 3-10 m: 54.7 % unseen; >= 10 m: 32.3 %; ground/roof 35.4 %.
Per-cell coverage varies (30-100 % unseen) without a simple west/east pattern, so it does not by itself explain the bad segments.

**Consequence for M3/M4:** methods trained on the drone images (Gaussian splatting, scene-coordinate regression) would have no observation of ~75 % of the street-level facade points the ground camera sees (<= 1 image for 74.5 %), consistent with M0's 0 %. Not recommended unless ground imagery is added, which would turn it into mapping with the ground camera.

### 4n. Multi-frame localization (V1): plain joint solve fails, consensus helps as an aliasing filter (done; route 2, 497 frames; `scripts/seq_collect.py`, `seq_solve.py`, `seq_consensus.py`)

Per-frame inlier correspondences were collected once (`seq_collect.py`, prior 5 m, settings of 4g) and multi-frame solutions computed offline. Odometry is simulated as the GT relative pose between frames plus Gaussian noise growing with the distance between them
(1 % of distance + 0.1 deg/m by default; 3 % + 0.3 deg/m tested); frames are 0.6 m apart.

**(a) Plain joint solve (all frames of a window in one reprojection solve, `seq_solve.py`): worse.** Even with perfect odometry gross-wrong poses rose from 74 to 118 of 494 frames (0 wrong->right, 44 right->wrong): wrong-but-self-consistent frames (aliasing, concentrated on a few streets) pull correct frames away; fine accuracy unchanged (median 0.62 -> 0.59-0.61 m).

**(b) Consensus (`seq_consensus.py`):** each window frame implies a pose for frame t through the odometry; the largest cluster of implied poses (1.5 m, 15 deg) is the consensus; only its frames enter the joint solve; the cluster size is the vote count. Gating on unanimity (odometry noise 1 %, 0.1 deg/m):

| Variant | accepted | within (5 m,10 deg) | gross-wrong accepted (% of all frames) | within (1 m,5 deg) | within (0.5 m,5 deg) | median error |
| --- | --- | --- | --- | --- | --- | --- |
| single frame, inliers >= 80 | 71.2 % | 92.1 % | 5.6 % | 87.0 % | ~41 % | 0.550 m |
| N = 5, 5/5 votes | 68.8 % | 96.8 % | **2.2 %** | 96.5 % | 50.9 % | 0.496 m |
| N = 7, 7/7 votes | 64.2 % | 96.9 % | 2.0 % | 96.9 % | 50.8 % | 0.497 m |
| N = 9, 9/9 votes | 60.2 % | 96.7 % | 2.0 % | 96.3 % | 52.5 % | 0.481 m |
| N = 12, 12/12 votes | 54.7 % | 97.4 % | 1.4 % | 96.7 % | 55.5 % | 0.470 m |
| N = 5, 4/5 votes | 81.1 % | 93.1 % | 5.6 % | 92.3 % | 47.4 % | 0.515 m |

Results change little with odometry noise 3 %/0.3 deg per m (N = 7, 7/7: gross-wrong 2.2 % vs 2.0 %).

**Reading.** Requiring the frames of a window to agree on the pose roughly halves-to-thirds the gross-wrong rate at a cost of ~10-16 points of acceptance (68.8 % accepted at 2.2 % vs 71.2 % at 5.6 %), and raises the share within 1 m from 87 % to ~96.5 %. It acts as an aliasing filter; it does **not** remove the ~0.5 m floor
(median 0.55 -> 0.47-0.50 m, within 0.5 m 41 % -> 51-56 %). The target (gross-wrong <= 1 % of queries) is still not reached (best 1.4 % at 54.7 % accepted).
**Caveats:** odometry is simulated from GT relative poses with iid Gaussian noise (real visual-inertial odometry has drift, bias and scale error and can fail in the same places); one route; vote thresholds and window sizes were scanned on the evaluation frames (the frontier is reported, no single setting is claimed as tuned);
a stale second collection process (killed with a non-matching pattern) briefly ran alongside the intended one and overwrote the data file in the old pickled format; data were identical (same settings and seeds) and were converted (`scripts/diag/convert_seq.py`); lesson: verify kills with `ps`.

### 4o. Audit of the render provenance and a fix attempt that failed (done; `scripts/audit_provenance.py`, `scripts/urban_prov_test.sh`)

**Audit against exact SDF geometry** (ground plane z = 0, building boxes; 40 GT poses, ~259 k pixels, map `map_ud0_f2`, splat 0.12 m / 4 px): the 3D point the pipeline pairs with a render pixel (provenance = nearest map point) vs the true hit of the pixel's viewing ray.

| | raw 3D error (median / p90) | reprojection offset of the point to its pixel under the GT pose (median / p90) |
| --- | --- | --- |
| directly splatted pixels (75 %) | 0.51 m / 5.9 m | **2.9 px / 4.7 px**; ground points +1.2 px low, facade ~0 |
| hole-filled pixels (25 %) | 0.48 m / 1.2 m | **10.0 px / 15.3 px**; -2.35 px (high) |
| ground / facade | 0.63 m / 0.37 m | depth along camera z: -0.2 to -0.43 m (points nearer than truth) |

Large raw 3D errors are partly intrinsic (grazing view of a 0.25 m voxel layer from a 0.44 m high camera: a +-0.125 m height quantisation becomes metres along the ray). What matters for PnP is the reprojection inconsistency (2-3 px random, 10 px on filled pixels).

**Fix attempt:** place the 3D point on the pixel's own ray at the chosen point's camera depth (`M1_PROV=ray`), optionally dropping correspondences on hole-filled pixels (`M1_DROP_FILLED=1`). On the held-out urban queries (ug1h, prior 5 m, gate >= 80 inliers):

| | original | ray + drop filled | ray only |
| --- | --- | --- | --- |
| accepted / within (5 m,10 deg) / gross-wrong (% of all) | 59.0 / 98.3 / 1.0 % | 59.5 / 96.7 / 2.0 % | 60.0 / 96.7 / 2.0 % |
| within 1 m / within 0.5 m (accepted) | 85.1 / 52.9 % | 82.0 / 35.2 % | 81.3 / 30.9 % |
| median translation error | 0.484 m | 0.615 m | 0.618 m |

**Worse.** The original points lie on the true surfaces (only their image location is off by ~3 px), whereas ray placement uses a depth that is biased towards the camera, pulling points off the surface. Five attempts on the ~0.5 m floor (render-and-refine, plane-corrected provenance, gravity prior,
ray-consistent provenance with and without hole-fill dropping) have not beaten the original; the floor stays an open problem. Not yet tested: choosing the farthest-depth point in the footprint, a depth-aware weighting of correspondences, a finer voxel size.

## 4p. Depth-weighted PnP, per-segment diagnosis (C-seg), particle filter (MCL) -- route 2

**Depth-weighted PnP** (`scripts/pnp_weight_test.py`, stored correspondences, 497 frames, paired against the stored pose): no gain. Re-solve unweighted 35.3 % within (0.5 m,5 deg) vs stored 34.1 %; weights 1/d 33.1 %, 1/d^2 32.7 %; median error ~0.62 m unchanged; gross-wrong ~15 % unchanged. Dropping far points (>25 m / >15 m) is worse than the stored pose on the same frames. The earlier unpaired "near-only is better" table was selection bias. Negative result.

**C-seg** (`scripts/cseg_segments.py`, 285 queries, oracle view = nearest virtual view): the failing streets fail for different reasons.
- x=-50 south: top-50 retrieval hit 50 %, but even the oracle view localizes only 7.1 % (median 21 confident matches) -> render/matching problem there, not retrieval (colour fraction 0.43 is not the cause).
- y=-50 east (2nd pass): retrieval 40 %, oracle 39.5 % -> both.
- start x=0 north: oracle 0 % (12 matches) and retrieval 0 % -> start segment unusable (looks along the street from the start pose).
- y=0 west and x=50 north: fine (oracle 89 % / 83 %).
- Colour fraction is not a predictor (0.25-0.5: 52.4 %, 0.5-1: 53.5 % oracle success). The earlier colour-coverage hypothesis is not supported for these streets.
Overall: R@50 64 %, oracle within (5 m,10 deg) 53 %, so retrieval AND matching/render both cap the single-frame result.

**MCL** (`scripts/mcl_test.py`, 500 particles, planar x/y/heading; predict with GT relative motion + noise, update with the single-frame PnP pose through a robust likelihood (outlier share EPS)). Initial cloud GT +-5 m / +-10 deg (the same prior assumption as the prior mode). Single frame: 84.9 % within (5 m,10 deg), gross-wrong 15.1 %; gate >=80 inliers: 7.9 %.
| odometry noise, EPS | MCL within (1 m,5 deg) | within (0.5 m,5 deg) | median | gross-wrong |
| --- | --- | --- | --- | --- |
| 1 %+0.1 deg/m, 0.2 | 90.5 % | 84.8 % | 0.27 m | 0.0 % |
| 3 %+0.3 deg/m, 0.2 | 93.2 % | 78.7 % | 0.27 m | 0.0 % |
| 1 %+0.1 deg/m, 0.5 | 95.7 % | 88.4 % | 0.26 m | 0.0 % |
Caveats (read before quoting): one route, 559 frames, three settings tried on the same data; odometry is simulated from GT; the filter starts near GT (no global relocalization / kidnapped case tested); error is planar only (x,y,heading, no height/roll/pitch); metric is on the filter output at every frame, not an accepted subset. The finding is that fusing odometry removes the gross-wrong frames and halves the fine error on this route; it still needs a held-out route and a test with real odometry drift/failure.

## 4q. Matcher swap: kornia XFeat vs LoFTR (route 2, ug2s, 285 queries; `scripts/matcher_bench.py`, `run_xfeat*.sh`, `M1LF_MATCHER`, `M1LF_REFINE_MATCHER`)

Oracle views (perfect retrieval): LoFTR pose 58.9 %, (5 m,10 deg) 53.0 %, (0.5 m,5 deg) 19.6 %, 100 ms/pair; XFeat 88.8 / 85.6 / 30.5 %, 30 ms; XFeat* 83.5 / 82.1 / 26.0 %, 20 ms.
Full pipeline (MegaLoc shortlist K, XFeat on every shortlisted view, no coarse stage):
| mode | (5 m,10 deg) | (0.5 m,5 deg) | median | gate>=40 precision | p50 |
| --- | --- | --- | --- | --- | --- |
| LoFTR, no prior | 46.0 % | 21.4 % | 1.47 m | 57.5 % | 2248 ms |
| XFeat K=20, no prior | 56.5 % | 17.9 % | 1.15 m | 95.6 % | 350 ms |
| XFeat K=50, no prior | 59.3 % | 15.4 % | 0.95 m | 96.3 % | 668 ms |
| XFeat K=50 + LoFTR refine, no prior | 59.6 % | 21.1 % | 0.71 m | 95.1 % | 832 ms |
| LoFTR, prior 5 m / r 20 m | 72.3 % | 27.4 % | 0.65 m | 85.8 % | 2232 ms |
| XFeat, prior | 73.0 % | 22.8 % | 0.82 m | 97.9 % | 654 ms |
| XFeat + LoFTR refine, prior | 74.0 % | 25.6 % | 0.77 m | 97.4 % | 843 ms |
Finding: XFeat is better for coarse localization, gate reliability and speed (2.6-6x); sparse keypoints cost some fine accuracy, which a LoFTR refine at the estimated pose partly recovers. Latency target <=1 s is met in PyTorch with the hybrid. Caveat: one route, 285 queries, single run (seed 0), no confidence intervals.

Added: DISK (kornia, 'depth' weights) + LightGlue (kornia, disk weights), render features cached in prepare (`M1LF_MATCHER=disklg`, `scripts/run_disklg.sh`). Oracle views: pose 95.4 %, (5 m,10 deg) 91.2 %, (0.5 m,5 deg) 33.7 %, 87 ms/pair.
| mode | (5 m,10 deg) | (0.5 m,5 deg) | median | gate>=40 returned / precision | p50 |
| --- | --- | --- | --- | --- | --- |
| DISK+LightGlue K=50, no prior | 64.6 % | 34.0 % | 0.65 m | 96.8 % / 65.9 % | 1000 ms |
| DISK+LightGlue K=20, no prior | 62.8 % | 32.3 % | 0.64 m | 95.8 % / 65.2 % | 461 ms |
| DISK+LightGlue K=50, prior 5 m / r 20 m | 91.2 % | 39.3 % | 0.57 m | 98.6 % / 91.8 % | 859 ms |
Best so far on route 2 (single run, 285 queries). The 40-inlier gate is too lax for this matcher (many matches): gate needs recalibration (leave-one-session-out). Not yet tested: MCL on these poses, XFeat-pose + DISK/LightGlue refine, second route.

Hybrid tested (`scripts/run_hybrid2.sh`: XFeat K=50 finds the pose, one render-at-estimate refine with DISK+LightGlue): prior mode 75.1 % (5 m,10 deg) / 39.3 % (0.5 m,5 deg) / 0.57 m / gate precision 95.0 % / 807 ms; no prior 60.4 % / 34.0 % / 0.54 m / 89.7 % / 790 ms. Compared with DISK+LightGlue alone (91.2 % / 39.3 % / 859 ms with prior; 64.6 % / 34.0 % / 1000 ms without): same fine accuracy, WORSE coarse accuracy (XFeat's wrong initial pose is not repaired by the refine), no meaningful speed gain; only the gate is more reliable. Decision: DISK+LightGlue alone is the baseline; hybrid dropped.

## 4r. MCL on DISK+LightGlue poses (route 2, prior-mode sequence `seq_ug2_disklg.npz`, 569 frames)

Single frame (prior mode): 92.3 % within (5 m,10 deg), 61.7 % within (0.5 m,5 deg), gross-wrong 7.7 %.
**The MCL of 4p did NOT transfer unchanged**: with the same settings it ended up at 28.8 % gross-wrong (1 % odometry, EPS 0.2) and 14.1 % (3 %, EPS 0.5). Cause: the likelihood is tight (many inliers -> sigma ~0.4 m) and the cloud has no way back after it collapses on a wrong stretch of consecutive wrong poses. So the 0 % of 4p was tuning-sensitive; report it as such.
Fixes tried on the SAME route (4 variants, so the best row is tuned on test data, not a held-out result): wider likelihood (SXY 1.5) and re-seeding a fraction INJECT of particles around the observation (frames with >= 40 inliers).
| variant (odo 1 %+0.1 deg/m, EPS 0.5) | all frames: (5 m,10 deg) / (0.5 m,5 deg) / gross-wrong | confident (spread<0.7 m): frames / (0.5 m,5 deg) / gross-wrong |
| --- | --- | --- |
| SXY 1.5, no inject | 99.1 / 42.0 / 0.9 % | 554 / 42.4 % / 0.4 % |
| SXY 0.6, inject 0.1 | 96.8 / 74.6 / 3.2 % | 504 / 81.5 % / 0.2 % |
| SXY 1.5, inject 0.1 | 96.4 / 80.7 / 3.6 % | 475 / 92.2 % / 0.0 % |
| SXY 1.5, inject 0.2 | 93.9 / 77.8 / 6.1 % | 295 / 91.2 % / 0.0 % |
Reading: wide likelihood alone is safe but loses fine accuracy (0.77 m); injection restores it. Needs a held-out route with the settings fixed in advance (SXY 1.5, inject 0.1) before it counts as evidence. Kidnapped-start run with global poses pending (`seq_ug2_disklg_global.npz`).

Kidnapped / global start (`KIDNAP=1`, particles uniform over the route bounding box + 30 m, 5000 particles; poses from GLOBAL retrieval, no position prior: `seq_ug2_disklg_global.npz`, `scripts/run_kidnap2.sh`, `run_kidnap3.sh`): single-frame global poses are only 65.0 % within (5 m,10 deg), 35.0 % gross-wrong. **Result: negative.** Original MCL settings never converge (never within 2 m for the rest of the route); with SXY 1.5 + INJECT 0.1 it converges only at frame 551 of 569; gating observations by inlier count (60/100/150) does not change that, because the wrong global poses are confident: share of wrong poses (>5 m) among frames with >= 40 / 100 / 150 / 200 inliers is 33 / 30 / 23 / 18 %. So inlier count is NOT a usable gate in global mode (consistent with the 66 % gate precision of 4q) and a top-1-pose MCL cannot resolve a global start. Candidate fix (untested): feed the filter several pose hypotheses per frame (all shortlisted views), letting motion consistency choose; or a learned gate (leave-one-session-out) with retrieval-margin features.

## 4s. Held-out route 3 (`scripts/urban_route3.sh`; settings frozen before the run)

Route 3 = new loop (start (0,0): y=0 east, y=50 west, x=-50 ..., 821 frames, 411-query subset `ug3s`). Honest scope: it is a different driving order/direction/start but 92 % of its poses are within 5 m of an ug1/ug2 pose (same streets), so it tests transfer of settings, not novel streets.
DISK+LightGlue K=50, no re-tuning: prior 5 m / r 20 m: 85.9 % within (5 m,10 deg), 41.4 % within (0.5 m,5 deg), median 0.54 m, 850 ms, gate>=40 precision 93.4 % (route 2: 91.2 / 39.3 / 0.57 / 859 / 91.8; ug1s: 97.1 / 47.8 / 0.52 / 814 / 98.0). Global (no prior): 78.6 % / 37.2 % / 0.57 m / 975 ms, gate precision 80.3 %.
MCL on route 3 with the settings chosen on route 2 (SXY 1.5, INJECT 0.1, EPS 0.5): all frames 87.5 % within (5 m,10 deg), **12.5 % gross-wrong (no better than single frame 12.2 %)**; confident frames only (spread < 0.7 m, 666 of 811): 100 % within 1 m, 85.9 % within (0.5 m,5 deg), 0.0 % gross-wrong. With 3 % odometry noise: confident 91.3 % fine, 0.0 % gross-wrong. The ORIGINAL settings (SXY 0.6, no inject, EPS 0.2) give 0.2 % gross-wrong and 80.5 % fine on route 3 but 28.8 % gross-wrong on route 2 (4r).
Conclusion: neither MCL parameterisation is robust across both routes. What does hold on both routes: the spread-confidence gate (spread < 0.7 m) removes the gross-wrong frames (route 2: 0.0 %, route 3: 0.0 %) at the cost of withholding ~18 % of frames. Single-route tuning was therefore partly overfit; the robust claim is "MCL + spread gate", not any specific setting. Multi-hypothesis observations are being tried next.

## 4t. Multi-hypothesis observations for the global (kidnapped) start -- route 2

Per frame, global retrieval (no position prior), DISK+LightGlue, one PnP pose per each of the 8 best shortlisted views (`M1LF_HYP=8`, `seq_collect.py`, `seq_ug2_hyp_global.npz`).
Oracle (`scripts/hyp_oracle.py`, valid hypothesis = >= 30 inliers): top-1 pooled pose correct (5 m,10 deg) 65.0 %; a correct hypothesis exists among the 8 in 82.8 % of frames, and in 50.8 % of the 199 frames where top-1 is wrong; but 54.9 % of the valid hypotheses are wrong, so the observation is a noisy mixture.
MCL with the observation = equal-weight mixture over the valid hypotheses (`MULTIHYP=1`), 5000 particles uniform over the route bounding box + 30 m, random heading, GT-derived odometry 1 %+0.1 deg/m (planar). Three settings tried on this same route:
| SXY / EPS / min inliers per hypothesis | converged (stays < 2 m) from frame | after convergence: (5 m,10 deg) / (1 m,5 deg) / (0.5 m,5 deg) / gross-wrong |
| --- | --- | --- |
| 1.5 / 0.5 / 30 | never | - |
| 1.0 / 0.5 / 60 | 86 of 569 | 100 / 84.1 / 79.5 % / 0.0 % |
| 1.0 / 0.3 / 100 | 86 of 569 | 100 / 83.6 / 80.1 % / 0.0 % |
vs top-1 observations (4r): never / frame 551. So multi-hypothesis fixes the global start on this route (frame 86 ~ the first 15 % of the route), but it is sensitive to the hypothesis inlier threshold (30 fails). Settings (1.0 / 0.5 / 60) are now FROZEN for route 3 (held-out; no further tuning). The odometry is simulated from GT and the filter is planar.

Held-out check and start-place sweep (frozen SXY 1.0 / EPS 0.5 / HMIN 60, 5000 particles, `scripts/run_mh_starts.sh`, start every 80 frames x 2 seeds): **route 3 from frame 0 never converges** (start = central crossing, most ambiguous); oracle on route 3: correct hypothesis among the 8 in 82.3 % of frames (top-1 78.7 %), but only 17.1 % of the frames where top-1 is wrong.
Sweep, kidnapped start: route 2 converged in 6/10 runs, route 3 in 7/16 (13/26 = 50 %); after convergence gross-wrong 0.0 % in every converged run. The failures are runs that stay on a wrong mode until the end (also seed-dependent). So the global-start claim is "works in about half of the start places/seeds", not "works".
Variant UNI = 0.02 (2 % of the lowest-weight particles re-drawn uniformly each frame, tuned on these same runs, so dev-only): route 2 7/10, route 3 10/16 converged (17/26 = 65 %), but two route-3 runs show gross-wrong after convergence (20.8 %, 5.4 %: heading drifts beyond 10 deg). Net: small gain in convergence, with a new failure mode. Open: needs a novel route to verify; candidate improvements are an adaptive injection or tracking several modes.

## 4u. Latency profile and speed-up attempts (DISK+LightGlue, prior mode, route 2; `scripts/profile_latency.py`)

Per localization (median, 40 queries): MegaLoc (query) 15 ms, DISK (query) 33 ms, PnP 6 ms, **LightGlue against 50 shortlisted views ~780 ms (~15.6 ms per pair)**, total 836 ms. The cost is the number of pair calls, not model size.
- fp16 autocast of LightGlue (`M1LF_LGFP16=1`): identical accuracy (91.2 / 39.3 % / 0.566 m) and identical latency (853 vs 859 ms) -> per-pair time is launch/overhead-bound, not FLOP-bound; so TensorRT of the same per-pair call is not expected to help either.
- Batched LightGlue over the 50 pairs (`M1LF_LGBATCH`, implemented in `_lg_batch`): **failed** - kornia's LightGlue does not support batch size > 1 with its cached rotary encoding (tensor-size error 2048 vs 25x2048). Left in the code, default off. A real fix would need the original `cvg/LightGlue` package or a custom batched implementation (not tried).
- Reducing the shortlist K is the lever that works: no prior K=20 461 ms (62.8 / 32.3 %) vs K=50 1000 ms (64.6 / 34.0 %); prior-mode K=20 (route 2, prior 5 m / r 20 m): **93.0 % within (5 m,10 deg), 41.1 % within (0.5 m,5 deg), median 0.566 m, 413 ms, gate>=40 precision 94.0 %** - better than K=50 (91.2 / 39.3 % / 859 ms) and 2x faster (single run; the shortlist inside the 20 m prior radius is small, so extra views mostly add confusers). New default for prior mode: K=20.
- TensorRT itself was NOT run: LightGlue has data-dependent control flow (adaptive depth/width), and the overhead-bound profile says little would be gained; an ONNX/TensorRT export would need a third-party repo. Stated as not done, not as failed.

## 4v. Colour-registration sensitivity (calibration error of the camera that colours the drone map; route 2, DISK+LightGlue K=20, prior 5 m / r 20 m, frozen settings; `scripts/run_calib.sh`, `COLOR_ROT_DEG` / `COLOR_TRANS_M` / `COLOR_JITTER_M` in `vps/build_lidar_map.py`)

The map GEOMETRY already comes from FAST-LIO (ATE rmse 8.3 cm, drift 0.01 % of 841 m); only the COLOURS were projected with simulator-exact camera poses. This sweep perturbs that colour projection (fixed extrinsic error in the camera frame, random axis).
| colour projection error | (5 m,10 deg) | (0.5 m,5 deg) | median | gate>=40 precision |
| --- | --- | --- | --- | --- |
| none (reference) | 93.0 % | 41.1 % | 0.57 m | 94.0 % |
| translation 0.1 m | 93.3 % | 34.4 % | 0.60 m | 94.3 % |
| per-image position jitter 0.1 m | 94.7 % | 34.7 % | 0.59 m | 97.1 % |
| rotation 0.5 deg | 94.4 % | 10.2 % | 0.92 m | 96.1 % |
| rotation 1 deg | 84.9 % | 5.6 % | 1.64 m | 88.6 % |
| rotation 1 deg + jitter 0.1 m | 89.8 % | 11.6 % | 1.51 m | 94.8 % |
| rotation 2 deg | 76.1 % | 0.0 % | 3.07 m | 83.9 % |
Reading: position errors of 0.1 m are tolerated; ANGULAR errors are not: 0.5 deg already cuts the fine accuracy 4x and 2 deg triples the median (a camera ~45 m above the ground turns 0.5 deg into ~0.4 m of colour displacement on the surface; the images then match geometry that is shifted relative to the texture). Requirement derived: the drone camera extrinsic/attitude used for colouring must be good to ~0.1-0.2 deg, or colours must be re-registered to the geometry automatically (not implemented; candidate: photometric/edge alignment of image to the LiDAR-projected depth/intensity). Coarse (5 m,10 deg) localization is robust up to ~1 deg. Single seed of the error direction per row; one route.

## 4w. Online filter with the prior taken from the filter itself (replay of route 2, `scripts/replay_online.py`) and the first closed-loop attempt

Assumption removed: until now every prior-mode number used GT + 5 m noise as the position prior. Here the prior = the MCL's own estimate (start: operator-given +-5 m / +-10 deg), odometry = GT increments with 1 % scale noise, delayed-update logic as in `ros/closed_loop.py`. Route 2 (284 frames), DISK+LightGlue K=20.
| version | est. error median / p95 / max | frames > 5 m | wrong observations (>5 m) |
| --- | --- | --- | --- |
| first version (global fallback when no view near the prior, no gate) | 0.44 m / 104 m / 113 m | 39.1 % | 38.4 % |
| + strict prior (no fallback), observation gate (reject poses > 15 m from a confident filter) | 37.9 m / 57 m / 58 m | 56.3 % | 54.6 % |
| + reject poses > 8 m from the retrieved view (`M1LF_MAXD=8`, `d_render_t`) | **0.29 m / 0.96 m / 8.0 m** | **4.2 %** | **0.4 %** |
Failure analysis: at the start (0,-85) the first PnP poses were 29-53 m off although all candidate views lay within 20 m of the prior (aliasing: the 3D points of the matches come from a far, similar-looking facade; the pose then lies far from every candidate view). The filter accepted them and, with injection, locked onto the x=50 street (spread 0.7 m, confident and wrong). Offline check of the new rejection rule on stored runs (`d_render_t <= 8 m`): removes 64 % (ug2s) and 84 % (route 3) of the wrong poses while keeping 81 % / 78 % of the frames. The 0.4 % wrong observations that remain are accepted.
Closed loop in Gazebo, first attempt (before these fixes, `results/urban/closedloop_1.npz`): FAILED - estimate jumped 58 m at the start (same cause), the robot drove into the building at (-6.8,-81) and stayed there (1005 s timeout, 1/7 waypoints). Note: the collision counter of that run also counted ground-noise points (fixed: obstacle points now z in 0.6-2 m).
Caveats: one route that is also in the dev set (the failing street x=-50 south is now handled but was seen), odometry simulated from GT, planar filter.

Closed loop in Gazebo, attempt 3 (`scripts/closed_loop.sh`, `ros/closed_loop.py`; fixes: strict prior, observation gate, `M1LF_MAXD=8`, crawl at 40 % speed instead of stopping while the filter is uncertain; `results/urban/closedloop_1.npz`): **not successful.** First ~270 s (~220 m, 4 of 7 waypoints): estimate error 0.4-1.5 m, spread 0.7-1.3 m, robot follows the route (cross-track median ~1-2 m). At the junction of y=0 / x=-50 the estimate drifts 10 m, on the x=-50 southbound street (the street where C-seg found oracle matching 7 %) the robot ends up against the right-hand wall (x=-55, no local obstacle avoidance in this sim) and the filter gets lost (spread 45 m); later the estimate sits 25-90 m away (aliasing between similar blocks), 1005 s timeout, GT never reaches the end. Totals: est error median 6.8 m / p95 53.6 m, 18 % of ticks within 0.35 m of an obstacle, 24 % of time stopped because lost. One run, one seed, one route; the failing section is part of the earlier dev set.
Open: (a) the weak street (render/matching) and the junction before it; (b) multi-hypothesis observations inside the closed loop; (c) re-localization when lost (global search with the hypothesis filter) and a safe behaviour (stop + report) instead of continuing; (d) local obstacle avoidance in the sim robot.

## 4x. Generated worlds (generalisation series; `worlds/gen_city.py`, `scripts/world_pipeline.sh`, `scripts/run_all_worlds.sh`)

Styles: grid / oldtown (BSP blocks, 3-8 m lanes) / suburb (houses, fences, tree boxes) / bridge (+ elevated deck and roofed tunnel) / canyon (30-60 m buildings, 6 m streets); 200 x 200 m, same drone and ground robot. Routes: random walk over free space on an occupancy grid, simplified (first version had a waypoint at every 1 m grid turn: the robot drove at ~0.3 m/s and needed >1 h per route; Ramer-Douglas-Peucker 1 m fixed it).
Per world, frozen settings (DISK+LightGlue, K=20, MegaLoc shortlist; prior 5 m / r 20 m and global), no tuning.
First world generated and mapped: oldtown12: FAST-LIO on the drone flight: **ATE rmse 5.1 m, max 24.5 m, drift 0.48 % of 1674 m** (the original world: 8.3 cm, 0.01 %). The map is therefore distorted in this world; absolute metrics against GT will be penalised by that distortion (a robot navigating in the map's own frame would not see it as an error, but its position relative to the true world would be off). **oldtown12 result with that map (zf 45 m): total failure** - prior mode (5 m / r 20 m): localized 4.4 %, 0.0 % within (5 m,10 deg), median error 46.6 m; global: localized 19.2 %, 0.0 %, median 79.3 m. Cause = the map, not the localizer (`scripts/world_check.py`): GT robot poses lie within 1 m of a map obstacle point in 24.5 % of frames (should be ~0 %), 69.9 % of map points at 2-8 m height fall inside the SDF building footprints, 88.8 % after shifting the whole map by dx = -12 m. FAST-LIO degenerated because the drone flew at 45 m over 6-22 m buildings (mostly flat ground in view). Fix applied for all generated worlds: flight height = max(30, hmax + 12) m; the registration check now runs for every world and is reported with its result; oldtown12 and suburb13 are re-flown. Queue order: grid11, bridge14, canyon15, oldtown12, suburb13.
Process note: a `pkill -f` inside a script left the old simulator/recorder running for 34 min and the next run silently reused a partial bag; `scripts/kill_all.sh` now kills by pid.
**Correction (root cause of the bad maps): the ALIGNMENT, not FAST-LIO.** `ros/eval_ate.py:align` fitted one rigid transform (Umeyama) to all poses; the first ~100 poses of each flight (take-off) disagree with GT by up to 17 m and pulled the fit, so the map of the new worlds was shifted/rotated relative to the world (ATE 3-5 m, "map shifted 12 m"). With a trimmed re-fit (reject poses whose error is above 3x the median, repeat): grid11: 2198/2300 poses used, **ATE rmse 4.6 cm, max 0.40 m**; the 102 outlier poses are the start of the flight. The original urban world is unaffected (ATE 8.3 cm, no start outliers). So the oldtown12 failure above was an alignment artefact, not FAST-LIO degeneration and not an altitude problem; the lower flight height (max(30, hmax+12) m) stays but was not the cause. Worlds oldtown12 and suburb13 are re-flown anyway.
**grid11 (new seed of the SAME style as the original world; frozen settings, no tuning; map registration verified: 99.9 % of map points inside SDF footprints, 0.8 % of GT poses within 1 m of a map obstacle; FAST-LIO ATE 4.6 cm):** prior 5 m / r 20 m, 459 queries: localized 69.1 %, (5 m,10 deg) 55.6 %, (0.5 m,5 deg) 12.6 %, median 0.84 m, gate>=40 precision 94.4 %, 363 ms. The original world with the same settings: 93.0 / 41.1 % / 0.57 m (route 2). The method does NOT transfer unchanged even to a new random draw of the same city style. grid11 GLOBAL (no prior): localized 84.1 %, **(5 m,10 deg) 11.3 %**, (0.5 m,5 deg) 3.7 %, median 100.8 m, gate>=40 returned 73.6 % with precision 14.5 % (original world: 64.6-78.6 %, gate precision 66-80 %): global retrieval is unusable here; a position prior is mandatory. Untested hypotheses: the generated worlds have no road lane markings (the original road texture had them) and different facade textures; routes are random walks through free space rather than street centres.
**bridge14** (bridge + tunnel + grid; FAST-LIO ATE 3.6 cm on 2124/2285 poses; map registration 99.0 %): prior: localized 60.2 %, (5 m,10 deg) 49.4 %, (0.5 m,5 deg) 10.3 %, median 0.90 m, gate>=40 returned 49 % with precision 95.9 %, 359 ms; global: localized 79.9 %, (5 m,10 deg) 25.7 %, (0.5 m,5 deg) 8.5 %, median 53.8 m, gate precision 37.7 %.
**canyon15** (tall 30-60 m buildings, 6 m streets; drone at 71 m; FAST-LIO ATE 10.9 cm on 2243/2301 poses; map registration 100 %): **prior: localized 1.6 %, 0.0 % within (5 m,10 deg), median 28.8 m; global: localized 0.9 %, 0 %.** Total failure.
Diagnosis (`scripts/cov_height.py`): share of map points that NO drone image saw (colour unknown), by height above ground. Street-level band z 0.6-3 m: original world 64 %, grid11 72 %, bridge14 74 %, **canyon15 79 %**; z 3-8 m: 54 / 62 / 58 / **79 %**; z 8-20 m: 30 / 37 / 41 / **79 %**. And canyon15 has only 12.8 k map points in z 0.6-3 m (vs 122-152 k elsewhere): a drone at 71 m looking into 6 m-wide streets between 59 m walls barely samples street-level facades at all. Across the four worlds, single-frame success with prior (5 m,10 deg) falls with that coverage: 93 % (64 % unseen) -> 56 % (72 %) -> 49 % (74 %) -> ~0 % (79 % and 10x fewer points). Correlation over 4 worlds, not proof; but it points at the mapping flight (viewpoint/altitude), not the matcher, as the limiting factor in narrow canyons.
**RETRACTION / narrowing (after oldtown12):** oldtown12 (flown at 32 m) has the BEST street-level colour coverage of all worlds (38 % unseen at z 0.6-3 m, 37 % at 3-8 m, 21 % at 8-20 m; 7.6e4 street-level points) yet only 15.9 % (5 m,10 deg) with prior. So colour coverage alone does NOT explain the results; it explains canyon15 (79 % unseen everywhere, 10x fewer street-level points) but not oldtown12. Other differences in oldtown12 (3-8 m lanes, tightly packed walls seen at very short range, large lots with the same facade texture) are untested; the retrieval-vs-matching oracle diagnosis (`scripts/urban_diag.py`) per world is needed.
Design hypothesis to test next: re-fly canyon15 low along the streets (z ~20 m on street centre lines, camera pitched down) and compare; and the planned ground-robot online wall colouring (R6).
**oldtown12** (re-flown at 32 m; FAST-LIO trimmed ATE 11.5 cm on 1744/2280 poses; map registration 95.3 %): prior: localized 29.2 %, (5 m,10 deg) 15.9 %, (0.5 m,5 deg) 8.4 %, median 1.69 m, gate>=40 returned 15.9 % precision 90.3 %; global: localized 43.8 %, (5 m,10 deg) 8.6 %, median 68.1 m.
**suburb13** (low houses <= 8 m, fences, tree boxes, mostly open ground; drone at 30 m): **FAST-LIO failed: ATE rmse 78.2 m, max 116.9 m, drift 5.7 % of path; the trimmed re-fit cannot help (all 2281 poses are off).** Planar open ground gives the LiDAR odometry too little structure (the known degeneracy of LiDAR-inertial odometry over flat terrain); the map is unusable, so the localization evaluation of this world was NOT run (it would only measure a broken map). Finding for the system design: a camera-only ground robot depends on the drone's SLAM; in featureless open terrain that dependency fails first. Not tried: lower flight, oblique LiDAR geometry, GNSS/visual aiding.
Results table: below as worlds complete.

## 4y. Sensor-degradation test (original world, route 2, DISK+LightGlue K=20, prior 5 m / r 20 m, frozen settings; `scripts/make_degraded.py`, `scripts/deg_analyze.py`, `results/urban/deg_all*`)

285 query images degraded 7 ways + clean, evaluated in one run (map loaded once). Degradations are synthetic and applied to simulator images.
| variant | pose returned | (5 m,10 deg) | (0.5 m,5 deg) | median |
| --- | --- | --- | --- | --- |
| clean | 100 % | 93.0 % | 41.1 % | 0.57 m |
| Gaussian noise sigma 10 | 98 % | 89.1 % | 44.2 % | 0.55 m |
| motion blur 15 px, random direction | 82 % | 69.1 % | 30.2 % | 0.63 m |
| dark (gamma 2.2 x 0.7) | 99 % | 88.1 % | 38.2 % | 0.62 m |
| bright (gamma 0.5 x 1.2) | 100 % | 94.7 % | 44.6 % | 0.52 m |
| colour cast (R x0.8, B x1.2) | 100 % | 94.7 % | 45.3 % | 0.54 m |
| barrel distortion k1 = -0.10, uncorrected | 100 % | 93.7 % | 4.9 % | 0.94 m |
| JPEG q=25 | 100 % | 95.1 % | 44.6 % | 0.55 m |
Reading: photometric changes (noise, exposure, colour cast, JPEG) barely matter; motion blur is the most harmful for coarse localization (93 -> 69 %), uncorrected lens distortion destroys the fine accuracy (41 -> 5 %) while coarse localization is untouched, i.e. the lens must be calibrated and the image undistorted (same lesson as the mapping-camera calibration of 4v). Not tested: dust/rain/droplets, lighting direction/shadows (needs new simulator runs), degradation of the DRONE camera and LiDAR.

## 4z. AR/XR case: head-height camera (grid11; `scripts/ar_test.sh`, `scripts/ar_metrics.py`)

Same world and drone map, query camera at 1.7 m (pitched 0.1 rad down), same route (459 queries), DISK+LightGlue K=20, prior 5 m / r 20 m, frozen settings.
| queries / views | pose returned | (5 m,10 deg) | (0.5 m,5 deg) | median |
| --- | --- | --- | --- | --- |
| robot height 0.44 m / views at 0.44 m (reference) | 69 % | 55.6 % | 12.6 % | 0.84 m |
| head height 1.7 m / views at 0.44 m (mismatch) | 62 % | 43.6 % | 13.5 % | 0.93 m |
| head height 1.7 m / views rendered at 1.7 m | 71 % | 54.9 % | 16.8 % | 0.78 m |
Reading: the camera height must match the rendered view height (mismatch costs ~11 points); with matching views head-height queries do as well as robot-height ones. Anchor error an AR user would see (a marker 20 m ahead lands off by translation error + 20 m x tan(rotation error)): median 0.87 m, within 0.5 m for 17 % and within 2 m for 71 % of the queries (10 m: 0.80 m; 50 m: 1.08 m) - far from the 0.2-0.3 m an AR overlay needs; usable for coarse "go that way / that building" guidance only, and only on frames the gate accepts. Not modelled: head motion (fast rotations, blur: blur alone cost 24 points in 4y), roll/pitch variation, a gait-induced camera shake, the fusion with the headset's own VIO that a real AR system would have.

## 4aa. Retrieval vs matching per world (oracle diagnosis, `scripts/urban_diag.py` with DISK+LightGlue, `scripts/run_world_diag.sh`, `results/worlds/diag_*.npz`) and cross-world gate

Oracle = the rendered view nearest to the true pose is matched directly (perfect retrieval). Queries: ug2s (original), ugs_img of each world.
| world | queries with a view within 4 m/30 deg | retrieval R@50 | oracle matching: pose returned / (5 m,10 deg) / (0.5 m,5 deg) | median confident matches | single-frame prior mode (5 m,10 deg) |
| --- | --- | --- | --- | --- | --- |
| original | 96.1 % | 64.2 % | 97.2 / 94.0 / 40.4 % | 349 | 93.0 % |
| grid11 | 82.4 % | 23.5 % | 58.2 / 56.2 / 11.1 % | 53 | 55.6 % |
| bridge14 | 74.9 % | 44.8 % | 49.9 / 49.0 / 9.2 % | 35 | 49.4 % |
| oldtown12 | 79.2 % | 24.9 % | 15.9 / 13.3 / 5.5 % | 11 | 15.9 % |
| canyon15 | 68.8 % | 10.1 % | 0.4 / 0.0 / 0.0 % | 7 | ~0 % |
Finding: in every new world the real result equals the ORACLE result almost exactly, so the bottleneck is MATCHING (render vs real image), not retrieval; the number of confident matches falls from 349 to 7 along the same ordering as the success rate. Retrieval is also worse in the new worlds (R@50 64 -> 10-45 %) and becomes the next limit once matching works. The coloured fraction of the oracle views is not the cause (original 0.52, grid11 0.48, bridge14 0.46, oldtown12 0.58, canyon15 0.35).
Cross-world gate (leave-one-session-out, `confidence_gate.py` with `GATE_LABEL=coarse`, label = not grossly wrong (5 m,10 deg), logistic regression on the pose features, trained on the other sessions; sessions: ug2s, ug1s, grid11, bridge14, oldtown12 - the first two from the same world): among returned poses the share correct is 80.4 % (grid11), 82.2 % (bridge14), 54.5 % (oldtown12). AUROC learned/inlier-count: 0.963/0.933, 0.990/0.950, 0.966/0.909. Share of the returned poses that can be accepted at precision >= 95 %: grid11 78.5/76.3 %, bridge14 85.1/82.9 %, oldtown12 **51.5 / 6.1 %**. The learned gate transfers across worlds and is clearly better than the inlier-count gate where it matters (oldtown12). Caveats: shares are of frames that returned a pose (oldtown12 returns a pose in only 29 % of frames), few training sessions, two of them from one world.

Render-setting sweep on oldtown12 (oracle diagnosis, `scripts/run_splat_sweep.sh`; reference splat 0.12 m / max radius 4 px: 13.3 % coarse, 5.5 % fine, 11 confident matches): splat 0.06 m: 15.0 % / 7.5 % / 12 matches; splat 0.25 m: 10.4 % / 5.1 % / 10; max radius 10 px: 16.8 % / 7.7 % / 14. All within a few points of the reference: **the splat size and radius, tuned on the original world, do not explain the dead matching in oldtown12.** (Next: background-leak filter in the renderer, `M1_LEAK`, following the neural point renderer of CRISTAL.)

## 5. Next (see `slam-project.md` section 5b for the aerial -> ground series)

Tracked in the project spec; this log is updated as each item gets a result file.
