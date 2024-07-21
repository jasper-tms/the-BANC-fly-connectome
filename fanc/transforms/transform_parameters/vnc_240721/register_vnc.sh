#!/bin/bash
# Run elastix to register the BANC's VNC to the JRC2018 female VNC template
#
# This isn't meant to be run by BANC users but instead to provide a record of
# how registration was done in case we want to reproduce it or improve it later

img_fn=banc-synapse-cloud-v1.1_sizethresh6_blursigma1_16bit0-3_VNC.nrrd
template_fn=templates/JRC2018_VNC_FEMALE_4iso.nrrd

# Elastix affine:
# - Initialize with a manually specified affine transform
run_elastix \
    "$img_fn" \
    -t "$template_fn" \
    -a \
    -at0 vnc_initial_transform/banc_vnc_manual_affine_transform.txt \
    -n


# Elastix Bspline round 1:
# - 32 micron grid spacing (produced by "-s 15.2-25-10.2" in combination with
#   the anisotropic stretching caused by the initial affine transform)
# - Low bending weight
# - Manually specified corresponding points
run_elastix \
    "$img_fn" \
    -t "$template_fn" \
    -p corresponding_points_vnc_banc.txt \
    -tp corresponding_points_vnc_JRC2018F.txt \
    -b \
    -o round1withpoints \
    -s "15.2-25-10.2" \
    -w "1" \
    -n


# Elastix Bspline round 2 to refine the alignment of smaller features:
# - 12 micron grid spacing (produced by "-s 5.7-9.4-3.9" in combination with
#   the anisotropic stretching caused by the initial affine transform)
# - Higher bending weight to reduce unrealistic deformations
# - No corresponding points to allow elastix to pay full attention to image correlation
run_elastix \
    "$img_fn" \
    -t "$template_fn" \
    -b \
    -bt0 "${img_fn/.nrrd/}"_elastix_to_fixed_template/elastix_Bspline/15.2-25-10.2spacing_1bendingweight_round1withpoints/TransformParameters.0.txt \
    -o round2 \
    -s "5.6-9.8-3.8" \
    -w "4" \
    -n
