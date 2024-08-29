#!/usr/bin/env python3
"""
Upload neuropil and tract meshes to Google Cloud Storage
in neuroglancer-compatible format.
"""

from glob import glob
from tqdm import tqdm

try:
    import bikinibottom
except ImportError:
    raise ImportError('Please install the bikinibottom package from'
                      'https://github.com/jasper-tms/bikini-bottom')

target = ('gs://'
          'lee-lab_brain-and-nerve-cord-fly-connectome/'
          'region_outlines/'
          'JRC2018_VNC_to_BANC')

for mesh_fn in tqdm(glob('VFB_001*stl')):
    segid = int(mesh_fn[8:12])
    bikinibottom.push_mesh(
        mesh_fn,
        segid,
        target,
        scale_by=1000
    )
