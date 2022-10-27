import math
import arcpy

def extended_coord(fp, lp, dist):
    """https://gis.stackexchange.com/questions/71645/extending-line-by-specified-distance-in-arcgis-for-desktop

    Computes new coordinates x3,y3 at a specified distance
    along the prolongation of the line from x1,y1 to x2,y2
    """
    coords = [(fp.X, fp.Y), (lp.X, lp.Y)]
    (x1,y1),(x2,y2) = coords
    dx = x2 - x1
    dy = y2 - y1
    linelen = math.hypot(dx, dy)

    x3 = x2 + dx/linelen * dist
    y3 = y2 + dy/linelen * dist
    return arcpy.Point(x3, y3)


def flip_array(array):
    """flips order of points or objects in array"""
    flipped = arcpy.Array()
    for i in range(array.count-1, -1, -1):
        flipped.append(array.getObject(i))

    for i in range(array.count):
        array.replace(i, flipped.getObject(i))


def midpoint(point_a, point_b):
    """returns the midpoint of a line"""
    x1 = point_a.X
    y1 = point_a.Y
    x2 = point_b.X
    y2 = point_b.Y

    # Find midpoint
    x = (x1 + x2) / 2.0
    y = (y1 + y2) / 2.0
    return (x, y)

def line_dir(line_geometry):
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

def get_angle(xy1, xy2):
    """Calculate azimuth angle from two points. (Zero is north.)

    # Curtis Price, cprice@usgs.gov,  9/18/2013 11:51:10 AM
    """
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

class Line(arcpy.Polyline):
    def __init__(self, geometry=None, firstPoint=None, lastPoint=None, array=None, sr=None):
        if not geometry:
            raise RuntimeError('NULL Geometry found!')
        if isinstance(sr, int):
            sr = arcpy.SpatialReference(sr)

        if geometry and isinstance(geometry, arcpy.Polyline):
            if not sr:
                sr = geometry.spatialReference
            else:
                if sr != geometry.spatialReference and sr.name.lower() != 'unknown':
                    geometry = arcpy.Polyline(arcpy.Array(geometry.getPart(i) for i in range(geometry.partCount)),
                                              geometry.spatialReference).projectAs(sr)
            super(Line, self).__init__(arcpy.Array(geometry.getPart(i) for i in range(geometry.partCount)), sr)

        elif firstPoint and lastPoint:
            if isinstance(firstPoint, arcpy.Point) and isinstance(lastPoint, arcpy.Point):
                super(Line, self).__init__(arcpy.Array([firstPoint, lastPoint]), sr)

            elif isinstance(firstPoint, (list, tuple)) and isinstance(lastPoint, (list, tuple)):
                super(Line, self).__init__(arcpy.Array([arcpy.Point(*firstPoint), arcpy.Point(*lastPoint)]), sr)

            elif array and isinstance(array, arcpy.Array):
                super(Line, self).__init__(array, sr)

    @staticmethod
    def getAngle(first_pt, last_pt):
        return get_angle(first_pt, last_pt)

    @property
    def isSinglePart(self):
        return not self.isMultipart

    @property
    def angle(self):
        """gets the line's angle between first and last point"""
        return self.getAngle(self.firstPoint, self.lastPoint)

    @property
    def direction(self):
        return line_dir(self)

    @property
    def bearing(self):
        """gets the bearing between the first and last point"""
        return quadrant_bearing(self)

    @property
    def midpoint(self):
        """gets the line's midpoint between first and last point"""
        return arcpy.Point(*midpoint(self.firstPoint, self.lastPoint))

    def getMidpoint(self):
        """returns the midpoint as an arcpy.PointGeometry().  Use midpoint property
        if you just want to get an arcpy.Point()"""
        return arcpy.PointGeometry(self.midpoint, self.spatialReference)

    def extend(self, distance, end=True):
        """extends line by specefied distance

        Required:
            distance -- distance in units of line to extend

        Optional:
            end -- boolean to extend end of line.  Default is True,
                set to False if you want to extend the start of line.
        """
        arr = arcpy.Array()
        for pi in range(self.partCount):
            part = self.getPart(pi)

            if part.count < 2:
                continue

            # current line array (use generator in case many vertices)
            line_arr = arcpy.Array()
            for i in range(part.count):
                line_arr.append(part.getObject(i))

            if end:
                fp, lp = part.getObject(part.count-2), part.getObject(part.count-1)
                index = part.count
            else:
                fp, lp = part.getObject(1), part.getObject(0) # flip to go the other way
                index = 0

            # add extension point
            np = extended_coord(fp, lp, distance)
            line_arr.insert(index, np)

            # add to array
            arr.append(line_arr)

        return arcpy.Polyline(arr, self.spatialReference)

    def fixedLength(self, length, adjust_end=True):
        """returns a line at a fixed length

        if the length is > the line's current length, it will extend to that
        length, if < the current length, will trim line to desired length

        Required:
            length -- desired length

        Optional:
            adjust_end -- boolean to adjust end of line to meet desired length.
                Default is True, set to False if you want to extend the start of line.
        """
        if self.isMultipart:
            print('cannot set multipart lines to fixed length!')
            return self

        if length < self.length:
            # trim line
            if adjust_end:
                return self.segmentAlongLine(0, length)
            else:
                return self.segmentAlongLine(self.length-length, self.length)

        else:
            # extend line
            return self.extend(length - self.length, adjust_end)


    def flip(self):
        """flips line direction for all parts"""
        arr = arcpy.Array()
        for pi in range(self.partCount):
            part = self.getPart(pi)
            flip_array(part)
            arr.append(part)
        return arcpy.Polyline(arr, self.spatialReference)