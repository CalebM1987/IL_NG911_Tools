import os
import arcpy
import warnings

LAYER_TYPE = arcpy.mapping.Layer if hasattr(arcpy, 'mapping') else arcpy._mp.Layer
TABLE_TYPE = arcpy.mapping.TableView if hasattr(arcpy, 'mapping') else arcpy._mp.Table

def find_ws(path, ws_type=None, return_type=False):
    """[summary]
    
    Args:
        path (str): path to features or workspace
        ws_type (str, optional):option to find specific workspace type (FileSystem|LocalDatabase|RemoteDatabase), can be a single string or list of these options.
        return_type (bool, optional): option to return workspace type as well.  If this option is selected, a tuple
            of the full workspace path and type are returned. Defaults to False.
    
    Returns:
        str: the path to the workspace.  If the return_type is set to True, it will return a tuple of (path, workspaceType)
    """
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


class EditableCursorMixin(object):
    indexLookup = {}

    def set(self, row, **kwargs):
        """convenience method for setting row values by field name, automatically
        calls updateRow()
        Required:
            row -- row object (list of values) from cursor
            **kwargs -- keyword arguments for setting row values
        """
        for k,v in kwargs.items():
            indx = self.indexLookup.get(k)
            if indx is not None:
                row[indx] = v
        self.updateRow(row)

    def add(self, **kwargs):
        """convenience method for adding row values by field name, will automatically form
        list of values to insert (defaulting to all Null) and insert row.
        Required:
            **kwargs -- keyword arguments for setting row values
        """
        row = [None] * len(self.indexLookup.keys())
        for k,v in kwargs.items():
            indx = self.indexLookup.get(k)
            if indx is not None:
                row[indx] = v
        self.insertRow(row)

class NGUpdateCursor(arcpy.da.UpdateCursor, EditableCursorMixin):

    def __init__(self, *args, **kwargs):
        super(NGUpdateCursor, self).__init__(*args, **kwargs)
        self.indexLookup = {f: i for i,f in enumerate(self.fields)}

    def add(self, *args, **kwargs):
        raise NotImplementedError('Update Cursor does not support inserting new records!')

class NGInsertCursor(arcpy.da.InsertCursor, EditableCursorMixin):

    def __init__(self, *args, **kwargs):
        super(NGInsertCursor, self).__init__(*args, **kwargs)
        self.indexLookup = {f: i for i,f in enumerate(self.fields)}

    def set(self, *args, **kwargs):
        raise NotImplementedError('Insert Cursor does not support Updating records!')


class InsertCursor(object):
    """wrapper clas for arcpy.da.InsertCursor, to automatically
    implement editing (required for versioned data, and data with
    geometric networks, topologies, network datasets, and relationship
    classes"""
    def __init__(self, *args, **kwargs):
        """initiate wrapper class for update cursor.  Supported args:
        in_table, field_names
        """
        self.args = args
        self.kwargs = kwargs
        self.edit = None
        self.alreadyInEditSession = False
        self.fields = self.kwargs.get('fields')
        if not self.fields and len(self.args) >=2:
            self.fields = self.args[1]
        self.indexLookup = {f: i for i,f in enumerate(self.fields or [])}

    def teardown(self):
        if not self.alreadyInEditSession and self.edit:
            try:
                self.edit.stopOperation()
                self.edit.stopEditing(True)
            except Exception as e:
                warnings.warn("Exception On Insert Cursor! Records May Not Have Inserted: {}".format(e))
                raise e
    
        self.edit = None

    def __enter__(self):
        ws = None
        if self.args:
            ws = find_ws(self.args[0])
        elif 'in_table' in self.kwargs:
            ws = find_ws(self.kwargs['in_table'])

        try:
            self.edit = arcpy.da.Editor(ws)
            self.edit.startEditing()
            self.edit.startOperation()
            self.cursor = NGInsertCursor(*self.args, **self.kwargs)
            return self.cursor
        except Exception as e:
            # explicit check for active edit session, do not attempt starting new session
            msg = ((hasattr(e,'message') and e.message == 'start edit session') or (hasattr(e,'msg') and e.msg == 'start edit session'))
            if isinstance(e, RuntimeError) and msg:
                self.cursor = NGInsertCursor(*self.args, **self.kwargs)
                self.alreadyInEditSession = True
                return self.cursor
            else:
                # raise e
                # errors with edit session, stop editing and try outside of edit session
                self.teardown()
                self.cursor = NGInsertCursor(*self.args, **self.kwargs)
                return self.cursor

    def __exit__(self, type, value, traceback):
        self.teardown()
        try:
            del self.cursor
        except:
            pass


class UpdateCursor(object):
    """wrapper clas for arcpy.da.UpdateCursor, to automatically
    implement editing (required for versioned data, and data with
    geometric networks, topologies, network datasets, and relationship
    classes"""
    def __init__(self, *args, **kwargs):
        """initiate wrapper class for update cursor.  Supported args:
            in_table, field_names, where_clause=None, spatial_reference=None,
            explode_to_points=False, sql_clause=(None, None)
        """
        self.args = args
        self.kwargs = kwargs
        self.edit = None
        self.alreadyInEditSession = False
        self.fields = self.kwargs.get('fields')
        if not self.fields and len(self.args) >=2:
            self.fields = self.args[1]
        self.indexLookup = {f: i for i,f in enumerate(self.fields or [])}

    def teardown(self):
        if not self.alreadyInEditSession and self.edit:
            try:
                self.edit.stopOperation()
                self.edit.stopEditing(True)
            except Exception as e:
                warnings.warn("Exception On Update Cursor! Records May Not Have Updated: {}".format(e))
            
        self.edit = None

    def __enter__(self):
        ws = None
        if self.args:
            ws = find_ws(self.args[0])
        elif 'in_table' in self.kwargs:
            ws = find_ws(self.kwargs['in_table'])

        try:
            self.edit = arcpy.da.Editor(ws)
            self.edit.startEditing()
            self.edit.startOperation()
            self.cursor = NGUpdateCursor(*self.args, **self.kwargs)
            return self.cursor
        except Exception as e:
            # explicit check for active edit session, do not attempt starting new session
            msg = ((hasattr(e,'message') and e.message == 'start edit session') or (hasattr(e,'msg') and e.msg == 'start edit session'))
            if isinstance(e, RuntimeError) and msg:
                self.cursor = NGUpdateCursor(*self.args, **self.kwargs)
                self.alreadyInEditSession = True
                return self.cursor
            else:
                 # raise e
                # errors with edit session, stop editing and try outside of edit session
                self.teardown()
                self.cursor = NGUpdateCursor(*self.args, **self.kwargs)
                return self.cursor

    def __exit__(self, type, value, traceback):
        self.teardown()
        try:
            del self.cursor
        except:
            pass