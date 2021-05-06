import os
import sys

is_arc = os.path.basename(sys.executable).startswith('Arc')

needs_arc_message = False
if is_arc:
    import arcpy
    needs_arc_message = True


def message(*args):
    """prints one or more messages to the stdout.  If being used in an arcpy process, it will also call arcpy.AddMessage()"""
    for msg in args:
        print(str(msg))
        if needs_arc_message:
            arcpy.AddMessage(str(msg))

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