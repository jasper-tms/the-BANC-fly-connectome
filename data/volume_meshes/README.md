## Warping VNC neuropil regions to BANC space
I downloaded the VNC neuropil region meshes and tract meshes in `.obj` format from Virtual Fly Brain. [Here's a direct VFB link](https://v2.virtualflybrain.org/org.geppetto.frontend/geppetto?id=Court2020&i=VFB_00200000,VFB_00104653,VFB_00104635,VFB_00104652,VFB_00104651,VFB_00104650,VFB_00104649,VFB_00104648,VFB_00104647,VFB_00104646,VFB_00104645,VFB_00104644,VFB_00104643,VFB_00104642,VFB_00104641,VFB_00104640,VFB_00104639,VFB_00104638,VFB_00104637,VFB_00104636,VFB_00104634,VFB_00104633) with the regions and tracts loaded into their 3D viewer. You can go to the `Layers` tab, click on the region or tract you're interested in which will jump you to the `Term Info` tab for that object, then scroll down to the `Downloads` section and download the `Mesh/Pointcloud (OBJ)`.


Once downloaded, I opened the .obj file in meshlab, inverted faces (`Filters > Normals, Curvatures and Orientation > Invert Faces Orientation`), deleted any small connected components that weren't attached to the main mesh, then saved as an `.stl` with binary encoding.
The meshes downloaded from VFB are aligned to the unisex VNC template, so I first used `navis.xform_brain()` to warp them into alignment with the female VNC template. Then, I warped the meshes from `JRC2018_VNC_FEMALE` space to BANC space by running:

    ./warp_mesh_to_BANC.py "JRC2018_VNC_FEMALE/VFB_00104652 prothoracic neuromeres_cleaned.stl" JRC2018_VNC_UNISEX_to_BANC

**NOTE:** Elastix must be installed and its lib and bin paths must be appended
to the `LD_LIBRARY_PATH` and `PATH` environment variables. See [`pytransformix` documentation](https://github.com/jasper-tms/pytransformix#installation) for details.


## [TODO for the BANC] Cutting region and tract meshes into left and right halves
In the template the neuromeres and tracts are not delineated by side. For
example the left and right prothoracic neuromeres are stored in a single mesh
`VFB_00104652 prothoracic neuromeres_cleaned.stl`.

Here, we cut each of these neuromeres and tracts into a left and a right half.
To do so, we (1) cut the meshes into halves by the midplane in the unisex
template space, (2) warping them to FANC space. The first step can be done by
simply creating two boxes, one on each side of the midplane, and taking the
intersections of the neuromere/tract mesh and the boxes.

To run it:

    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:<elastix-installation-dir>/lib
    export PATH=$PATH:<elastix-installation-dir>/bin
    python cut_neuromeres_by_side.py

**NOTE:** Elastix must be installed and its lib and bin paths must be appended
to the `LD_LIBRARY_PATH` and `PATH` environment variables. See [`pytransformix` documentation](https://github.com/jasper-tms/pytransformix#installation) for details.

This will create a set of STL files under `JRC2018_VNC_UNISEX_to_FANC/meshes_by_side`. Note that left/right designations are inverted when transforming from the template space to the FANC space. This is due to different Z ordering conventions.
