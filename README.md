# Aerial-LiDAR-to-Ground-Camera Localization (simulation study)

A drone with LiDAR and a camera maps an urban area. A ground robot with **only a camera** then estimates its own 6-DoF pose inside that map.
Everything here runs in simulation (Gazebo Harmonic, ROS 2 Jazzy, one RTX 4060 Ti 8 GB). It is a design and evidence study, **not** a field-ready system; the negative results are part of the deliverable.

## Approach

1. **Mapping (drone).** FAST-LIO builds a LiDAR map; the drone camera colours it. Map geometry comes from the odometry; colours are projected with the camera poses.
2. **Render-and-match (robot).** The coloured map is rendered from thousands of virtual ground-level viewpoints (z-buffer splatting plus hole filling). For every rendered pixel the source map point is stored (provenance).
3. **Localization.** A global descriptor (MegaLoc) shortlists views, a learned matcher (DISK + LightGlue; LoFTR and XFeat were also tested) matches the robot image with each view, and PnP + RANSAC on the stored 3D points returns a metric 6-DoF pose.
4. **Filtering.** A planar particle filter (MCL) fuses the poses with odometry; a learned confidence gate and a particle-spread gate decide when a pose can be trusted.

## Main results (simulation only)

Thresholds: coarse = (5 m, 10 deg), fine = (0.5 m, 5 deg). "Prior" = a ~5 m position prior; "global" = no prior.

| Experiment | Result |
|---|---|
| Matcher comparison, development world, prior, 285 queries | LoFTR 72 % coarse, 27 % fine, 2.2 s; **DISK + LightGlue 93 % coarse, 41 % fine, 0.41 s** |
| Same method on other routes of the development world | 97 % and 86 % coarse |
| Particle filter + spread gate (2 routes, simulated odometry) | 0.0 % grossly wrong accepted poses, 85-92 % fine on accepted frames, 15-18 % of frames withheld |
| Learned confidence gate, leave-one-session-out | AUROC 0.96-0.99 across worlds, clearly better than an inlier-count gate on the hardest world |
| **Five randomly generated worlds** (frozen settings, no per-world tuning), prior | grid 56 %, bridge/tunnel 49 %, old town 16 %, tall-building canyon ~0 % coarse; one open suburban world could not be evaluated because the drone's LiDAR odometry failed |
| Global start (no prior) in the new worlds | 0-26 % coarse; a prior is mandatory |
| Colour-registration error of the drone map | 0.1 m position error tolerated; **0.5 deg rotation error cuts fine accuracy from 41 % to 10 %** |
| Image degradation (route 2) | noise, exposure, colour cast, JPEG: negligible; motion blur: 93 % to 69 % coarse; uncorrected lens distortion: fine 41 % to 5 % |
| Camera at head height (AR use case) | needs views rendered at the same height; anchor 20 m ahead lands off by a median 0.9 m (not AR-grade) |
| Closed-loop driving in Gazebo (estimate-only control) | first ~220 m accurate (0.4-1.5 m), then lost on a hard street; **not completed** |

### Why the new worlds are worse
An oracle diagnosis (perfect retrieval, match the nearest rendered view) shows that the result in each world equals the oracle result, i.e. **matching rendered views against real images is the bottleneck, not retrieval**. The number of confident matches falls from ~350 (development world) to 7-11 (hardest worlds). Rendered views of a sparse aerial LiDAR map are far sparser than the dense scans used in related work; narrow canyons also have almost no street-level facade points. See `docs/failure-modes.md`.

## Limitations (read before citing any number)

- Simulation only: box buildings with synthetic textures, constant lighting, no vehicles, people or vegetation, ideal camera.
- The strongest numbers come from the world the method was developed on. Frozen-settings results on new worlds are much lower.
- Odometry for the particle filter is simulated from ground truth; the filter is planar.
- Closed-loop driving did not complete the route; global (no prior) localization is not usable.
- Night, smoke, rain, moving or destroyed structures are not tested.
- Colour registration of the map must be accurate to roughly 0.1-0.2 deg for fine accuracy; targetless calibration methods in the literature report ~0.4 deg.

## Repository layout

| Path | Content |
|---|---|
| `vps/` | localizer (map rendering, matchers, PnP), particle filter, evaluation harness |
| `ros/` | ROS 2 nodes: waypoint driving/flying, closed-loop node, FAST-LIO configuration, bag tools, ATE evaluation |
| `worlds/` | world generators (room, 200 m urban world, five random city styles) |
| `scripts/` | experiment drivers and analysis scripts (one per experiment; names match the log) |
| `results/` | per-experiment metrics (JSON) and per-query error arrays |
| `docs/experiment-log.md` | full experiment log, including corrections and negative results |
| `docs/REPORT.md` / `docs/REPORT.html` | long report (self-contained HTML) |
| `docs/failure-modes.md` | catalogue of failure factors with evidence status |
| `docs/papers-notes.md` | notes from the related work that was read in full |
| `docs/evidence-plan.md` | acceptance criteria and what a simulation can and cannot establish |
| `TODO.md` | living task list |

## Reproducing (outline)

Requirements: Ubuntu 24.04 (WSL2 works), ROS 2 Jazzy, Gazebo Harmonic, a CUDA GPU (8 GB is enough), PyTorch, kornia, FAST-LIO (ROS 2 port).
Typical flow for one world: generate the world (`worlds/gen_city.py`), record a drone flight and a ground drive (`ros/run_urban_session.sh`), run FAST-LIO and build the coloured map (`ros/run_lio.sh`, `vps/build_lidar_map.py`), build viewpoints (`vps/viewpoints.py`), evaluate (`scripts/world_pipeline.sh NAME`). Settings used for the headline numbers are in the scripts (`scripts/run_disklg.sh`, `scripts/world_pipeline.sh`).
Large recordings and maps are not included.

## Related work

CRISTAL (camera registration in coloured LiDAR scans with neural rendering), Visual Localization in 3D Maps (point cloud, mesh and NeRF databases), 3DGS-ReLoc, SemCityLoc (semantic-geometric alignment), MegaLoc, LightGlue, DISK, XFeat, MINIMA, RoMa v2, FAST-LIVO2. Notes on what each paper does and how it relates to this study are in `docs/papers-notes.md`. This study does not claim novelty over them; the cross-view setting (aerial map, ground camera) and the failure analysis are its focus.

## What is not done yet

**Missing evidence**
- Real data of any kind (no real camera, LiDAR or drone data has been used).
- Lighting changes, shadows, rain, night, smoke, vegetation, vehicles and people; changed or destroyed structures after the map was built.
- A second simulator or a more realistic world (textures, assets) to check that conclusions are not specific to Gazebo's boxes.
- Closed-loop driving of a whole route (only the first ~220 m worked).
- Latency and memory on embedded hardware (all timings are PyTorch on a desktop RTX 4060 Ti; TensorRT was not run).
- Drone-camera and drone-LiDAR degradation (only the ground-camera images were degraded).
- Planar filter only: no height, roll or pitch in the particle filter; odometry is simulated from ground truth.
- Bridge and tunnel segments of the bridge world were not analysed separately.
- No comparison against a ground visual SLAM baseline.

**Not solved**
- Fine accuracy has a floor near 0.5 m (five attempted fixes failed).
- Matching of rendered views against real images fails in narrow or sparse-map worlds (7-11 confident matches on average in the hardest worlds).
- Localization without a position prior (global): 0-26 % coarse in new worlds; start-from-unknown filtering converges in only half of the start places.
- Confident but wrong poses (aliasing) are only mitigated by gates, not eliminated.
- The drone's LiDAR odometry fails on flat open terrain; the ground robot depends on it.
- Fine accuracy depends on the colour registration of the map being accurate to ~0.1-0.2 deg.

## Planned improvements and fixes

| Problem | Planned fix | Status / expected effort |
|---|---|---|
| Rendered views too sparse and leaky (background points show through gaps) | Background-leak (depth) filter in the renderer, then a hole-filling / neural point renderer as in CRISTAL; later a Gaussian-splat map initialised from the LiDAR | Leak filter implemented (`M1_LEAK`), being evaluated; neural renderer is a multi-day item with uncertain payoff |
| Dependence on colour (calibration, appearance gap) | Align by geometry instead of colour: predict depth from the image (monocular metric depth) and compare with depth rendered from the LiDAR map around the prior (SemCityLoc-style); alternatively match RGB to rendered depth with a cross-modal matcher (MINIMA) | Not started; prototype is 1-2 days plus evaluation on all worlds; needs model downloads |
| Colour registration error | Automatic re-registration of the colours using photometric consistency across drone frames; test recovery of injected 0.5-2 deg errors | Not started; about half a day to a day |
| Missing street-level facades (canyon) | Mapping flight that flies low along the streets with oblique views; let the ground robot colour the walls it sees; compare street-level coverage and success | Not started; a few hours |
| Loss of tracking / no prior in the field | Growing search radius with the filter uncertainty, filter-based recovery after cutting the fixes for N seconds, road-graph map matching (HMM), several pose hypotheses | Not started; a few hours for the radius growth and recovery test |
| Aliasing (confident but wrong) | Offline self-similarity ("ambiguity") map of the rendered views to demand more frames in risky zones; confusion analysis of wrong top-K; learned gate calibrated on held-out worlds (done); active localization | Self-similarity map and confusion analysis: a few hours |
| Scene changes after mapping | Remove / add structures after the map is built and measure; change masking (down-weight regions whose render disagrees with the image while localization is confident); later online map update | Simulation test: a few hours |
| Drone SLAM failure on open flat terrain | Fly lower or oblique; try a LiDAR-inertial-visual odometry (FAST-LIVO2, ROS 1 port needed) | Not started |
| Latency on embedded hardware | Smaller shortlist K, early exit, a custom batched matcher or an exported engine; measure on a Jetson-class board | Not started |
| Larger areas | Tile / level-of-detail streaming of the map (out-of-core chunks as in DiskChunGS) | Not started |
| Planar filter | Full 6-DoF filter with IMU | Not started |
| Real-world gap | A small real dataset (phone video + a LiDAR map, or a public dataset with LiDAR and camera such as KITTI-360 to test the renderer on real images); registration and licence terms must be handled by the user | Needs real data from the user |

The most informative next steps, in order: leak filter and renderer, geometry-based (depth) alignment, recovery after tracking loss, scene-change tests, street-level mapping flights. If these do not lift the new-world results above roughly 70 % coarse accuracy, the honest conclusion is a set of conditions under which the approach works, not a general claim.

## Licenses

No license has been chosen yet. Third-party code and weights used (kornia, DISK, LightGlue, XFeat, MegaLoc, FAST-LIO and others) have their own terms that must be checked before redistributing anything derived from them.
