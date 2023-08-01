#!/usr/bin/env python3

import os
from pathlib import Path
import json

from caveclient import CAVEclient
from cloudvolume import CloudVolume
from meshparty import trimesh_io

DATASTACK_NICKNAMES = {
    'banc': 'brain_and_nerve_cord',
    'BANC': 'brain_and_nerve_cord',
    'production': 'brain_and_nerve_cord',
}

DEFAULT_MESH_CACHE = os.path.expanduser('~/banc-meshes')

# To enable lazy loading of CAVEclients and cloudvolumes
_clients = {}
_cloudvolumes = {}


def save_cave_credentials(token, dataset='brain_and_nerve_cord', overwrite=False):
    # If a nickname was used, get the proper datastack name
    dataset = DATASTACK_NICKNAMES.get(dataset, dataset)

    client = CAVEclient()
    client.auth.save_token(token, token_key=dataset, overwrite=overwrite)
    try:
        client.auth.save_token(token, token_key='token', overwrite=False)
    except KeyError:
        print('Global credentials (with key "token") already set, will not overwrite')

    print('Token succesfully stored at: '
          f'~/.cloudvolume/secrets/cave-secret.json under key "{dataset}"')


def get_caveclient(dataset='brain_and_nerve_cord'):
    # If a nickname was used, get the proper datastack name
    dataset = DATASTACK_NICKNAMES.get(dataset, dataset)

    if dataset not in _clients:
        _clients[dataset] = CAVEclient(dataset, auth_token_key=dataset)

    return _clients[dataset]


def get_cloudvolume(dataset='brain_and_nerve_cord'):
    # If a nickname was used, get the proper datastack name
    dataset = DATASTACK_NICKNAMES.get(dataset, dataset)

    if dataset not in _cloudvolumes:
        client = get_caveclient(dataset=dataset)

        _cloudvolumes[dataset] = CloudVolume(
            client.info.get_datastack_info()['segmentation_source'].replace('middleauth+', ''),
            use_https=True,
            secrets=client.auth.token
        )

    return _cloudvolumes[dataset]


def get_meshmanager(dataset='brain_and_nerve_cord',
                    mesh_cache=DEFAULT_MESH_CACHE):
    return trimesh_io.MeshMeta(
        cv_path=get_caveclient().info.segmentation_source(),
        disk_cache_path=mesh_cache,
        map_gs_to_https=True
    )
