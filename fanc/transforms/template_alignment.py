#!/usr/bin/env python3
"""
Transform points and neurons between the BANC and the 2018 Janelia templates
"""

import os
import subprocess

import numpy as np

from .. import template_spaces


vnc_template_plane_of_symmetry_x_voxel = 329
vnc_template_plane_of_symmetry_x_microns = 329 * 0.400
brain_template_plane_of_symmetry_x_voxel = 825
brain_template_plane_of_symmetry_x_microns = 825 * 0.380


def align_mesh(mesh, target_space='JRC2018_VNC_FEMALE', inplace=True):
    """
    Given a mesh of a neuron in FANC-space, warp its vertices' coordinates to
    be aligned to a 2018 Janelia VNC template space.

    --- Arguments ---
    mesh :
      The mesh to warp. Can be any type of mesh object that has .faces and
      .vertices attributes.
      The coordinate locations of .vertices must be specified in nanometers.

    target_space : str (default 'JRC2018_VNC_FEMALE')
      The template space to warp the mesh into alignment with. This string will
      be passed to `template_spaces.to_navis_name()`, so check that function's
      docstring for the complete list of valid values for this argument.
      See template_spaces.py for more information about each template space.

    inplace : bool (default True)
      If true, replace the vertices of the given mesh object. If false, return
      a copy, leaving the given mesh object unchanged.
    """
    raise NotImplementedError('This function has not yet been adapted from'
                              ' FANC for use in the BANC.')
    import navis
    import flybrains
    if not inplace:
        mesh = mesh.copy()

    # First remove any mesh faces in the neck connective or brain,
    # since those can't be warped to the VNC template
    # This cutoff is 75000voxels * 4.3nm/voxel, plus a small epsilon
    y_cutoff = 322500 + 1e-4
    # Find row numbers of vertices that are out of bounds
    out_of_bounds_vertices = (mesh.vertices[:, 1] < y_cutoff).nonzero()[0]
    in_bounds_faces = np.isin(mesh.faces,
                              out_of_bounds_vertices,
                              invert=True).all(axis=1)
    mesh.faces = mesh.faces[in_bounds_faces]

    target = template_spaces.to_navis_name(target_space)
    print(f'Warping into alignment with {target}')
    mesh.vertices = navis.xform_brain(mesh.vertices, source='FANC', target=target)

    if not inplace:
        return mesh


def warp_points_BANC_to_brain_template(points,
                                       input_units='nanometers',
                                       output_units='microns',
                                       reflect=False):
    """
    Transform point coordinates from the BANC to the corresponding point
    location in the 2018 Janelia Female Brain Template (JRC2018_FEMALE).

    Parameters
    ---------
    points (numpy.ndarray) :
        An Nx3 numpy array representing x,y,z point coordinates in the BANC

    input_units (str) :
        The units of the points you provided as an input. Set to 'nm',
        'nanometer', or 'nanometers' to indicate nanometers;
        'um', 'µm', 'micron', or 'microns' to indicate microns; or
        'pixels' or 'voxels' to indicate pixel indices within the
        full-resolution BANC image volume, which has a pixel size of
        (4, 4, 45) nm.
        Default is nanometers.

    output_units (str) :
        The units you want points returned to you in. Same set of
        options as for `input_units`, except that the pixel size of the
        output space, JRC2018_FEMALE, is (0.38, 0.38, 0.38) µm.
        Default is microns.

    reflect (bool) :
        Whether to reflect the point coordinates across the midplane of
        the JRC2018_FEMALE template before returning them. This
        reflection moves points' x coordinates from the left to the
        right side of the brain template or vice versa, but does not
        affect their y coordinates (anterior-posterior axis) or z
        coordinates (dorsal-ventral axis).
        Default is False.

    Returns
    -------
    An Nx3 numpy array representing x,y,z point coordinates in
    JRC2018_FEMALE, in units specified by `output_units`.
    """
    import navis
    import flybrains
    # Only required for deprecated functions so not imported up top
    import transformix  # https://github.com/jasper-tms/pytransformix

    points = np.array(points, dtype=np.float64)
    if len(points.shape) == 1:
        result = warp_points_BANC_to_brain_template(
            np.expand_dims(points, 0),
            input_units=input_units,
            output_units=output_units,
            reflect=reflect
        )
        if result is None:
            return result
        else:
            return result[0]

    if input_units in ['nm', 'nanometer', 'nanometers']:
        input_units = 'nanometers'
    elif input_units in ['um', 'µm', 'micron', 'microns']:
        input_units = 'microns'
    elif input_units in ['pixel', 'pixels', 'voxel', 'voxels']:
        input_units = 'voxels'
    else:
        raise ValueError("Unrecognized value provided for input_units. Set it"
                         " to 'nanometers', 'microns', or 'pixels'.")
    if output_units in ['nm', 'nanometer', 'nanometers']:
        output_units = 'nanometers'
    elif output_units in ['um', 'µm', 'micron', 'microns']:
        output_units = 'microns'
    elif output_units in ['pixel', 'pixels', 'voxel', 'voxels']:
        output_units = 'voxels'
    else:
        raise ValueError("Unrecognized value provided for output_units. Set it"
                         " to 'nanometers', 'microns', or 'pixels'.")

    if input_units == 'nanometers' and (points < 1000).all():
        resp = input("input_units is set to 'nanometers' but you provided "
                     'points with small values. You likely forgot to set '
                     'input_units correctly. Continue [y] or exit [enter]? ')
        if resp.lower() != 'y':
            return None
    if input_units == 'microns' and (points > 1000).any():
        resp = input("input_units is set to 'microns' but you provided "
                     'points with large values. You likely forgot to set '
                     'input_units correctly. Continue [y] or exit [enter]? ')
        if resp.lower() != 'y':
            return None

    # Convert points to nm so that the math below works
    if input_units == 'microns':
        points *= 1000
    elif input_units == 'voxels':
        points *= (4, 4, 45)

    points /= 1000  # Convert nm to microns as required for this transform
    transform_params = os.path.join(
        os.path.dirname(__file__),
        'transform_parameters',
        'brain',
        'BANC_to_template.txt',
    )
    # Do the transform. This requires input in microns and gives output in microns
    points = transformix.transform_points(points, transform_params)

    if reflect:
        points[:, 0] = brain_template_plane_of_symmetry_x_microns * 2 - points[:, 0]

    if output_units == 'nanometers':
        points *= 1000  # Convert microns to nm
    elif output_units == 'voxels':
        points /= 0.38  # Convert microns to JRC2018_FEMALE voxels

    return points


def warp_points_brain_template_to_BANC(points,
                                       input_units='microns',
                                       output_units='nanometers',
                                       reflect=False):
    """
    Transform point coordinates from the 2018 Janelia Female Brain Template
    (JRC2018_FEMALE) to the corresponding point location in the BANC.

    Parameters
    ---------
    points (numpy.ndarray) :
        An Nx3 numpy array representing x,y,z point coordinates in the
        2018 Janelia Female Brain Template, JRC2018_FEMALE.

    input_units (str) :
        The units of the points you provided as an input. Set to 'nm',
        'nanometer', or 'nanometers' to indicate nanometers; 'um', 'µm',
        'micron', or 'microns' to indicate microns; or 'pixels' or
        'voxels' to indicate pixel indices within the JRC2018_FEMALE
        image volume, which has a pixel size of (0.38, 0.38, 0.38) µm.
        Default is microns.

    output_units (str) :
        The units you want points returned to you in. Same set of
        options as for `input_units`, except that the pixel size of the
        output space, the BANC, is (4, 4, 45) nm.
        Default is nanometers.

    reflect (bool) :
        Whether to reflect the point coordinates across the midplane of
        the JRC2018_FEMALE template before warping them into
        BANC-space. This reflection moves points' x coordinates from the
        left to the right side of the brain template or vice versa, but
        does not affect their y coordinates (anterior-posterior axis) or
        z coordinates (dorsal-ventral axis).
        Default is False.

    Returns
    -------
    An Nx3 numpy array representing x,y,z point coordinates in the BANC,
    in units specified by `output_units`.
    """
    # Only required for deprecated functions so not imported up top
    import transformix  # https://github.com/jasper-tms/pytransformix

    points = np.array(points)
    if len(points.shape) == 1:
        result = warp_points_brain_template_to_BANC(
            np.expand_dims(points, 0),
            input_units=input_units,
            output_units=output_units,
            reflect=reflect
        )
        if result is None:
            return result
        else:
            return result[0]

    if input_units in ['nm', 'nanometer', 'nanometers']:
        input_units = 'nanometers'
    elif input_units in ['um', 'µm', 'micron', 'microns']:
        input_units = 'microns'
    elif input_units in ['pixel', 'pixels', 'voxel', 'voxels']:
        input_units = 'voxels'
    else:
        raise ValueError("Unrecognized value provided for input_units. Set it"
                         " to 'nanometers', 'microns', or 'pixels'.")
    if output_units in ['nm', 'nanometer', 'nanometers']:
        output_units = 'nanometers'
    elif output_units in ['um', 'µm', 'micron', 'microns']:
        output_units = 'microns'
    elif output_units in ['pixel', 'pixels', 'voxel', 'voxels']:
        output_units = 'voxels'
    else:
        raise ValueError("Unrecognized value provided for output_units. Set it"
                         " to 'nanometers', 'microns', or 'pixels'.")

    if input_units == 'nanometers' and (points < 1000).all():
        resp = input("input_units is set to 'nanometers' but you provided "
                     'points with small values. You likely forgot to set '
                     'input_units correctly. Continue [y] or exit [enter]? ')
        if resp.lower() != 'y':
            return None
    if input_units == 'microns' and (points > 1000).any():
        resp = input("input_units is set to 'microns' but you provided "
                     'points with large values. You likely forgot to set '
                     'input_units correctly. Continue [y] or exit [enter]? ')
        if resp.lower() != 'y':
            return None

    # Convert to microns as required for this transform
    if input_units == 'nanometers':
        points /= 1000  # Convert nm to microns
    elif input_units == 'voxels':
        points = points * 0.38  # Convert voxels to microns

    if reflect:
        points[:, 0] = brain_template_plane_of_symmetry_x_microns * 2 - points[:, 0]

    transform_params = os.path.join(
        os.path.dirname(__file__),
        'transform_parameters',
        'brain',
        'template_to_BANC.txt',
    )
    # Do the transform. This requires input in microns and gives output in microns
    points = transformix.transform_points(points, transform_params)

    points *= 1000  # Convert microns to nm

    if output_units == 'microns':
        points /= 1000  # Convert nm to microns
    elif output_units == 'voxels':
        points /= (4, 4, 45)  # Convert nm to BANC voxels
    return points
