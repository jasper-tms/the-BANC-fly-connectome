#!/usr/bin/env python3

from pathlib import Path

import stl
import trimesh
#import navis
#import flybrains

from banc.transforms.template_alignment import warp_points_template_to_BANC


# Configs
output_units = 'microns'
midline = 329 * 0.4    # 0.4um per voxel
unisex_template_dir = Path(
    'JRC2018_VNC_UNISEX/'
)
output_dir = Path(
    'JRC2018_VNC_UNISEX_to_BANC/meshes_by_side'
)
output_dir.mkdir(parents=True, exist_ok=True)
uncut_neuromere_mesh_paths = {
    path.stem: path
    for path in unisex_template_dir.glob('*.stl')
}
whole_vnc_mesh = 'VFB_00200000 JRC2018UnisexVNC'

# Download template mapping transform
#flybrains.download_jrc_vnc_transforms()


# Load meshes with trimesh, split in halves, save
print('Loading meshes...')
uncut_neuromere_meshes = {
    k: trimesh.load_mesh(v)
    for k, v in uncut_neuromere_mesh_paths.items()
}
vnc_bounds = uncut_neuromere_meshes[whole_vnc_mesh].bounds[1, :]
_, y_size, z_size = vnc_bounds.astype('int') + 1

# arguments are: edge lengths, and homogeneous transformation matrix (4x4)
# for the box center. See link below under "Translation" for how this works
# http://www.it.hiof.no/~borres/j3d/math/threed/p-threed.html
right_box = trimesh.creation.box(
    [midline, y_size, z_size],
    [[1, 0, 0, midline * 0.5],
     [0, 1, 0, y_size * 0.5],
     [0, 0, 1, z_size * 0.5],
     [0, 0, 0, 1]]
)
left_box = trimesh.creation.box(
    [midline, y_size, z_size],
    [[1, 0, 0, midline * 1.5],
     [0, 1, 0, y_size * 0.5],
     [0, 0, 1, z_size * 0.5],
     [0, 0, 0, 1]]
)

print('Cutting meshes...')
cut_meshes = {}
for k, mesh in uncut_neuromere_meshes.items():
    if k == whole_vnc_mesh:
        continue    # this is the whole VNC
    cut_meshes[f'{k}_L'] = mesh.intersection(left_box)
    cut_meshes[f'{k}_R'] = mesh.intersection(right_box)

for k, mesh in cut_meshes.items():
    mesh.export(output_dir / f'unisex_template_{k}.stl')


print('Transforming meshes to BANC space...')
# Reload with numpy-stl, transform to BANC space, and save
for k in cut_meshes:
    template_space_mesh_path = output_dir / f'unisex_template_{k}.stl'
    mesh = stl.mesh.Mesh.from_file(template_space_mesh_path)
    mesh.v0 = warp_points_template_to_BANC(mesh.v0, 'vnc', input_units='microns',
                                           output_units=output_units)
    mesh.v1 = warp_points_template_to_BANC(mesh.v1, 'vnc', input_units='microns',
                                           output_units=output_units)
    mesh.v2 = warp_points_template_to_BANC(mesh.v2, 'vnc', input_units='microns',
                                           output_units=output_units)
    mesh.save(output_dir / f'{k}.stl')
    template_space_mesh_path.unlink()
