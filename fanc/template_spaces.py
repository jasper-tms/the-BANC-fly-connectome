#/usr/bin/env python3
"""
Info on the stack dimensions and voxel sizes
of the different VNC standard templates
"""

template_info = {
    # Standard JRC2018 templates, available to download from
    # https://www.janelia.org/open-science/jrc-2018-brain-templates
    'JRC2018_FEMALE_38um_iso': {
        'stack dimensions': (1652, 768, 479),
        'voxel size': (0.38, 0.38, 0.38)
    },
    'JRC2018_MALE_38um_iso': {
        'stack dimensions': (1561, 744, 546),
        'voxel size': (0.38, 0.38, 0.38)
    },
    'JRC2018_UNISEX_38um_iso': {
        'stack dimensions': (1652, 773, 456),
        'voxel size': (0.38, 0.38, 0.38)
    },

    'JRC2018_VNC_FEMALE_4iso': {
        'stack dimensions': (660, 1342, 358),
        'voxel size': (0.4, 0.4, 0.4)
    },
    'JRC2018_VNC_MALE_4iso': {
        'stack dimensions': (659, 1342, 401),
        'voxel size': (0.4, 0.4, 0.4)
    },
    'JRC2018_VNC_UNISEX_4iso': {
        'stack dimensions': (660, 1290, 382),
        'voxel size': (0.4, 0.4, 0.4)
    },

    # The color-depth MIPs from Janelia FlyEM have been registered to versions of
    # the standard templates above that have been rescaled to a different voxel size.
    #
    # Brain
    # https://neuronbridge.janelia.org/upload says that the brain
    # colormips are expected to be in JRC2018_UNISEX_20x_HR space.
    # That template can be downloaded from
    # https://open.quiltdata.com/b/janelia-flylight-templates/tree/JRC2018_Unisex_20x_HR/
    # from which the template's dimensions and voxel size can be obtained.
    'JRC2018_UNISEX_20x_HR': {
        'stack dimensions': (1210, 566, 174),
        'voxel size': (0.5189161, 0.5189161, 1.0)
    },
    # VNC
    # The voxel size is 461.122 nm in x and y, so Janelia has chosen to
    # distribute these rescaled templates with filenames ending in '_461'.
    # These templates are available to download from
    # https://open.quiltdata.com/b/janelia-flylight-templates/tree/
    # from which their dimensions and voxel size can be obtained.
    'JRC2018_VNC_FEMALE_461': {
        'stack dimensions': (573, 1164, 205),
        'voxel size': (0.461122, 0.461122, 0.7)
    },
    'JRC2018_VNC_MALE_461': {
        'stack dimensions': (572, 1164, 229),
        'voxel size': (0.461122, 0.461122, 0.7)
    },
    # The unisex template is the one to which most of the Janelia VNC
    # MCFO data have been aligned. It can be downloaded from
    # https://open.quiltdata.com/b/janelia-flylight-templates/tree/JRC2018_VNC_Unisex/
    'JRC2018_VNC_UNISEX_461': {
        'stack dimensions': (573, 1119, 219),
        'voxel size': (0.461122, 0.461122, 0.7)
    }
}


def get_template_info(template_space):
    if template_space not in template_info:
        raise ValueError(
            'template_space was {} but must be one of: '
            '{}'.format(template_space, list(template_info.keys()))
        )
    return template_info[template_space]


# For each list of aliases, the first one is the nickname
# recognized by navis.xform_brain
aliases = (
    # Female brain aliases
    ('JRC2018F',
     'JRC2018_FEMALE',
     'JRC2018_FEMALE_38um_iso'),
    # Male brain aliases
    ('JRC2018M',
     'JRC2018_MALE',
     'JRC2018_MALE_38um_iso'),
    # Unisex brain aliases
    ('JRC2018U',
     'JRC2018_UNISEX',
     'JRC2018_UNISEX_38um_iso',
     'JRC2018_UNISEX_20x_HR'),
    # Female VNC aliases
    ('JRCVNC2018F',
     'JRC2018_VNC_FEMALE',
     'JRC2018_VNC_FEMALE_4iso',
     'JRC2018_VNC_FEMALE_461',
     'FEMALE'),
    # Male VNC aliases
    ('JRCVNC2018M',
     'JRC2018_VNC_MALE',
     'JRC2018_VNC_MALE_4iso',
     'JRC2018_VNC_MALE_461',
     'MALE'),
    # Unisex VNC aliases
    ('JRCVNC2018U',
     'JRC2018_VNC_UNISEX',
     'JRC2018_VNC_UNISEX_4iso',
     'JRC2018_VNC_UNISEX_461',
     'UNISEX')
)


def to_navis_name(template_space):
    """
    Convert from any of a number of nicknames for a template space
    into the nickname recognized by `navis.xform_brain()`

    'JRCVNC2018F' is returned if the input is any of the following:
      'JRCVNC2018F'
      'JRC2018_VNC_FEMALE
      'JRC2018_VNC_FEMALE_4iso'
      'JRC2018_VNC_FEMALE_461'
      'FEMALE'

    'JRCVNC2018M' is returned if the input is any of the following:
      'JRCVNC2018M'
      'JRC2018_VNC_MALE'
      'JRC2018_VNC_MALE_4iso'
      'JRC2018_VNC_MALE_461'
      'MALE'

    'JRCVNC2018U' is returned if the input is any of the following:
      'JRCVNC2018U'
      'JRC2018_VNC_UNISEX'
      'JRC2018_VNC_UNISEX_4iso'
      'JRC2018_VNC_UNISEX_461'
      'UNISEX'

    """
    for alias_list in aliases:
        if template_space in alias_list:
            return alias_list[0]
    raise ValueError('Template space name not recognized.'
                     ' See docstring for recognized names')


def get_nrrd_metadata(template_space):
    voxel_size = template_info[template_space]['voxel size']
    return {
        'space dimension': 3,
        'space units': ['microns', 'microns', 'microns'],
        'space directions': [
            [voxel_size[0], 0, 0],
            [0, voxel_size[1], 0],
            [0, 0, voxel_size[2]]
        ]
    }
