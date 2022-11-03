import os
import sys
import arcpy

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ilng911.env import get_ng911_db
from ilng911.schemas import DataSchema, DataType
# from ilng911.core.parser

ng911_db = get_ng911_db()

addressSchema = DataSchema(DataType.ADDRESS_POINTS)
roadSchema = DataSchema(DataType.ROAD_CENTERLINE)

# # sample: 142 main
# pg = arcpy.AsShape({
#     "x": -90.76689954799997,
#     "y": 39.98611309700004,
#     "spatialReference": {
#     "wkid": 4326,
#     "latestWkid": 4326
#     }
# }, True)

# kwargs = {
#     "Effective": None,
#     "Expire": None,
#     "AddCode": None,
#     "AddDataURI": None,
#     "Nbrhd_Comm": None,
#     "AddNum_Pre": None,
#     "Add_Number": 142,
#     "AddNum_Suf": None,
#     "ESN": None,
#     "Building": None,
#     "Floor": None,
#     "Unit": None,
#     "Room": None,
#     "Seat": None,
#     "Addtl_Loc": None,
#     "LandmkName": None,
#     "Mile_Post": None,
#     "Place_Type": None,
#     "Placement": None
# }

# ft = schema.create_feature(pg, **kwargs)


