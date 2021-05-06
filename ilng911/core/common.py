import re
import arcpy
import json
from ..schemas import DataSchema, DataType
from ..env import ng911_db 
from ..support.munch import Munch, munchify
from typing import List

SHAPE_PAT = re.compile('^(shape)[@]?', re.I)
SHAPE_ATTR_PAT = re.compile('^(shape)[@._](\w+)', re.I)
WGS_84_WKID = 4326
WGS_84 = arcpy.SpatialReference(WGS_84_WKID)
WEB_MERCATOR_WKID = 102100
WEB_MERCATOR = arcpy.SpatialReference(WEB_MERCATOR_WKID)
LATITUDE_FIELD = 'Lat'
LONGITUDE_FIELD = 'Long'

def is_shape_field(fld: str) -> bool:
    return SHAPE_PAT.fullmatch(fld) is not None

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


class Feature(object):
    def __init__(self, fields: List[str], geometry: arcpy.Geometry=None, **kwargs):
        
        self.fields = fields
        self.geometry = geometry
        self.attributes = {}
        
        for fld, val in kwargs.items():
            if is_shape_field(fld):
                if not self.geometry and isinstance(val, arcpy.Geometry):
                    self.geometry = val
                
            elif fld.lower() == 'oid@':
                kwargs[self.oidField] = val

        # set attributes
        if (LATITUDE_FIELD in self.fieldNames and LONGITUDE_FIELD in self.fieldNames) and geometry:
            if geometry.spatialReference.factoryCode != WGS_84_WKID:
                wgs84 = geometry.projectAs(arcpy.SpatialReference(4326))
            else:
                wgs84 = geometry
            kwargs[LATITUDE_FIELD] = wgs84.centroid.Y
            kwargs[LONGITUDE_FIELD] = wgs84.centroid.X

        self.attributes.update(self.filter_attrs(kwargs))

    @lazyprop
    def fieldNames(self):
        return [f.name for f in self.fields if f.type != 'Geometry']

    @lazyprop
    def oidField(self):
        return [f.name for f in self.fields if f.type == 'OID'][0]

    @lazyprop
    def _writable(self):
        return [f for f in self.fieldNames if not SHAPE_ATTR_PAT.match(f)]

    def filter_attrs(self, kwargs={}) -> Munch:
        return munchify({k: kwargs.get(k) for k in self._writable if not self.attributes.get(k)})

    def get(self, attribute: str, default=None):
        """shorthand getter for any feature attributes

        Args:
            attribute (str): the attribute name (must be a valid field or field token)
            default ([type], optional): [description]. Defaults to None.

        Returns:
            the desired attribute
        """
        return self.attributes.get(attribute, default)

    def update(self, **kwargs):
        self.attributes.update(self.filter_attrs(kwargs))

    def toJson(self) -> Munch:
        return munchify(
            dict(
                attributes=self.attributes,
                geometry=json.loads(self.geometry.JSON)
            )
        )

    def toRow(self, fields: List[str]):
        vals = []
        for f in fields:
            if f in self.attributes:
                vals.append(self.attributes[f])
            elif is_shape_field(f):
                vals.append(self.geometry)
            elif f.lower() == 'oid@':
                vals.append(self.objectId)
        return vals


class FeatureHelper:
    def __init__(self, schema: DataSchema):
        self._schema = schema
        self.table = ng911_db.get_911_table(self._schema.layer)

    @lazyprop
    def fields(self):
        return arcpy.ListFields(self.table)

    @lazyprop
    def fieldNames(self):
        return [f.name for f in self.fields if f.type != 'Geometry']

    def get_layer(self):
        return ng911_db.get_911_layer(self._schema.layer)

    def create_feature(self, geometry: arcpy.Geometry=None, **kwargs) -> Feature:
        return Feature(self.fields, geometry, **kwargs)

    def update_feature(self, feature: Feature, **kwargs) -> Feature:
        feature.update(**kwargs)
        return feature

    def fromRow(self, fields: List[str], row: tuple) -> Feature:
        attrs = dict(zip(fields, row))
        geometry = None
        for i,f in enumerate(fields):
            if is_shape_field(f) and isinstance(row[i], arcpy.Geometry):
                geometry = row[i]
                break
        return create_feature(geometry, **attrs)
        