#!/usr/bin/env python3

from datetime import datetime, timezone

import numpy as np
import pandas as pd

import fanc


def test_lookup():
    pts = np.array([[48848, 114737, 2690],
                    [49198, 114622, 2690]])
    jan2022 = datetime(2022, 1, 1, tzinfo=timezone.utc)
    july2023 = datetime(2023, 7, 30, tzinfo=timezone.utc)

    # Supervoxel IDs
    print('fanc.lookup: Test supervoxel ID lookup')
    assert isinstance(fanc.lookup.svid_from_pt(pts[0, :]), int)
    assert isinstance(fanc.lookup.svid_from_pt(pts), list)
    assert fanc.lookup.svid_from_pt(list(pts[0, :])) == 73679924787396631
    assert fanc.lookup.svid_from_pt(tuple(pts[0, :])) == 73679924787396631
    assert fanc.lookup.svid_from_pt(pts) == [73679924787396631, 73750224812092331]

    # Segment IDs
    print('fanc.lookup: Test segment ID lookup')
    assert isinstance(fanc.lookup.segid_from_pt(pts[0, :]), np.int64)
    assert isinstance(fanc.lookup.segid_from_pt(pts), np.ndarray)
    assert all(fanc.lookup.segid_from_pt(pts, timestamp=jan2022) == np.array([648518346494405175, 648518346502740211], dtype=np.int64))
    assert all(fanc.lookup.segid_from_pt(pts) != np.array([648518346494405175, 648518346502740211], dtype=np.int64))
    assert all(fanc.lookup.segid_from_pt(pts, timestamp=july2023) == np.array([648518346486614449, 648518346489747799], dtype=np.int64))

    # Cell IDs
    print('fanc.lookup: Test cell ID lookup')
    assert fanc.lookup.cellid_from_segid(648518346486614449, timestamp=july2023) == 12967
    assert fanc.lookup.cellid_from_segid([648518346486614449, 648518346486614449], timestamp=july2023) == [12967, 12967]
    assert fanc.lookup.cellid_from_segid([648518346486614449, 648518346489747799], timestamp=july2023) == [12967, 17206]
    assert fanc.lookup.segid_from_cellid(12967, timestamp=july2023) == 648518346486614449
    assert fanc.lookup.segid_from_cellid([12967, 12967], timestamp=july2023) == [648518346486614449, 648518346486614449]
    assert fanc.lookup.segid_from_cellid([12967, 17206], timestamp=july2023) == [648518346486614449, 648518346489747799]

    # Somas
    print('fanc.lookup: Test soma lookup')
    soma = fanc.lookup.soma_from_segid(648518346486614449, timestamp=july2023)
    assert isinstance(soma, pd.DataFrame)
    assert soma.shape == (1, 13)
    assert all(soma.pt_position.values[0] == np.array((43232, 134024, 4218)))
    assert soma['id'].values[0] == 72763481576702247

    print('fanc.lookup: PASS')


def test_annotations():

    table = 'neuron_information'
    assert fanc.annotations.is_valid_annotation(('primary class', 'motor neuron'), table_name=table)
    assert fanc.annotations.is_valid_annotation('primary class: motor neuron', table_name=table)
    assert fanc.annotations.is_valid_annotation('primary class > motor neuron', table_name=table)
    assert fanc.annotations.is_valid_annotation('primary class, motor neuron', table_name=table)
    assert fanc.annotations.is_valid_annotation('primary class, motor neuron', table_name=table)
    assert fanc.annotations.is_valid_annotation('neuron identity: foo', table_name=table)

    assert not fanc.annotations.is_valid_annotation(None, table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation('', table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation('foo', table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation('motor neuron: primary class', table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation('motor neuron > primary class', table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation('motor neuron, primary class', table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation(('motor neuron', 'primary class'), table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation('primary class: leg motor neuron', table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation('leg motor neuron: primary class', table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation('leg motor neuron: motor neuron', table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation('neuron identity: sensory neuron', table_name=table, raise_errors=False)

    segid = fanc.lookup.segid_from_pt((48848, 114737, 2690))
    assert not fanc.annotations.is_allowed_to_post(segid, 'neuron identity: sensory neuron', table_name=table, raise_errors=False)
    assert not fanc.annotations.is_allowed_to_post(segid, 'primary class: sensory neuron', table_name=table, raise_errors=False)

    table = 'proofreading_notes'
    assert fanc.annotations.is_valid_annotation('no major merge errors', table_name=table)
    try:
        fanc.annotations.is_valid_annotation(None, table_name=table, raise_errors=False)
        assert False
    except TypeError:
        pass
    assert not fanc.annotations.is_valid_annotation('', table_name=table, raise_errors=False)
    assert not fanc.annotations.is_valid_annotation('n mjr mrg rrrs', table_name=table, raise_errors=False)


def test_false():
    assert 0 == 1


if __name__ == '__main__':
#    test_lookup()
#    print('test_lookup: PASS')
    test_annotations()
    print('test_annotations: PASS')
    print('All tests passed')

