#!/usr/bin/env python3

import os

import numpy as np
import requests
import tqdm


def fanc4_to_3(*pts, subpixel_interpolation=False, scale=2, return_dict=False):
    """
    Convert points from alignment V4 (used on neuroglancer) to their
    corresponding locations in alignment V3 (used on CATMAID).

    Args:
        pts:         A nx3 array of points in mip0 voxel coordinates.
                         (Accepts lists, tuples, or numpy arrays.)
        scale:       Selects the granularity of the field being used, but
                         does not change the units.
        return_dict: If false, returns an nx3 numpy array. If false,
                         returns a dict containing x, y, z, dx, and dy values.
    
    Returns:
        (by default) an nx3 numpy array containing the transformed points
        (if return_dict=True) a dictionary of transformed x/y/z values and the
            dx/dy values.
        Returned coordinates are floats (i.e. can have fractional values)
    """
             
    base = 'https://catmaid3.hms.harvard.edu/services/transform-service/dataset/fanc_v4_to_v3/s/{}/'.format(scale)

    if len(pts) == 1:
        pts = pts[0]

    def transform(pts, return_dict=False):
        pts = np.array(pts, dtype=np.uint32)
        ndims = len(pts.shape)
        if ndims == 1:  # Single point
            full_url = base + 'z/{}/x/{}/y/{}'.format(pts[2], pts[0], pts[1])
            r = requests.get(full_url)
        else:  # Multiple points
            full_url = base + 'values_array'
            r = requests.post(full_url, json={
                'x': list(pts[:, 0].astype(str)),
                'y': list(pts[:, 1].astype(str)),
                'z': list(pts[:, 2].astype(str))
            })
        try:
            r = r.json()
            if return_dict:
                return r
            if ndims == 1:
                return np.array((r['x'], r['y'], r['z']))
            else:
                return np.array((r['x'], r['y'], r['z'])).T
        except:
            return r

    if not subpixel_interpolation:
        return transform(pts, return_dict=return_dict)
    else:  # Do subpixel interpolation.
        pts = np.array(pts, dtype=np.float64)
        # Need to query the 4 pixels surrounding each point
        query = []
        for x, y, z in pts:
            query.extend([(int(x)  , int(y)  , z),
                          (int(x)  , int(y)+1, z),
                          (int(x)+1, int(y)  , z),
                          (int(x)+1, int(y)+1, z)])
        query_t = transform(query, return_dict=False)
        pts_t = []
        for i, pt in enumerate(pts):
            # Retrieve the 4 pixels surrounding the point
            corners = query_t[4*i:4*(i+1), :]
            #print('corners', corners)
            # Get the point's decimal component
            subpix = pt - pt.astype(int)
            #print('subpix', subpix)
            # Perform bilinear interpolation
            # First interpolate y
            l = corners[0] + subpix[1] * (corners[1] - corners[0])
            r = corners[2] + subpix[1] * (corners[3] - corners[2])
            # Then interpolate x
            pts_t.append(l + subpix[0] * (r - l))

        if return_dict:
            # TODO
            raise NotImplementedError
        return np.array(pts_t)


def fanc3_to_4(*pts, mode='descent', precision=1, verbose=False):
    """
    Convert points from alignment V3 (used on CATMAID) to their
    corresponding locations in alignment V4 (used on neuroglancer).

    Args:
        pts:       A nx3 array of points in mip0 voxel coordinates.
                       (Accepts lists, tuples, or numpy arrays.)
        mode:      'descent' or 'inversefield'
                   Use 'descent' if the v3 to v4 alignment field isn't available.
                   Use 'inversefield' if it is and you want faster (but
                       potentially less accurate?) mappings.
        precision: when in 'descent' mode, how accurate of an inverse must be
                       found before descent stops. In units of mip0 pixels.

    Returns:
        An nx3 numpy array containing the transformed points.
    """
    if len(pts) == 1:
        pts = pts[0]
    pts = np.array(pts, dtype=np.float64)
    ndims = len(pts.shape)

    if mode == 'descent':
        # Use this mode if the v3 to v4 alignment
        # field hasn't been calculated yet.

        def mag(v):
            """Magnitude of a vector"""
            return np.sum(v**2)**0.5
        def mags(m):
            """Magnitudes of n vectors in an nxm matrix"""
            return np.sum(m**2, axis=1)**0.5

        def find_inverse_by_descent(pt, precision, max_iterations=10):
            """
            This is deprecated. Use the parallel version below. The parallel
            version also has subpixel interpolation implemented.
            """
            def report():
                print(i, pt, inv, fanc4_to_3(inv), error_vec)

            inv = pt.copy()
            error_vec = fanc4_to_3(inv) - pt
            i = 0
            if verbose: report()
            while mag(error_vec) > precision and i < max_iterations:
                inv = inv - error_vec
                error_vec = fanc4_to_3(inv) - pt
                i += 1
                if verbose: report()
            if i >= max_iterations:
                print('WARNING: Max iterations ({}) reached.'.format(max_iterations))

            return inv.astype(np.uint32)


        def find_inverse_by_descent_parallel(pts, precision, max_iterations=20):
            def report():
                print('i', i)
                print('num points with large errors:', sum(rows_to_process))
                print(pts[rows_to_process, :])
                print(inv[rows_to_process, :])
                print(fanc4_to_3(inv[rows_to_process, :]))
                print(error_mags[rows_to_process])
                print()

            # Initialize
            inv = pts.copy()
            error_vecs = fanc4_to_3(inv) - pts
            error_mags = mags(error_vecs)
            rows_to_process = error_mags > precision
            subpixel_interpolation = False
            descent_rate = 1
            i = 0
            if verbose: report()

            # Start iterations
            while any(rows_to_process) and i < max_iterations:
                if i == 3:
                    # ~99% of points are resolved within 3 iterations without
                    # needing subpixel interpolation. Resolve the troublemakers
                    # with subpixel interpolation and slower descent.
                    subpixel_interpolation = True
                    descent_rate = 0.5
                # Descent algorithm:
                # Adjust points based on error
                inv[rows_to_process, :] = (
                    inv[rows_to_process, :]
                    - descent_rate * error_vecs[rows_to_process]
                )
                # Calculate new error
                error_vecs[rows_to_process, :] = (
                    fanc4_to_3(inv[rows_to_process, :], subpixel_interpolation=subpixel_interpolation)
                    - pts[rows_to_process, :]
                )
                error_mags = mags(error_vecs)
                # Find points still in need of improvement
                rows_to_process = error_mags > precision
                i += 1
                if verbose: report()
            if i >= max_iterations:
                print('WARNING: Max iterations ({}) reached.'.format(max_iterations))

            return inv

        if len(pts.shape) == 1:  # Vector
            return find_inverse_by_descent(pts, precision=precision)
        elif len(pts.shape) == 2:  # Matrix
            #return np.apply_along_axis(find_inverse_by_descent, 1, pts, precision)  # Serial (slow)
            return find_inverse_by_descent_parallel(pts, precision)  # Parallel (fast)

    elif mode == 'inversefield':
        # Use if the inverse field (v3->v4) has been calculated.
        # (This has not been done yet as of Apr 21, 2021)
        raise NotImplementedError

    else:
        raise ValueError("mode must be 'descent' or 'inversefield' but was {}".format(mode))


# Some example points to test
test_pts_v3 = np.array([
    [5207, 98758, 3028],
    [23540, 116496, 1228]
], dtype=np.uint32)
test_pts_v4 = np.array([
    [5286, 98834, 3028],
    [23622, 116520, 1228]
], dtype=np.uint32)

def test_3_to_4(pts_v3=test_pts_v3, pts_v4=test_pts_v4, verbose=True):
    pts3to4 = fanc3_to_4(pts_v3, verbose=verbose)
    error = np.subtract(pts3to4, pts_v4, dtype=float)

    print('True v4 points:')
    print(pts_v4)
    print('Predicted v4 points:')
    print(pts3to4)
    print('Error:')
    print(error)
    # TODO add some assertion about the error being small, and a True/False
    # return value based on that


def test_4_to_3(pts_v4=test_pts_v4, pts_v3=test_pts_v3):
    pts4to3 = fanc4_to_3(pts_v4)
    error = np.subtract(pts4to3, pts_v3, dtype=float)

    print('True v3 points:')
    print(pts_v3)
    print('Predicted v3 points:')
    print(pts4to3)
    print('Error:')
    print(error)
    # TODO add some assertion about the error being small, and a True/False
    # return value based on that


def test_343(pts=test_pts_v3, verbose=True):
    pts_3_to_4 = fanc3_to_4(pts, verbose=verbose)
    pts_3_to_4_to_3 = fanc4_to_3(pts_3_to_4, subpixel_interpolation=True)
    error343 = np.subtract(pts_3_to_4_to_3, pts, dtype=float)
    print('Error upon v3 -> v4 -> v3')
    print(error343)


def test_434(pts=test_pts_v4, verbose=True):
    pts_4_to_3 = fanc4_to_3(pts, subpixel_interpolation=True)
    pts_4_to_3_to_4 = fanc3_to_4(pts_4_to_3, verbose=verbose)
    error434 = np.subtract(pts_4_to_3_to_4, pts, dtype=float)
    print('Error upon v4 -> v3 -> v4')
    print(error434)


def test_1000_points(verbose=True):
    from itertools import product
    x = range(10000, 65001, 5000)
    y = range(90000, 150001, 5000)
    z = range(2000, 3001, 150)
    pts = np.array(list(product(x, y, z)))
    test_343(pts, verbose=verbose)
    test_434(pts, verbose=verbose)
