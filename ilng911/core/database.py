import os
import arcpy
from ..support.munch import munchify, Munch
# from ..schemas import load_schema, DataType
from ..utils import lazyprop, PropIterator, Singleton
from ..logging import log
from ..config import load_config

class NG911LayerTypes(PropIterator):
    __props__ = [
        'PSAP',
        'ESB',
        'ESB_EMS',
        'ESB_FIRE',
        'ESB_LAW',
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
        'CADVendorFeatures',
        'SpatialJoinFields',
        'SpatialJoinFeatures',
    ]

    NG911_TABLES = 'NG911_Tables'
    AGENCY_INFO = 'AgencyInfo'
    CUSTOM_FIELDS = 'CustomFields'
    CAD_VENDOR_FIELDS = 'CADVendorFields'
    CAD_VENDOR_FEATURES = 'CADVendorFeatures'
    SPATIAL_JOIN_FIELDS = 'SpatialJoinFields'
    SPATIAL_JOIN_FEATURES = 'SpatialJoinFeatures'

class NG911Data(metaclass=Singleton): 
    state = None
    county = None
    country = 'US'
    agencyID = None
    types = NG911LayerTypes
    schemaTables = NG911SchemaTables
    config = Munch()

    __tables__ = NG911SchemaTables.__props__

    def __init__(self, config_file='config.json'):
        """NextGen 911 Data helper

        Args:
            schema_gdb (str): the path to the "NG911_Schemas" geodatabse
        """
        self.config_file = config_file
        self.setupComplete = False
        self.gdb_path = None
        self.setup()
        
    def setup(self):
        """setup feature class registration"""
        if self.setupComplete:
            return 
        
        log('ng911 database setup initializing')
        config = load_config(self.config_file)
        if config:
            gdb_path = config.get("ng911GDBSchemasPath")
            if not arcpy.Exists(gdb_path):
                log('ng911 database setup exited: no geodatabase exists')
                return

            self.config = config
            self.gdb_path = gdb_path
            schema = os.path.join(self.gdb_path, self.schemaTables.NG911_TABLES)
            schemaExists = arcpy.Exists(schema)
            if schemaExists:
                with arcpy.da.SearchCursor(schema, ['Path', 'FeatureType']) as rows:
                    self.requiredTables = munchify([dict(zip(['path', 'type'], r)) for r in rows])
            
            agencyTab = os.path.join(self.gdb_path, self.schemaTables.AGENCY_INFO)
            agencyTabExists = arcpy.Exists(agencyTab)
            if agencyTabExists:
                with arcpy.da.SearchCursor(agencyTab, ['County', 'State', 'AgencyID']) as rows:
                    for r in rows:
                        self.county, self.state, self.agencyID = r
                        break

            if schemaExists and agencyTabExists and self.agencyID and self.requiredTables:
                self.setupComplete = True
                log(f'Initialized NG911 Database for "{self.county}" with agency ID of "{self.agencyID}"')
            else:
                log(f'ng911 database setup incomplete - schemaExists: {schemaExists}, agency info set: {agencyTabExists and bool(self.agencyID)}, required tables set: {bool(self.requiredTables)}')

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
        if name in self.types.__props__:
            where = f"FeatureType = '{name}'"
            index = 2
        else:
            where = f"Basename = '{name}'"
            index = 0

        with arcpy.da.SearchCursor(schemaTab, ['BaseName', 'Path', 'FeatureType'], where) as rows:
            try:
                return [r[1] for r in rows if r[index] == name][0]
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
            full_path = os.path.join(self.gdb_path, name)
            if self.setupComplete:
                # skip exists check if setup is complete
                return full_path
            else:
                self.setup()
                if self.setupComplete and arcpy.Exists(full_path):
                    return full_path

        return None

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

    
