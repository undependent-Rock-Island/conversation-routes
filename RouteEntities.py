"""Route entities"""

import math

def populate_lines(coordinates):
    """Populate lines list from text coordinates"""
    points = []

    for item in coordinates.split():
        values = item.split(',')
        points.append(Point(float(values[0]), float(values[1])))

    for i in range(0, len(points) - 1):
        yield Line(points[i], points[i+1])

class RouteStep(object):
    """One block step along a route."""
    def __init__(self, block_id, rating):
        self.block_id = block_id
        self.rating = rating

class ConversationRoute(object):
    """A route that was mentioned during a conversation."""
    def __init__(self, rating, coordinates):
        self.lines = list(populate_lines(coordinates))
        self.rating = rating

class StreetBlock(object):
    """A street block in Rock Island."""
    def __init__(self, name, coordinates):
        self.name = name
        self.lines = list(populate_lines(coordinates))
        self.trigger_lines = []

    def populate_trigger_lines(self, distance):
        """Populate trigger lines for this street block"""
        for line in self.lines:
            self.trigger_lines.append(
                self.find_line_through_midpoint(distance, line.midpoint(), -1 / line.slope()))

    def find_line_through_midpoint(self, distance, point, slope):
        """Find line through midpoint"""
        k = distance / (math.sqrt(1 + slope ** 2))
        point_neg = Point(point.longitude - k, point.latitude - (k * slope))
        point_pos = Point(point.longitude + k, point.latitude + (k * slope))
        return Line(point_neg, point_pos)

class Point(object):
    """A single point on the globe"""
    def __init__(self, longitude, latitude):
        self.longitude = longitude
        self.latitude = latitude

    def __str__(self):
        return '{0},{1},0'.format(self.longitude, self.latitude)

class Line(object):
    """A line connecting two points on the globe"""
    def __init__(self, p1, p2):
        self.point1 = p1
        self.point2 = p2

    def slope(self):
        """Find slope of the line"""
        rise = self.point2.latitude - self.point1.latitude
        run = self.point2.longitude - self.point1.longitude
        return rise / run

    def midpoint(self):
        """Find the midpoint of the line"""
        mid_x = (self.point1.longitude + self.point2.longitude) / 2
        mid_y = (self.point1.latitude + self.point2.latitude) / 2
        return Point(mid_x, mid_y)

    def __str__(self):
        return '{0} {1}'.format(self.point1, self.point2)
