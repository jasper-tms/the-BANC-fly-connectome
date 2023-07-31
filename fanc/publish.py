#!/usr/bin/env python3

import os
from xml.etree import ElementTree

import numpy as np
import requests
import cloudvolume

from . import auth, transforms

PUBLISHED_MESHES_CLOUDPATH = ('gs://lee-lab_female-adult-nerve-cord/'
                              'meshes/{}/FANC_neurons')
VALID_TEMPLATE_SPACES = ('FANC', 'JRC2018_VNC_FEMALE',
                         'JRC2018_VNC_UNISEX', 'JRC2018_VNC_MALE')


def list_public_segment_ids(template_space='JRC2018_VNC_FEMALE',
                            gcloud_path=PUBLISHED_MESHES_CLOUDPATH):
    """
    List the segment IDs of all neurons that have been published to the
    specified template space.
    """
    if template_space not in VALID_TEMPLATE_SPACES:
        raise ValueError('{} not in {}'.format(template_space,
                                               VALID_TEMPLATE_SPACES))
    gcloud_path = gcloud_path.format(template_space)
    # Implementation aided by GPT-4
    url = f'https://storage.googleapis.com/{gcloud_path.split("/")[2]}'
    params = {'prefix': '/'.join(gcloud_path.split('/')[3:])}

    segids = []
    while True:
        response = requests.get(url, params=params)
        tree = ElementTree.fromstring(response.text)

        # namespaces cause trouble, so find them and remove them
        namespaces = {'ns': 'http://doc.s3.amazonaws.com/2006-03-01'}

        for elem in tree.findall('ns:Contents/ns:Key', namespaces):
            filename = elem.text.split('/')[-1]
            if filename.endswith(':0'):
                segids.append(np.int64(filename[:-2]))

        # Each query can only get 500 neurons, so we need to check whether
        # there are more results to fetch
        marker_elem = tree.find('ns:NextMarker', namespaces)
        if marker_elem is None:
            break
        # If there are, add the marker to the params and allow the while loop
        # to continue, making a request for the next batch
        params['marker'] = marker_elem.text

    return segids


def publish_mesh_to_gcloud(segids,
                           template_space='JRC2018_VNC_FEMALE',
                           gcloud_path=PUBLISHED_MESHES_CLOUDPATH):
    """
    Download the mesh for a neuron, warp it into alignment with the specified
    VNC template (optional), and upload it to a public google cloud storage bucket.
    Neurons uploaded to the public project will have the same ID as the source
    neuron they came from in FANC.

    Currently only admins like Jasper and Wei have the necessary permissions
    for the upload to succeed. Please ask one of them to run this function for
    you when you have a list of neurons you're ready to make public.

    See a complete list of IDs of public neurons via one of the following
    links, depending on which template space you want to see neurons in:
    https://console.cloud.google.com/storage/browser/lee-lab_female-adult-nerve-cord/meshes/FANC/FANC_neurons/meshes
    https://console.cloud.google.com/storage/browser/lee-lab_female-adult-nerve-cord/meshes/JRC2018_VNC_FEMALE/FANC_neurons/meshes
    Not implemented yet: https://console.cloud.google.com/storage/browser/lee-lab_female-adult-nerve-cord/meshes/JRC2018_VNC_UNISEX/FANC_neurons/meshes
    Not implemented yet: https://console.cloud.google.com/storage/browser/lee-lab_female-adult-nerve-cord/meshes/JRC2018_VNC_MALE/FANC_neurons/meshes

    These neurons can be viewed by entering their ID(s) into one of the following neuroglancer links:
    FANC: https://neuromancer-seung-import.appspot.com/?json_url=https://global.daf-apis.com/nglstate/api/v1/5104409098846208
    JRC2018_VNC_FEMALE: https://neuromancer-seung-import.appspot.com/?json_url=https://global.daf-apis.com/nglstate/api/v1/6230309005688832
    JRC2018_VNC_UNISEX: Not implemented yet
    JRC2018_VNC_MALE: Not implemented yet

    """
    try:
        iter(segids)
    except:
        segids = [segids]

    if template_space not in VALID_TEMPLATE_SPACES:
        raise ValueError('{} not in {}'.format(template_space,
                                               VALID_TEMPLATE_SPACES))

    already_published_ids = list_public_segment_ids(template_space=template_space,
                                                    gcloud_path=gcloud_path)
    already_published_ids = set(already_published_ids)

    fancneurons_cloudvolume = cloudvolume.CloudVolume(gcloud_path.format(template_space))

    mm = auth.get_meshmanager()
    for segid in segids:
        if segid in already_published_ids:
            print(f'Segment {segid} already published in {template_space}-space, skipping.')
            continue
        print(f'Publishing segment {segid} to {template_space}-space.')
        mesh = mm.mesh(seg_id=segid)
        if template_space != 'FANC':
            transforms.template_alignment.align_mesh(mesh, target_space=template_space)
            mesh.vertices *= 1000  # TODO delete this after adding nm/um to align_mesh
        mesh = cloudvolume.mesh.Mesh(mesh.vertices, mesh.faces, segid=segid)
        fancneurons_cloudvolume.mesh.put(mesh)


def publish_skeleton_to_catmaid(segids,
                                catmaid_instance=None):
    """
    Download the mesh for a neuron, skeletonize it, upload it to one
    catmaid project, warp the skeleton into alignment with the female VNC
    template, and upload that to a different catmaid project
    """
    raise NotImplementedError


def _configure_template_cloudvolumes(template_space='JRC2018_VNC_FEMALE'):
    """
    This function was run once to configure some cloudvolumes to hold published
    neurons. Only admins like Jasper and Wei have the necessary permissions on
    the google cloud project for this function to complete successfully.
    The code is included here in case we need to do something similar again.
    """
    print('Uploading {}_4iso.nrrd image data'.format(template_space))
    import npimage  # pip install numpyimage
    import npimage.operations
    # Load VNC template from local file (you must have this file in this folder)
    # Use xyz order because that's what cloudvolume wants
    template_image_data = npimage.load('{}_4iso.nrrd'.format(template_space),
                                       dim_order='xyz')
    template_image_data_8bit = npimage.operations.to_8bit(template_image_data)

    # Open a CloudVolume
    gcloud_path = ('gs://lee-lab_female-adult-nerve-cord/VNC_templates/'
                   '{}/image/'.format(template_space))
    info = cloudvolume.CloudVolume.create_new_info(
        num_channels = 1,
        layer_type = 'image', # 'image' or 'segmentation'
        data_type = 'uint8', # can pick any popular uint
        encoding = 'jpeg', # other options: 'jpeg', 'compressed_segmentation' (req. uint32 or uint64)
        resolution = [400, 400, 400], # X,Y,Z values in nanometers
        voxel_offset = [0, 0, 0], # values X,Y,Z values in voxels
        chunk_size = [660, 1342, 1], # rechunk of image X,Y,Z in voxels
        volume_size = [660, 1342, 358], # X,Y,Z size in voxels
    )
    template_image_cloudvolume = cloudvolume.CloudVolume(gcloud_path, info=info)
    template_image_cloudvolume.provenance.description = (
        '{}_4iso.nrrd from https://www.janelia.org/open-science/jrc-2018-brain-templates'
        ' converted from 16-bit to 8-bit.'.format(template_space)
    )
    template_image_cloudvolume.provenance.owners = ['jasper.s.phelps@gmail.com']
    template_image_cloudvolume.commit_info()
    template_image_cloudvolume.commit_provenance()

    # Upload image data
    template_image_cloudvolume[:] = template_image_data_8bit

    print('Making cloudvolumes to hold meshes')
    volumes_cloudpath = ('gs://lee-lab_female-adult-nerve-cord/VNC_templates/'
                         '{}/volume_meshes/'.format(template_space))
    info = cloudvolume.CloudVolume.create_new_info(
        num_channels = 1,
        layer_type = 'segmentation', # 'image' or 'segmentation'
        mesh = 'meshes',
        data_type = 'uint64', # can pick any popular uint
        encoding = 'raw', # other options: 'jpeg', 'compressed_segmentation' (req. uint32 or uint64)
        resolution = [400, 400, 400], # X,Y,Z values in nanometers
        voxel_offset = [0, 0, 0], # values X,Y,Z values in voxels
        chunk_size = [660, 1342, 1], # rechunk of image X,Y,Z in voxels
        volume_size = [660, 1342, 358], # X,Y,Z size in voxels
    )
    volumes_cv = cloudvolume.CloudVolume(volumes_cloudpath, info=info)
    volumes_cv.provenance.description = (
        'Meshes encompasing various regions of the VNC, including the whole '
        'VNC, the the whole VNC neuropil, and the different VNC neuropil '
        'regions defined in Court et al. 2020 Neuron. All are in the template '
        'space {}.'.format(template_space)
    )
    volumes_cv.provenance.owners = ['jasper.s.phelps@gmail.com']
    volumes_cv.commit_info()
    volumes_cv.commit_provenance()

    fancneurons_path = ('gs://lee-lab_female-adult-nerve-cord/VNC_templates/'
                        '{}/FANC_neurons/'.format(template_space))
    info = cloudvolume.CloudVolume.create_new_info(
        num_channels = 1,
        layer_type = 'segmentation', # 'image' or 'segmentation'
        mesh = 'meshes',
        data_type = 'uint64', # can pick any popular uint
        encoding = 'raw', # other options: 'jpeg', 'compressed_segmentation' (req. uint32 or uint64)
        resolution = [400, 400, 400], # X,Y,Z values in nanometers
        voxel_offset = [0, 0, 0], # values X,Y,Z values in voxels
        chunk_size = [660, 1342, 1], # rechunk of image X,Y,Z in voxels
        volume_size = [660, 1342, 358], # X,Y,Z size in voxels
    )
    fancneurons_cloudvolume = cloudvolume.CloudVolume(fancneurons_path, info=info)
    fancneurons_cloudvolume.provenance.description = (
        'Meshes of neurons reconstructed in FANC and warped into alignment with '
        '{}'.format(template_space)
    )
    fancneurons_cloudvolume.provenance.owners = ['jasper.s.phelps@gmail.com']
    fancneurons_cloudvolume.commit_info()
    fancneurons_cloudvolume.commit_provenance()


    print('Uploading volume outline meshes')
    meshes_folder = '../data/volume_meshes/{}'.format(template_space)
    volume_meshes = [
        ('tissueOutline_Aug2019.stl', 1),
        ('VNC_neuropil_Aug2020.stl', 2)
    ]
    # TODO add neuropil region meshes

    import trimesh.exchange
    for filename, segid in volume_meshes:
        with open(os.path.join(meshes_folder, filename), 'r') as f:
            mesh = trimesh.exchange.stl.load_stl(f)
        mesh = cloudvolume.mesh.Mesh(
            mesh['vertices'],
            mesh['faces'],
            segid=segid
        )
        volumes_cv.mesh.put(mesh)
