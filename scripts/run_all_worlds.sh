#!/bin/bash
# waits for the calibration sweep (one heavy job at a time), then runs the five generated worlds one after another

for W in grid11 bridge14 canyon15 oldtown12 suburb13; do bash /mnt/a/SlamProject/scripts/world_pipeline.sh $W > /mnt/a/SlamProject/scripts/world_$W.log 2>&1; done
echo ALLWORLDS_DONE
