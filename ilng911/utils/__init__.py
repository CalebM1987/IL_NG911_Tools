import os
import sys
import arcpy
import datetime
import warnings

is_arc = os.path.basename(sys.executable).startswith('Arc')

def updir(path: str, levels: int=1):
    """gets path n levels up from given path"""
    p = path
    for i in range(levels):
        p = os.path.dirname(p)
    return p

needs_arc_message = False
if is_arc:
    import arcpy
    needs_arc_message = True

class lazyprop:
    """Based on code from David Beazley's "Python Cookbook".
    
    @see: https://stackoverflow.com/q/62160411/3005089
    """
    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = instance.__dict__[self.func.__name__] = self.func(instance)
            return value


def message(*args):
    """prints one or more messages to the stdout.  If being used in an arcpy process, it will also call arcpy.AddMessage()"""
    for msg in args:
        print(str(msg))
        if needs_arc_message:
            arcpy.AddMessage(str(msg))

def mil_to_date(mil):
    """Date items from REST services are reported in milliseconds,
            this function will convert milliseconds to datetime objects.
    Args:
        mil: Time in milliseconds.
    Returns:
        Datetime object.
    """

    if isinstance(mil, str):
        mil = int(mil)
    if mil == None:
        return None
    elif mil < 0:
        return datetime.datetime.utcfromtimestamp(0) + datetime.timedelta(seconds=(mil/1000))
    else:
        try:
            return datetime.datetime.utcfromtimestamp(mil / 1000)
        except Exception as e:
            warnings.warn('bad milliseconds value: {}'.format(mil))
            raise e

def date_to_mil(date=None):
    """Converts datetime.datetime() object to milliseconds.
    Args:
        date: datetime.datetime() object
    Returns:
        Time in milliseconds.
    """

    if isinstance(date, datetime.datetime):
        epoch = datetime.datetime.utcfromtimestamp(0)
        return int((date - epoch).total_seconds() * 1000.0)


def find_ws(path, ws_type=None, return_type=False):
    """finds the workspace for a given feature class or shapefile
    
    Args:
        path (str): path to features or workspace
        ws_type (str, optional):option to find specific workspace type (FileSystem|LocalDatabase|RemoteDatabase), can be a single string or list of these options.
        return_type (bool, optional): option to return workspace type as well.  If this option is selected, a tuple
            of the full workspace path and type are returned. Defaults to False.
    
    Returns:
        str: the path to the workspace.  If the return_type is set to True, it will return a tuple of (path, workspaceType)
    """
    import arcpy
    LAYER_TYPE = arcpy.mapping.Layer if hasattr(arcpy, 'mapping') else arcpy._mp.Layer
    TABLE_TYPE = arcpy.mapping.TableView if hasattr(arcpy, 'mapping') else arcpy._mp.Table

    def find_existing(path):
        if arcpy.Exists(path):
            return arcpy.Describe(path).catalogPath
        else:
            if not arcpy.Exists(path):
                return find_existing(os.path.dirname(path))

    # try original path first
    if isinstance(path, (LAYER_TYPE, TABLE_TYPE)):
        path = path.dataSource

    if os.sep not in str(path):
        if hasattr(path, 'dataSource'):
            path = path.dataSource
        else:
            path = arcpy.Describe(path).catalogPath

    path = find_existing(path)

    # first make sure it's not an "in_memory" workspace
    if (path or '').startswith('in_memory'):
        return ('in_memory', 'LocalDatabase') if return_type else 'in_memory'

    desc = arcpy.Describe(path)
    if not isinstance(ws_type, list) and ws_type:
        ws_type = [ws_type]

    if hasattr(desc, 'workspaceType'):
        if ws_type:
            if desc.workspaceType in ws_type:
                if return_type:
                    return (path, desc.workspaceType)
                else:
                    return path
        else:
            if return_type:
                return (path, desc.workspaceType)
            else:
                return path

    # search until finding a valid workspace
    path = str(path)
    split = list(filter(None, str(path).split(os.sep)))
    if path.startswith('\\\\'):
        split[0] = r'\\{0}'.format(split[0])

    # find valid workspace
    for i in range(1, len(split)):
        sub_dir = os.sep.join(split[:-i])
        desc = arcpy.Describe(sub_dir)
        if hasattr(desc, 'workspaceType'):
            if ws_type == desc.workspaceType:
                if return_type:
                    return (sub_dir, desc.workspaceType)
                else:
                    return sub_dir
            else:
                if return_type:
                    return (sub_dir, desc.workspaceType)
                else:
                    return sub_dir

def copy_schema(template: str, output: str, sr: arcpy.SpatialReference=None, shapeType: str='') -> str:
    """creates an empty feature class or table based on a template

    Args:
        template (str): the template feature class or table
        output (str): the output empty table or feature class
        sr (arcpy.SpatialReference, optional): an arcpy.SpatialReference object.
        shapeType (str, optional): a shapeType. Defaults to ''.

    Returns:
        str: the output feature class or table

    >>> #Example
    >>> copy_schema(r'C:\Temp\soils_city.shp', r'C:\Temp\soils_county.shp')
    """
    path, name = os.path.split(output)
    desc = arcpy.Describe(template)
    ftype = desc.dataType
    exp = '{0} is null'.format(arcpy.AddFieldDelimiters(template, desc.OIDFieldName))
    # if not emptyTable:
    #     exp = ''
    if 'table' in ftype.lower() or shapeType.lower() == 'table':
        arcpy.conversion.TableToTable(template, path, name, exp)
    else:
        if not shapeType:
            shapeType = desc.shapeType.upper()
        sm = 'SAME_AS_TEMPLATE'
        if not sr:
            sr = desc.spatialReference
        arcpy.management.CreateFeatureclass(path, name, shapeType, template, sm, sm, sr)
    return output
