#!/usr/bin/env python3
"""
Warp meshes from JRC2018_VNC_FEMALE template space to BANC space.
"""

import sys
import os

import trimesh

import banc

#import navis
#import flybrains

#target_space = 'FANC'
#target_space = 'JRCVNC2018F'


def show_help():
    print('Run via: ./warp_mesh_to_BANC.py some_mesh.{obj,stl} folder_to_put_output_in/')


def main():
    # Argument validation
    if len(sys.argv) < 3:
        show_help()
        return
    try:
        input_filename = sys.argv[1]
        if not os.path.exists(input_filename):
            raise FileNotFoundError(input_filename)

        output_folder = sys.argv[2]
        if not os.path.exists(output_folder):
            raise FileNotFoundError(output_folder)
    except:
        show_help()
        raise

    # Load
    mesh = trimesh.load_mesh(input_filename)
    # Do the warping
    warped_vertices = banc.transforms.template_alignment.warp_points_vnc_template_to_BANC(
        mesh.vertices,
        input_units='microns',
        output_units='microns'
    )
    assert warped_vertices is not None, f'Warping failed for {input_filename}'
    mesh.vertices = warped_vertices
    # Warping using navis on the old numpy-stl type meshes
    #mesh.v0 = navis.xform_brain(mesh.v0, source='JRCVNC2018U', target=target_space)
    #mesh.v1 = navis.xform_brain(mesh.v1, source='JRCVNC2018U', target=target_space)
    #mesh.v2 = navis.xform_brain(mesh.v2, source='JRCVNC2018U', target=target_space)
    # Save
    mesh.export(output_folder + '/' + os.path.basename(input_filename))
    print('Saved to', output_folder + '/' + os.path.basename(input_filename))


if __name__ == "__main__":
    main()
