#!/usr/bin/env python3
"""
Contains paths and settings relevant to building neuroglancer states
"""

from . import auth

client = auth.get_caveclient()
info = client.info.get_datastack_info()

ngl_app_url = info['viewer_site']
#ngl_app_url = 'https://neuromancer-seung-import.appspot.com/'
voxel_size = (info['viewer_resolution_x'],
              info['viewer_resolution_y'],
              info['viewer_resolution_z'])

im = {'name': 'BANC EM',
      # As of Nov 2023, path is 'precomputed://gs://zetta_lee_fly_cns_001_alignment/v1_sharded'
      'path': info['aligned_volume']['image_source']}

seg = {'name': 'segmentation proofreading',
       # As of Nov 2023, path is 'graphene://middleauth+https://cave.fanc-fly.com/segmentation/table/wclee_fly_cns_001'
       'path': info['segmentation_source']}

syn = {'name': 'postsynapses',
       'path': '<not available>'}

# The soma_table's flat_segmentation_source is the un-_verified layer
#nuclei = {'name': 'nuclei_TODO-DATE',
#          'path': client.annotation.get_table_metadata(info['soma_table'])['flat_segmentation_source']
# so instead hardcode the _verified layer:
nuclei = {'name': 'nuclei (verified)',
          'path': '<not available>'}

view_options = dict(
    position=[113200, 106900, 3100],
    zoom_3d=6700,
    layout='xy-3d'
)
zoom_2d = 12


outlines_layer = {'type': 'segmentation', 'source': {'url': 'precomputed://gs://zetta_lee_fly_cns_001_kisuk/final/v2/volume_meshes', 'transform': {'matrix': [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0.9462, 0]], 'outputDimensions': {'x': [4e-9, 'm'], 'y': [4e-9, 'm'], 'z': [4.5e-8, 'm']}}, 'subsources': {'mesh': True}, 'enableDefaultSubsources': False}, 'tab': 'segments', 'meshSilhouetteRendering': 2, 'segments': ['1'], 'segmentDefaultColor': '#2a7fff', 'name': 'region outlines'}



def final_json_tweaks(state):
    """
    Apply some final changes to the neuroglancer state that I didn't take the
    time to figure out how to do through nglui, by directly modifying the
    json/dict representation of the state.
    """
    for layer in state['layers']:
        if layer['name'] == seg['name']:
            layer['selectedAlpha'] = 0.4
        if layer['name'] == nuclei['name']:
            #layer['visible'] = False
            layer['ignoreSegmentInteractions'] = True
            layer['selectedAlpha'] = 0.8
        if layer['name'] == syn['name']:
            layer['visible'] = False
            layer['shader'] = 'void main() { emitRGBA(vec4(1, 0, 1, toNormalized(getDataValue()))); }'

    state['crossSectionScale'] = zoom_2d
    state['crossSectionOrientation'] = [0, 1, 0, 0]
    state.update({
        'gpuMemoryLimit': 4_000_000_000,
        'systemMemoryLimit': 4_000_000_000,
    })
