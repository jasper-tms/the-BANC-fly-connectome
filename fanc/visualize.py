#!/usr/bin/env python3

import os

import numpy as np
from matplotlib import cm, colors
import vtk
from meshparty import trimesh_vtk, trimesh_io, meshwork
from cloudvolume.frontends.precomputed import CloudVolumePrecomputed
try:
    from trimesh import exchange
except ImportError:
    from trimesh import io as exchange

from . import auth, connectivity
from .transforms import template_alignment


def plot_neurons(segment_ids,
                 template_space='JRC2018_VNC_FEMALE',
                 cmap='Blues', opacity=1,
                 plot_type='mesh',
                 resolution=[4.3,4.3,45],
                 camera=None,
                 zoom_factor=300,
                 plot_synapses=False,
                 synapse_type='all',
                 synapse_threshold=3,
                 plot_soma=False,
                 show_outlines=False,
                 scale_bar_origin_3D=None,
                 scale_bar_origin_2D=None,
                 view='X',
                 scale_bar_length=10000,
                 save=False,
                 save_path=None,
                 width=1080,
                 height=720,
                 **kwargs):
    """
    Visualize neurons in 3d meshes, optionally saving high-resolution png images.

    Parameters
    ----------
    segment_ids :  list
        list of segment IDs of neurons
    template_space :  str
        Name of template space to warp neurons into. Must be one of:
          'JRC2018_VNC_FEMALE'
          'JRC2018_VNC_UNISEX'
          'JRC2018_VNC_MALE'
          'FANC'
          None
        Both 'FANC' and None result in neurons being displayed in the
        original FANC-space (i.e. no warping is applied).
    camera :  int
        json state id of neuroglancer scene. required to plot scale bar
    plot_synapses :  bool
        visualize synapses
    plot_soma : bool
        visualize soma
    show_outlines :  bool
        visualize volume outlines
    scale_bar_origin_3D : list
        specify an origin of a 3D scale bar that users want to place in xyz
    scale_bar_origin_2D :  list
        specify an origin of a 2D scale bar that users want to place in xyz
    view : str
        'X', 'Y', or 'Z' to specify which plane you want your 2D scale bar to appear
    scale_bar_length :  int
        length of a scale bar in nm
    save : bool
        write png image to disk, if false will open interactive window (default False)
    save_path : str
        filepath to save png image

    Additional kwargs
    -----------------
    client : caveclient.CAVEclient
        CAVEclient to use instead of the default one

    Returns
    -------
    vtk.vtkRenderer
        renderer when code was finished
    png
        output png image
        (generate two images with/without scale bar if you specify to plot it)
    """

    if isinstance(segment_ids, (int, np.integer)):
        segment_ids = [segment_ids]

    colormap = cm.get_cmap(cmap, len(segment_ids))

    if 'client' in kwargs:
        client = kwargs['client']
    else:
        client = auth.get_caveclient()

    if isinstance(camera, (int, np.integer)):
        state = client.state.get_state_json(camera)
        camera = trimesh_vtk.camera_from_ngl_state(state, zoom_factor=zoom_factor)

    meshmanager = auth.get_meshmanager()

    neuron_actors = []
    annotation_actors = []
    # outline_actor = []
    for j in enumerate(segment_ids):
        # Get mesh
        mp_mesh = meshmanager.mesh(seg_id=j[1])
        if template_space and not template_space.startswith('FANC'):
            template_alignment.align_mesh(mp_mesh, target_space=template_space, inplace=True)
            mp_mesh.vertices *= 1000  # TODO delete this after adding nm/um to align_mesh
        neuron = meshwork.Meshwork(mp_mesh, seg_id=j[1], voxel_resolution=[4.3, 4.3, 45])

        if plot_soma == True:
            soma_df = client.materialize.query_table(client.info.get_datastack_info()['soma_table'],
                                                     filter_equal_dict={'pt_root_id': j[1]})
            neuron.add_annotations('soma_pt', soma_df, point_column='pt_position', anchored=False)

        # get synapses
        if plot_synapses is True:
            if synapse_type == 'inputs':
                input_table = connectivity.get_synapses(j[1],
                                                          direction='inputs',
                                                          threshold=synapse_threshold)

                neuron.add_annotations('syn_in', input_table, point_column='post_pt')


            elif synapse_type == 'outputs':
                input_table = None
                output_table = connectivity.get_synapses(j[1],
                                                           direction='outputs',
                                                           threshold=synapse_threshold)
            elif synapse_type == 'all':
                input_table = connectivity.get_synapses(j[1],
                                                          direction='inputs',
                                                          threshold=synapse_threshold)

                output_table = connectivity.get_synapses(j[1],
                                                           direction='outputs',
                                                           threshold=synapse_threshold)

                neuron.add_annotations('syn_in', input_table, point_column='post_pt')
                neuron.add_annotations('syn_out', output_table, point_column='pre_pt')


            else:
                raise Exception('incorrect synapse type, use: "inputs", "outputs", or "all"')

        # Plot

        if 'mesh' in plot_type:
            neuron_actors.append(trimesh_vtk.mesh_actor(neuron.mesh, color=colormap(j[0])[0:3], opacity=opacity))
        elif 'skeleton' in plot_type and plot_soma is not None:
            neuron.skeletonize_mesh(soma_pt=neuron.anno.soma_pt.points[0], invalidation_distance=5000)
            neuron_actors.append(trimesh_vtk.skeleton_actor(neuron.skeleton, line_width=3, color=colormap(j[0])[0:3]))
        elif 'skeleton' in plot_type and plot_soma is None:
            raise Exception('need a soma point to skeletonize')
        else:
            raise Exception('incorrect plot type, use "mesh" or "skeleton"')

        for i in neuron.anno.table_names:
            if 'syn_in' in i:
                annotation_actors.append(
                    trimesh_vtk.point_cloud_actor(neuron.anno.syn_in.points, size=200, color=(0.0, 0.9, 0.9)))
            elif 'syn_out' in i:
                annotation_actors.append(
                    trimesh_vtk.point_cloud_actor(neuron.anno.syn_out.points, size=200, color=(1.0, 0.0, 0.0)))
            else:
                annotation_actors.append(
                    trimesh_vtk.point_cloud_actor(neuron.anno[i].points, size=200, color=(0.0, 0.0, 0.0)))

    all_actors = neuron_actors + annotation_actors

    if show_outlines:
        outlines_actors = []
        base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'volume_meshes'
        )
        if template_space == 'JRC2018_VNC_FEMALE':
            outer_mesh_filename = os.path.normpath(os.path.join(base, 'JRC2018_VNC_FEMALE', 'tissueOutline_Aug2019.stl'))
            inner_mesh_filename = os.path.normpath(os.path.join(base, 'JRC2018_VNC_FEMALE', 'VNC_neuropil_Aug2020.stl'))
        elif template_space == 'JRC2018_VNC_UNISEX':
            raise NotImplementedError
            outer_mesh_filename = needtogetfile
            inner_mesh_filename = needtogetfile
        elif template_space == 'JRC2018_VNC_MALE':
            raise NotImplementedError
            outer_mesh_filename = needtogetfile
            inner_mesh_filename = needtogetfile
        elif template_space == 'FANC' or not template_space:
            outer_mesh_filename = os.path.normpath(os.path.join(base, 'tissueoutline_aug2019.stl'))
            inner_mesh_filename = os.path.normpath(os.path.join(base, 'JRC2018_VNC_FEMALE_to_FANC', 'VNC_template_Aug2020.stl'))
        mesh_outer = read_mesh_stl(outer_mesh_filename)
        mp_mesh = trimesh_io.Mesh(mesh_outer[0], mesh_outer[1])
        outlines_outer = meshwork.Meshwork(mp_mesh, seg_id=[1], voxel_resolution=[4.3, 4.3, 45])
        outlines_actors.append(trimesh_vtk.mesh_actor(outlines_outer.mesh, color=(191/255,191/255,191/255), opacity=0.1))

        mesh_inner = read_mesh_stl(inner_mesh_filename)
        mp_mesh = trimesh_io.Mesh(mesh_inner[0], mesh_inner[1])
        outlines_inner = meshwork.Meshwork(mp_mesh, seg_id=[2], voxel_resolution=[4.3, 4.3, 45])
        outlines_actors.append(trimesh_vtk.mesh_actor(outlines_inner.mesh, color=(211/255,67/255,214/255), opacity=0.1))

        all_actors = all_actors + outlines_actors

    # add actor for scale bar
    if (scale_bar_origin_3D is not None) or (scale_bar_origin_2D is not None):
        if camera is not None:
            if scale_bar_origin_3D is not None:
                scale_bar_ctr = np.array(scale_bar_origin_3D)*np.array(resolution) # - np.array([0,scale_bar_length,0])
                scale_bar_actor = trimesh_vtk.scale_bar_actor(scale_bar_ctr,camera=camera,length=scale_bar_length,linewidth=1)
            else:
                scale_bar_ctr = np.array(scale_bar_origin_2D)*np.array(resolution) - np.array([0,scale_bar_length,0])
                scale_bar_actor = scale_bar_actor_2D(scale_bar_ctr,view=view,camera=camera,length=scale_bar_length,linewidth=1)
        else:
            raise Exception('Need camera to set up scale bar')

    if (scale_bar_origin_3D is None) and (scale_bar_origin_2D is None):
        trimesh_vtk.render_actors(all_actors, camera=camera, do_save=save,
                                  filename=save_path,
                                  scale=4, video_width=width, video_height=height)
    elif save_path is None:
        trimesh_vtk.render_actors((all_actors + [scale_bar_actor]), camera=camera, do_save=save,
                                  filename=save_path,
                                  scale=4, video_width=width, video_height=height)
    else:
        trimesh_vtk.render_actors(all_actors, camera=camera, do_save=save,
                                  filename=save_path,
                                  scale=1, video_width=width, video_height=height)
        trimesh_vtk.render_actors((all_actors + [scale_bar_actor]), camera=camera, do_save=save,
                                    filename=(save_path.rsplit('.', 1)[0] + '_scalebar.' + save_path.rsplit('.', 1)[1]),
                                    scale=1, video_width=width, video_height=height)


def scale_bar_actor_2D(center, camera, view='X', length=10000, color=(0, 0, 0), linewidth=5, font_size=20):
    """
    Creates a scale bar actor very similar to trimesh_vtk.scale_bar_actor(), but on a specific plane with
    a given size.
    """
    axes_actor = vtk.vtkCubeAxesActor2D()
    axes_actor.SetBounds(center[0], center[0]+length,
                         center[1], center[1]+length,
                         center[2], center[2]+length)

    axes_actor.SetLabelFormat("")
    axes_actor.SetCamera(camera)
    axes_actor.SetNumberOfLabels(0)
    axes_actor.SetFlyModeToNone()
    axes_actor.SetFontFactor(1.0)
    axes_actor.SetCornerOffset(0.0)
    if view == 'X':
        axes_actor.XAxisVisibilityOn()
    else:
        axes_actor.XAxisVisibilityOff()
    if view == 'Y':
        axes_actor.YAxisVisibilityOn()
    else:
        axes_actor.YAxisVisibilityOff()
    if view == 'Z':
        axes_actor.ZAxisVisibilityOn()
    else:
        axes_actor.ZAxisVisibilityOff()
    axes_actor.GetProperty().SetColor(*color)
    axes_actor.GetProperty().SetLineWidth(linewidth)

    tprop = vtk.vtkTextProperty()
    tprop.SetColor(*color)
    tprop.ShadowOff()
    tprop.SetFontSize(font_size)
    if view == 'X':
        axes_actor.SetXLabel((str(length)+' nm'))
    if view == 'Y':
        axes_actor.SetYLabel((str(length)+' nm'))
    if view == 'Z':
        axes_actor.SetZLabel((str(length)+' nm'))
    axes_actor.SetAxisTitleTextProperty(tprop)
    axes_actor.SetAxisLabelTextProperty(tprop)

    return axes_actor


def read_mesh_stl(filename):
    with open(filename, 'r') as fp:
        mesh_d = exchange.stl.load_stl(fp)
    vertices = mesh_d['vertices']
    faces = mesh_d['faces']
    normals = mesh_d.get('normals', None)
    link_edges = None
    node_mask = None
    return vertices, faces, normals, link_edges, node_mask
