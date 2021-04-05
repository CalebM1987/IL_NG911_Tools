import itertools
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from ilng911.utils.json_helpers import write_json_file
from ilng911.env import NG_911_DIR

ATTRIBUTES = ['field_name', 'field_alias', 'field_type', 'field_length', 'field_category']
PROPERTIES = [f.split('_')[1] for f in ATTRIBUTES[:-1]]

LAYERS = dict(
    RoadCenterline='esriGeometryPolyline',
    AddressPoint='esriGeometryPoint',
    PSAP='esriGeometryPolygon',
    ProvisioningBoundary='esriGeometryPolygon'
)

MAPPING = dict(
    Text='esriFieldTypeString',
    Short='esriFieldTpeSmallInteger',
    Integer='esriFieldTypeInteger',
    Date='esriFieldTypeDate',
    Double='esriFieldTypeDouble',
    Single='esriFieldTypeSingle'
)

get_field_type = lambda x: MAPPING.get(x, 'TEXT')

def pdf_schema_to_json(text, layer, group_length=5):
    fields, fieldInfos = [], []

    parts = text.split('\n')

    # form fields for feature set
    for i in range(int(len(parts) / group_length)):
        group = list(itertools.islice(parts, i*group_length, (i*group_length) + group_length))
        group[0] = group[0].replace('*', '')
        group[3] = int(group[3]) if group[2] == 'Text' else None
        group[2] = get_field_type(group[2])
        fields.append(dict(zip(PROPERTIES, group[:-1])))
        # assign feature category
        fieldInfos.append(
            dict(
                name=group[0],
                category=group[-1],
                # TODO: assign domain
                domain=None
            )
        )
    
    # form feature set
    fs = dict(
        geometryType=LAYERS.get(layer),
        spatialReference=dict(
            wkid=4326
        ),
        fields=fields,
        features=[]
    )
    out_file = os.path.join(NG_911_DIR, 'schemas', '_schemas', layer)
    print(out_file)
    config = dict(
        layer=layer,
        fieldInfos=fieldInfos,
        featureSet=fs
    )
    write_json_file(config, out_file)

if __name__ == '__main__':
    import glob
    schema_lists = os.path.join(os.path.dirname(__file__), 'schema_lists')
    files = glob.glob(os.path.join(schema_lists, '*.txt'))
    for fl in files:
        layer = os.path.splitext(os.path.basename(fl))[0]
        with open(fl, 'r') as f:
            text = f.read()
            pdf_schema_to_json(text, layer)