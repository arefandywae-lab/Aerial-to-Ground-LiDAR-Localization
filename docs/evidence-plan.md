# Evidence plan: from proof of concept to "worth deploying"

Goal (user): a PoC that gives evidence the approach is worth taking to real use and can be made accurate. A simulation cannot prove real-world viability; it can show feasibility,
quantify the failure modes, and de-risk the expensive real-data work. This plan separates what the sim can answer from what needs real data.

## 1. Proposed acceptance criteria (to be agreed; numbers are proposals, not facts)

Measured on **held-out worlds and sessions**, per query set, with confidence intervals bootstrapped over *sessions* (frames within a session are near-duplicates):

| Criterion | Proposed target | Current (room v2, one world) |
| --- | --- | --- |
| Accepted poses within (0.5 m, 5 deg) | >= 95 % of accepted | 90.5 % localized-within at q1v2 (no gate); gate not yet built |
| Wrong pose accepted by the confidence gate (false accept) | <= 1 % of queries | not measured (gate data being re-collected) |
| Fraction of queries accepted | >= 70 % | 93 % localized, 77-92 % within 5 m |
| Median accepted error | <= 0.15 m, 1 deg | 0.07 m, 0.25 deg (q1v2) |
| Latency, median / p95, on an 8 GB GPU | <= 1 s / 2 s | 3.7 s / ~4 s (6.4 s with 4 yaws); retrieval step now ~8.5 ms |
| Map memory resident on the robot | fits the 8 GB budget at 200 x 200 m, scales by tiles beyond | not measured on the urban map |
| Behaviour when something is wrong | detects and reports (not silent): aliasing, stale map, miscalibration | aliasing detection yes (gate pending), others untested |

## 2. What the sim CAN establish (and what is still missing)

| Question | Experiment | Status |
| --- | --- | --- |
| Does the aerial-LiDAR-map -> ground-camera pipeline work at all? | series B (C-B2): M1 on `ug1` vs M0 | M0 = 0 %; M1 pending (views + retrieval ready) |
| How does accuracy depend on viewpoint (yaw, offset, height)? | q2v2, q3v2, B3 | yaw done in the room; lateral/height not |
| Does it survive repeated structure? | exp 5, urban facades (4 texture variants) | aliasing diagnosed in the room, not in the city |
| Does it survive **calibration and timing errors** (real systems always have them)? | perturb camera-LiDAR extrinsic (1-2 cm, 0.5-1 deg) and time offset (+-20-50 ms) when colouring the map, and pose noise on the mapping poses | **not done; all current maps use GT poses for colour** (we even found 0.5 s timing issues in our own recording) |
| Does it survive appearance change between mapping and query? | exp 3 (sun intensity/direction, shadows), CLAHE/robust-feature variants | not done |
| Does it survive a changed world (parked cars, moved objects)? | exp 7 (`--moved`), moving actors | not done |
| Is it robust across scenes, not one lucky layout? | >= 3 worlds (layout + texture seeds), session-level bootstrap | not done (single room, single city) |
| Can it run within the compute budget? | exp 9: latency/VRAM per query on the urban map, tiled streaming, LOD | partly (retrieval timing) |
| Can failures be detected and handled? | confidence head (docs/system-one-gate.md), fusion with odometry (exp 8) | features logged, data re-collection pending |
| Can the map improve itself (ground robot colours unseen facades)? | closed-loop colour update after high-confidence fixes | idea only |

## 3. What the sim CANNOT establish (needs real data; state this in every report)

- Real image formation: lens distortion, exposure and auto-gain, motion blur, rolling shutter, sun glare, weather. The sim camera is an undistorted pinhole under constant light.
- Real LiDAR: noise structure, multipath, dropouts on glass/water, intensity; sim LiDAR is Gaussian noise on ideal ray hits.
- Real textures and clutter: the sim has 4 repeating facade textures and no cars, people, signs, vegetation or glass.
- Real dynamics and drift: GPS-denied flight, wind, vibration; real odometry error models.
- Real mapping alignment: here the LiDAR-to-world alignment uses GT; in reality the map lives in its own frame (fine for localization, but colour projection needs calibrated, time-synced sensors).

Cheapest real-data de-risking, in order: (1) test render-and-match on an existing public real dataset that has a LiDAR/3D map and camera queries to measure the **real appearance gap** (candidate datasets to verify before use: KITTI, nuScenes, Oxford Spires,
which appear in the DRS-VPT training list; none is aerial-map -> ground-camera); (2) a small real capture (handheld or ground robot with LiDAR + camera) mapped and re-visited under different light; (3) real aerial LiDAR/photogrammetry of a street, queried from the ground.

## 4. Evidence standards we will keep
- Held-out worlds and sessions; nothing tuned on the test set; every tuning knob listed with where it was tuned.
- Session-level bootstrap intervals, not frame-level; seeds reported only for what they vary.
- Negative results kept (SIFT on renders, M0 cross-view, aliasing).
- Everything reproducible from the scripts in the repo; "design study: GT used at X, Y, Z" stated wherever a number appears.

## 5. Order of work (cheap and decisive first)
1. Finish end-to-end retrieval (running), then **M1 on the ground queries** (the headline claim, with ground-level views and the uncoloured-facade problem measured).
2. Confidence head with held-out sessions (false-accept rate is the deployment-critical number).
3. Perturbation studies: calibration/timing/pose noise in the colouring step; lighting change; stale map.
4. A second and third world; recompute everything with session-level intervals.
5. Closed-loop map colouring by the ground robot (the lever aimed at the measured coverage gap).
6. Real-data de-risking per section 3.
