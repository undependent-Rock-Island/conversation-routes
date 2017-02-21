"""Route entities"""

class RouteStep(object):
    """One block step along a route."""
    def __init__(self, block_id, rating):
        self.block_id = block_id
        self.rating = rating

class Point(object):
    """A single point on the globe"""
    def __init__(self, longitude, latitude, altitude):
        self.longitude = longitude
        self.latitude = latitude
        self.altitude = altitude

class Line(object):
    """A line connecting two points on the globe"""
    def __init__(self, p1, p2):
        self.point1 = p1
        self.point2 = p2

    def midpoint(self):
        mid_x = (self.point1.longitude + self.point2.longitude) / 2
        mid_y = (self.point1.latitude + self.point2.latitude) / 2
        return Point(mid_x, mid_y, 0)
