# "System One" head for the localizer (design note)

Concept borrowed from Jev-style "System One" models as described in a [DataCamp article](https://www.datacamp.com/blog/system-one-models-jev): a fast model whose output is a typed decision with a calibrated probability instead of free text.
Only the *idea* is used; Jev's own claims (70-500 ms, 0 % structured-output errors, RLCD training) are the vendor's, relayed by that article, and unverified here. Jev takes text-like program state, so it cannot consume our images or point clouds.

## What we build
A small model of our own on top of the localizer. System Two = LoFTR + PnP (slow, already there). System One = a few-microsecond head that reads the statistics System Two already produced and returns a **typed output**:

| Output | Type | Use |
| --- | --- | --- |
| `p_correct` | probability, calibrated | accept / reject / fall back (re-localize, ask for another view, trust odometry) |
| `error_bucket` | distribution over {<0.25 m & 2 deg, <1 m & 5 deg, <5 m & 10 deg, wrong} | downstream filter can weight the fix by expected error (exp 8) |
| later: `rank_score` per candidate render | scores | cheap re-ranking after the vector-database shortlist |

Input features (logged per query by `vps/m1l.py`): inlier count and ratio, matches, retrieval top-1/top-2 counts and margin, number of renders contributing inliers, spatial spread of inliers, reprojection error, median depth, and the **agreement between the PnP pose and the retrieved render's pose** (position and heading distance) which is the signal that should expose aliasing: a self-consistent but wrong pose sits far from where the retrieved render was taken.

## Why it is needed
With the original textures, 25/154 poses were wrong yet had a median of 204 inliers (good: 758), so no inlier threshold could separate them (audit finding). With clean textures the plain inlier gate works (99.7 % precision at 40 inliers) but accepts only part of the correct poses; a learned head should accept more at the same precision, and it must keep working when aliasing is present.

## Protocol (guards against fooling ourselves)
- Leave-one-**session**-out (train on two query sessions, test on the third); frames within a session are near-duplicates, so a random split would leak.
- Compare against the baseline gate "inliers >= N" on AUROC and on the accepted fraction at fixed precision (90/95/99 %); report Brier score and calibration bins.
- Plain logistic regression first (`scripts/confidence_gate.py`); a bucketed (ordinal) head and gradient boosting only if the linear model leaves a clear gap.

## Limits already known
- Few labelled queries, strongly correlated, one room and one texture set: generalisation to the urban world is **not** established by a room-trained head. It must be retrained/validated per world, and ideally on a second room.
- Calibration under distribution shift (new world, lighting) will degrade; this needs a held-out world to measure.
- It cannot fix a wrong pose, only flag it; recall at high precision is the figure of merit.
