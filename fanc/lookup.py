#!/usr/bin/env python3

import collections
from concurrent import futures
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import tqdm
import cloudvolume

from . import auth, statebuilder

default_cellid_table = 'cell_ids'
default_proofreading_tables = []
default_annotation_sources = [('cell_info', 'tag'),
                              ('neck_connective_y92500', 'tag'),
                              ('peripheral_nerves', 'tag')]
default_anchor_point_sources = ['neck_connective_y92500', 'peripheral_nerves']
default_svid_lookup_url = '<not implemented>'


# --- START CAVE TABLES / ANNOTATIONS SECTION --- #
def proofreading_status(segids: int or list[int],
                        source_tables: str or list[str] = default_proofreading_tables,
                        timestamp='now') -> None or str or tuple(str, list):
    """
    Determine whether a segment has been marked as proofread.

    Arguments
    ---------
    segids: int, or iterable of ints
      The segment ID or IDs to look up proofreading status for.

    source_tables: str, or list of str
      The name(s) of the CAVE proofreading table(s) to query

    timestamp: 'now' (default) OR datetime OR None
      The timestamp at which to query the segment's proofreading status.
      If 'now', use the current time.
      If datetime, use the time specified by the user.
      If None, use the timestamp of the latest materialization.

    Returns
    -------
    None: The given segment ID has not been marked as proofread in any of the
      given tables.
    str: The name of the proofreading table in which the segment is marked as
      proofread.
    2-tuple of (str, list): The name of the proofreading table in which an earlier
      version of this the segment was marked as proofread, and a list
      containing the previous segment ID(s) that were marked as proofread.
    """
    if isinstance(segids, (int, np.integer)):
        return proofreading_status([segids], source_tables=source_tables, timestamp=timestamp)[0]

    client = auth.get_caveclient()
    if timestamp in ['now', 'live']:
        timestamp = datetime.utcnow()
    elif timestamp is None:
        timestamp = client.materialize.get_timestamp()

    if not all(client.chunkedgraph.is_latest_roots(segids, timestamp=timestamp)):
        raise KeyError('A given ID(s) is not valid at the given timestamp.'
                       ' Use updated IDs or provide the timestamp where'
                       ' the ID(s) is valid.')

    if isinstance(source_tables, str):
        source_tables = [source_tables]

    results = pd.Series(index=segids, data=None, dtype=object)
    for table_name in source_tables[::-1]:
        table = client.materialize.live_live_query(table_name, timestamp)
        results.loc[results.isna() & results.index.isin(table.valid_id)] = table_name
        if results.notna().all():
            return results.loc[segids].to_list()
        results.loc[results.isna()] = table.groupby('pt_root_id')['valid_id'].apply(lambda x: (table_name, list(x)))
        if results.notna().all():
            return results.loc[segids].to_list()

    results.loc[results.isna()] = None
    return results.loc[segids].to_list()


def num_proofread_neurons(source_tables: str or list[str] = default_proofreading_tables,
                          timestamp='now') -> int:
    """
    Count the number of unique neurons that have been marked as proofread.
    """
    if timestamp in ['now', 'live']:
        timestamp = datetime.utcnow()

    client = auth.get_caveclient()
    tables = [client.materialize.live_live_query(table_name, timestamp)
              for table_name in source_tables]
    return pd.concat(tables).pt_root_id.nunique()


def cells_annotated_with(tags: str or list[str],
                         *,
                         exclude_tags: str or list[str] = None,
                         source_tables=default_annotation_sources,
                         timestamp='now',
                         return_as: ['list', 'url'] = 'list',
                         raise_not_found=True):
    """
    Get all the cells annotated with a given text tag / all of the given text
    tags.

    Arguments
    ---------
    tags: str or list of str
      The tag(s) to query. If multiple are provided, only cells
      with all the given tags will be returned.
      Any tag that starts with 'not ' or 'NOT ' will be moved
      to exclude_tags (see below).

    exclude_tags: str or list of str, default None
      The tag(s) to exclude from the query. If multiple are provided, only
      cells with none of the given tags will be returned.
      You may also specify exclude_tags via the tags argument (above) by
      prepending 'not ' or 'NOT ' to the tag name.

    source_tables: str OR list of str OR list of 2-tuple of str
      str OR list of str:
        The name(s) of the CAVE table(s) to query for annotations. Annotations
        will be pulled from the column named 'tag', so they must contain a
        column with that name.
      list of 2-tuple of str:
        Each tuple specifies the name of a CAVE table to query for annotations,
        then the name of the column to use from that table.

    timestamp: 'now' (default) OR datetime OR None
      The timestamp at which to query the segment's proofreading status.
      If 'now', use the current time.
      If datetime, use the time specified by the user.
      If None, use the timestamp of the latest materialization.

    return_as: 'list' (default) OR 'url'
      Controls output format, see Returns section below

    Returns
    -------
    If return_as == 'list':
      list of ints: The segment IDs of cells annotated with the given tag(s)
    If return_as == 'url':
      str: A neuroglancer state (to be opened in a browser) showing the cells
        annotated with the given tag(s)
    """
    if isinstance(tags, str):
        tags = [tags]
    if exclude_tags is None:
        exclude_tags = []
    if isinstance(exclude_tags, str):
        exclude_tags = [exclude_tags]
    if not return_as in ['list', 'url']:
        raise ValueError('return_as must be either "list" or "url"')
    exclude_tags = exclude_tags + [tag[4:] for tag in tags if tag.lower().startswith('not ')]
    tags = [tag for tag in tags if not tag.lower().startswith('not ')]
    annos = all_annotations(source_tables=source_tables,
                            timestamp=timestamp,
                            group_by_segid=False)
    is_invalid = [tag not in annos.tag.unique() for tag in tags]
    if any(is_invalid):
        raise KeyError('Check your spelling – the following tags are not'
                       ' present at all in the annotation tables:'
                       f' {np.array(tags)[is_invalid].tolist()}')
    is_invalid = [tag not in annos.tag.unique() for tag in exclude_tags]
    if any(is_invalid):
        raise KeyError('Check your spelling – the following tags are not'
                       ' present at all in the annotation tables:'
                       f' {np.array(exclude_tags)[is_invalid].tolist()}')

    annos_grouped = annos.groupby('pt_root_id')['tag'].apply(list)
    do_tags_match = lambda x: (all([tag in x for tag in tags]) and
                               all([tag not in x for tag in exclude_tags]))
    matching_segids = annos_grouped.index[annos_grouped.apply(do_tags_match)]
    matching_segids = matching_segids.to_list()
    if len(matching_segids) == 0 and raise_not_found:
        if exclude_tags is None:
            raise LookupError(f'Found no objects annotated with all of: {tags}')
        raise LookupError(f'Found no objects annotated with all of: {tags}'
                          f' and none of: {exclude_tags}')

    if return_as == 'list':
        return matching_segids
    # else, return_as == 'url'
    points = annos.loc[annos.pt_root_id.isin(matching_segids) &
                       annos.tag.isin(tags)].groupby('pt_root_id')['pt_position'].apply(lambda x: list(x)[0])
    return statebuilder.render_scene(neurons=matching_segids,
                                     annotations={'name': 'annotation points',
                                                  'type': 'points',
                                                  'data': points})


def all_annotations(source_tables=default_annotation_sources,
                    timestamp='now',
                    group_by_segid=True) -> pd.Series or pd.DataFrame:
    """
    Get a list of all annotations in the given CAVE table(s).

    Arguments
    ---------
    source_tables: str OR list of str OR list of 2-tuple of str
      str OR list of str:
        The name(s) of the CAVE table(s) to query for annotations. Annotations
        will be pulled from the column named 'tag', so they must contain a
        column with that name.
      list of 2-tuples containing (table_name, column_with_annotations):
        Each tuple specifies the name of a CAVE table to query for annotations,
        then the name of the column to pull annotations from for that table.

    timestamp: 'now' (default) OR datetime OR None
      The timestamp at which to query the segment's proofreading status.
      If 'now', use the current time.
      If datetime, use the time specified by the user.
      If None, use the timestamp of the latest materialization.

    group_by_segid: bool (default: True)
      Controls output format, see Returns section below

    Returns
    -------
    If group_by_segid == False:
      pd.DataFrame: A dataframe where every row is one annotation on one segment.
    If group_by_segid == True:
      pd.Series: A series with the segment IDs as the index and a list of
      annotations (strings) as the values.
    """
    client = auth.get_caveclient()
    if timestamp in ['now', 'live']:
        timestamp = datetime.utcnow()
    elif timestamp is None:
        timestamp = client.materialize.get_timestamp()

    source_tables = _format_annotation_sources(source_tables)

    annos = []
    for table_name, column_name in source_tables:
        table = client.materialize.live_live_query(table_name, timestamp)
        table['source_table'] = table_name
        table['created'] = table['created'].apply(datetime.date)
        if 'user_id' not in table.columns:
            table['user_id'] = None
        if column_name != 'tag2':
            if 'tag2' not in table.columns:
                table['tag2'] = None
            table.rename(columns={column_name: 'tag'}, inplace=True)
        else:
            table['tag'] = table['tag2']
        annos.append(table[['pt_root_id', 'tag', 'tag2', 'pt_position',
                            'user_id', 'source_table', 'created']])

    annos = pd.concat(annos).sort_values(by='created').reset_index(drop=True)
    if group_by_segid:
        annos = annos.groupby('pt_root_id')['tag'].apply(list)
    return annos


def annotations(segids: int or list[int],
                source_tables=default_annotation_sources,
                timestamp='now',
                return_details=False,
                slow_mode=False) -> list or pd.DataFrame:
    """
    Get cell(s) annotations from CAVE table(s).

    Arguments
    ---------
    segids: int, or iterable of ints
      The segment ID or IDs to look up annotations for.

    source_tables: str OR list of str OR list of 2-tuple of str
      str OR list of str:
        The name(s) of the CAVE table(s) to query for annotations. Annotations
        will be pulled from the column named 'tag', so they must contain a
        column with that name.
      list of 2-tuples containing (table_name, column_with_annotations):
        Each tuple specifies the name of a CAVE table to query for annotations,
        then the name of the column to pull annotations from for that table.

    timestamp: 'now' (default) OR datetime OR None
      The timestamp at which to query the segment's proofreading status.
      If 'now', use the current time.
      If datetime, use the time specified by the user.
      If None, use the timestamp of the latest materialization.

    return_details: bool (default: False)
      Controls output format, see Returns section below

    slow_mode: bool (default: False)
      Whether to rely on faster queries with server-side filtering (False) or
      fall back to slower queries with client-side filtering (True). The reason
      this option exists is that server-side filtering has been buggy at times,
      but generally users should be fine leaving this as False.

    Returns
    -------
    list of strings OR pd.DataFrame, depending on `return_details`
    """
    if isinstance(segids, (int, np.integer)) and not return_details:
        return annotations([segids], source_tables=source_tables, timestamp=timestamp,
                           return_details=False, slow_mode=slow_mode)[0]
    elif isinstance(segids, (int, np.integer)):
        segids = [segids]

    source_tables = _format_annotation_sources(source_tables)

    client = auth.get_caveclient()
    if timestamp in ['now', 'live']:
        timestamp = datetime.utcnow()
    elif timestamp is None:
        timestamp = client.materialize.get_timestamp()

    # Slow mode: get all annotations (big dataframe!) then filter down to the ones we want
    if slow_mode:
        if return_details:
            table = all_annotations(source_tables, timestamp=timestamp,
                                    group_by_segid=False)
            return table.loc[table.pt_root_id.isin(segids)].reset_index(drop=True)
        else:
            table = all_annotations(source_tables, timestamp=timestamp,
                                    group_by_segid=True)
            return [table.loc[s] for s in segids]

    # Fast mode: use filter_in_dict to request only the annotations we want from the server
    tables = []
    for table_name, column_name in source_tables:
        table = client.materialize.live_live_query(
            table_name, timestamp, filter_in_dict={table_name: {'pt_root_id': segids}})
        table['source_table'] = table_name
        if 'user_id' not in table.columns:
            table['user_id'] = None
        if column_name != 'tag2':
            if 'tag2' not in table.columns:
                table['tag2'] = None
            table.rename(columns={column_name: 'tag'}, inplace=True)
        else:
            table['tag'] = table['tag2']
        tables.append(table[['pt_root_id', 'tag', 'tag2', 'pt_position',
                            'user_id', 'source_table', 'created']])
    table = pd.concat(tables).sort_values(by='created').reset_index(drop=True)

    if return_details:
        return table
    return [[anno for anno in table.loc[table.pt_root_id == s, 'tag']] for s in segids]


def _format_annotation_sources(source_tables):
    """
    Insist that source_tables is a list of 2-tuples of str, where the first
    element of each tuple is the name of a CAVE table to query for annotations,
    and the second element is the name of the column to use from that table.

    This function is used by a few functions in this module – not intended for
    users to call directly.
    """
    if isinstance(source_tables, str):
        return [(source_tables, 'tag')]
    if isinstance(source_tables, list):
        for i, row in enumerate(source_tables):
            if isinstance(row, str):
                source_tables[i] = (row, 'tag')
            elif not isinstance(row, (tuple, list)) or len(row) != 2:
                raise ValueError('source_tables must be a str, a list of str, or a list of 2-tuple of str')
        return source_tables
    raise ValueError('source_tables must be a str, a list of str, or a list of 2-tuple of str')
# --- END CAVE TABLES / ANNOTATIONS SECTION --- #


# --- START SEGMENTATION/CHUNKEDGRAPH SECTION --- #
def svid_from_pt(points: 'Nx3 iterable', service_url=default_svid_lookup_url):
    """
    Return the supervoxel IDs for a set of points.

    This function relies on an external service hosted on services.itanna.io,
    created and maintained by Eric Perlman, which provides very fast svid
    lookups. If this service is down, you can try the slower version
    instead, `fanc.lookup.segid_from_pt_cv()`.

    Arguments
    ---------
    points: Nx3 iterable (list / tuple / np.ndarray / pd.Series)
      Point or points to query. Provide these in xyz order and in mip0 voxel coordinates.

    Returns
    -------
    The requested supervoxel IDs as a list of ints.
    Order is preserved - the svid corresponding to the Nth point in the
    argument will be the Nth value in the returned list.
    """
    if isinstance(points, pd.Series):
        points = np.vstack(points)

    if len(points) == 3:
        try: iter(points[0])
        except: return svid_from_pt([points], service_url=service_url)[0]

    points = np.array(points, dtype=np.uint32)
    if points.ndim == 1:
        points = points.reshape(-1, 3)
    r = requests.post(service_url, json={
        'x': list(points[:, 0].astype(str)),
        'y': list(points[:, 1].astype(str)),
        'z': list(points[:, 2].astype(str))
    })
    r = r.json()['values'][0]
    return [int(i) for i in r]


def segid_from_pt(points: 'Nx3 iterable',
                  timestamp='now',
                  service_url=default_svid_lookup_url,
                  **kwargs):
    """
    Return the segment IDs (also called root IDs) for a set of points
    at a specified timestamp.

    Arguments
    ---------
    points: Nx3 iterable (list / tuple / np.ndarray / pd.Series)
      Point or points to query. Provide these in xyz order and in mip0 voxel coordinates.

    timestamp: 'now' or None or datetime
      If 'now' or None, look up the current rootID corresponding to the point
      location. Otherwise, look up the rootID for the point location at the
      specified time in the past.

    Additional kwargs:
      cv: cloudvolume.CloudVolume
        If provided, lookup rootIDs using the given cloudvolume instead of the
        default one. Not common to need this.

    Returns
    -------
    The requested segIDs as a numpy array of int64 values
    Order is preserved - the segID corresponding to the Nth point in
    the argument will be the Nth value in the returned array.
    """
    if timestamp == 'now':
        # cv.get_roots interprets timestamp=None as requesting the latest root
        timestamp = None

    svids = svid_from_pt(points, service_url=service_url)

    if 'cv' in kwargs:
        cv = kwargs['cv']
    else:
        cv = auth.get_cloudvolume()

    try:
        iter(svids)
        return cv.get_roots(svids, timestamp=timestamp).astype(np.int64)
    except:
        return cv.get_roots(svids, timestamp=timestamp).astype(np.int64)[0]


def segid_from_cellid(cellids: int or list[int],
                      timestamp='now',
                      table_name=default_cellid_table):
    """
    Return the segment ID for a given cell ID at the given timestamp.

    Arguments
    ---------
    cellids: int, or list of ints
      The cell ID(s) to look up segment IDs for.

    timestamp: 'now' (default) OR datetime OR None
      The timestamp at which to query the segment's proofreading status.
      If 'now', use the current time.
      If datetime, use the time specified by the user.
      If None, use the timestamp of the latest materialization.

    table_name: str
      The name of the CAVE table to query for cell IDs.

    Returns
    -------
    If cellids is an int, the requested segID as an int.
    If cellids is a list, the requested segIDs as a list of ints.
    """
    try: iter(cellids)
    except: return segid_from_cellid([cellids], timestamp=timestamp, table_name=table_name)[0]

    client = auth.get_caveclient()
    if timestamp in ['now', 'live']:
        timestamp = datetime.utcnow()
    elif timestamp is None:
        timestamp = client.materialize.get_timestamp()

    cell_ids = client.materialize.live_live_query(
        table_name,
        timestamp=timestamp,
        filter_in_dict={table_name: {'id': cellids}})
    cell_ids.set_index('id', inplace=True)
    if any([i not in cell_ids.index for i in cellids]):
        raise ValueError('There is no cell with these cell IDs: {}'.format(
            [i for i in cellids if i not in cell_ids.index]))
    return cell_ids.loc[cellids, 'pt_root_id'].to_list()


def cellid_from_segid(segids: int or list[int],
                      timestamp='now',
                      table_name=default_cellid_table):
    """
    Return the cell ID for a given segment ID.

    Arguments
    ---------
    segids: int, or list of int
      The segment ID(s) to look up cell IDs for.

    timestamp: 'now' (default) OR datetime OR None
      The timestamp at which to query the segment's proofreading status.
      If 'now', use the current time.
      If datetime, use the time specified by the user.
      If None, use the timestamp of the latest materialization.

    table_name: str (default 'cell_ids')
      The name of the CAVE table containing cell IDs.

    Returns
    -------
    If segids is an int, the requested cell ID as an int.
    If segids is a list, the requested cell IDs as a list of ints.
    """
    try: iter(segids)
    except: return cellid_from_segid([segids], timestamp=timestamp, table_name=table_name)[0]

    client = auth.get_caveclient()
    if timestamp in ['now', 'live']:
        timestamp = datetime.utcnow()
    elif timestamp is None:
        timestamp = client.materialize.get_timestamp()

    cell_ids = client.materialize.live_live_query(
        table_name,
        timestamp=timestamp,
        filter_in_dict={table_name: {'pt_root_id': segids}})
    cell_ids.set_index('pt_root_id', inplace=True)
    if any([i not in cell_ids.index for i in segids]):
        raise ValueError("These segment IDs don't have a cell ID: {}".format(
            [i for i in segids if i not in cell_ids.index]))
    if any(cell_ids.index.value_counts() > 1):
        raise ValueError("These segment IDs have multiple cell IDs: {}".format(
            [segid for segid, count in cell_ids.index.value_counts().iteritems() if count > 1]))
    return cell_ids.loc[segids, 'id'].to_list()
# --- END SEGMENTATION/CHUNKEDGRAPH SECTION --- #


# --- START KEY ATTRIBUTES SECTION --- #
def anchor_point(segids: int or list[int],
                 source_tables=default_anchor_point_sources,
                 timestamp='now', resolve_duplicates=False,
                 select_nth_duplicate: int = 0, slow_mode=False) -> np.ndarray:
    """
    Return a representative "anchor" point for each of the given
    segment ID(s).

    The returned point is expected to be a stable identifier for the
    segment, meaning that correct proofreading operations should not
    disconnect this point from the main body of the segment.

    Arguments
    ---------
    segids: int, or iterable of ints
      The segment ID(s) to look up anchor points for.

    source_tables: iterable of str
      An list of names of CAVE tables to search for anchor points. This list
      must be ordered by priority, as the first table that contains a point for
      this segment will have its point used.

    timestamp: None or 'now' or datetime (default 'now')
      The timestamp to use to query the CAVE tables.
      If None, use the timestamp of the latest materialization.
      If 'now', use the current time.
      If datetime, use that time.

    resolve_duplicates: bool (default False)
    &
    select_nth_duplicate: int (default 0)
      If multiple anchor points are found within a single table for a
      single segment ID, raise an error (if resolve_duplicates==False) or
      select one of the points (if resolve_duplicates==True) by sorting the
      points by x coordinate and then picking the Nth one, with N given by
      select_nth_duplicate. (N is zero-indexed, so the default value of
      select_nth_duplicate=0 results in selection of the point with the
      smallest x coordinate). select_nth_duplicate is ignored if
      resolve_duplicates==False.

    slow_mode: bool (default: False)
      Whether to rely on faster queries with server-side filtering (False) or
      fall back to slower queries with client-side filtering (True). The reason
      this option exists is that server-side filtering has been buggy at times,
      but generally users should be fine leaving this as False.

    Returns
    -------
    points: np.ndarray (3-length vector or Nx3 array)
      If segids is an int, returns a single xyz point coordinate with shape (3,).
      If segids is iterable, returns an Nx3 array of xyz point coordinates.
        Order is preserved (that is, points[n] is the point for segids[n]).
    """
    try: iter(segids)
    except:
        return anchor_point(
            [segids], source_tables=source_tables, timestamp=timestamp,
            resolve_duplicates=resolve_duplicates
        )[0]

    client = auth.get_caveclient()
    if timestamp in ['now', 'live']:
        timestamp = datetime.utcnow()
    elif timestamp is None:
        timestamp = client.materialize.get_timestamp()

    if not all(client.chunkedgraph.is_latest_roots(segids, timestamp=timestamp)):
        raise KeyError('A given ID(s) is not valid at the given timestamp.'
                       ' Use updated IDs or provide the timestamp where'
                       ' the ID(s) is valid.')

    anchor_points = pd.Series(index=set(segids), dtype=object)

    for table in source_tables:
        unanchored_ids = anchor_points[anchor_points.isna()].index.values
        if slow_mode:
            points = client.materialize.live_live_query(table,
                                                        timestamp=timestamp)
            points = points.loc[points.pt_root_id.isin(unanchored_ids)]
        else:
            points = client.materialize.live_live_query(
                table,
                filter_in_dict={table: {'pt_root_id': unanchored_ids}},
                timestamp=timestamp
            )
        for seg, point in points.groupby('pt_root_id'):
            if len(point) > 1:
                # Sort points by x coordinate
                point = point.sort_values('pt_position', key=lambda x: x.str[0])
                if table == 'somas_dec2022':
                    raise ValueError('Multiple somas points found for segid'
                                     f' {seg} in table "{table}".')
                elif not resolve_duplicates:
                    raise ValueError('Multiple anchor points found for segid'
                                     f' {seg} in table "{table}":\n'
                                     f'{np.vstack(point.pt_position)}.\nSet'
                                     ' resolve_duplicates to choose one.')
                if select_nth_duplicate >= len(point):
                    raise ValueError('select_nth_duplicate is too large given'
                                     f' that {len(point)} points were found'
                                     f' for segid {seg} in table "{table}".')
                anchor_points.loc[seg] = point['pt_position'].iloc[select_nth_duplicate]
            else:
                anchor_points.loc[seg] = point['pt_position'].iloc[0]
        if not any(anchor_points.isna()):
            break

    if any(anchor_points.isna()):
        raise ValueError(f'No anchor point found for segid(s)'
                         f' {anchor_points[anchor_points.isna()].index.values}'
                         f' in tables {source_tables}')
    return np.vstack(anchor_points[segids])


def nucleusid_from_pt(points, nucleus_segmentation_path=None):
    """
    Query the nucleus segmentation for the nucleus ID at the given point(s).

    Arguments
    ---------
    points: 3-length iterable, or Nx3 np.ndarray/pd.Series
      The xyz point coordinate(s) to query the nucleus segmentation at.
    nucleus_segmentation_path: str (default None)
      If None, use FANC's nucleus segmentation layer. Or provide a path to a
      nucleus segmentation you want to query.

    Returns
    -------
    np.int64 (if points is a single point) OR
    N-length np.ndarray of np.int64 (if points is an Nx3 array)
    """
    if isinstance(points, pd.Series):
        if points.empty:
            return None
        points = np.vstack(points)
    elif not isinstance(points, np.ndarray):
        points = np.array(points)
    if points.ndim == 1:
        return nucleusid_from_pt(points[np.newaxis, :], nucleus_segmentation_path)[0]


    if nucleus_segmentation_path is None:
        client = auth.get_caveclient()
        table_name = client.info.get_datastack_info()['soma_table']
        table_info = client.annotation.get_table_metadata(table_name)
        nucleus_segmentation_path = table_info['flat_segmentation_source']
    nucleus_cv = cloudvolume.CloudVolume( # mip4
        nucleus_segmentation_path,
        progress=False,
        cache=False, # to avoid conflicts with LocalTaskQueue
        use_https=True,
        autocrop=True, # crop exceeded volumes of request
        bounded=False
    )
    return segid_from_pt_cv(points, nucleus_cv, return_roots=False, progress=False)


# TODO implement the raise kwargs
def soma_from_segid(segids,
                    table='default_soma_table',
                    select_columns=['id', 'volume', 'pt_root_id', 'pt_position'],
                    timestamp='now',
                    raise_not_found=True,
                    raise_multiple=True):
    """
    Given a segID (ID of an object from the full dataset segmentation),
    return information about its soma listed in the soma table.

    Arguments
    ---------
    segids: int, or iterable of ints
      The segment ID(s) to look up soma information for.

    table: str (default 'default_soma_table')
      The name or nickname of the soma table to query. Available nicknames:
        'default_soma_table' or 'neuron' or 'neurons' -> neuron_somas_dec2022
        'all' or 'somas' -> somas_dec2022
        'glia' -> glia_somas_dec2022

    select_columns: list of str (default ['id', 'volume', 'pt_root_id', 'pt_position'])
      The columns to get from the soma table.

    timestamp: None or 'now' or datetime (default 'now')
      The timestamp to use to query the CAVE tables.
      If None, use the timestamp of the latest materialization.
      If 'now', use the current time.
      If datetime, use that time.

    raise_not_found: bool (default True)
      If no entry is found in the soma table for the given segID, raise an
      exception. Otherwise, return None.

    raise_not_found: bool (default True)
      If multiple entries are found in the soma table for the given segID,
      raise an exception. Otherwise, return all soma table entries

    Returns
    -------
    pd.DataFrame containing the soma table entries for the given segID(s).
    """
    try: iter(segids)
    except: segids = [segids]

    client = auth.get_caveclient()
    if timestamp in ['now', 'live']:
        timestamp = datetime.utcnow()
    elif timestamp is None:
        timestamp = client.materialize.get_timestamp()

    if not all(client.chunkedgraph.is_latest_roots(segids, timestamp=timestamp)):
        raise KeyError('A given ID(s) is not valid at the given timestamp.'
                       ' Use updated IDs or provide the timestamp where'
                       ' the ID(s) is valid.')

    if table in [None, 'default_soma_table']:
        table = client.info.get_datastack_info()['soma_table']
        select_columns = None  # Feature not currently supported on reference tables
    elif table in ['all', 'somas']:
        table = 'somas_dec2022'
    elif table in ['neurons', 'neuron']:
        table = 'neuron_somas_dec2022'
        select_columns = None  # Feature not currently supported on reference tables
    elif table == 'glia':
        table = 'glia_somas_dec2022'
        select_columns = None  # Feature not currently supported on reference tables
    somas = client.materialize.query_table(table,
                                           select_columns=select_columns,
                                           timestamp=timestamp)
    return somas.loc[somas.pt_root_id.isin(segids)]
# --- END KEY ATTRIBUTES SECTION --- #


# The code below implements a slower version of segid_from_pt that
# you should never need to run as long as the service is operational. If the
# service goes down, try using segid_from_pt_cv instead
class GSPointLoader(object):
    """Build up a list of points, then load them batched by chunk.
    This code is based on an implementation by
    `Peter Li<https://gist.github.com/chinasaur/5429ef3e0a60aa7a1c38801b0cbfe9bb>_.
    """

    def __init__(self, cloud_volume, point_resolution):
        """Initialize with zero points.
        See add_points to queue some.
        Parameters
        ----------
        cloud_volume:  cloudvolume.CloudVolume (SET AGGLOMERATE = FALSE for the cloudvolume object.)
        point_resolution:  iterable of 3 floats specifying the units in nm that
        the points are in.
        """

        CVtype = cloudvolume.frontends.precomputed.CloudVolumePrecomputed
        if not isinstance(cloud_volume, CVtype):
            raise TypeError('Expected CloudVolume, got "{}"'.format(type(cloud_volume)))

        self._volume = cloud_volume
        self._image_res = np.array(point_resolution)
        if not self._image_res.shape == (3,):
            raise TypeError('Expected point_resolution to be iterable of 3 floats')
        self._chunk_map = collections.defaultdict(set)
        self._points = None

    def add_points(self, points):
        """Add more points to be loaded.
        Parameters
        ----------
        points:     iterable of XYZ iterables
                    E.g. Nx3 ndarray.  Assumed to be in absolute units relative
                    to volume.scale['resolution'].
        """
        points_array = np.zeros([len(points), 3])
        for i in range(len(points_array)):
            points_array[i, :] = points[i]

        points = points_array

        if isinstance(self._points, type(None)):
            self._points = points
        else:
            self._points = np.concatenate(self._points, points)

        resolution = np.array(self._volume.scale['resolution']) / self._image_res
        chunk_size = np.array(self._volume.scale['chunk_sizes'])
        chunk_starts = (points // resolution).astype(int) // chunk_size * chunk_size
        for point, chunk_start in zip(points, chunk_starts):
            self._chunk_map[tuple(chunk_start)].add(tuple(point))

    def _load_chunk(self, chunk_start, chunk_end):
        # (No validation that this is a valid chunk_start.)
        return self._volume[chunk_start[0]:chunk_end[0],
               chunk_start[1]:chunk_end[1],
               chunk_start[2]:chunk_end[2]]

    def _load_points(self, chunk_map_key):
        chunk_start = np.array(chunk_map_key)
        points = np.array(list(self._chunk_map[chunk_map_key]))

        resolution = np.array(self._volume.scale['resolution']) / self._image_res
        indices = (points // resolution).astype(int) - chunk_start

        # We don't really need to load the whole chunk here:
        # Instead, we subset the chunk to the part that contains our points
        # This should at the very least save memory
        mn, mx = indices.min(axis=0), indices.max(axis=0)

        chunk_end = chunk_start + mx + 1
        chunk_start += mn
        indices -= mn

        chunk = self._load_chunk(chunk_start, chunk_end)
        return points, chunk[indices[:, 0], indices[:, 1], indices[:, 2]]

    def load_all(self, max_workers=4, return_sorted=True, progress=True):
        """Load all points in current list, batching by storage chunk.
        Parameters
        ----------
        max_workers:    int, optional
                        The max number of workers for parallel chunk requests.
        return_sorted:  bool, optional
                        If True, will order the returned data to match the order
                        of the points as they were added.
        progress:       bool, optional
                        Whether to show progress bar.
        Returns
        -------
        points:         np.ndarray
        data:           np.ndarray
                        Parallel Numpy arrays of the requested points from all
                        cumulative calls to add_points, and the corresponding
                        data loaded from volume.
        """
        progress_state = self._volume.progress
        self._volume.progress = False
        pbar = tqdm.tqdm(total=len(self._chunk_map),
                         desc='Segmentation IDs',
                         disable=not progress)
        with futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            point_futures = [ex.submit(self._load_points, k) for k in self._chunk_map]
            for f in futures.as_completed(point_futures):
                pbar.update(1)
        self._volume.progress = progress_state
        pbar.close()

        results = [f.result() for f in point_futures]

        if return_sorted:
            points_dict = dict(zip([tuple(p) for result in results for p in result[0]],
                                   [i for result in results for i in result[1]]))

            data = np.array([points_dict[tuple(p)] for p in self._points])
            points = self._points
        else:
            points = np.concatenate([result[0] for result in results])
            data = np.concatenate([result[1] for result in results])

        return points, data


def segid_from_pt_cv(points: 'Nx3 iterable',
                     cv=None,
                     n=100000,
                     max_tries=3,
                     return_roots=True,
                     max_workers=4,
                     progress=True,
                     timestamp=None):
    """
    Query a cloudvolume for root or supervoxel IDs.

    This method is slower than segid_from_pt, but does not depend on
    the supervoxel ID lookup service created by Eric Perlman and hosted on
    services.itanna.io. As such, this function might be useful if that service
    is not available for some reason.

    Arguments
    ---------
    points: Nx3 numpy array or pd.Series
      Point or points to query, in xyz order and in mip0 coordinates.
    cv: cloudvolume.CloudVolume or None
      The cloudvolume object to query. If None, will query from the
      latest proofread FANC segmentation.
    n: int (default 100,000)
      number of coordinates to query in a single batch. Default is 100000,
      which seems to prevent server errors.
    max_tries: int (default 3)
      number of attempts per batch. Usually if it fails 3 times, something is
      wrong and more attempts won't work.
    return_roots: bool (detault True)
      If True, will look up root ids from supervoxel ids. Otherwise, supervoxel
      ids will be returned.

    Returns
    -------
    root IDs or supervoxel IDs for queried coordinates as int64
    """
    if cv is None:
        cv = auth.get_cloudvolume()
    if hasattr(cv, 'agglomerate'):
        cv.agglomerate = False

    if isinstance(points, pd.Series):
        points = np.vstack(points)

    if len(points) == 3:
        try: iter(points[0])
        except:
            return segid_from_pt_cv(
                [points], cv=cv, n=n, max_tries=max_tries,
                return_roots=return_roots, max_workers=max_workers,
                progress=progress, timestamp=timestamp
            )[0]

    points = np.array(points, dtype=np.uint32)
    if points.ndim == 1:
        points = points.reshape(-1, 3)

    sv_ids = []
    failed = []
    bins = np.array_split(np.arange(0, len(points)), np.ceil(len(points) / 10000))

    # This import is delayed because it triggers creation of a CAVEclient
    # and a somewhat slow API call, which I don't want to do until this
    # function is called
    from . import ngl_info

    for i in bins:
        pt_loader = GSPointLoader(cv, ngl_info.voxel_size)
        pt_loader.add_points(points[i])
        try:
            chunk_ids = pt_loader.load_all(max_workers=max_workers, progress=progress)[1].reshape(len(points[i]), )
            sv_ids.append(chunk_ids)
        except:
            print('Failed, retrying')
            fail_check = 1
            while fail_check < max_tries:
                try:
                    chunk_ids = pt_loader.load_all(max_workers=max_workers, progress=progress)[1].reshape(len(points[i]), )
                    sv_ids.append(chunk_ids)
                    fail_check = max_tries + 1
                except:
                    print('Fail: {}'.format(fail_check))
                    fail_check += 1

            if fail_check == max_tries:
                failed.append(i)
    sv_ids = np.concatenate(sv_ids)

    if return_roots:
        return cv.get_roots(sv_ids, timestamp=timestamp).astype(np.int64)
    else:
        return sv_ids.astype(np.int64)
