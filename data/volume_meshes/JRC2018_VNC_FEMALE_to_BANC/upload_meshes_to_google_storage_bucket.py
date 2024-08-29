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

bikinibottom.push_mesh(
    'VNC_neuropil_Aug2020.stl',
    1,
    target,
    scale_by=1000
)
