import arcpy
from ilng911.core.geometry import get_angle
from ilng911.env import get_ng911_db
from ilng911.core.common import Feature
from ilng911.schemas import DataSchema
from ilng911.core.fields import STREET_FIELDS, ROAD_SIDE_ATTRS
from ilng911.core.address import STREET_ATTRIBUTES
from ilng911.logging import log
from typing import Union

def mixin_road_properties(line: Feature, angle_tolerance=15) -> Feature:
    """will attempt to find a connected road, and if located will mix in common street properties

    Args:
        line (Feature): a road centerline feature
        angle_tolerance (int, optional): the minimum angle tolerance to determine match. Defaults to 15.

    Returns:
        Feature: the original feature, which may or may not have mixed in attributes
    """
    ng911_db = get_ng911_db()
    lyr = ng911_db.get_911_layer(ng911_db.types.ROAD_CENTERLINE)

    arcpy.management.SelectLayerByLocation(lyr, 'WITHIN_A_DISTANCE', line.geometry, '50 FEET')
    with arcpy.da.SearchCursor(lyr, ['SHAPE@', 'OID@']) as rows:
        nearby = [r for r in rows]

    if not nearby:
        return line
    
    roadSchema = DataSchema(ng911_db.types.ROAD_CENTERLINE)
    match = None
    if len(nearby) == 1:
        match = roadSchema.find_feature_from_oid(nearby[0][1])
    else:
        angles = {get_angle(n[0]): n for n in nearby}
        similar = min(list(angles.keys()))
        if abs(similar - get_angle(line.geometry)) < angle_tolerance:
            match = roadSchema.find_feature_from_oid(angles.get(similar)[1])


    if match:
        sf = STREET_FIELDS
        log(f'found similar road segment with OID: {match.get(match.oidField)} ("{match.get(sf.NAME)}"), attempting to mixin properties')
        log(f'match attributes: {match.attributes}')
        # mixin road attributes
        skip = [sf.TO_ADDRESS_LEFT, sf.FROM_ADDRESS_LEFT, sf.TO_ADDRESS_RIGHT, sf.FROM_ADDRESS_RIGHT, sf.GUID]
        whitelist = [f for f in (STREET_ATTRIBUTES + ROAD_SIDE_ATTRS) if f not in skip]
        log(f'white listed attributes to mixin: {whitelist}')
        updates = {attr: match.attributes.get(attr) for attr in whitelist}
        log(f'mixing in similar road attributes: {updates}')
        line.update(**updates)

        # snap geometry
        sr = line.geometry.spatialReference
        fpDist = line.geometry.distanceTo(match.geometry.firstPoint)
        lpDist = line.geometry.distanceTo(match.geometry.lastPoint)
        if fpDist < lpDist:
            log("feature is closer to match's first point")
            # first point is closer
            fp = arcpy.PointGeometry(line.geometry.firstPoint, sr).distanceTo(match.geometry.firstPoint)
            lp = arcpy.PointGeometry(line.geometry.lastPoint, sr).distanceTo(match.geometry.firstPoint)
        else:
            # last point is closer
            log("feature is closer to match's last point")
            fp = arcpy.PointGeometry(line.geometry.firstPoint, sr).distanceTo(match.geometry.lastPoint)
            lp = arcpy.PointGeometry(line.geometry.lastPoint, sr).distanceTo(match.geometry.lastPoint)

        # rebuild part arrays
        
        allParts = arcpy.Array()
        if line.geometry.partCount == 1:
            part = line.geometry.getPart(0)
            arr = arcpy.Array([p for p in part])
            if fp < lp:
                # snap to first point
                arr.replace(0, match.geometry.firstPoint)
                log('snapped geometry to first point')
            else:
                arr.replace(arr.count-1, match.geometry.lastPoint)
                log('snapped geometry to last point')
            allParts.append(arr)
        
        else:
            # multipart line, only replace nearby part
            for part in line.geometry:
                arr = arcpy.Array([p for p in part])
                first = arr.getObject(0)
                last = arr.getObject(arr.count-1)
                targ = first if fp < lp else last
                if targ.X == match.geometry.firstPoint.X and targ.Y == match.geometry.firstPoint.Y:
                    # this is the matching part
                    if fp < lp:
                        # snap to first point
                        arr.replace(0, match.geometry.firstPoint)
                        log('snapped geometry to first point')
                    else:
                        arr.replace(arr.count-1, match.geometry.lastPoint)
                        log('snapped geometry to last point')

                # append the part
                allParts.append(arr)

        line.geometry = arcpy.Polyline(allParts, spatial_reference=sr)

    return line
                



       

    

