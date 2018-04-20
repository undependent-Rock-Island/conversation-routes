from lxml import etree
from RouteEntities import StreetBlock, Conversation, ConversationRoute, populate_lines

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def get_kml_namespace():
    """Returns standard KML namespaces"""
    return {'kml': 'http://www.opengis.net/kml/2.2',
            'gx' : 'http://www.google.com/kml/ext/2.2'}

def read_street_blocks(document_path):
    """Read in street blocks from KML document"""
    doc = etree.parse(document_path)
    namespace = get_kml_namespace()

    folder = doc.xpath("//kml:Folder[./kml:name[starts-with(.,'STREETBLOCKS ')]]",
                       namespaces=namespace)[0]

    for placemark in folder.xpath('.//kml:Placemark', namespaces=namespace):
        yield StreetBlock(placemark[0].text, placemark[3][1].text.strip())

def read_conversations(document_path, street_blocks):
    """Read in conversation routes from KML document"""
    doc = etree.parse(document_path)
    namespace = get_kml_namespace()

    # Cache style -> color maps
    style_dict = {}
    for style in doc.xpath('//kml:Style', namespaces=namespace):
        style_dict['#' + style.attrib['id']] = style[0][0].text

    # Cache the style maps
    style_map_dict = {}
    for style_map in doc.xpath('//kml:StyleMap', namespaces=namespace):
        style_url = style_map[0].xpath('.//kml:styleUrl', namespaces=namespace)
        style_map_dict['#' + style_map.attrib['id']] = style_dict[style_url[0].text]

    folder = doc.xpath("//kml:Folder", namespaces=namespace)[0]
    subFolders = folder.xpath("./kml:Folder", namespaces=namespace)

    for subFolder in subFolders:
        yield Conversation(subFolder[0].text, list(read_conversation_routes(subFolder, namespace, style_map_dict, street_blocks)))

def read_conversation_routes(folder, namespace, style_map_dict, street_blocks):
    for placemark in folder.xpath('.//kml:Placemark', namespaces=namespace):
        style_url = placemark.xpath('.//kml:styleUrl', namespaces=namespace)
        coordinates = placemark.xpath('.//kml:LineString/kml:coordinates', namespaces=namespace)
        color = style_map_dict[style_url[0].text]

        rating = -1
        #ff12ff0a for green?
        if color == 'ff00ff55': # Green
            rating = 3
        elif color == 'ff00ffff': # Yellow
            rating = 2
        elif color == 'ff0000ff': # Red
            rating = 1

        if coordinates != []:
            lines = list(populate_lines(coordinates[0].text.strip()))
            yield ConversationRoute(rating, find_overlapping_streetblocks(street_blocks, lines))

def find_overlapping_streetblocks(street_blocks, path_measure_lines):
    blocks = []

    for block in street_blocks:
        if is_block_overlapping(block, path_measure_lines):
            blocks.append(block)

    return blocks;

def is_block_overlapping(block, path_measure_lines):
    for trigger_line in block.trigger_lines:
            for path_measure_line in path_measure_lines:
                if lines_cross(trigger_line, path_measure_line):
                    return True

    return False

def ccw(A,B,C):
    return (C.latitude-A.latitude) * (B.longitude-A.longitude) > (B.latitude-A.latitude) * (C.longitude-A.longitude)

# Return true if line segments AB and CD intersect
def intersect(A,B,C,D):
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

def lines_cross(a, b):
    return intersect(a.point1, a.point2, b.point1, b.point2)
    
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

def create_placemark(parent, name, line, styleId):
    placemark = create_node(parent, "Placemark", name)
    append_node_with_text(placemark, "visibility", "0")
    append_node_with_text(placemark, "styleUrl", "#" + styleId)

    line_string = etree.SubElement(placemark, "LineString")
    append_node_with_text(line_string, "tessellate", "1")
    append_node_with_text(line_string, "coordinates", str(line))

def write_trigger_lines_kml(output_path, street_blocks):
    """Create a KML file with trigger lines"""
    kml = etree.Element('kml', nsmap=get_kml_namespace())
    document = create_node(kml, "Document", "Trigger Lines")
    #folder = create_folder(document, "Trigger Lines")

    # Add styles
    append_line_style(document, "purple", "FF00A5FF", 2)
    append_line_style(document, "highlight", "ffaaaaaa", 2)
    append_style_map(document, "StyleMap", "purple", "highlight")

    for block in street_blocks:
        for trigger_line in block.trigger_lines:
            create_placemark(document, block.name, trigger_line, "StyleMap")

    with open(output_path, 'w') as generated_kml:
        generated_kml.write('<?xml version="1.0" encoding="UTF-8"?>' '\n')
        generated_kml.write(etree.tounicode(kml, pretty_print=True))
        generated_kml.close()
