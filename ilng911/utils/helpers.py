import os
import arcpy
import json
from typing import Optional, List, Any, Dict#,  Literal, TypedDict # not supported until ^3.8
from ilng911.utils.json_helpers import load_json
from ilng911.support.munch import munchify, Munch
from ilng911.logging import log, log_exception

datatypes_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'datatypes.json')

dataTypes_json = load_json(datatypes_file)
datatypes = [d.value for d in dataTypes_json.datatypes]
# datatypes = ["DEAddressLocator","GPAddressLocatorStyle","analysis_cell_size","GPType","DEMapDocument","GPArealUnit","GPBoolean","DECadDrawingDataset","GPCalculatorExpression","DECatalogRoot","GPSACellSize","GPCellSizeXY","GPCompositeLayer","GPSAGDBEnvCompression","GPCoordinateSystem","DESpatialReferencesFolder","DECoverage","DECoverageFeatureClasses","DEType","GPDataFile","DERemoteDatabaseFolder","DEDatasetType","GPDate","DEDbaseTable","GP3DADecimate","GPDiagramLayer","DEDiskConnection","GPDouble","GPEncryptedString","GPEnvelope","GPEvaluationScale","GPExtent","GPSAExtractValues","DEFeatureClass","DEFeatureDataset","GPFeatureLayer","GPFeatureRecordSetLayer","Field","GPFieldInfo","GPFieldMapping","DEFile","DEFolder","GPRasterFormulated","GPSAFuzzyFunction","DEGeodatasetType","DEGeoDataServer","DEGeometricNetwork","GPGALayer","GPGASearchNeighborhood","GPGAValueTable","DEGlobeServer","DEGPServer","GPGraph","GPGraphDataTable","GPGroupLayer","GPSAHorizontalFactor","DEImageServer","Index","GPINFOExpression","GPArcInfoItem","DEArcInfoTable","GPInternetTiledLayer","GPKMLLayer","DELasDataset","GPLasDatasetLayer","GPLayer","DELayer","GPLine","GPLinearUnit","GPLong","GPMDomain","GPMap","DEMapServer","GPMapServerLayer","DEMosaicDataset","GPMosaicLayer","GPSANeighborhood","NAClassFieldMap","GPNAHierarchySettings","GPNALayer","DENetworkDataset","GPNetworkDatasetLayer","NetworkTravelMode","DECadastralFabric","GPCadastralFabricLayer","GPPoint","GPPolygon","DEPrjFile","GPSAGDBEnvPyramid","GPSARadius","GPRandomNumberGenerator","DERasterBand","GPRasterCalculatorExpression","DERasterCatalog","GPRasterCatalogLayer","GPRasterDataLayer","DERasterDataset","GPRasterLayer","GPSAGDBEnvStatistics","GPRasterBuilder","GPRecordSet","DERelationshipClass","GPSARemap","GPRouteMeasureEventProperties","GPSceneServiceLayer","DESchematicDataset","DESchematicDiagram","DESchematicDiagramClass","DESchematicFolder","GPSchematicLayer","GPSASemiVariogram","DEServerConnection","DEShapefile","GPSpatialReference","GPSQLExpression","GPString","GPStringHidden","DETable","GPTableView","GPTerrainLayer","DETextfile","GPSAGDBEnvTileSize","GPSATimeConfiguration","GPTimeUnit","DETin","GPTinLayer","DETool","DEToolbox","GPSATopoFeatures","DETopology","GPTopologyLayer","GPSATransformationFunction"," DEUtilityNetwork","GPUtilityNetworkLayer","GPValueTable","GPVariant","GPVectorLayer","GPSAVerticalFactor","DEVPFCoverage","DEVPFTable","DEWCSCoverage","GPSAWeightedOverlayTable","GPSAWeightedSum","DEWMSMap","DEWorkspace","GPXYDomain","GPZDomain"]
# class ParamterAsJSON: # cannot inherit from TypedDict until ^3.8
#     name: str
#     displayName: str
#     # direction: Optional[Literal['Input', 'Output']]
#     direction: Optional[List[str]]
#     datatype: datatypes
#     # parameterType: Optional[Literal['Required', 'Optional', 'Derived']]
#     parameterType: Optional[List[str]]
#     enabled: Optional[bool]
#     category: Optional[str]
#     message: Optional[str]
#     multiValue: Optional[bool]
#     parameterDependencies: Optional[List[str]]
#     filterList: Optional[List[Any]]

# class ToolAsJSON: # cannot inherit from TypedDict until ^3.8
#     name: str
#     label: str
#     params: List[ParamterAsJSON]

# [{
#                     "name": "target_field",
#                     "displayName": "Target Field",
#                     "datatype": "Field",
#                     "parameterDependencies": ["target_table"]
#                 },
#                 {
#                     "name": "expression",
#                     "displayName": "Expression",
#                     "datatype": "GPString"
#                 }]

field_types = {
    'esriFieldTypeString': 'TEXT',
    'esriFieldTypeDate': 'DATE',
    'esriFieldTypeSingle': 'FLOAT',
    'esriFieldTypeDouble':'DOUBLE',
    'esriFieldTypeSmallInteger': 'SHORT',
    'esriFieldTypeInteger':'LONG',
    'esriFieldTypeGUID':'GUID',
    'esriFieldTypeGlobalID': 'GUID'
}

def parse_value_table(vt, value_type=None):
    """parses a value table to either a dictionary or nested list, must have at least
    2 columns.

    Required:
        vt -- value table as string

    Optional:
        frmat -- return format. Default is 'dict'.  Use 'list' to return as nested list.
        value_type -- type for values, needs to be callable. (float|str|int) (will
            be string by default).
    """
    d = []
    for row in vt.split(';'):
        if "'" in row:
            all_vals = list(filter(None, row.split("'")))
            if len(all_vals) > 2:
                key, value = all_vals[0], [v for v in all_vals[1:] if v != ' ']
            elif len(all_vals) == 2:
                key, value = all_vals[0], all_vals[1]
            # if isinstance(value, list) and len(value) == 1:
            #     value = value[0]
        else:
            if row.count(' ') > 1:
                rowVals = row.split()
                key = rowVals[0]
                value = rowVals[1:]
            else:
                try:
                    key, value = row.split()
                except ValueError:
                    key, value = row, 'delete-me' #flag to delete

        if isinstance(value, list):
            value = [v.strip() for v in value]
        else:
            value = value.strip()

        # cast value types
        if value_type in (float, int, str):
            if isinstance(value, list):
                try:
                    value = map(value_type, value)
                except:
                    continue
            else:
                value = value_type(value)

        # flatten list if there is only one column
        if value == 'delete-me':
            d.append(key)
        else:
            d.append([key.strip(), value])
    return d

def parameter_from_json(d: Dict) -> arcpy.Parameter:
    """create an arcpy.Parameter from a json definition

    Args:
        d (ParamterAsJSON): _description_

    Returns:
        arcpy.Parameter: _description_
    """
    d = munchify(d)
    skip = ['parameterDependencies', 'filterList', 'valueTable']
    param = arcpy.Parameter(**{k: v for k,v in d.items() if k not in skip})

    # check for value table
    if d.get('datatype') == 'GPValueTable':
        vtConf = d.get('valueTable', {})
        vtFields = vtConf.get('fields', [])
        param.columns = [[d.datatype, d.name] for d in vtFields]

        # check for filters, does not work, cannot set filter for fields in VT :( 
        # if isinstance(vtConf.get('filters'), list):
        #     for i, ft in enumerate(vtConf.get('filters')):
        #         param.filters[i].type = ft.type
        #         param.filters[i].list = ft.list

    if isinstance(d.get('parameterDependencies'), list):
        param.parameterDependencies = d.parameterDependencies

    if isinstance(d.get('filterList'), list):
        param.filter.list = d.filterList

    return param

def params_to_kwargs(parameters: List[arcpy.Parameter]):
    return { p.name: p for p in parameters }
