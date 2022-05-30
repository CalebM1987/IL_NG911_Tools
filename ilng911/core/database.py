import os
import arcpy
from ..support.munch import munchify, Munch
# from ..schemas import load_schema, DataType
from ..utils import lazyprop
from ..logging import log

class PropIterator:
    __props__ = []

    def __iter__(self):
        for p in self._props:
            return p

class NG911LayerTypes(PropIterator):
    __props__ = [
        'PSAP',
        'ESB',
        'ESB_EMS',
        'ESB_FIRE',
        'ESB_LAW,'
        'ADDRESS_POINTS',
        'ROAD_CENTERLINE',
        'PROVISIONING_BOUNDARY'
    ]
    PSAP = 'PSAP'
    ESB = 'ESB'
    ESB_EMS = 'ESB_EMS'
    ESB_FIRE = 'ESB_FIRE'
    ESB_LAW = 'ESB_LAW'
    ADDRESS_POINTS = 'ADDRESS_POINTS'
    ROAD_CENTERLINE = 'ROAD_CENTERLINE'
    PROVISIONING_BOUNDARY = 'PROVISIONING_BOUNDARY'

    
class NG911SchemaTables(PropIterator):
    __props__ = [
        'NG911_Tables',
        'AgencyInfo',
        'CustomFields',
        'CADVendorFields',
        'CADVendorFeatures'
    ]

    NG911_TABLES = 'NG911_Tables'
    AGENCY_INFO = 'AgencyInfo'
    CUSTOM_FIELDS = 'CustomFields'
    CAD_VENDOR_FIELDS = 'CADVendorFields'
    CAD_VENDOR_FEATURES = 'CADVendorFeatures'

class NG911Data: 
    state = None
    county = None
    country = 'US'
    agencyID = None
    types = NG911LayerTypes
    schemaTables = NG911SchemaTables

    __tables__ = NG911SchemaTables.__props__

    def __new__(cls):
        """ensure singleton instance"""
        if not hasattr(cls, 'instance'):
            cls.instance = super(NG911Data, cls).__new__(cls)
        return cls.instance

    def __init__(self, schema_gdb: str):
        """NextGen 911 Data helper

        Args:
            schema_gdb (str): the path to the "NG911_Schemas" geodatabse
        """
        self.gdb_path = schema_gdb
        
        schema = self.get_table(self.schemaTables.NG911_TABLES)
        with arcpy.da.SearchCursor(schema, ['Path', 'FeatureType']) as rows:
            self.requiredTables = munchify([dict(zip(['path', 'type'], r)) for r in rows])
        
        with arcpy.da.SearchCursor(self.get_table(self.schemaTables.AGENCY_INFO), ['County', 'State', 'Country', 'AgencyID']) as rows:
            for r in rows:
                self.county, self.state, self.country, self.agencyID = r
                break
        log(f'Initialized NG911 Database for "{self.county}" with agency ID of "{self.agencyID}"')

    @lazyprop
    def psap(self):
        try:
            return [t.path for t in filter(lambda x: x.type == self.types.PSAP, self.requiredTables)][0]
        except IndexError:
            return None

    @lazyprop
    def esb(self):
        try:
            return [t.path for t in filter(lambda x: x.type == self.types.ESB, self.requiredTables)][0]
        except IndexError:
            return None

    @lazyprop
    def esbFire(self):
        try:
            return [t.path for t in filter(lambda x: x.type == self.types.ESB_FIRE, self.requiredTables)][0]
        except IndexError:
            return None

    @lazyprop
    def esbLaw(self):
        try:
            return [t.path for t in filter(lambda x: x.type == self.types.ESB_LAW, self.requiredTables)][0]
        except IndexError:
            return None

    @lazyprop
    def esbEMS(self):
        try:
            return [t.path for t in filter(lambda x: x.type == self.types.ESB_EMS, self.requiredTables)][0]
        except IndexError:
            return None

    @lazyprop
    def esbTables(self):
        return [t.path for t in filter(lambda x: x.type.startswith('ESB'), self.requiredTables)]

    @lazyprop
    def addressPoints(self):
        try:
            return [t.path for t in self.requiredTables if t.type == self.types.ADDRESS_POINTS][0]
        except IndexError:
            return None

    @lazyprop
    def roadCenterlines(self):
        try:
            return [t.path for t in self.requiredTables if t.type == self.types.ROAD_CENTERLINE][0]
        except IndexError:
            return None

    @lazyprop
    def provisioningBoundary(self):
        try:
            return [t for t in self.requiredTables if t.type == self.types.PROVISIONING_BOUNDARY][0]
        except IndexError:
            return None

    @staticmethod
    def get_basename(path: str) -> str:
        """gets the basname for a feature class

        Args:
            path (str): the feature class path

        Returns:
            str: the basename
        """
        return os.path.basename(path or '').split('.')[-1]

    def has_911_type(self, name: str) -> bool:
        """returns a boolean for whether there is a 911 type

        Args:
            name (str): [description]

        Returns:
            bool: [description]
        """
        return name in self.types.__props__

    def get_911_table(self, name: str) -> str:
        """checks to see if a layer exists in the NG911 data by basename

        Args:
            name (str): the 911 data type 

        Returns:
            str: the feature class path
        """
        schemaTab = self.get_table(self.schemaTables.NG911_TABLES)
        where = f"Basename = '{name}'"
        with arcpy.da.SearchCursor(schemaTab, ['BaseName', 'Path'], where) as rows:
            try:
                return [r[1] for r in rows if r[0] == name][0]
            except:
                return None

    # def has_911_table(self, name: str) -> str:
    #     """checks to see if a layer exists in the NG911 data by basename

    #     Args:
    #         name (str): [description]

    #     Returns:
    #         bool: [description]
    #     """
    #     fc = self.get_911_table(name)
    #     if not fc:
    #         return False
    #     try:
    #         schemaTab = self.get_table(self.schemaTables.NG911_TABLES)
    #         where = f"Basename = '{name}'"
    #         with arcpy.da.SearchCursor(schemaTab, ['BaseName', 'Path'], where) as rows:
    #             fc = [r[1] for r in rows if r[0] == name][0]
    #             return arcpy.Exists(fc)
    #     except:
    #         return False

    def get_table(self, name: str=NG911SchemaTables.NG911_TABLES) -> str:
        """gets the full path to a table

        Args:
            name (str): the table name

        Returns:
            str: the full path to the table
        """
        if name in self.__tables__:
            return os.path.join(self.gdb_path, name)

    # def load_911_schema(self, name: str) -> Munch:
    #     return load_schema(name)      

    def get_911_layer(self, name: str, check_map=False) -> arcpy._mp.Layer:
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
                    log(f"layer for {name} not found in map, or running standalone")
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

    
