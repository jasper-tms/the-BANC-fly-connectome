#!/bin/bash

# Elastix affine
# Use corresponding points to drive the alignment (ignoring two pairs
# at the start of the neck connective which will be used in Bspline).
# Use a mask to only pay attention to image correlation in the central
# brain (though image correlation isn't that important anyway when
# corresponding points are provided).
run_elastix \
    banc-synapse-cloud-v1.1_sizethresh6_blursigma1_16bit0-3_brain.nrrd \
    -t templates/JRC2018_FEMALE_38um_iso_16bit.nrrd \
    -tm templates/JRC2018_FEMALE_38um_iso_centralbrainmask.nrrd \
    -p corresponding_points_brain_banc_22minus2.txt \
    -tp corresponding_points_brain_JRC2018F_22minus2.txt \
    -a \
    -at0 brain_initial_transform/banc_brain_manual_affine_transform.txt \
    #-n
    

# Elastix Bspline round 1 at 12 micron spacing, with manually specified corresponding points
run_elastix \
    banc-synapse-cloud-v1.1_sizethresh6_blursigma1_16bit0-3_brain.nrrd \
    -t templates/JRC2018_FEMALE_38um_iso_16bit.nrrd \
    -p corresponding_points_brain_banc_22.txt \
    -tp corresponding_points_brain_JRC2018F_22.txt \
    -b \
    -o round1 \
    -s 12 \
    -w 10 \
    #-n

# Elastix Bspline round 2 at 8 micron spacing, with manually specified corresponding points
run_elastix \
    banc-synapse-cloud-v1.1_sizethresh6_blursigma1_16bit0-3_brain.nrrd \
    -t templates/JRC2018_FEMALE_38um_iso_16bit.nrrd \
    -p corresponding_points_brain_banc_22.txt \
    -tp corresponding_points_brain_JRC2018F_22.txt \
    -b \
    -bt0 banc-synapse-cloud-v1.1_sizethresh6_blursigma1_16bit0-3_brain_elastix_to_fixed_template/elastix_Bspline/12spacing_10bendingweight_round1/TransformParameters.0.txt \
    -o round2 \
    -s 8 \
    -w 4

# Invert the final Bspline transform
invert_elastix \
    banc-synapse-cloud-v1.1_sizethresh6_blursigma1_16bit0-3_brain_elastix_to_fixed_template/elastix_Bspline/8spacing_4bendingweight_round2
