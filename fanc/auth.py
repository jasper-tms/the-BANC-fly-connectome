#!/usr/bin/env python3

import os

from caveclient import CAVEclient
from cloudvolume import CloudVolume
from meshparty import trimesh_io

DEFAULT_DATASET = 'brain_and_nerve_cord'
DATASTACK_NICKNAMES = {
    'banc': 'brain_and_nerve_cord',
    'BANC': 'brain_and_nerve_cord',
    'production': 'brain_and_nerve_cord',
}

configs = {
    'mesh_cache': os.path.expanduser('~/banc-meshes'),
    'cave_auth_token_key': 'brain_and_nerve_cord',
}
if os.environ.get('BANC_AUTH_TOKEN_KEY'):
    configs['cave_auth_token_key'] = os.environ['BANC_AUTH_TOKEN_KEY']

# To enable lazy loading and caching of CAVEclients and cloudvolumes
_clients = {}
_cloudvolumes = {}


def save_cave_credentials(token,
                          token_key=DEFAULT_DATASET,
                          overwrite=False):
    # If a nickname was used, get the proper datastack name
    token_key = DATASTACK_NICKNAMES.get(token_key, token_key)

    client = CAVEclient()
    client.auth.save_token(token, token_key=token_key, overwrite=overwrite)
    try:
        client.auth.save_token(token, token_key='token', overwrite=False)
    except KeyError:
        print('Global credentials (with key "token") already set, will not overwrite')

    print('Token succesfully stored at: '
          f'~/.cloudvolume/secrets/cave-secret.json under key "{token_key}"')


def use_auth_token_key(token_key):
    """
    Set the auth token key to use for all subsequent calls to get_caveclient()

    Note that existing clients that you got from calling get_caveclient() will
    not be updated. Call get_caveclient() again after calling this function to
    get a client with the new auth token key.
    """
    configs['cave_auth_token_key'] = token_key


def get_caveclient(dataset=DEFAULT_DATASET, auth_token_key=None):
    # If a nickname was used, get the proper datastack name
    dataset = DATASTACK_NICKNAMES.get(dataset, dataset)

    # If auth_token_key is not provided, use the default
    if auth_token_key is None:
        auth_token_key = configs['cave_auth_token_key']

    if dataset not in _clients:
        _clients[dataset] = {}
    if auth_token_key not in _clients[dataset]:
        _clients[dataset][auth_token_key] = CAVEclient(dataset,
                                                       auth_token_key=auth_token_key)

    return _clients[dataset][auth_token_key]


def get_chunkedgraph_path(dataset=DEFAULT_DATASET):
    client = get_caveclient(dataset=dataset)
    return client.info.segmentation_source().replace('middleauth+', '')


def get_cloudvolume(dataset=DEFAULT_DATASET):
    # If a nickname was used, get the proper datastack name
    dataset = DATASTACK_NICKNAMES.get(dataset, dataset)

    if dataset not in _cloudvolumes:
        _cloudvolumes[dataset] = CloudVolume(
            get_chunkedgraph_path(dataset),
            use_https=True,
            secrets=get_caveclient(dataset).auth.token
        )
    return _cloudvolumes[dataset]


def get_meshmanager(dataset=DEFAULT_DATASET,
                    mesh_cache=None):
    if mesh_cache is None:
        mesh_cache = configs['mesh_cache']

    return trimesh_io.MeshMeta(
        cv_path=get_chunkedgraph_path(dataset),
        disk_cache_path=mesh_cache,
        map_gs_to_https=True
    )
