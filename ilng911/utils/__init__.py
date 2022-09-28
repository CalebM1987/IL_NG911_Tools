import os
import sys
import arcpy
import datetime
import warnings
from itertools import zip_longest

is_arc = os.path.basename(sys.executable).startswith('Arc')

def updir(path: str, levels: int=1):
    """gets path n levels up from given path"""
    p = path
    for i in range(levels):
        p = os.path.dirname(p)
    return p

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class PropIterator:
    __props__ = []

    def __iter__(self):
        for p in (self.__props__ or [p for p in dir(self) if not p.startswith('__')]):
            yield p

    def __len__(self):
        return len(self.__props__)

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


def iter_chunks(iterable, n):
    args = [iter(iterable)] * n
    for group in zip_longest(*args, fillvalue=None):
        yield list(filter(lambda x: x != None, group))