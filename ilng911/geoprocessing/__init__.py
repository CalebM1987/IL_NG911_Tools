import arcpy
from ..env import ng911_db
from ..support.munch import munchify

field_types = dict(
    Date='GPDate',
    String='GPString',
    Integer="GPLong",
    SmallInteger="GPLong", # no matching parameter type for this
    Single="GPDouble", # no gp type for this
    Double="GPDouble"
)

SKIP_TYPES = ('OID', 'Geometry', 'Blob', 'GUID', 'Raster')
SKIP_NAMES = [
    "DiscrpAgID",
    "RCL_NGUID"
]

def table_to_params(table: str):
    """creates tool parameters for fields from a given table

    Args:
        table (str): the source table

    Returns:
        list[arcpy.Parameter]: the arcpy parameters
    """
    params = []
    fields = [f for f in arcpy.Describe(table) if f.type not in SKIP_TYPES and f.name not in SKIP_NAMES]
    for field in fields:
        param = arcpy.Parameter(
            name=field.name,
            displayName=field.aliasName,
            datatype=field_types.get(field.type, 'GPString'),
            direction='Input'
        )

        # add filter if necessary
        if field.domain:
            domain = ng911_db.get_domain(field.domain)
            if isinstance(domain, dict):
                param.filter.list = sorted(list(domain.keys()))

        if field.defaultValue:
            param.value = field.defaultValue

        params.append(param
            # dict(
            #     field=field.name,
            #     fieldType=field.type,
            #     fieldLength=field.length,
            #     defaultValue=field.defaultValue,
            #     domain=field.domain,
            #     param=arcpy.Parameter(
            #         name=field.name,
            #         displayName=field.aliasName,
            #         datatype=field_types.get(field.type, 'GPString'),
            #         direction='Input'
            #     )
            # )
        )

    return params #munchify(params)