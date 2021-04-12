import os
import arcpy
from ..support.munch import munchify, Munch
from ..schemas import load_schema


class NG911Data: 
    __tables__ = [
        'NG911_Tables'
    ]

    def __init__(self, schema_gdb: str):
        """NextGen 911 Data helper

        Args:
            schema_gdb (str): the path to the "NG911_Schemas" geodatabse
        """
        self.gdb_path = schema_gdb
        
        schema = self.get_table('NG911_Tables')
        with arcpy.da.SearchCursor(schema, ['Path', 'FeatureType']) as rows:
            self.requiredTables = munchify([dict(zip(['path', 'type'], r)) for r in rows])


    @property
    def esbTables(self):
        return [t.path for t in filter(lambda x: x.type == 'PSAP_ESB', self.requiredTables)]

    @property
    def addressPoints(self):
        try:
            return [t.path for t in self.requiredTables if t.type == 'ADDRESS_POINTS'][0]
        except IndexError:
            return None

    @property
    def roadCenterlines(self):
        try:
            return [t.path for t in self.requiredTables if t.type == 'ROAD_CENTERLINE'][0]
        except IndexError:
            return None

    @property
    def provisioningBoundary(self):
        try:
            return [t for t in self.requiredTables if t.type == 'PROVISIONING_BOUNDARY'][0]
        except IndexError:
            return None

    def get_table(self, name: str) -> str:
        """gets the full path to a table

        Args:
            name (str): the table name

        Returns:
            str: the full path to the table
        """
        if name in self.__tables__:
            return os.path.join(self.gdb_path, name)

    def load_911_schema(name: str) -> Munch:
        return load_schema(name)

    def get_domain(self, name: str) -> dict:
        """returns domain values by name

        Args:
            name (str): [description]

        Returns:
            dict: [description]
        """
        for domain in arcpy.da.ListDomains(self.gdb_path):
            if domain.name == name:
                return domain.codedValues if domain.domainType == 'CodedValue' else domain.range

    



    