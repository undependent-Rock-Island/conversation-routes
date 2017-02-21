"""Working with trigger lines"""

from __future__ import print_function
from RouteEntities import Point

__test__ = '-90.59597733915027,41.5042308249657,0 -90.59552213220775,41.5031320159257,0'
print(__test__)

__points__ = []
for i, item in enumerate(__test__.split()):
    values = item.split(',')
    __points__.append(Point(float(values[0]), float(values[1]), float(values[2])))

def create_trigger_line_placemark(point_x, point_y):
    """Experiment with trigger lines"""
    # Find slope
    slope = (point_y.latitude - point_x.latitude) / (point_y.longitude - point_x.longitude)

    # Find midpoint
    mid_x = (point_x.longitude + point_y.longitude) / 2
    mid_y = (point_x.latitude + point_y.latitude) / 2

    # Find both end points of trigger line

    print(slope)
    print(mid_x)
    print(mid_y)

create_trigger_line_placemark(__points__[0], __points__[1])
