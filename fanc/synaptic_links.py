#!/usr/bin/env python3

import os
from pathlib import Path
import json
import csv
from secrets import token_hex
import random
import sqlite3

import numpy as np
import pandas as pd


def flip_xyz_zyx_convention(array, inplace=True):
    """
    Given an Nx6 array, swap values in columns 1 and 3 and swap values in
    columns 4 and 6. This converts xyz-ordered point pairs to be zyx-ordered,
    or zyx-order point pairs to be xyz-ordered.
    """
    if not inplace:
        array = np.copy(array)
    assert array.shape[1] == 6
    array[:, 0:3] = array[:, 2::-1]
    array[:, 3:6] = array[:, 5:2:-1]
    if not inplace:
        return array


def flip_pre_post_order(array, inplace=True):
    """
    Given an Nx6 array, swap columns 1-3 with columns 4-6.
    """
    if not inplace:
        array = np.copy(array)
    assert array.shape[1] == 6
    tmp = array[:, 0:3].copy()
    array[:, 0:3] = array[:, 3:6]
    array[:, 3:6] = tmp
    if not inplace:
        return array


def upscale(array, scale_factor, inplace=True):
    """
    Given an Nx6 array and a scaling factor (constant or 3-length), multiply the
    first 3 columns and the last 3 columns of the array by the scale factor.
    """
    if not inplace:
        array = np.copy(array)
    array[:, 0:3] = array[:, 0:3] * scale_factor
    array[:, 3:6] = array[:, 3:6] * scale_factor
    if not inplace:
        return array


def downscale(array, scale_factor, inplace=True):
    """
    Given an Nx6 array and a scaling factor (constant or 3-length), divide the
    first 3 columns and the last 3 columns of the array by the scale factor.
    """
    if not inplace:
        array = np.copy(array)
    array[:, 0:3] = array[:, 0:3] / scale_factor
    array[:, 3:6] = array[:, 3:6] / scale_factor
    if not inplace:
        return array


def load(fn, convention='xyz', units='voxels', voxel_size=None, verbose=False, threshold = 12):
    """
    Given a filename of a file containing synaptic links, load the links and
    return them as an Nx6 numpy array representing the N links.  The first 3
    columns represent presynaptic coordinates, last 3 columns represent
    postsynaptic coordinates.

    Supports .npy, .csv, and binary files, though the code makes some
    assumptions about the units and column orderings of each format that you
    should verify are correct for your files.

    fn: filename
    convention: 'xyz' (default) or 'zyx'
        Determines ordering of the 3 columns representing each point.
    units: 'voxels' (default) or 'nm'/'nanometers'
        Determines units of the returned points.
    voxel_size: None (default) or 3-tuple (e.g. (4, 4, 40))
        Determines voxel size to use for conversions. If left as None, the code
        knows what default voxel size to use for different file formats.

    threshold: int, threshold to apply based on "sum"
    """
    assert convention in ['xyz', 'zyx']
    assert units in ['voxels', 'nm', 'nanometers']

    if fn.endswith('.npy'):
        if verbose: print('Mode 1: npy')
        # For opening .npy files saved from np.save
        links = np.load(fn)

        # The .npy files Jasper generated on Feb 8 were saved in zyx, so flip them to xyz
        if True:  # Update this if convention changes
            flip_xyz_zyx_convention(links)
        # The .npy files Jasper generated on Feb 8 were saved in post-pre order
        if True:  # Update this if convention changes
            flip_pre_post_order(links)

        if voxel_size is None:
            # The .npy files Jasper generated on Feb 8 are saved in nm, so
            # convert to units of voxels at (4, 4, 40) nm voxel size for easier
            # entering into ng.
            voxel_size = (4, 4, 40)
        if units == 'voxels':
            downscale(links, voxel_size)

        # If the default kwargs were used, links is now pre-post, xyz, in units
        # of voxels at (4, 4, 40)nm

    elif fn.endswith('.csv'):
        if verbose: print('Mode 2: csv')
        # For opening ground truth annotation files
        links = np.genfromtxt(fn, delimiter=',', skip_header=1, dtype=np.uint16)

        # Ground truth annotations were saved in zyx, so flip them to xyz
        if True:  # Update this if convention changes
            flip_xyz_zyx_convention(links)
        # Ground truth annotations were saved in pre-post order, so OK as is
        if False:  # Update this if convention changes
            flip_pre_post_order(links)

        if voxel_size is None:
            # Ground truth annotations were saved in nm, so convert to units of
            # voxels at (4, 4, 40) nm voxel size for easier entering into ng.
            voxel_size = (4, 4, 40)
        if units == 'voxels':
            downscale(links, voxel_size)

        # If the default kwargs were used, links is now pre-post, xyz, in units
        # of voxels at (4, 4, 40)nm

    else:
        if verbose: print('Mode 3: binary')
        # For opening binary files saved by ../detection/worker.py
        # post coord(x,y,z), pre coord(x,y,z), mean, max, area, 4x4x4 moments
        data = np.fromfile(fn, dtype=np.dtype("6f8,3f8,(4,4,4)f8"))

        # Apply threshold based on "sum" and return links that pass.
        try:
            links = np.stack([x[0].astype("int32") for x in data if x[2][0][0][0] > threshold])
        except:
            return np.array([])

        if True:  # The Feb 7 predictions were saved in post-pre order
            flip_pre_post_order(links)

        if units == 'voxels':
            # The Feb 7 predictions are in units of mip1 voxels ((8.6, 8.6, 45)
            # nm) so convert to mip0 voxels for easier entering into ng.
            upscale(links, (2, 2, 1))
            # To indicate the location in the middle of the mip1 voxel, add 1
            # after the upscaling (since integers indicate top-left corners).
            links = links + np.array([1, 1, 0, 1, 1, 0])
        else:
            if voxel_size is None:
                voxel_size = (8.6, 8.6, 45)
            upscale(links, voxel_size)

        # If the default kwargs were used, links is now pre-post, xyz, in units
        # of voxels at (4.3, 4.3, 45)nm

    if convention == 'zyx':
        flip_xyz_zyx_convention(links)

    return links


def to_ng_annotations(synapses, input_order='xyz', input_units=(1, 1, 1),
                      voxel_mip_center=None):
    """
    Create a json representation of a set of synaptic links, appropriate for
    pasting into a neuroglancer annotation layer.
    synapses: np.array or pd.DataFrame
        Nx6 numpy array representing N pre-post point pairs OR
        DataFrame with columns 'pre_pt_position' and 'post_pt_position'
    input_order: 'xyz' (default) or 'zyx'
        Indicate which column order the input array has.
    input_units: (1, 1, 1) (default) or some other 3-tuple
        If your coordinates are in nm, indicate the voxel size in nm.
        e.g. (4, 4, 40) or (40, 4, 4) depending on the input order. If
        your synapses are already in units of voxels, leave this at the
        default value.
    voxel_mip_center: None or int
        In neuroglancer, an annotation with an integer coordinate value appears
        at the top-left corner of a voxel, not at the center of that voxel.
        Point annotations often make more sense being placed in the middle of
        the voxel. If False, nothing is added and the neuroglancer default of
        integer values pointing to voxel corners is kept. If voxel_mip_center
        is set to 0, 0.5 will be added to each coordinate so that
        integer-valued inputs end up pointing to the middle of the mip0 voxel.
        If set to 1, 1 will be added to point to the middle of the mip1 voxel.
        If set to x, 0.5 * 2^x will be added to point to the middle of the mipx
        voxel.
        The z coordinate is not changed no matter what, since mips only
        downsample x and y.
    """
    assert input_order in ['xyz', 'zyx']

    def line_anno(pre, post):
        return {
            'pointA': [x for x in pre],
            #'pointA': [int(x) for x in pre],
            'pointB': [x for x in post],
            #'pointB': [int(x) for x in post],
            'type': 'line',
            'id': token_hex(40)
        }

    if isinstance(synapses, str):
        synapses = load(synapses)

    if isinstance(synapses, pd.DataFrame):
        synapses = np.hstack([np.vstack(synapses.pre_pt_position.values),
                              np.vstack(synapses.post_pt_position.values)])

    if tuple(input_units) != (1, 1, 1):
        synapses = downscale(synapses.astype(float), input_units, inplace=False)
        # Now synapses are in units of voxels

    if input_order == 'zyx':
        synapses = flip_xyz_zyx_convention(synapses, inplace=False)

    if voxel_mip_center is not None:
        delta = 0.5 * 2**voxel_mip_center
        adjustment = (delta, delta, 0, delta, delta, 0)
        synapses = synapses.astype(float) + adjustment

    annotations = [line_anno(synapses[i, 0:3].tolist(),
                             synapses[i, 3:6].tolist())
                   for i in range(synapses.shape[0])]
    print(json.dumps(annotations, indent=2))

    try:
        import pyperclip
        answer = input("Want to copy the output to the clipboard? (Only works if "
                       "you're running this script on a local machine, not on a "
                       "server.) [y/n] ")
        if answer.lower() == 'y':
            print('Copying')
            pyperclip.copy(json.dumps(annotations))
    except:
        print("Install pyperclip (pip install pyperclip) for the option to"
              " programmatically copy the output above to the clipboard")
