#!/usr/bin/env python3
"""
Create a json file listing the segment IDs and abbreviations/names
of each neuropil, in a format that neuroglancer recognizes, then
upload it to a Google Cloud bucket in the appropriate location.
"""

import json

from google.cloud import storage
from google.cloud.exceptions import NotFound

info = [
    ('1', 'FANC outline'),
    ('2', 'VNC neuropil'),
    ('4633', 'DLT'),
    ('4634', 'DLV'),
    ('4635', 'DMT'),
    ('4636', 'MDT'),
    ('4637', 'VLT'),
    ('4638', 'ITD'),
    ('4639', 'CFF'),
    ('4640', 'ITD halt. chi.'),
    ('4641', 'ITD halt. tr.'),
    ('4642', 'VTV'),
    ('4643', 'ANm'),
    ('4644', 'AMNp'),
    ('4645', 'HTct'),
    ('4646', 'IntTct'),
    ('4647', 'LTct'),
    ('4648', 'MesoNm'),
    ('4649', 'MetaNm'),
    ('4650', 'mVAC'),
    ('4651', 'NTct'),
    ('4652', 'ProNm'),
    ('4653', 'WTct'),
]

client = storage.Client(project='prime-sunset-531')
bucket = client.bucket('lee-lab_female-adult-nerve-cord')
blobs = [bucket.blob('alignmentV4/volume_meshes/segment_properties/info'),
         bucket.blob('VNC_templates/JRC2018_VNC_FEMALE/volume_meshes/segment_properties/info')]


def make_segment_properties(info: list):
    segment_properties = {
        "@type": "neuroglancer_segment_properties",
        "inline": {"ids": [],
                   "properties": [{"id": "mesh",
                                   "type": "label",
                                   "values": []}]}
    }

    def add_label(segment_properties, segid, label):
        segment_properties['inline']['ids'].append(str(segid))
        segment_properties['inline']['properties'][0]['values'].append(label)

    for segid, label in info:
        add_label(segment_properties, segid, label)

    return segment_properties



segment_properties = make_segment_properties(info)
print(json.dumps(segment_properties, indent=2))
for blob in blobs:
    try:
        blob.reload()
        print(f'Blob {blob.name} already exists, skipping')
    except NotFound:
        blob.upload_from_string(
            json.dumps(segment_properties, indent=2),
            content_type='application/json'
        )
        print('Uploaded segment properties to', blob.name)
