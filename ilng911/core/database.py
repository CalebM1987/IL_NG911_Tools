import os
import arcpy
from ..support.munch import munchify, Munch
from ..schemas import load_schema
from ..utils import message


class NG911LayerTypes:
    __props__ = [
        'ADDRESS_POINTS',
        'ROAD_CENTERLINE',
        'PSAP_ESB',
        'PROVISIONING_BOUNDARY'
    ]
    ADDRESS_POINTS = 'ADDRESS_POINTS'
    ROAD_CENTERLINE = 'ROAD_CENTERLINE'
    PSAP_ESB = 'PSAP_ESB'
    PROVISIONING_BOUNDARY = 'PROVISIONING_BOUNDARY'

    def __iter__(self):
        for p in self._props:
            return p

class NG911SchemaTables:
    __props__ = [
        'NG911_Tables'
    ]

    NG911_TABLES = 'NG911_Tables'


class NG911Data: 
    types = NG911LayerTypes
    schemaTables = NG911SchemaTables

    __tables__ = NG911SchemaTables.__props__

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
        return [t.path for t in filter(lambda x: x.type == self.types.PSAP_ESB, self.requiredTables)]

    @property
    def addressPoints(self):
        try:
            return [t.path for t in self.requiredTables if t.type == self.types.ADDRESS_POINTS][0]
        except IndexError:
            return None

    @property
    def roadCenterlines(self):
        try:
            return [t.path for t in self.requiredTables if t.type == self.types.ROAD_CENTERLINE][0]
        except IndexError:
            return None

    @property
    def provisioningBoundary(self):
        try:
            return [t for t in self.requiredTables if t.type == self.types.PROVISIONING_BOUNDARY][0]
        except IndexError:
            return None

    @staticmethod
    def get_basename(path: str) -> str:
        return os.path.basename(path or '').split('.')[-1]

    def has_911_type(self, name: str) -> bool:
        """[summary]

        Args:
            name (str): [description]

        Returns:
            bool: [description]
        """
        return name in self.types.__props__

    def get_911_table(self, name: str) -> str:
        """checks to see if a layer exists in the NG911 data by basename

        Args:
            name (str): [description]

        Returns:
            bool: [description]
        """
        schemaTab = self.get_table(self.schemaTables.NG911_TABLES)
        where = f"Basename = '{name}'"
        with arcpy.da.SearchCursor(schemaTab, ['BaseName', 'Path'], where) as rows:
            try:
                return [r[1] for r in rows if r[0] == name][0]
            except:
                return None

    def has_911_table(self, name: str) -> str:
        """checks to see if a layer exists in the NG911 data by basename

        Args:
            name (str): [description]

        Returns:
            bool: [description]
        """
        fc = self.get_911_table(name)
        if not fc:
            return False
        try:
            fc = [r[1] for r in rows if r[0] == name][0]
            return arcpy.Exists(fc)
        except:
            return False

    def get_table(self, name: str) -> str:
        """gets the full path to a table

        Args:
            name (str): the table name

        Returns:
            str: the full path to the table
        """
        if name in self.__tables__:
            return os.path.join(self.gdb_path, name)

    def load_911_schema(self, name: str) -> Munch:
        return load_schema(name)      

    def get_911_layer(self, name: str, check_map=True) -> arcpy._mp.Layer:
        """gets a NG 911 feature class as a arcpy._mp.Layer

        Args:
            name (str): the basename of the layer to fetch
            check_map (bool): if the context is within a current map (aprx project),
                this will attempt to find the layer if it exists in the TOC. This will
                honor any active feature selections.

        Returns:
            arcpy._mp.Layer: the layer for the requested feature class
        """
        fc = self.get_911_table(name)
        if fc:
            if check_map:
                try:
                    aprx = arcpy.mp.ArcGISProject("CURRENT")
                    for m in aprx.listMaps():
                        for lyr in m.listLayers():
                            if lyr.supports('DATASOURCE') and lyr.dataSource == fc:
                                    return lyr
                except:
                    message(f"layer for {name} not found in map, or running standalone")
            return arcpy.management.MakeFeatureLayer(fc).getOutput(0)
        return None

    def get_domain(self, name: str, workspace=None) -> dict:
        """returns domain values by name

        Args:
            name (str): [description]

        Returns:
            dict: [description]
        """
        for domain in arcpy.da.ListDomains(workspace or self.gdb_path):
            if domain.name == name:
                return domain.codedValues if domain.domainType == 'CodedValue' else domain.range

    
