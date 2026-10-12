# TODO

Living list. Tick with `[x]`. Rationale lives in `docs/experiment-log.md` and `slam-project.md`; this file is the queue.

## A. Audit fixes (do first — numbers aren't trustworthy until these land)

- [x] A1. Painter's algorithm reversed in `vps/m1.py:32` — iterate `range(5)` so near overwrites far
- [x] A2. (corrected on re-audit) bag frame ids are EMPTY so name filtering would crash; kept positional `transforms[0]` (= model pose in world, verified) + assert 4 transforms/msg. Series B must bridge per-model poses
- [x] A3. (re-audit: seed DOES change results - M0 recall@0.25m 50.0% seed0 vs 53.9% seed7, 10 queries flip localized) RANSAC seed — `cv2.setRNGSeed(seed)` in `harness.py`; `--seed` flag added; 3 seeds in `scripts/rerun_audit.sh`
- [x] A4. Added inlier gate columns (`gate12/20/40/80_precision`, `gate*_returned`); per-query inliers now in `*_err.npy` 3rd col
- [x] A5. VRAM now `torch.cuda.max_memory_allocated()` per process; falls back to 0 for CPU-only
- [x] A6. `vps/dump_session.py` now asserts encoding and converts correctly for rgb8/bgr8
- [x] A7. `vps/m1l.py` guards empty match list
- [x] A8. `vps/m0.py` guards `knnMatch` len and `d is None`
- [x] A9. Superseded: the v1 rerun was killed by a WSL shutdown; M0/M1/M1-LoFTR were re-run properly on dataset v2 (3 seeds, `results/v2/`, docs 3c)

- [~] A10. (partly done: q2v2 reversed direction, q3v2 in-place spins; lateral offset still only 0.5-1.15 m) Report query->map offset: q1 retraces s0 ~1.06 m lateral (max 1.46 m), yaw med 0.4 deg - results are best-case; add far-offset query set (exp 4) before any generalisation claim
- [ ] A11. Seeds only vary RANSAC; real variance sources (world seed, trajectory, mapping run) are not varied - need >=3 worlds/sessions for a meaningful spread
- [ ] A12. Report precision at (0.25 m, 2 deg) per inlier gate, not only the lax (5 m, 10 deg)
- [ ] A13. VRAM metric = torch allocator only (excludes CUDA context ~300+ MiB); also report nvidia-smi delta, label both
- [x] A14. (done: read from the bag's stamped sensor frames; verified identical on v2 data, ATE unchanged, drone camera pitch recovered) Parametrise camera/IMU extrinsics (hard-coded in dump_session.py/eval_ate.py) before using the drone model
- [ ] A15. M1/M1-LoFTR render params (splat, fill, blur) were tuned while looking at q1 results - hold out a separate validation session

- [x] A16. (fixed with --distinct, dataset v2; confirmed: wrong poses 16% -> 1.6%, mirror signature gone) World aliasing (found by audit 3): all 4 perimeter walls share ONE texture (`worlds/gen_world.py:124`), so the room is 180-deg symmetric. 80% of M1-LoFTR wrong poses are the point reflection of the GT camera through the room centre (pos err = 2*|xy|, rot ~180 deg). Fix: distinct texture per wall + re-collect s0/q1, or report as a deliberate repeating-structure case (exp 5). `urban` world must NOT repeat facade textures unless that is the variable under test
- [ ] A17. Inlier gate cannot catch aliasing (wrong poses are self-consistent: median 204 inliers vs 758 for good poses, p90 1067). Needs retrieval-level verification, e.g. check that the top-K renders agree spatially, or reject when two distant clusters of renders score similarly
- [x] A18. CPU painter renderer is only an approximation of a z-buffer: it differs from the exact nearest-point z-buffer on 3-29% of pixels (up to ~1 m in 3D at depth edges). `m1lf.render_gpu` is exact (float32 == float64 reference, 100%). All earlier M1/M1-LoFTR numbers used the painter; ablation `m1lf_f0c0` isolates the effect
- [x] A19. Warm-up localize calls (reseeded afterwards) in `harness.py` so p95/p99 latency excludes CUDA autotune
- [x] A20. m1lf ablation done (docs/experiment-log.md 3b): f0c1 = 2.8x faster within noise (default); f1c1 = 4.6x but significantly less accurate (14 vs 4 flips). Single seed, repeat with more sessions

- [x] A21. Root cause of the "clock jumps" in new recordings (audit 4): data is intact, but a loaded `ros2 bag record` receives ~2 % of messages up to 0.54 s late, so receive (log) order is shuffled for /clock, /imu, /lidar, images. v1 bags happen to be clean (verified). Two code paths depended on receive order:
  (a) GT timing: `/gt/poses` is bridged from the scene broadcaster and the Pose_V->TFMessage conversion DROPS its stamp, so GT time was receive time mapped through /clock receive times. Fix: bridge PosePublisher `/model/robot/pose` as `/gt/model` (per-pose sim stamp + frame names, `publish_model_pose`), `eval_ate.gt_track()` prefers it; legacy path now REFUSES bags whose /clock is not monotone instead of returning silently wrong GT. v1 regression: identical poses/stamps.
  (b) FAST-LIO replay: `ros2 bag play` follows log time -> IMU/LiDAR going back in time. Fix: `ros/resort_bag.py` rewrites log time from sim stamps; `run_lio.sh` replays the sorted copy (verified 0 back-steps).
  Also: `dump_session.py` now writes images in stamp order (M0 triangulates index neighbours). Why the recorder is slower now than for v1 is NOT known (suspect disk I/O on A: after the pagefile move); the fixes make the pipeline independent of it.
- [x] A22. My first "fix" for A21 (drop non-increasing GT samples) was wrong: it crashed and would have hidden mistimed GT. Replaced by A21(a)
- [ ] A23. `scripts/diag/clock_probe5.sh` bag mode hangs: SIGINT to a background job in a non-interactive shell without `set -m` is ignored (run_session.sh has `set -m` for this reason). Diagnostic only; fix if reused
- [x] A24. `ros/lidar_prep.py` comment says FAST-LIO `timestamp_unit=2`; config uses 0 (seconds), which matches the code. Fix the comment
- [ ] A25. Multi-robot world (series B): `/model/<name>/pose` per model and `drive_waypoints.py` still reads unstamped `/gt/poses` transforms[0] (fine for control, wrong if another model is first)

- [~] A26. (q3v2 done, docs 3e: gain shrinks with misalignment +39/+17/+9 pts; still to do: 45-deg yaw spacing test, second world) Held-out evaluation for the yaw result: new query set with non-aligned yaw offsets (45/135 deg, diagonal paths, in-place rotation) and a second world (different layout + texture seed); do not tune the yaw set on it. Also test yaw spacing 45 deg and the corner failures
- [~] A27. (retrieval now ~17 ms with MegaLoc; remaining ~2.3 s is LoFTR coarse 1.09 s + full 1.17 s, latency sweep running) Retrieval cost scales with renders (6.4 s/query at 236). Needs a global-descriptor retrieval (e.g. pooled LoFTR/CNN features or per-render keypoint-count prefilter) before any real-time claim

- [x] A28. (done, docs 4i: NO gain on urban queries, fine-accuracy limit is 3D provenance precision, testing plane-corrected provenance) (CRISTAL) Render-and-refine: after PnP, re-render the map at the estimated pose, re-match, re-solve; check whether M1's 6.8 cm median error drops towards M0's 4.6 cm
- [ ] A29. (CRISTAL) Depth filter against background leaking through sparse foreground in `render_gpu`/`shade` (min-pooled depth, reject pixels deeper than neighbourhood min + delta); measure matches/recall
- [ ] A30. (CRISTAL) Lighter matcher than LoFTR (XFeat): verify that Kornia ships it with weights before planning; compare accuracy/latency
- [ ] A31. (CRISTAL) Exp 6: include map downsampling (point-based render reportedly collapses at 10 % density); test a learned hole-filler only if downsampling hurts
- [ ] A32. docs/related-work.md: re-read the two abstract-only papers' full text before citing numbers

- [~] A33. (stage 1 3f weak; stage 2 3g: MegaLoc R@50 90 % on hard sets, 8.5 ms/img; wired into m1lf (M1LF_RETR=megaloc), end-to-end run in progress) Vector database for retrieval: render descriptors (start with LoFTR-backbone pooled features, no download; then MegaLoc, needs a weights download = ask first); measure recall@1/5/10 vs GT on q1v2/q2v2/q3v2 BEFORE wiring to LoFTR; then end-to-end latency and aliasing behaviour
- [ ] A34. Comparison point: DRS-VPT (image-to-scan feed-forward) if code/weights turn out to be released and fit in 8 GB; check first, otherwise cite only
- [x] C-frame. VelocityControl linear command is in the BODY frame (drone yawed 95 deg, +x command moved (-1.1, +12.4) m), so `fly_waypoints.py` can yaw-follow the travel direction (camera then sees facade faces on both lane directions). Smoke test passed: urban world RTF 1.0 with sensors, drone/ground follow commands, all bridged topics deliver, GT frames incl. sensors present

- [~] A35. (first attempt negative, docs 3h: inlier count AUROC 0.506 on reversed queries; learned head does not dominate; next: per-candidate pose consensus feature, more sessions/worlds, odometry consistency) "System One" confidence head (docs/system-one-gate.md): features are logged (vps/m1l.py -> *_feat.npy); gather data with yaw4 / M1L_STEP=12 on q1v2, q2v2, q3v2 (`scripts/run_gate_data.sh`), run `scripts/confidence_gate.py` (leave-one-session-out), compare to the inliers>=N gate; then bucketed head and re-use in exp 8 as fix weight. Needs a second world before any generalisation claim

- [ ] C-sync. Design the drone->ground map hand-off (docs/map-sync.md): 25 m tiles with 5 m overlap on the ground plane, versioned/hashed so only changed tiles are pulled; LOD 0 = one global vector per tile (always resident), LOD 1 = coarse render descriptors (4 yaws, sparse positions), LOD 2 = fine 3D points + dense renders for the nearest 1-2 tiles (render-and-refine). Sizes unknown until the urban map exists (measure points/tile)
- [~] C-B6. (first version done as a prior-radius experiment, docs 4g: sigma 5 m -> 81.5 %, gross-wrong 1 % at gate 80; tiles/LOD/streaming proper still open) Tile-streaming experiment on the urban map: restrict M1 to tiles within radius R of a deliberately perturbed prior; measure recall vs R, memory, latency, and the failure/recovery path when the prior is wrong (fall back to LOD 0 global index). Literature on map streaming not yet searched

- [ ] A36. Resource discipline (two crashes from host memory exhaustion): one heavy job at a time; page-cache drop in scripts (done for record/map/gate scripts); optional user-approved `.wslconfig` (memory cap ~10-12 GB, autoMemoryReclaim); gate data q2v2/q3v2 and retrieval_recall must be re-run (lost in the crash)

## B. Room experiments (spec section 5)

- [x] B-exp1. ATE/RPE of FAST-LIO2 vs GT: v2 room, rmse 0.026 m, drift 0.05 % (one trajectory; repeat on other speeds/worlds)
- [x] B-exp2. VPS normal (M0, M1, M1-LoFTR) — re-run after A fixes
- [ ] B-exp3. Lighting change (`--sun`), re-collect q2, re-run methods
- [ ] B-exp4. Viewpoint offset (query path differs from map path)
- [ ] B-exp5. Low-/repeating-texture worlds
- [ ] B-exp6. Map degradation tool (drift/noise/downsample) → recall vs level
- [ ] B-exp7. Stale map (`--moved 0.3`)
- [ ] B-exp8. Pose graph (GTSAM): LIO vs +loop vs +VPS vs both; ATE
- [ ] B-exp9. Compute: p50/p95/p99 latency, VRAM, prepare s

## C. Series B — aerial map → ground query (headline, spec section 5b)

- [x] C-world. `worlds/gen_urban.py` 200×200 m, 50 buildings — **not yet loaded in Gazebo**
- [x] C-smoke. Open `urban.sdf` in Gazebo; check it loads, measure RTF + VRAM; verify drone/robot sensors publish
- [x] C-drone-ctrl. Script a lawnmower path for the drone (`gz topic -t drone/cmd_vel` or similar); record session bag
- [~] C-ground-ctrl. (streets done: ug1, 819 images; alleys still to do) Script a ground-robot drive on roads + alleys; record query bag
- [x] C-B1. FAST-LIO2 on drone bag; ATE, map density, coverage of facades/alleys
- [~] C-B2. (M0 = 0 % of 819; M1-LoFTR 9.8 % within (5 m,10 deg) of 205, docs 4b, decision gate triggered: diagnose before optimising)  M0 / M1 / M1-LoFTR on ground queries (cross-view) — the headline result
- [ ] C-B3. Vary drone altitude + camera pitch; recall vs offset
- [ ] C-B4. Repeating-facade and long-street worlds; recall per world
- [ ] C-B5. Compute on 8 GB for the urban map size
- [ ] C-viewpoint. Change `m1.py` virtual viewpoints from "drone mapping poses" to "sampled ground-level poses" for the urban map (B-d)
- [~] C-coverage. (map-based version done: 60 % coloured, street-level facade 64.8 % uncoloured; GT-surface version not done) Facade/alley coverage metric from GT (B-e)

- [~] C-render. (docs 4d: D0 8.8 -> 73.2 % within (5 m,10 deg); splat size was the main lever; strict 24 % limited by 3D-point precision -> A28) Render fidelity, benchmarked by D0 (zero-gap, 2 min, `scripts/urban_d0.py`; baseline 8.8 %, colour fill 35.1 %): class-aware colour fill (no bleeding onto the road), per-class road colour, push-pull / adaptive splats for near field, depth filter (A29), image inpainting; budget: stop if D0 within (5 m,10 deg) < 70 % after these
- [ ] C-geo. Geometry-only alternative (the map's strength): depth/normal edge or silhouette alignment (analysis by synthesis) and vertical-line / skyline matching against the render; compare with appearance matching on D0 and the 205 queries
- [x] C-decide. (docs 4e: 50.2 % within (5 m,10 deg) >= 30 %, appearance path continues; inlier gate precision only 63.6 %) After C-render: rerun the end-to-end urban test (`scripts/urban_m1_test.sh`) on the same 205 queries; if still < 30 % within (5 m,10 deg) switch to C-geo and report before investing further

- [ ] C-alias. Urban aliasing check: do wrong high-inlier poses show a structure (e.g. a street with the same facade texture repeated)? Compare errors by position/street; then test with unique facade textures (clean-world control, as in the room) to separate texture repetition from other causes
- [~] C-heldout. (route 2 done, docs 4m: 72.3 % within (5 m,10 deg), gross-wrong accepted 6.0 % - the 4h figures were inflated; second world still open) The render fixes were chosen on the 205 queries; re-evaluate on the other 614 ground queries (`ug1` minus the subset) and on a second ground route/world without re-tuning

- [x] C-grav. (done, docs 4l: +4-5 points at IMU 0.1 deg, worse than no IMU at 0.5 deg; decision: stop chasing sub-0.5 m) Gravity-aided 4-DoF refinement (IMU gravity gives pitch/roll): implemented (m1l.grav_refine, harness GRAV_SIGMA_DEG), test running; if it works also test with realistic IMU gravity error (>0.1 deg, bias, motion acceleration) and on ug1s
- [~] C-const. (audit 4o: provenance points reproject 3 px / 10 px (filled) off with ground +1.2 px bias and depth -0.2..-0.4 m; ray-consistent fix made accuracy WORSE; still open) A constant ~0.3 m vertical offset remains at zero pitch error (docs 4k); candidates: ground/voxel-layer bias in the provenance, near-field render; not yet isolated

- [x] C-seg. (result: docs 4p; x=-50 south = render/matching, oracle 7 %; colour not the cause) Why do x=-50 south and the second y=-50 pass fail (28.6 % / 74.4 % within (5 m,10 deg)) while other streets reach 93-98 %? Candidates not yet tested: viewpoint/yaw coverage at those places, aliasing between similar blocks (4 facade textures), local colour coverage along the street rather than per 25 m cell

## V. Vision techniques from the 2026 search (docs/related-work.md); ordered by cost/benefit against MEASURED problems

- [x] V1. (done, docs 4n: plain joint solve worse; consensus unanimity halves gross-wrong (5.6 -> 2.2 % at 69 % accepted), 1 m accuracy 87 -> 96.5 %, 0.5 m floor stays; target <= 1 % not reached; odometry simulated) Multi-frame pose (no download): jointly solve ONE pose from N consecutive frames with relative motion from odometry (simulate: GT relative pose + drift/noise) as a rig/generalised PnP over the existing LoFTR matches. Targets the 0.5 m rotation-translation coupling (corr 0.95, distant structure has no parallax in one frame) and aliasing (consensus across frames); report vs single frame, with odometry noise levels
- [ ] V2. Geometry-only matching (C-geo): render depth/normal from the map, predict query depth with MoGe-2 (or Metric3D v2), score candidate poses by depth/semantic agreement (SemCityLoc-style); needs weights downloads (ask first) and a check of MoGe-2 metric scale on our synthetic street images
- [ ] V3. Matcher swap: RoMa v2 (DINOv3 backbone, synthetic-heavy training) instead of LoFTR on D0/D1 and the urban queries; MINIMA for RGB-vs-depth/normal renders; check licences, VRAM (8 GB) and weights size first
- [ ] V4. Semantics: SAM 3 masks (sky/building/road) for skyline/IoU scoring and for masking dynamic objects; only if V2 needs it
- [ ] V5. Tracking models (CoTracker3 / TAPIP3D) for persistent landmarks: only if V1 shows multi-frame constraints help and the matcher-based version is too slow

## R. Evidence for real use (docs/evidence-plan.md)

- [ ] R1. Agree the acceptance criteria table with the user (false-accept <= 1 %, accepted within (0.5 m, 5 deg) >= 95 %, latency <= 1 s, ...)
- [ ] R2. Perturbation study in the colouring step: camera-LiDAR extrinsic error (1-2 cm, 0.5-1 deg), time offset (+-20-50 ms), mapping-pose noise; report recall and gate behaviour vs error size
- [ ] R3. >= 3 worlds (layout + texture seeds), session-level bootstrap intervals for every headline number
- [ ] R4. Lighting change between mapping and query (sun intensity/direction), with CLAHE/robust preprocessing variants (= B-exp3 for the urban world)
- [ ] R5. Changed world: moved/removed objects, parked cars or moving actors (= B-exp7 for the urban world)
- [ ] R6. Closed-loop map colouring: after a high-confidence fix the ground robot projects its image onto unseen facade points; measure coverage and later recall
- [ ] R7. Real-appearance-gap test on a public real dataset with a LiDAR/3D map + camera queries (dataset to be verified first)
- [ ] R8. Report: which claims are sim-only, which survived perturbations, and the stated limits (README/CV wording)

## D. Packaging — GitHub + CV

- [~] D1. (git init done locally, nothing committed/pushed) `git init`, `.gitignore` (data/, `__pycache__`, model weights, `*.sdf` outputs)
- [ ] D2. `README.md`: headline, how to reproduce one run, result table, caveats
- [~] D3. (2 figures: docs/figures/v2_q1_same_direction.png, v2_q2_reversed.png) Figures: recall-threshold curves + per-threshold bars from `results/*_err.npy`
- [ ] D4. In every doc: "design study — all methods consume GT at some step; not a deployable VPS yet"
- [ ] D5. CV bullet, drafted from actual results after audit re-run

## E. M2–M4 (optional, do only if time permits)

- [ ] E-M2 CMR-Agent / LHMap-loc (learned 2D-3D)
- [ ] E-M3 3DGS-ReLoc (Gaussian map) - DEPRIORITISED by measurement (docs 4m): 64.8 % of street-level facade points are seen by 0 drone images; no official 3DGS-ReLoc code found
- [ ] E-M4 R-SCoRe (scene coordinate regression) - DEPRIORITISED (docs 4m): needs ground-level training views; R-SCoRe trained on 4x RTX 4090 for 4-8 h (not feasible on one 8 GB GPU)

- [ ] C-mcl. MCL (docs 4p): 0 % gross-wrong, 85-88 % within (0.5 m,5 deg) on route 2 with simulated odometry. TODO: held-out route, kidnapped/global start, real odometry noise model, full 6-DoF.
- [x] C-wpnp. Depth-weighted PnP: no gain (docs 4p).
- [x] C-xfeat. XFeat matcher (docs 4q): hybrid XFeat+LoFTR refine 74.0 %, 843 ms. TODO: LightGlue (DISK), TensorRT/fp16, XFeat on the sequence+MCL, a second route.
- [x] C-disklg. DISK+LightGlue (docs 4q): prior mode 91.2 % / 39.3 % / 0.57 m / 859 ms = best so far. TODO: recalibrate gate, MCL on these poses, hybrid refine, TensorRT, second route.
- [x] C-hybrid. XFeat+DISK refine hybrid: not better than DISK+LightGlue alone (docs 4q). Dropped.
- [ ] C-mcl2. MCL with DISK+LightGlue poses needs recovery injection (docs 4r); settings SXY 1.5 / INJECT 0.1 chosen on route 2 -> verify on a held-out route; kidnapped start with top-1 global poses FAILS (docs 4r): needs multi-hypothesis observations or a learned gate.
- [x] C-route3. Held-out route 3: DISK+LightGlue transfers (85.9 % prior); MCL settings do NOT transfer, only the spread<0.7 m gate does (docs 4s).
- [~] C-mh. Multi-hypothesis MCL: kidnapped start converges at frame 86 on route 2 (docs 4t); frozen settings (SXY 1.0, EPS 0.5, HMIN 60) to be verified on route 3 (seq_ug3_hyp_global.npz, collecting).
- [~] C-trt. Profiled (docs 4u): LightGlue x50 = 780 of 836 ms, overhead-bound. fp16 no effect; kornia batch unsupported; lever = smaller K. TensorRT not run (needs 3rd-party export; little expected gain).
- [ ] C-stream. Streaming replay (drone map from FAST-LIO poses in time chunks) vs GT-pose map: tests the map-drift risk.
- [~] C-calib. Colour-registration sensitivity (extrinsic rot 0.5/1/2 deg, 0.1 m, jitter) with frozen settings: scripts/run_calib.sh -> results/urban/calib_*.json (running).
- [~] R3-worlds. Generated worlds oldtown12, suburb13, bridge14, canyon15, grid11 (worlds/gen_city.py); scripts/world_pipeline.sh runs each end to end with frozen settings; scripts/run_all_worlds.sh queues them (hours). Results: results/worlds/*.json.
- [x] C-calib. Done (docs 4v): angular colour-registration error is the sensitive factor (0.5 deg: 41 -> 10 % fine; 2 deg: median 3 m); position errors 0.1 m tolerated. TODO: automatic colour re-registration if the real calibration cannot be ~0.1-0.2 deg.
- [~] C-closed. Closed-loop Gazebo test: attempt 1 failed (docs 4w); replay with filter-prior + far-pose rejection works (0.29 m median); attempt 3 in Gazebo: first 220 m fine (0.4-1.5 m), lost on the x=-50 south street, not successful (docs 4w). Next: weak street, multi-hypothesis in the loop, re-localization, obstacle avoidance.
- [~] R3-worlds queue started again (scripts/run_all_worlds.sh) after the closed-loop attempts.
- [ ] C-flight. Mapping-flight design test: re-fly canyon15 (and grid11) low along street centre lines (z ~15-25 m) and compare street-level colour coverage + localization (docs 4x: success tracks street-level coverage across worlds).
