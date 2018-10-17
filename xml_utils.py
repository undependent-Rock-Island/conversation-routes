from lxml import etree
from RouteEntities import StreetBlock, Conversation, ConversationRoute, Color, populate_lines

color_3 = Color(255, 85, 255, 0) # 'ff00ff55'
color_2 = Color(255, 255, 255, 0) # 'ff00ffff'
color_1 = Color(255, 255, 0, 0) # 'ff0000ff'

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
        if color == str(color_3): # Green
            rating = 3
        elif color == str(color_2): # Yellow
            rating = 2
        elif color == str(color_1): # Red
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

def write_final_kml(output_path, conversations):
    """Create the final KML output file"""
    kml = etree.Element('kml', nsmap=get_kml_namespace())
    document = create_node(kml, "Document", "Final Python Output")
    residents = create_folder(document, "Residents")
    compilations = create_folder(document, "Compilations")

    # Add styles
    append_line_style(document, "purple", "FFFF01EA", 2)
    append_line_style(document, "color_3", str(color_3), 2)
    append_line_style(document, "color_2", str(color_2), 2)
    append_line_style(document, "color_1", str(color_1), 2)
    append_line_style(document, "highlight", "ffaaaaaa", 2)
    append_style_map(document, "Color3", "color_3", "highlight")
    append_style_map(document, "Color2", "color_2", "highlight")
    append_style_map(document, "Color1", "color_1", "highlight")
    append_style_map(document, "Color-1", "purple", "highlight")

    color_dict = {}

    color_dict[3.0] = "Color3"
    color_dict[2.0] = "Color2"
    color_dict[1.0] = "Color1"
    color_dict[-1.0] = "Color-1"

    for conversation in conversations:
        resident = create_folder(residents, conversation.residentName)
        for route in conversation.routes:
            for block in route.street_blocks:
                for line in block.lines:
                    create_placemark(resident, block.name, line, "Color" + str(route.rating))

    rating_sum = {}
    rating_count = {}

    for conversation in conversations:
        for route in conversation.routes:
            if route.rating < 0:
                continue

            for block in route.street_blocks:
                if block in rating_sum:
                    rating_sum[block] += route.rating
                else:
                    rating_sum[block] = route.rating

                if block in rating_count:
                    rating_count[block] += 1
                else:
                    rating_count[block] = 1

    for block in rating_sum.keys():
        rating = rating_sum[block] / rating_count[block]
        color = get_color_string(rating)

        if color not in color_dict:
            append_line_style(document, "color_" + color, color, 2)
            append_style_map(document, "Color-" + color, "color_" + color, "highlight")
            color_dict[color] = "Color-" + color

        for line in block.lines:
            create_placemark(compilations, block.name, line, color_dict[color])

    with open(output_path, 'w') as generated_kml:
        generated_kml.write('<?xml version="1.0" encoding="UTF-8"?>' '\n')
        generated_kml.write(etree.tounicode(kml, pretty_print=True))
        generated_kml.close()

def get_color_string(rating):
    """Convert a rating floating point value to a color string"""
    if rating == 1.0: return str(color_1)
    if rating == 2.0: return str(color_2)
    if rating == 3.0: return str(color_3)

    if rating < 2.0:
        return str(color_1.merge_color(color_2, rating - 1.0))

    if rating < 3.0:
        return str(color_1.merge_color(color_2, rating - 2.0))