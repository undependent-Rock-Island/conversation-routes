from lxml import etree
from RouteEntities import StreetBlock, PassThroughFolder, Conversation, ConversationFolder, ConversationRoute, Color, populate_lines

color_3 = Color(255, 0, 255, 0) # 'ff00ff00' Green
color_2 = Color(255, 255, 255, 0) # 'ff00ffff' Yellow
color_1 = Color(255, 255, 0, 0) # 'ff0000ff' Red
color_non_trad = Color(255, 255, 0, 255) # Purple
walking_folder_name = "Walking"
biking_folder_name = "Biking"

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

def create_pass_through_folder(folder_root, style_nodes_dict, namespace):
    style_urls = folder_root.xpath('.//kml:styleUrl', namespaces=namespace)
    styles = []
    
    for url in style_urls:
        styles.extend(style_nodes_dict[url.text])

    return PassThroughFolder(folder_root, styles)

def read_conversations(document_path, folder_name, street_blocks):
    """Read in conversation routes from KML document"""
    doc = etree.parse(document_path)
    namespace = get_kml_namespace()

    # Cache style -> color maps
    style_dict = {}
    for style in doc.xpath('//kml:Style', namespaces=namespace):
        style_dict['#' + style.attrib['id']] = style

    # Cache the style maps
    style_map_dict = {}
    style_nodes_dict = {}
    for style_map in doc.xpath('//kml:StyleMap', namespaces=namespace):
        style_url = style_map.xpath('.//kml:styleUrl', namespaces=namespace)
        style_map_dict['#' + style_map.attrib['id']] = style_dict[style_url[0].text]
        
        # Add all needed nodes for this style map
        style_nodes_dict['#' + style_map.attrib['id']] = [style_map, style_dict[style_url[0].text], style_dict[style_url[1].text]]

    folder = doc.xpath("//kml:Folder[./kml:name[text()='" + folder_name + "']]", namespaces=namespace)[0]
    residentFolders = folder.xpath("./kml:Folder", namespaces=namespace)

    for residentFolder in residentFolders:
        subFolder_mapping = {}
        pass_through_nodes = []

        for subFolder in residentFolder.xpath("./kml:Folder", namespaces=namespace):
            subFolderName = subFolder[0].text

            if (subFolderName == walking_folder_name or subFolderName == biking_folder_name):
                subFolder_mapping[subFolderName] = read_conversation_routes(subFolder, namespace, style_map_dict, street_blocks, style_nodes_dict)
            else:
                pass_through_nodes.append(create_pass_through_folder(subFolder, style_nodes_dict, namespace))

        yield Conversation(residentFolder[0].text, subFolder_mapping, pass_through_nodes)

def read_conversation_routes(folder, namespace, style_map_dict, street_blocks, style_nodes_dict):
    routes = []
    nontraditional = []
    
    for placemark in folder.xpath('.//kml:Placemark', namespaces=namespace):
        style_url = placemark.xpath('.//kml:styleUrl', namespaces=namespace)
        coordinates = placemark.xpath('.//kml:LineString/kml:coordinates', namespaces=namespace)
        color = style_map_dict[style_url[0].text][0][0].text

        if coordinates != []:      
            rating = -1
        
            if color == str(color_3): # Green
                rating = 3
            elif color == str(color_2): # Yellow
                rating = 2
            elif color == str(color_1): # Red
                rating = 1
            
            if rating > 0.0:
                # This is a regular route
                lines = list(populate_lines(coordinates[0].text.strip()))
                routes.append(ConversationRoute(rating, find_overlapping_streetblocks(street_blocks, lines)))
            else:
                # This is non traditional
                nontraditional.append(create_pass_through_folder(placemark, style_nodes_dict, namespace))

    return ConversationFolder(routes, nontraditional)

def find_overlapping_streetblocks(street_blocks, path_measure_lines):
    blocks = []

    for block in street_blocks:
        if is_block_overlapping(block, path_measure_lines):
            blocks.append(block)

    return blocks

def is_block_overlapping(block, path_measure_lines):
    for trigger_line in block.trigger_lines:
            for path_measure_line in path_measure_lines:
                if lines_cross(trigger_line, path_measure_line):
                    return True

    return False

def ccw(A,B,C):
    return (C.latitude - A.latitude) * (B.longitude - A.longitude) > (B.latitude - A.latitude) * (C.longitude - A.longitude)

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

        # Add named conversation route groups
        for route_folder_name, route_folder in conversation.route_groups.items():
            route_folder_node = create_folder(resident, route_folder_name)

            # Create category folders
            np = create_folder(route_folder_node, "NP")
            hm = create_folder(route_folder_node, "HM")
            nw = create_folder(route_folder_node, "NW")

            for route in route_folder.routes:
                for block in route.street_blocks:
                    for line in block.lines:
                        if route.rating == 1.0:
                            create_placemark(nw, block.name, line, "Color" + str(route.rating))
                        elif route.rating == 2.0:
                            create_placemark(hm, block.name, line, "Color" + str(route.rating))
                        elif route.rating == 3.0:
                            create_placemark(np, block.name, line, "Color" + str(route.rating))
                        else:
                            print(block.name)

            if route_folder.nontraditional != []:
                nt_folder = create_folder(route_folder_node, "nontraditional")
                for nt in route_folder.nontraditional:
                    nt_folder.append(nt.folder_root)

                    for style in nt.styles:
                        document.append(style)

        # Add extra stuff (pass through nodes)
        for pass_through in conversation.pass_through_nodes:
            resident.append(pass_through.folder_root)
            
            for style in pass_through.styles:
                document.append(style)

    rating_sum = {}
    rating_count = {}

    for conversation in conversations:
        for route_folder_name, route_folder in conversation.route_groups.items():
            for route in route_folder.routes:
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
        return str(color_2.merge_color(color_3, rating - 2.0))