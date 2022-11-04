import arcpy
import math
from typing import Union

def get_line_direction(line_geometry):
    """returns a tuple of direction in y,x
    ex: line_dir(line) --> ('N','E')
    """
    start_x = line_geometry.firstPoint.X
    end_x = line_geometry.lastPoint.X
    start_y =line_geometry.firstPoint.Y
    end_y = line_geometry.lastPoint.Y

    easting = start_x - end_x
    northing = start_y - end_y

    # get directions
    if easting < 0:
        e_dir = 'E'
    else:
        e_dir = 'W'
    if northing < 0:
        n_dir = 'N'
    else:
        n_dir = 'S'
    return n_dir, e_dir

def get_angle(xy1: Union[arcpy.Point, arcpy.Polyline], xy2: arcpy.Point=None):
    """Calculate azimuth angle from two points. (Zero is north.)
    # Curtis Price, cprice@usgs.gov,  9/18/2013 11:51:10 AM
    """
    if isinstance(xy1, arcpy.Polyline):
        geom = xy1
        xy1 = geom.firstPoint
        xy2 = geom.lastPoint
    if not xy2:
        raise RuntimeError('Missing xy2 parameter')
    try:
        # ArcPy point objects
        x1, y1, x2, y2 = xy1.X, xy1.Y, xy2.X, xy2.Y
    except:
        # xy strings, e.g. "0 0"
        if isinstance(xy1, str) and isinstance(xy2, str):
            xy1, xy2 = xy1.replace('NaN',''), xy2.replace('NaN','')
        x1, y1 = map(float, xy1.split())
        x2, y2 = map(float, xy2.split())
    dx, dy = (x2 - x1, y2 - y1)
    return 90 - math.degrees(math.atan2(dy, dx))


