import os
from ..utils.json_helpers import load_json
from ..support.munch import Munch
from .enums import FieldCategory

schemasDir = os.path.join(os.path.dirname(__file__), '_schemas')

TYPE_LOOKUP = dict(
    ADDRESS_POINTS="AddressPoints",
    ROAD_CENTERLINE="RoadCenterline",
    PROVISIONING_BOUNDARY="ProvisioningBoundary",
    PSAP_ESB="PSAP"
)

class DataType:
    ADDRESS_POINTS="AddressPoints"
    ROAD_CENTERLINE="RoadCenterline"
    PROVISIONING_BOUNDARY="ProvisioningBoundary"
    PSAP_ESB="PSAP"

class DataSchema(Munch):

    @property
    def reservedFields(self):
        return [f.name for f in self.get('fieldInfos', []) if f.category == FieldCategory.RESERVED]

    @property
    def requiredFields(self):
        return [f.name for f in self.get('fieldInfos', []) if f.category == FieldCategory.MANDATORY]

    @property
    def conditionalFields(self):
        return [f.name for f in self.get('fieldInfos', []) if f.category == FieldCategory.CONDITIONAL]

    @property
    def optionalFields(self):
        return [f.name for f in self.get('fieldInfos', []) if f.category == FieldCategory.OPTIONAL]

    def get_field(self, name: str) -> Munch:
        """returns the field info

        Args:
            name (str): the field name

        Returns:
            Munch: the field info containing the { name, category, ... }
        """
        fieldInfos = self.get('fieldInfos', [])
        try:
            return [f for f in fieldInfos if f.name == name][0]
        except IndexError:
            return None


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
        return DataSchema(load_json(fl))

 

    