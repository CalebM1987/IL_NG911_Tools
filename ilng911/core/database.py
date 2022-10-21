import os
import arcpy
from ..support.munch import munchify, Munch
# from ..schemas import load_schema, DataType
from ..utils import lazyprop, PropIterator, Singleton, date_to_mil
from ..utils.cursors import InsertCursor, UpdateCursor
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
        'SpatialJoinFields',
        'SpatialJoinFeatures',
        'ValidatedAddresses',
        'AddressFlags'
    ]

    NG911_TABLES = 'NG911_Tables'
    AGENCY_INFO = 'AgencyInfo'
    CUSTOM_FIELDS = 'CustomFields'
    CAD_VENDOR_FIELDS = 'CADVendorFields'
    SPATIAL_JOIN_FIELDS = 'SpatialJoinFields'
    SPATIAL_JOIN_FEATURES = 'SpatialJoinFeatures'
    VALIDATED_ADDRESSES = 'ValidatedAddresses'
    ADDRESS_FLAGS = 'AddressFlags'

class NG911Data(metaclass=Singleton): 
    state = None
    county = None
    country = 'US'
    agencyID = None
    types = NG911LayerTypes()
    schemaTables = NG911SchemaTables()
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
        self.nena_id_table = None
        self.new_nena_ids = Munch()
        self.requiredTables = []
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

            self.nena_id_table = os.path.join(self.gdb_path, 'NENA_IDs')
            if arcpy.Exists(self.nena_id_table):
                fields = self.types.__props__
                with arcpy.da.SearchCursor(self.nena_id_table, fields) as rows:
                    for r in rows:
                        self.new_nena_ids = munchify(dict(zip(fields, r)))
                        break
            else:
                log('NENA IDs table does not exist, make sure to run the register_nena_identifiers() function', level='warn')

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

    @property
    def addressFlags(self) -> str:
        return os.path.join(self.gdb_path, 'AddressFlags') if self.gdb_path else None
    
    @property
    def validatedAddresses(self) -> str:
        return os.path.join(self.gdb_path, 'ValidatedAddresses') if self.gdb_path else None

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

    def get_nena_ids_table(self, target: str) -> str:
        """fetches the nena ids table for the given target

        Args:
            target (str): the target type (ADDRESS_POINTS, ROAD_CENTERLINE, etc)

        Returns:
            str: full path to the nena ids table
        """
        nenaTab = os.path.join(self.gdb_path, f'NENA_ID_{target}')
        print('nena tab is?', nenaTab)
        if arcpy.Exists(nenaTab):
            return nenaTab

    def get_next_nena_id(self, target: str) -> int:
        """creates a newly incremented integer number for the new nena feature

        Args:
            target (str): the target type (ADDRESS_POINTS, ROAD_CENTERLINE, etc)

        Returns:
            int: next integer id
        """
        print('target for next nena id: ', target)
        used_id = self.new_nena_ids.get(target)
        if used_id:
            # get new id and append to list of ids
            new_id = used_id + 1
            self.new_nena_ids[target] = new_id
            log(f'using database cache to comput next NENA Identifier for "{target}": {new_id}')
            return new_id

        # no new ids yet, need to read from nena identifiers table
        log('checking table')
        nenaTab = self.get_nena_ids_table(target)
        desc = arcpy.Describe(nenaTab)
        sql_clause=(None, f'ORDER BY {desc.oidFieldName} DESC')
        with arcpy.da.SearchCursor(nenaTab, ['UniqueID'], sql_clause=sql_clause) as rows:
            for r in rows:
                num = r[0]
                if num:
                    break
        
        # increment by 1
        new_id = num + 1
        self.new_nena_ids[target] = new_id
        return new_id

    
    def save_nena_id(self, target: str, uid: int=None):
        """updates the nena identifiers table with a given unique ID

        Args:
            target (str): _description_
            uid (int, optional): _description_. Defaults to None.
        """
        if uid and uid <= self.new_nena_ids.get(target, 0):
            uid += 1
            self.new_nena_ids[target] = uid

        elif not uid:
            # don't need to auto increment?
            # uid = self.get_next_nena_id(target) 
            # instead use cache, or attempt to auto increment
            uid = self.new_nena_ids.get(target, 0) or self.get_next_nena_id(target)

        count = int(arcpy.management.GetCount(self.nena_id_table).getOutput(0))
        if not count:
            with InsertCursor(self.nena_id_table, [target]) as irows:
                irows.insertRow([uid])
                log(f'created NENA Identifiers row')
        else:
            # record already exists, just update it
            with UpdateCursor(self.nena_id_table, [target]) as rows:
                for i, r in enumerate(rows):
                    if i == 0:
                        rows.updateRow([uid])
                        log(f'found MAX NENA Identifier for "{target}": {uid}')
                    else:
                        rows.deleteRow()
                        log(f'removed NENA IDs row at index: {i}')

        log(f'set maximum NENA Identifier for "{target}": {uid}')


    def valiate_nena_id_fields(self):
        # TODO - check for IDs that were maybe added outside of these tools
        pass

    def get_table_type(self, path):
        """get the table type from a given path

        Args:
            path (str): the path for the table

        Returns:
            str: the table type
        """
        schemaTab = self.get_table(self.schemaTables.NG911_TABLES)
        with arcpy.da.SearchCursor(schemaTab, ['Path', 'FeatureType']) as rows:
            try:
                return [r[1] for r in rows if r[0] == path][0]
            except:
                return None


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
                try:
                    self.setup()
                except Exception as e:
                    log(f'error on setup for path: "{full_path}"')
                    raise e
                if self.setupComplete and arcpy.Exists(full_path):
                    return full_path

        return None


    def get_table_view(self, name: str=NG911SchemaTables.NG911_TABLES, where: str=None, view_name: str=None):
        """creates a table view

        Args:
            name (str, optional): _description_. Defaults to NG911SchemaTables.NG911_TABLES.
            where (str, optional): _description_. Defaults to None.
            view_name (str, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        if not os.path.sep in name:
            tab = self.get_table(name)
        else:
            tab = name
       
        if not view_name:
            view_name = f'{os.path.basename(name)}_{date_to_mil()}'

        return arcpy.management.MakeTableView(tab, view_name, where)

    # def load_911_schema(self, name: str) -> Munch:
    #     return load_schema(name)      

    def get_911_layer(self, name: str, where=None, check_map=False) -> arcpy._mp.Layer:
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
            return arcpy.management.MakeFeatureLayer(fc, where_clause=where).getOutput(0)
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

    
