#!/usr/bin/env python3
"""
Upload data to CAVE tables

See some examples at https://github.com/htem/FANC_auto_recon/blob/main/example_notebooks/update_cave_tables.ipynb
"""

from datetime import datetime
from textwrap import dedent

import numpy as np
import pandas as pd
from requests.exceptions import HTTPError
from caveclient import CAVEclient
from caveclient.chunkedgraph import root_id_int_list_check
from cloudvolume import CloudVolume
from cloudvolume.lib import green, red

from . import annotations, auth, lookup, statebuilder


def new_cell(pt_position,
             pt_type: ['soma', 'peripheral nerve', 'neck connective', 'cut-off soma', 'orphan'],
             cell_type: ['motor', 'efferent', 'sensory', 'descending', 'ascending', 'central', 'glia'],
             user_id: int,
             cell_ids_table='cell_ids',
             add_to_soma_table=False,
             fake=True):
    """
    Add a new cell to the cell_ids table, annotate its type, and optionally add
    it to the soma table.
    """
    client = auth.get_caveclient()
    cell_ids = client.materialize.live_live_query(cell_ids_table, timestamp=datetime.utcnow())
    segid = lookup.segid_from_pt(pt_position)
    if segid == 0:
        raise ValueError(f'Point {pt_position} is a location with no segmentation')
    if segid in cell_ids.pt_root_id.values:
        raise ValueError(f"Segment {segid} already has a cell ID, {cell_ids.loc[cell_ids.pt_root_id == segid, 'id'].values[0]}")
    if pt_type not in ['soma', 'peripheral nerve', 'neck connective', 'cut-off soma', 'orphan']:
        raise ValueError(f'pt_type {pt_type} is not valid')
    start_ids = {
        'motor': 100,
        'efferent': 100,
        'sensory': 1000,
        'descending': 10_000,
        'ascending': 12_000,
        'central': 15_000,
        'glia': 100_000
    }
    if cell_type not in start_ids.keys():
        raise ValueError(f'cell_type {cell_type} is not valid')
    start_id = start_ids[cell_type]
    # Annotations that were deleted aren't materialized so they won't be in the
    # cell_ids dataframe, but new annotations can't re-use their IDs.
    deleted_cell_ids = [1815, 10552, 10766, 13325, 25983, 100000]
    while start_id in cell_ids['id'].values or start_id in deleted_cell_ids:
        start_id += 1
    stage = client.annotation.stage_annotations(cell_ids_table, id_field=True)
    stage.add(id=start_id,
              pt_position=np.array(pt_position),
              tag=pt_type,
              valid=True)

    if add_to_soma_table:
        if pt_type not in ['soma', 'cut-off soma']:
            raise ValueError(f'pt_type {pt_type} is not valid for adding to soma table')
        if not fake:
            try:
                if cell_type == 'glia':
                    add_soma(pt_position, is_neuron=False)
                else:
                    add_soma(pt_position, is_neuron=True)
            except ValueError as e:
                print(type(e))
                print(e)

    def try_annotate_neuron(*args, **kwargs):
        try:
            annotate_neuron(*args, **kwargs)
        except ValueError as e:
            print(type(e))
            print(e)

    if fake:
        if add_to_soma_table:
            print(f'FAKE – would add new soma table entry and cell_id for {cell_type} neuron:')
        else:
            print(f'FAKE – would new cell_id for {cell_type} neuron:')
        print(stage.annotation_dataframe)
    else:
        response = client.annotation.upload_staged_annotations(stage)
        print('New cell ID posted:', response)
        if cell_type == 'glia':
            return
        if cell_type == 'motor':
            try_annotate_neuron(segid, 'primary class', 'motor neuron', user_id)
        if cell_type == 'efferent':
            try_annotate_neuron(segid, 'primary class', 'efferent non-motor neuron', user_id)
        elif cell_type == 'sensory':
            try_annotate_neuron(segid, 'primary class', 'sensory neuron', user_id)
        elif cell_type == 'descending':
            try_annotate_neuron(segid, 'primary class', 'central neuron', user_id)
            try_annotate_neuron(segid, 'anterior-posterior projection pattern', 'descending', user_id)
        elif cell_type == 'ascending':
            try_annotate_neuron(segid, 'primary class', 'central neuron', user_id)
            try_annotate_neuron(segid, 'anterior-posterior projection pattern', 'ascending', user_id)
        elif cell_type == 'central':
            try_annotate_neuron(segid, 'primary class', 'central neuron', user_id)


def annotate_neuron(neuron: 'segID (int) or point (xyz)',
                    annotation: str or tuple[str, str],
                    user_id: int,
                    table_name='cell_info',
                    convert_given_point_to_anchor_point=True,
                    resolve_duplicate_anchor_points=False) -> dict:
    """
    Upload information about a neuron to a CAVE table.

    This function will first check that `annotation` is a valid
    annotation for the given table, according to the rules described at
    https://github.com/htem/FANC_auto_recon/wiki/Neuron-annotations#neuron_information
    If it is, the annotation will be posted to the table.

    This function is designed for use with tables with one of these schemas:
    - "bound_tag_user", in which case `annotation` should be a single annotation
    - "bound_double_tag_user", in which case `annotation` should be a pair of
      annotations, either as a colon-separated string formatted like
      "annotation_class: annotation", or as a 2-tuple of strings in the order
      (annotation_class, annotation).

    Arguments
    ---------
    neuron: int OR 3-length iterable of ints/floats
        Segment ID or point coordinate of a neuron to upload information about

    annotation: str OR 2-tuple of (str, str)
        Annotation to upload, or a pair of annotations if trying to upload to a
        table with two tag columns. See the docstring of
        `fanc.annotations.parse_annotation_pair()` for options on how to format
        an annotation pair.

    user_id: int
        The CAVE user ID number to associate with this annotation

    table_name: str
        Name of the CAVE table to upload information to. Only works
        with tables of schema "bound_tag_user" or "bound_double_tag_user".

    convert_given_point_to_anchor_point: bool
        Only matters if `neuron` is a point (not a segment ID).
        If False, the given point will just be used directly as the
        annotation's point. If True, the point used for the annotation will
        instead be the anchor point (see `lookup.anchor_point()`) of the
        segment corresponding to the given point.

    resolve_duplicate_anchor_points: bool or int
        This argument is passed to `lookup.anchor_point`, see its
        docstring for details.

    Returns
    -------
    list: Response from server containing information about the
          success or failure of the upload. If successful, the list
          contains the ID of the new annotation.
    """
    client = auth.get_caveclient()
    if isinstance(neuron, (int, np.integer)):
        if not client.chunkedgraph.is_latest_roots(int(neuron)):
            raise ValueError(f'{neuron} is not a current segment ID.')
        segid = neuron
        point = lookup.anchor_point(neuron, resolve_duplicates=resolve_duplicate_anchor_points)
    else:
        try:
            iter(neuron)
            segid = lookup.segid_from_pt(neuron)
            if segid == 0:
                raise ValueError(f'Point {neuron} is a location with no segmentation.')
            if convert_given_point_to_anchor_point:
                point = lookup.anchor_point(segid, resolve_duplicates=resolve_duplicate_anchor_points)
                print(f'Found segID {segid} with anchor point {point}.')
            else:
                point = np.array(neuron)
        except TypeError:
            raise TypeError('First argument must be a segID or a point coordinate.')
    if not isinstance(user_id, (int, np.integer)):
        raise TypeError(f'user_id must be an integer but got "{user_id}".')

    stage = client.annotation.stage_annotations(table_name)
    if not annotations.is_allowed_to_post(segid, annotation,
                                          table_name=table_name,
                                          raise_errors=True):
        raise ValueError(f'"{annotation}" is not allowed to be posted to'
                         f' segment {segid} in table "{table_name}".')

    if 'tag2' in stage.fields:
        annotation = annotations.parse_annotation_pair(annotation)

    if isinstance(annotation, tuple):
        assert len(annotation) == 2
        stage.add(pt_position=point,
                  tag=annotation[1],
                  tag2=annotation[0],
                  user_id=user_id)
    elif isinstance(annotation, str):
        stage.add(pt_position=point,
                  tag=annotation,
                  user_id=user_id)
    else:
        raise TypeError('annotation must be a string or a tuple of 2 strings')

    response = client.annotation.upload_staged_annotations(stage)
    if isinstance(response, list) and len(response) == 1:
        return response[0]
    else:
        return response


def xyz_StringSeries2List(StringSeries: pd.Series):
    pts = StringSeries.str.strip('()').str.split(',',expand=True)
    return pts.astype(int).values.tolist()


class SomaTableOrganizer(object):
    def __init__(
        self,
        client=None
    ):
        self._client = client

    def initialize(self,
                   soma_table_name="",
                   subset_table_name=""):
        """
        Set soma table and subset table you want to edit.

        ---Arguments---
        soma_table_name: string
            Name of soma table you want to edit. If "" (default), this will
            be set to the most recent soma table on CAVE: 'soma_mmmYYYY'
        subset_table_name: string
            Name of subset table you want to edit. You can choose from either
            the name of cell types ("neuron", "glia") or the name of subset tables
            on CAVE: 'celltype_soma_mmmYYYY'
        """
        if soma_table_name != "":
            self._soma_table_name = soma_table_name
        else:
            self._soma_table_name = self._client.info.get_datastack_info()['soma_table'].split("neuron_")[-1]

        self._subset_table_dict = {"neuron": "neuron_" + self._soma_table_name, "glia": "glia_" + self._soma_table_name}

        self._voxel_size = [self._client.info.get_datastack_info()['viewer_resolution_x'],
                            self._client.info.get_datastack_info()['viewer_resolution_y'],
                            self._client.info.get_datastack_info()['viewer_resolution_z']]

        if subset_table_name in list(self._subset_table_dict.keys()):
            self._subset_table_name = self._subset_table_dict[subset_table_name]
        elif subset_table_name in list(self._subset_table_dict.values()):
            self._subset_table_name = subset_table_name
        else:
            raise ValueError("Need name of subset or subset table name. Choose from {}.".format(self._subset_table_dict))

        self.update_tables()
        txt_msg = """\
            Ready to update soma table: {} and subset soma table: {}
            Please make sure you have separate soma in each annotation and have all information required: {}.
            When you upload somas locating outside the dataset, use the coordinates on the final slice.""".format(self._soma_table_name, self._subset_table_name, self._required_props())
        print(dedent(txt_msg))

    @property
    def soma_table_name(self):
        return self._soma_table_name

    @soma_table_name.setter
    def soma_table_name(self, value):
        self._soma_table_name = value

    @property
    def subset_table_name(self):
        return self._subset_table_name

    @subset_table_name.setter
    def subset_table_name(self, value):
        self._subset_table_name = value

    @property
    def soma_table(self):
        return self._soma_table

    @property
    def subset_table(self):
        return self._subset_table

    @property
    def subset_table_dict(self):
        return self._subset_table_dict

    @subset_table_dict.setter
    def subset_table_dict(self, value):
        self._subset_table_dict = value

    def _required_props(self):
        return self._client.schema.schema_definition('nucleus_detection')['definitions']['NucleusDetection']['required']

    def add_radius_column(self, soma_table):
        if ('bb_start_position' not in soma_table.columns) or ('bb_end_position' not in soma_table.columns):
            raise ValueError("Need 'bb_start_position' and 'bb_end_position' columns.")

        soma_table['radius_nm'] = 0
        for i, r in soma_table.iterrows():
            if soma_table['bb_start_position'][i] is not np.nan and soma_table['bb_end_position'][i] is not np.nan:
                dist = np.array(soma_table['bb_end_position'][i]) - np.array(soma_table['bb_start_position'][i])
                soma_table.at[i,'radius_nm'] = np.linalg.norm(dist[:2])/2 # distance in nm in xy plane
            else:
                soma_table.at[i,'radius_nm'] = 10 # np.nan
        return soma_table

    @staticmethod
    def find_manual_ids(existing_ids, initial_digit=1):
        initials = [int(str(i)[0]) for i in existing_ids]
        idx = np.where(np.array(initials)==initial_digit)
        return existing_ids[idx]

    def _get_man_id(self, initial_digit=1, digit=17):
        ExistingID = self.find_manual_ids(self._soma_table.id.values, initial_digit=1)
        if len(ExistingID) >0:
            MaxExistingID = np.max(ExistingID)
        else:
            MaxExistingID = initial_digit*10**(digit-1)
        return MaxExistingID + 1

    def _get_man_id_column(self, length, initial_digit=1, digit=17):
        ExistingID = self.find_manual_ids(self._soma_table.id.values, initial_digit=1)
        if len(ExistingID) >0:
            MaxExistingID = np.max(ExistingID)
        else:
            MaxExistingID =initial_digit*10**(digit-1)
        return [MaxExistingID + i for i in range(1, 1+length)]

    def _check_change(self, table_name, timestamp=datetime.utcnow()):
        try:
            return self._client.materialize.live_live_query(table_name, timestamp, allow_missing_lookups=False).reset_index(level=0)
        except HTTPError as e:
            raise UpdateUnsuccessful(red(e.response.text + "Please check after 1 hour. Only works between 10 AM - 12 AM PST."))

    def update_tables(self, timestamp=datetime.utcnow()):
        """
        Update both soma table and subset table to the most recent version. Will give
        an error if newly added points are not ingested yet.
        """
        self._soma_table = self._check_change(self._soma_table_name, timestamp)
        self._subset_table = self._check_change(self._subset_table_name, timestamp)

    def _validate(self, df):
        stage = self._client.annotation.stage_annotations(self._soma_table_name, schema_name="nucleus_detection", id_field=True)
        stage.add_dataframe(df) # check whether the df has necessary columns
        stage.clear_annotations()

        svIDs = lookup.svid_from_pt(df.pt_position)
        rIDs = root_id_int_list_check(self._client.chunkedgraph.get_roots(svIDs))

        overlap = np.isin(rIDs, root_id_int_list_check(self._soma_table.pt_root_id.values))
        if sum(overlap) == 0:
            pass
        else:
            raise UploadUnsuccessful("The information below has root ids that are already registed in soma table. \n {}".format(df.drop(columns=['id'])[overlap].to_string()))

    def join_table(self):
        return self._subset_table.join(self._soma_table.set_index('id'), on='target_id', lsuffix='_subset', rsuffix='_soma')

    def preview(self, asPoint=True, asSphere=False):
        """
        Generate Neuroglancer link to inspect somata on the subset table.

        ---Arguments---
        asPoint: bool (default True)
            If True, produce an annotation layer that has all the subset somas as points
        asSphere: bool (default True)
            If True, produce an annotation layer that has all the subset somas as sheperes.
            Their radius are estimated based on their bounding boxes in nanometers.

        ---Returns---
        Neuroglancer url (as a string)
        """

        joined = self.join_table()
        st = joined.reindex(columns=['id', 'pt_root_id', 'pt_position', 'bb_start_position', 'bb_end_position'])

        annotations = []
        if asPoint == True and asSphere == False:
            LayerName = '{}_pt_{}'.format(self.subset_table_name, datetime.now().strftime("%Y%m%d"))
            annotations.append({'name':LayerName,'type':'points','data': st})
        elif asPoint == False and asSphere == True:
            LayerName = '{}_sp_{}'.format(self.subset_table_name, datetime.now().strftime("%Y%m%d"))
            st_r = self.add_radius_column(st)
            annotations.append({'name':LayerName,'type':'spheres','data': st_r})
        else:
            raise ValueError("Either asPoint or asSphere should be True")

        print(statebuilder.render_scene(annotations=annotations,
                                        nuclei=st.id.values,
                                        client=self._client,
                                        annotation_units='voxels'))

    def add_dataframe(self, df: pd.DataFrame, batch_size=10000):
        """
        Add dataframe to both soma table and subset table.

        ---Arguments---
        df: pandas.DataFrame
            A dataframe with coordinates of new somas that you want to upload
        batch_size: int (default 10000)
            How many annotations you upload in each batch. The CAVE server does not
            allow users to upload more than 10000 annotations at a time.
        """
        print("Checking the format of your table...")
        self.update_tables()
        df_i = df.reset_index(drop=True).astype({'id': np.int64})
        id_missing_idx = np.where(df_i['id'] == 0)[0]

        new_man_ids = self._get_man_id_column(len(id_missing_idx))
        new_nuc_ids = lookup.nucleusid_from_pt(df_i['pt_position'].loc[id_missing_idx])
        j=0
        for i, idx in enumerate(id_missing_idx):
            if new_nuc_ids[i] != 0:
                df_i.at[idx, 'id'] = new_nuc_ids[i]
            else:
                df_i.at[idx, 'id'] = new_man_ids[j]
                j += 1
        self._validate(df_i)
        print("Ready to upload...")

        if len(df_i) <= 10000:
            stage = self._client.annotation.stage_annotations(self._soma_table_name, schema_name="nucleus_detection", id_field=True)
            stage.add_dataframe(df_i)
            self._client.annotation.upload_staged_annotations(stage)
            stage.clear_annotations()

            df_is = df_i.reindex(columns=['id'])
            df_is['target_id'] = df_is['id']
            # df_is = df_is.rename(columns={'id': 'target_id'})
            stage = self._client.annotation.stage_annotations(self._subset_table_name, schema_name="simple_reference", id_field=True)
            stage.add_dataframe(df_is)
            self._client.annotation.upload_staged_annotations(stage)
            stage.clear_annotations()

        else:
            minidfs = [df_i.loc[i:i+batch_size-1, :] for i in range(0, len(df_i), batch_size)]
            stage = self._client.annotation.stage_annotations(self._soma_table_name, schema_name="nucleus_detection", id_field=True)
            for dftmp in minidfs:
                stage.add_dataframe(dftmp)
                self._client.annotation.upload_staged_annotations(stage)
                stage.clear_annotations()

            df_is = df_i.reindex(columns=['id'])
            df_is['target_id'] = df_is['id']
            # df_is = df_is.rename(columns={'id': 'target_id'})
            minidfs = [df_is.loc[i:i+batch_size-1, :] for i in range(0, len(df_is), batch_size)]
            stage = self._client.annotation.stage_annotations(self._subset_table_name, schema_name="simple_reference", id_field=True)
            for dftmp in minidfs:
                stage.add_dataframe(dftmp)
                self._client.annotation.upload_staged_annotations(stage)
                stage.clear_annotations()

        # self.update_tables()
        print(green("Successfully uploaded!"))


def update_verified_nuclei_layer(point, cube_size_microns=16):
    """
    Update the verified nuclei segmentation layer.

    This is typically called just after the user has added a new annotation to
    the soma table, for example through `add_soma()`, to make the nucleus of
    this new soma appear in the "nuclei (verified)" layer.
    The user provides a point in the nucleus, then this function updates the
    nucleus segmentation layer in a reasonably large cube surrounding the given
    point to make sure the full nucleus is transferred.

    Arguments
    ---------
    point: 3-length iterable
        A coordinate inside the nucleus. In xyz order, in units of the FANC
        image data's voxels (that is, voxels at 4.3x4.3x45nm resolution –
        note that the nucleus segmentation layer's voxel size is
        68.8x68.8x45nm, so the voxel coordinate that the user gives from the
        FANC image data will be divided by 16 to get the corresponding voxel
        coordinate in the nucleus segmentation layer).

    Returns
    -------
    Nothing
    """
    all_nuclei = CloudVolume('gs://lee-lab_female-adult-nerve-cord/alignmentV4/nuclei/nuclei_seg_Mar2022')
    verified_nuclei = CloudVolume('gs://lee-lab_female-adult-nerve-cord/alignmentV4/nuclei/nuclei_seg_Mar2022_verified')
    assert all(all_nuclei.chunk_size == verified_nuclei.chunk_size)
    assert all(all_nuclei.resolution == verified_nuclei.resolution)
    assert all_nuclei.bounds == verified_nuclei.bounds
    chunk_size = all_nuclei.chunk_size
    bounds = all_nuclei.bounds
    cube_size_nm = cube_size_microns * 1000
    cube_size_voxels = cube_size_nm / np.array(all_nuclei.resolution)

    soma_table = auth.get_caveclient().materialize.live_live_query('somas_dec2022', datetime.utcnow())
    verified_ids = set(soma_table.loc[soma_table['id'] > 20000000000000000, 'id'])
    verified_ids.add(0)

    def update_chunk(x_slice, y_slice, z_slice,
                     valid_ids=verified_ids,
                     verbose=False):
        """
        Process a given range of the nuclei predictions, removing invalid ids
        from all_nuclei and saving the result to the same location within
        verified_nuclei.
        """
        if not isinstance(valid_ids, set):
            raise TypeError('valid_ids must be a set but was {}'.format(type(valid_ids)))

        data = np.array(all_nuclei[x_slice, y_slice, z_slice])

        if verbose: print('Running ravel & unique')
        unique_values = pd.unique(data.ravel())
        if verbose: print('Checking ids for validity')
        invalid_values = [i for i in unique_values if i not in valid_ids]
        if verbose: print('Removing invalid ids from data')
        data[np.isin(data, invalid_values)] = 0

        # Upload result
        verified_nuclei[x_slice, y_slice, z_slice] = data

    point_mip4 = np.array(point) / (16, 16, 1)
    # Find the start of the cube, rounding down to the nearest chunk boundary
    x_start = (point_mip4[0] - cube_size_voxels[0] // 2 - bounds.minpt[0]) // chunk_size[0] * chunk_size[0] + bounds.minpt[0]
    y_start = (point_mip4[1] - cube_size_voxels[1] // 2 - bounds.minpt[1]) // chunk_size[1] * chunk_size[1] + bounds.minpt[1]
    z_start = (point_mip4[2] - cube_size_voxels[2] // 2 - bounds.minpt[2]) // chunk_size[2] * chunk_size[2] + bounds.minpt[2]
    # Find the end of the cube, rounding up to the nearest chunk boundary
    x_end = ((point_mip4[0] + cube_size_voxels[0] // 2 - bounds.minpt[0]) // chunk_size[0] + 1) * chunk_size[0] + bounds.minpt[0]
    y_end = ((point_mip4[1] + cube_size_voxels[1] // 2 - bounds.minpt[1]) // chunk_size[1] + 1) * chunk_size[1] + bounds.minpt[1]
    z_end = ((point_mip4[2] + cube_size_voxels[2] // 2 - bounds.minpt[2]) // chunk_size[2] + 1) * chunk_size[2] + bounds.minpt[2]
    # Make sure we don't go outside the bounds of the volume
    x_start = max(bounds.minpt[0], int(x_start))
    y_start = max(bounds.minpt[1], int(y_start))
    z_start = max(bounds.minpt[2], int(z_start))
    x_end = min(bounds.maxpt[0] - chunk_size[0], int(x_end))
    y_end = min(bounds.maxpt[1] - chunk_size[1], int(y_end))
    z_end = min(bounds.maxpt[2] - chunk_size[2], int(z_end))
    print('Updating nucleus segmentation from {} to {}...'.format((x_start, y_start, z_start), (x_end, y_end, z_end)))
    for x in range(x_start, x_end, chunk_size[0]):
        for y in range(y_start, y_end, chunk_size[1]):
            for z in range(z_start, z_end, chunk_size[2]):
                update_chunk(slice(x, x + chunk_size[0]),
                             slice(y, y + chunk_size[1]),
                             slice(z, z + chunk_size[2]))
    print('Done updating nucleus segmentation.')


def add_soma(point=None, is_neuron=True, nucleus_id=None):
    """
    Upload one new soma to a corresponding CAVE table.

    Arguments
    ---------
    point: 3-length iterable
        A point coordinate of a soma to upload, in xyz order.
        This point:
        - must be in the segmentation (that is, not in a location
          where the segmentation is 0 due to knifemarks).
        - should be as close to the center of the neuron's
          nucleus as possible.
        - does NOT have to overlap with the nucleus_id object
          that you specify (optional, see below).

    is_neuron: bool
        Whether the soma belongs to a neuron (True) or a glia (False).

    nucleus_id: int or np.uint64
        An ID of an object in the FANC nucleus segmentation
        (precomputed://gs://lee-lab_female-adult-nerve-cord/alignmentV4/nuclei/nuclei_seg_Mar2022)
        to represent this soma. If left as None, this function will try looking
        in the nucleus segmentation at the provided point coordinate for a
        nucleus ID to use. If there is no nucleus segmentation there, a
        "meaningless" ID (that doesn't correspond to any object in the nucleus
        segmentation) will be used for the soma annotation instead.
    """
    sto = SomaTableOrganizer(client=auth.get_caveclient())
    if is_neuron:
        sto.initialize(subset_table_name='neuron')
    else:
        sto.initialize(subset_table_name='glia')
    upload_df = pd.DataFrame(columns=['pt_position', 'id']).astype({'id': np.int64})
    point = np.array(point)
    if nucleus_id is not None:
        upload_df.loc[0] = [point, nucleus_id]
    else:
        upload_df.loc[0] = [point, 0]
    sto.add_dataframe(upload_df)

    update_verified_nuclei_layer(point)


def add_soma_df(points: pd.DataFrame, is_neuron=True, pt_position_column='pt_position', id_column='id'):
    """
    Upload multiple new soma to a corresponding CAVE table.

    Arguments
    ---------
    points: pd.DataFrame
        Point coordinates (with or without IDs that you want to use) of somata to upload

    is_neuron: bool
        True, if it is neuron

    pt_position_column: str
        If points has a column of point coordinates and use a non-standarized name (i.e., not 'pt_position'),
        you need to tell the name of the column to this code.

    id_column: str
        If points has a column of IDs and use a non-standarized name (i.e., not 'id'),  you need to tell the
        name of the column to this code. If you don't have preference, you can use np.nan (by default).
        The code then will check the nucleus IDs by looking up the same coordinates on the nucleus segmentation,
        and use the nucleus IDs that it finds. If it cannot find anything, then the code will generate
        "meaningless" artificial annotation IDs for this soma.
    """
    sto = SomaTableOrganizer(client=auth.get_caveclient())
    if is_neuron:
        sto.initialize(subset_table_name='neuron')
    else:
        sto.initialize(subset_table_name='glia')

    if len(points.columns)<2:
        points['id'] = np.nan

    points = points.rename(columns={pt_position_column: 'pt_position', id_column: 'id'})
    sto.add_dataframe(points)
    # transfer_segmentation()


class UploadUnsuccessful(Exception):
    def __init__(self, message):
        super().__init__(red("Uploading failed. ") + message)


class UpdateUnsuccessful(Exception):
    def __init__(self, message):
        super().__init__(red("Updating failed. ") + message)
