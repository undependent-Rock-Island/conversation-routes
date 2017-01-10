from __future__ import print_function
import csv
import math
from lxml import etree

class Point(object):
    """A single point on the globe"""
    def __init__(self, longitude, latitude, altitude):
        self.longitude = longitude
        self.latitude = latitude
        self.altitude = altitude

class RouteStep(object):
    """One block step along a route."""
    def __init__(self, blockId, rating):
        self.blockId = blockId
        self.rating = rating

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def append_node_with_text(parent, tagName, text):
    node = etree.SubElement(parent, tagName)
    node.text = text

def create_node(parent, tagName, name):
    folder = etree.SubElement(parent, tagName)
    append_node_with_text(folder, "name", name)
    return folder

def create_folder(parent, name):
    return create_node(parent, "Folder", name)

def create_rating_folder(parent, num):
    return create_folder(parent, "Rating" + str(num))

def append_line_style(parent, id, color, width):
    style = etree.SubElement(parent, "Style", id=id)
    lineStyle = etree.SubElement(style, "LineStyle")
    append_node_with_text(lineStyle, "color", color)
    append_node_with_text(lineStyle, "width", str(width))

def append_style_map(parent, id, normalId, highlightId):
    styleMap = etree.SubElement(parent, "StyleMap", id=id)
    append_style_map_pair(styleMap, "normal", normalId)
    append_style_map_pair(styleMap, "highlight", highlightId)

def append_style_map_pair(parent, key, styleId):
    pair = etree.SubElement(parent, "Pair")
    append_node_with_text(pair, "key", key)
    append_node_with_text(pair, "styleUrl", "#" + styleId)

def parseCsv(filePath, routesPerson, routesComp):
    with open(filePath, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        reader.next() # skip headers
        
        currentResident = None
        for row in reader:
            if row[1] != "":
                currentResident = row[1]
                routesPerson[currentResident] = []

            for i in chunks(row[5:], 2):
                if i[0] != "":
                    if (i[1] == ""):
                        print("Missing rating: " + i[0])
                    else:
                        blockId = i[0]
                        rating = int(i[1])
                        routesPerson[currentResident].append(RouteStep(blockId, rating))

                        # Populate compilations
                        if not routesComp.has_key(blockId):
                            routesComp[blockId] = []
                        routesComp[blockId].append(rating)

def fill_in_route_steps(routes, personFolder, person, coordinatesDict):

    ratingsDict = {
        1 : create_rating_folder(personFolder, 1),
        2 : create_rating_folder(personFolder, 2),
        3 : create_rating_folder(personFolder, 3)
    }

    for route_step in routes[person]:
        # Put the placemark in the right folder
        parentFolder = ratingsDict[route_step.rating]
        
        placemark = create_node(parentFolder, "Placemark", route_step.blockId)
        append_node_with_text(placemark, "visibility", "0")
        append_node_with_text(placemark, "styleUrl", "#" + str(route_step.rating) + "StyleMap")

        line_string = etree.SubElement(placemark, "LineString")
        append_node_with_text(line_string, "tessellate", "1")
        coordinates = etree.SubElement(line_string, "coordinates")
        
        if coordinatesDict.has_key(route_step.blockId):
            coordinates.text = coordinatesDict[route_step.blockId]
        else:
            print("Unknown streetblock2: \"" + route_step.blockId + "\"")

    # Remove ratings folders with no placemarks
    for rating in ratingsDict.keys():
        if len(ratingsDict[rating]) <= 1: personFolder.remove(ratingsDict[rating])

#  Read in street block mappings
print("Reading street blocks ... ", end="")

dockml = etree.parse('doc.kml')
root = dockml.getroot()
NSMAP = {'kml': 'http://www.opengis.net/kml/2.2', 'gx' : 'http://www.google.com/kml/ext/2.2'}

folder = dockml.xpath("//kml:Folder[./kml:name = 'STREETBLOCKS 11/8/16']", namespaces = NSMAP)[0]

coordinatesDict = {}
for placemark in folder.xpath('.//kml:Placemark', namespaces=NSMAP):
    #print(placemark[0].text, placemark[3][1].text.strip())
    coordinatesDict[placemark[0].text] = placemark[3][1].text.strip()

print(len(coordinatesDict))

__test__ = '-90.59597733915027,41.5042308249657,0 -90.59552213220775,41.5031320159257,0'
print(__test__)

points = []
for i, item in enumerate(__test__.split()):
    values = item.split(',')
    points.append(Point(float(values[0]), float(values[1]), float(values[2])))

def createTriggerLinePlacemark(point_x, point_y):
    slope = (point_y.latitude - point_x.latitude) / (point_y.longitude - point_x.longitude)
    mid_x = (point_x.longitude + point_y.longitude) / 2
    mid_y = (point_x.latitude + point_y.latitude) / 2

    # Find slope
    # Find midpoint
    # Find both end points of trigger line

    print(slope)
    print(mid_x)
    print(mid_y)

createTriggerLinePlacemark(points[0], points[1])
