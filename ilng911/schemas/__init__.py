import os
from ..utils.json_helpers import load_json
from ..support.munch import Munch

schemasDir = os.path.join(os.path.dirname(__file__), '_schemas')

TYPE_LOOKUP = dict(
    ADDRESS_POINTS="AddressPoints",
    ROAD_CENTERLINE="RoadCenterline",
    PROVISIONING_BOUNDARY="ProvisioningBoundary",
    PSAP_ESB="PSAP"
)


def load_schema(name: str) -> Munch:
    """loads a json schema

    Args:
        name (str): the name of the json schema to load

    Returns:
        Munch: the schema
    """
    if name in TYPE_LOOKUP:
        name = TYPE_LOOKUP[name]
    fl = os.path.join(schemasDir, name + '.json')
    if os.path.exists(fl):
        return load_json(fl)