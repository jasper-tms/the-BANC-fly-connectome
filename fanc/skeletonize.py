#!/usr/bin/env python3
"""
Generate skeletons from FANC segmentation objects (meshes).

See examples of running these skeletonization functions at:
https://github.com/htem/FANC_auto_recon/blob/main/example_notebooks/skeletonization.ipynb
"""

import numpy as np
import pandas as pd
from scipy.spatial import distance

from meshparty import trimesh_io, meshwork, mesh_filters
import navis
import pcg_skel

from . import auth


def get_pcg_skeleton(segid, **kwargs):
    """
    Create a skeleton from an object in the FANC segmentation.

    This function just calls pcg_skel.pcg_skeleton, so its main purpose
    is just to inform you that pcg_skel is the recommended way to
    generate a skeleton from a FANC neuron.

    Examples
    --------
    >>> skel = fanc.skeletonize.get_pcg_skeleton(648518346481082458)
    >>> fanc.statebuilder.render_scene(annotations=skel.vertices, annotation_units='nm')

    This example pulls a skeleton of the "homepage" FANC neuron, then renders
    a neuroglancer scene with the skeleton nodes displayed as point annotations.
    """
    if 'client' not in kwargs:
        kwargs['client'] = auth.get_caveclient()
    return pcg_skel.pcg_skeleton(segid, **kwargs)


# --- Older skeletonization methods below --- #

# Default parameters for skeletonization
contraction_defaults = {'epsilon': 1e-05, 'iter_lim': 8, 'precision': 1e-5, 'SL': 2, 'WH0': .05, 'WL0': 'auto'}

skeletonization_defaults = {'voxel_resolution': np.array([4.3, 4.3, 45]),
                            'merge_size_threshold': 100,
                            'merge_max_dist': 1000,
                            'merge_distance_step': 500,
                            'soma_radius': 7500,
                            'invalidation_distance': 8500,
                            'merge_collapse_soma': True}

diameter_smoothing_defaults = {'smooth_method': 'smooth',
                               'smooth_bandwidth': 1000}


def skeletonize_neuron(seg_id,
                       soma_pt,
                       output='meshwork',
                       cloudvolume=None,
                       voxel_resolution=skeletonization_defaults['voxel_resolution']):
    """
    Skeletonize a neuron from a FANC segmentation object (mesh).

    This function is more flexible than get_pcg_skeleton (there are a
    ton of parameters that you could tweak if you're really motivated to
    get a skeleton that's optimized for your purposes) and produces
    higher-resolution skeletons, but it takes much longer to run. For
    most purposes, get_pcg_skeleton is recommended.

    Arguments
    ---------
    seg_id: int
      The segment ID to skeletonize

    soma_pt: 3-element iterable (xyz)
      The coordinates of the soma, in voxels

    output: 'meshwork' or 'navis'
      A string specifying the type of object to return.

    cv: None or cloudvolume.CloudVolume
      The cloudvolume to use for fetching meshes. If None, will use the
      one returned by auth.get_cloudvolume() by default.
    """
    if cloudvolume is None:
        cloudvolume = auth.get_cloudvolume()

    mesh = cloudvolume.mesh.get(seg_id, use_byte_offsets=True)[seg_id]
    mp_mesh = trimesh_io.Mesh(mesh.vertices, mesh.faces)

    mp_mesh.merge_large_components(size_threshold=skeletonization_defaults['merge_size_threshold'],
                                   max_dist=skeletonization_defaults['merge_max_dist'],
                                   dist_step=skeletonization_defaults['merge_distance_step'])
    in_comp = mesh_filters.filter_largest_component(mp_mesh)
    mesh_anchor = mp_mesh.apply_mask(in_comp)

    neuron = meshwork.Meshwork(mesh_anchor, seg_id=seg_id, voxel_resolution=voxel_resolution)
    neuron.skeletonize_mesh(soma_pt=soma_pt * voxel_resolution,
                            invalidation_distance=skeletonization_defaults['invalidation_distance'])

    if output == 'meshwork':
        return neuron
    elif output == 'navis':
        neuron = mp_to_navis(neuron.skeleton)
        neuron = set_soma(neuron, soma_pt)
        neuron = diameter_smoothing(neuron)
        neuron.nodes.loc[neuron.soma, 'radius'] = skeletonization_defaults['soma_radius']

        return neuron


def mp_to_navis(meshparty_skel, node_labels=None, xyz_scaling=1):
    """
    Convert a meshparty skeleton into a dataframe for navis/catmaid import.

    Arguments
    ----
    skel: meshparty skeleton
    node_labels: list , list of node labels, default is None and will generate new ones.
    xyz_scaling: int, scale factor for coordinates
    """
    ds = meshparty_skel.distance_to_root
    order_old = np.argsort(ds)
    new_ids = np.arange(len(ds))
    order_map = dict(zip(order_old, new_ids))

    if node_labels is None:
        node_labels = new_ids
    else:
        node_labels = np.array(node_labels)[order_old]

    xyz = meshparty_skel.vertices[order_old]
    par_ids = np.array([order_map.get(nid, -1)
                        for nid in meshparty_skel._rooted._parent_node_array[order_old]])

    data = {'node_id': node_labels,
            'parent_id': par_ids,
            'x': xyz[:, 0] / xyz_scaling,
            'y': xyz[:, 1] / xyz_scaling,
            'z': xyz[:, 2] / xyz_scaling,
            'radius': meshparty_skel.radius}
    df = pd.DataFrame(data=data)

    df['label'] = np.ones(len(df))

    neuron = navis.TreeNeuron(df)

    return neuron


def set_soma(neuron, soma_coord):
    dists = [distance.euclidean(soma_coord, i) for i in np.array(neuron.nodes[['x', 'y', 'z']])]
    neuron.soma = neuron.nodes['node_id'][dists.index(min(dists))]
    navis.reroot_neuron(neuron, neuron.soma, inplace=True)
    neuron.nodes.parent_id = neuron.nodes.parent_id.where(pd.notnull(neuron.nodes.parent_id), None)

    return neuron


def diameter_smoothing(neuron, smooth_method='smooth', smooth_bandwidth=1000):
    ''' This will smooth out the node diameters by either setting every node of a similar strahler order to the mean radius of every node with that     strahler order, or apply a smoothing function by setting the radius of a node to the mean of every node within a given bandwidth.  For the latter case, it will also make sure that the nodes radii being averaged are from the same strahler order.

        Parameters
        ----------
        neuron :           A navis neuron.

        smooth_method:            Either 'strahler' or 'smooth'. Default is 'strahler' as it is much faster, and gave good results for motor neurons.  This determines the method of smoothing.  See above for the difference.

        smooth_bandwidth:         If 'smooth' is chosen, this is the distance threshold (in nm) whose radii will be averaged to determine a given nodes radius.
                           Default is 1000nm.

        Returns
        -------
        neuron:            a pymaid neuron'''

    gm = navis.geodesic_matrix(neuron)

    if 'strahler_index' not in neuron.nodes:
        navis.strahler_index(neuron)

    if 'strahler' in smooth_method:
        for i in range(max(neuron.nodes.strahler_index) + 1):
            radius = np.mean(
                neuron.nodes.loc[(neuron.nodes.strahler_index == i) & (neuron.nodes.node_id != neuron.soma), 'radius'])
            neuron.nodes.loc[
                (neuron.nodes.strahler_index == i) & (neuron.nodes.node_id != neuron.soma), 'radius'] = radius
            print(i, radius)
    elif 'smooth' in smooth_method:
        smooth_r = []
        for i in range(len(neuron.nodes)):
            smooth_r.append(np.mean(neuron.nodes.loc[np.array(gm.iloc[i, :] < smooth_bandwidth) & np.array(
                neuron.nodes.loc[:, 'strahler_index'] == neuron.nodes.loc[i, 'strahler_index']) & (
                                                                 neuron.nodes.node_id != neuron.soma), 'radius']))

        neuron.nodes.radius = smooth_r

    return neuron


def downsample_neuron(neuron, downsample_factor=4):
    downsampled = navis.resample.downsample_neuron(neuron, downsample_factor, inplace=False)

    return downsampled
