#!/bin/bash
# Run elastix to register the BANC's brain to the JRC2018 female brain template
#
# This isn't meant to be run by BANC users but instead to provide a record of
# how registration was done in case we want to reproduce it or improve it later

img_fn=banc-synapse-cloud-v1.1_sizethresh6_blursigma1_16bit0-3_brain.nrrd
img_edges_fn=banc-synapse-cloud-v1.1_sizethresh6_blursigma1_16bit0-3_brain_sigma7_edges.nrrd
template_fn=templates/JRC2018_FEMALE_38um_iso_16bit.nrrd
template_edges_fn=templates/JRC2018_FEMALE_38um_iso_16bit_sigma1_edges.nrrd


# Elastix affine:
# - Initialize with a manually specified affine transform
# - Use a mask to only pay attention to image correlation in the central brain
run_elastix \
    "$img_fn" \
    -t "$template_fn" \
    -tm templates/JRC2018_FEMALE_38um_iso_centralbrainmask.nrrd \
    -a \
    -at0 brain_initial_transform/banc_brain_manual_affine_transform.txt \
    -n
    

# Elastix Bspline round 1 to correct coarse elastic deformations:
# - 32 micron grid spacing (produced by "-s 24-24-14.2" in combination with the
#   anisotropic stretching caused by the initial affine transform)
# - Low bending weight
# - Manually specified corresponding points
# - Align the edge-detected version of the images which empirically seems to produce
#   slightly better results at this step
run_elastix \
    "$img_edges_fn" \
    -t "$template_edges_fn" \
    -p corresponding_points_brain_banc.txt \
    -tp corresponding_points_brain_JRC2018F.txt \
    -b \
    -bt0 "${img_fn/.nrrd/}"_elastix_to_fixed_template/elastix_affine/TransformParameters.0.txt \
    -o round1withpoints \
    -s "24-24-14.2" \
    -w 1 \
    -n


# Elastix Bspline round 2 to refine the alignment of smaller features:
# - 12 micron grid spacing (produced by "-s 9-9-5.8" in combination with the
#   anisotropic stretching caused by the initial affine transform
# - Higher bending weight to reduce unrealistic deformations
# - No corresponding points to allow elastix to pay full attention to image correlation
# - Align the original images because empirically aligning edge-detected images in this
#   step seems to produce worse results
run_elastix \
    "$img_fn" \
    -t "$template_fn" \
    -b \
    -bt0 "${img_edges_fn/.nrrd/}"_elastix_to_fixed_template/elastix_Bspline/24-24-14.2spacing_1bendingweight_round1withpoints/TransformParameters.0.txt \
    -o round2 \
    -s "9-9-5.8" \
    -w "16" \
    -n

# Invert the transform using a slightly coarser grid spacing of 16 microns
# (produced by "-s 11.7-9.6-8.7" in combination with the anisotropic
# stretching caused by the initial affine transform).
invert_elastix \
    "${img_fn/.nrrd/}"_elastix_to_fixed_template/elastix_Bspline/9-9-5.8spacing_16bendingweight_round2 \
    -s "11.7-9.6-8.7"
