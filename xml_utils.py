from lxml import etree
from RouteEntities import StreetBlock, PassThroughFolder, Conversation, ConversationFolder, ConversationCodedFolder, \
    ConversationRoute, Color, populate_lines

color_3 = Color(255, 0, 255, 0)  # 'ff00ff00' Green
color_2 = Color(255, 255, 255, 0)  # 'ff00ffff' Yellow
color_1 = Color(255, 255, 0, 0)  # 'ff0000ff' Red
hyp_color = Color(255, 70, 100, 250)  # fffa6446
non_traditional_color = Color(255, 255, 0, 255)
would_consider_color = Color(255, 70, 100, 250)

walking_folder_name = "W"
biking_folder_name = "B"
hypotheticals_folder_name = "wConsider"
hypothetical_rating = 1000
would_consider_rating = 2000


#  Add a Notes folder to compilation -> 2 sub folders for push pins, avoided
#  intersections and other (white images)
def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def get_kml_namespace():
    """Returns standard KML namespaces"""
    return {'kml': 'http://www.opengis.net/kml/2.2',
            'gx': 'http://www.google.com/kml/ext/2.2'}


def read_street_blocks(doc):
    """Read in street blocks from KML document"""
    namespace = get_kml_namespace()

    folder = doc.xpath("//kml:Folder[./kml:name[starts-with(.,'STREETBLOCKS ')]]",
                       namespaces=namespace)[0]

    for placemark in folder.xpath('.//kml:Placemark', namespaces=namespace):
        yield StreetBlock(placemark[0].text, placemark[2][1].text.strip())


def create_pass_through_folder(folder_root, style_nodes_dict, namespace):
    style_urls = folder_root.xpath('.//kml:styleUrl', namespaces=namespace)
    styles = []

    for url in style_urls:
        styles.extend(style_nodes_dict[url.text])

    return PassThroughFolder(folder_root, styles)


def read_conversations(doc, street_blocks):
    """Read in conversation routes from KML document"""
    namespace = get_kml_namespace()

    # Cache style -> color maps
    style_dict = {}
    for style in doc.xpath('//kml:Style', namespaces=namespace):
        if len(style.attrib) > 0:
            style_dict['#' + style.attrib['id']] = style

    # Cache the style maps
    style_map_dict = {}
    style_nodes_dict = {}
    for style_map in doc.xpath('//kml:StyleMap', namespaces=namespace):
        style_url = style_map.xpath('.//kml:styleUrl', namespaces=namespace)
        style_map_dict['#' + style_map.attrib['id']] = style_dict[style_url[0].text]

        # Add all needed nodes for this style map
        style_nodes_dict['#' + style_map.attrib['id']] = [style_map, style_dict[style_url[0].text],
                                                          style_dict[style_url[1].text]]

    folder = doc.xpath("//kml:Folder[./kml:name[starts-with(.,'hdConversations ')]]", namespaces=namespace)[0]

    residentFolders = folder.xpath("./kml:Folder", namespaces=namespace)

    for residentFolder in residentFolders:

        # if 'Ailin' not in residentFolder[0].text: continue

        print(' Reading conversation ' + residentFolder[0].text)
        subFolder_mapping = {}
        pass_through_nodes = []

        walking_ability = get_walking_ability(residentFolder, namespace)
        biking_ability = get_biking_ability(residentFolder, namespace)

        for subFolder in residentFolder.xpath("./kml:Folder", namespaces=namespace):
            subFolderName = subFolder[0].text

            if subFolderName.lower() == walking_folder_name.lower() or \
                    subFolderName.lower() == biking_folder_name.lower() or \
                    subFolderName.lower() == hypotheticals_folder_name.lower():
                subFolder_mapping[subFolderName] = read_conversation_routes(subFolder, namespace, style_map_dict,
                                                                            street_blocks, style_nodes_dict)
            # elif subFolderName.lower() == hypotheticals_folder_name.lower():
            # for subHypFolder in subFolder.xpath("./kml:Folder",
            # namespaces=namespace):
            #    subHypFolderName = subHypFolder[0].text
            #    hyp_folder_key =
            #    get_hypothetical_folder_key(subHypFolderName)

            #    if subHypFolderName.lower() == walking_folder_name.lower()
            #    or subHypFolderName.lower() == biking_folder_name.lower():
            #        subFolder_mapping[hyp_folder_key] =
            #        read_conversation_routes(subHypFolder, namespace,
            #        style_map_dict, street_blocks, style_nodes_dict)
            else:
                pass_through_nodes.append(create_pass_through_folder(subFolder, style_nodes_dict, namespace))

        yield Conversation(residentFolder[0].text, walking_ability, biking_ability, subFolder_mapping,
                           pass_through_nodes)


def get_walking_ability(folder, namespace):
    description = folder.xpath("./kml:description", namespaces=namespace)[0].text

    abilities = list(filter(None, description.replace('\n', ' ').split(' ')))

    if "WGTD?=Y" in abilities or "GFW?=Y" in abilities:
        if "eWN?=WNOS" in abilities: return "WNOS"
        if "eWN?=WNSSS" in abilities: return "WNSSS"

        raise ValueError('Unknown walking code in description ' + description)

    return None


def get_biking_ability(folder, namespace):
    description = folder.xpath("./kml:description", namespaces=namespace)[0].text
    abilities = list(filter(None, description.replace('\n', ' ').split(' ')))

    if "BGTD?=Y" in abilities or "GFBR?=Y" in abilities:
        if "eBN?=BNCRC" in abilities: return "BNCRC"
        if "eBN?=BNAAS" in abilities: return "BNAAS"

        raise ValueError('Unknown biking code in description ' + description)


def read_conversation_routes(folder, namespace, style_map_dict, street_blocks, style_nodes_dict):
    coded_folders = []

    for subFolder in folder.xpath("./kml:Folder", namespaces=namespace):
        code = subFolder[0].text

        folders = []
        nontraditional = []

        for placemark in subFolder.xpath('.//kml:Placemark', namespaces=namespace):
            style_url = placemark.xpath('.//kml:styleUrl', namespaces=namespace)
            coordinates = placemark.xpath('.//kml:LineString/kml:coordinates', namespaces=namespace)
            color = style_map_dict[style_url[0].text][0][0].text

            if coordinates != []:
                rating = -1

                if color == str(non_traditional_color):
                    nontraditional.append(create_pass_through_folder(placemark, style_nodes_dict, namespace))
                else:
                    if color == str(hyp_color):
                        rating = hypothetical_rating
                    elif color == str(would_consider_color):
                        rating = would_consider_rating
                    elif color == str(color_3):
                        rating = 3  # Green
                    elif color == str(color_2):
                        rating = 2  # Yellow
                    elif color == str(color_1):
                        rating = 1  # Red
                    else:
                        print('WARN: Unknown color ' + color + ' in ' + folder[0].text + '/' + code + '. Skipping ...')
                        continue

                    lines = list(populate_lines(coordinates[0].text.strip()))
                    folders.append(ConversationRoute(rating, find_overlapping_streetblocks(street_blocks, lines)))

        coded_folders.append(ConversationCodedFolder(code, folders, nontraditional))

    return ConversationFolder(folder[0].text, coded_folders)


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


def ccw(A, B, C):
    return (C.latitude - A.latitude) * (B.longitude - A.longitude) > (B.latitude - A.latitude) * (
                C.longitude - A.longitude)


# Return true if line segments AB and CD intersect
def intersect(A, B, C, D):
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)


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
    # folder = create_folder(document, "Trigger Lines")

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

def write_final_kml(output_path, conversations, date):
    """Create the final KML output file"""
    kml = etree.Element('kml', nsmap=get_kml_namespace())
    document = create_node(kml, "Document", "Final Python Output " + date.strftime("%m/%d/%y"))
    residents = create_folder(document, "Conversations")
    compilations = create_folder(document, "Compilations")

    # Add styles
    append_line_style(document, "purple", "FFFF01EA", 2)
    append_line_style(document, "color_3", str(color_3), 2)
    append_line_style(document, "color_2", str(color_2), 2)
    append_line_style(document, "color_1", str(color_1), 2)
    append_line_style(document, "color_hyp", str(hyp_color), 2)
    append_line_style(document, "highlight", "ffaaaaaa", 2)
    append_style_map(document, "Color3", "color_3", "highlight")
    append_style_map(document, "Color2", "color_2", "highlight")
    append_style_map(document, "Color1", "color_1", "highlight")
    append_style_map(document, "ColorHyp", "color_hyp", "highlight")
    append_style_map(document, "Color-1", "purple", "highlight")

    color_dict = {}

    color_dict[3.0] = "Color3"
    color_dict[2.0] = "Color2"
    color_dict[1.0] = "Color1"
    color_dict[hypothetical_rating] = "ColorHyp"
    color_dict[-1.0] = "Color-1"

    # Create one folder for each conversation
    for conversation in conversations:
        resident = create_folder(residents, conversation.residentName)

        hyp_folder = None
        codes = {}

        # Add named conversation route groups
        for route_folder_name, conversation_folder in conversation.conversation_folders.items():
            route_folder_node = None

            # Handle hypothetical differently
            if hypotheticals_folder_name in route_folder_name:
                if hyp_folder is None:
                    hyp_folder = create_folder(resident, hypotheticals_folder_name)

                for coded_folder in conversation_folder.coded_folders:
                    hyp_lines = []

                    for route in coded_folder.routes:
                        for block in route.street_blocks:
                            for line in block.lines:
                                if route.rating == hypothetical_rating:
                                    hyp_lines.append([block.name, line])
                                else:
                                    print(block.name)

                    create_rating_subfolder(hyp_lines, hyp_folder, coded_folder.code, color_dict[hypothetical_rating])

            else:
                for coded_folder in conversation_folder.coded_folders:

                    # Find correct code folder
                    if "GF" in coded_folder.code:
                        if "GF" not in codes:
                            # Create parent GF folder if it does not exist
                            codes["GF"] = create_folder(resident, "GF")
                        # Create biking or walking subfolder within GF
                        codes[coded_folder.code] = create_folder(codes["GF"], coded_folder.code)
                    elif "GTD" in coded_folder.code:
                        if "GTD" not in codes:
                            # Create parent GTD folder if it does not exist
                            codes["GTD"] = create_folder(resident, "GTD")
                        # Create biking or walking subfolder within GTD
                        codes[coded_folder.code] = create_folder(codes["GTD"], coded_folder.code)

                    coded_folder_node = codes[coded_folder.code]

                    # Create category folders
                    np_lines = []
                    hm_lines = []
                    nw_lines = []

                    for route in coded_folder.routes:
                        for block in route.street_blocks:
                            for line in block.lines:
                                if route.rating == 1.0:
                                    nw_lines.append([block.name, line])
                                elif route.rating == 2.0:
                                    hm_lines.append([block.name, line])
                                elif route.rating == 3.0:
                                    np_lines.append([block.name, line])
                                else:
                                    print(block.name)

                    # Only populate folders with children
                    create_rating_subfolder(np_lines, coded_folder_node, "NP", color_dict[3.0])
                    create_rating_subfolder(hm_lines, coded_folder_node, "HM", color_dict[2.0])
                    create_rating_subfolder(nw_lines, coded_folder_node, "NW", color_dict[1.0])

                    # Copy over nontraditional nodes and styles
                    if coded_folder.nontraditional != []:
                        nt_folder = create_folder(coded_folder_node, "nontraditional")
                        for nt in coded_folder.nontraditional:
                            nt_folder.append(nt.folder_root)

                            for style in nt.styles:
                                document.append(style)

        # Add extra stuff (pass through nodes)
        for pass_through in conversation.pass_through_nodes:
            resident.append(pass_through.folder_root)

            for style in pass_through.styles:
                document.append(style)

    create_walking_compilation(document, compilations, conversations, color_dict)
    # create_gradient_compilation(document, compilations, conversations, color_dict)

    with open(output_path, 'w') as generated_kml:
        generated_kml.write('<?xml version="1.0" encoding="UTF-8"?>' '\n')
        generated_kml.write(etree.tounicode(kml, pretty_print=True))
        generated_kml.close()


def create_walking_compilation(document, compilations, conversations, color_dict):
    # top_level_folders = {}

    folder_dict = {}

    for conversation in conversations:
        for route_folder_name, conversation_folder in conversation.conversation_folders.items():

            # if route_folder_name not in top_level_folders:
            #    top_level_folders[route_folder_name] = create_folder(compilations, route_folder_name)

            # top_level_folder = top_level_folders[route_folder_name]

            # Setup folder dictionary
            if route_folder_name not in folder_dict:
                folder_dict[route_folder_name] = {}

            ability_dict = folder_dict[route_folder_name]

            # Setup ability dictionary
            if route_folder_name == walking_folder_name:
                ability_dict_key = conversation.walking_ability
            elif route_folder_name == biking_folder_name:
                ability_dict_key = conversation.biking_ability
            elif route_folder_name == hypotheticals_folder_name:
                ability_dict_key = ''

            if ability_dict_key not in ability_dict:
                ability_dict[ability_dict_key] = {}

            coding_dict = ability_dict[ability_dict_key]

            for coded_folder in conversation_folder.coded_folders:
                if coded_folder.code not in coding_dict:
                    coding_dict[coded_folder.code] = {}

                block_dict = coding_dict[coded_folder.code]

                for route in coded_folder.routes:
                    if route.rating < 0:
                        continue

                    for block in route.street_blocks:
                        if block in block_dict:
                            block_dict[block].append(route.rating)
                        else:
                            block_dict[block] = [route.rating]

    # process codes in a custom order
    def folderSort(val):
        if val == walking_folder_name: return 0
        if val == biking_folder_name: return 1
        if val == hypotheticals_folder_name: return 2
        return 100

    def abilitySort(val):
        if val[0] == 'BNCRC': return 0
        if val[0] == 'BNAAS': return 1
        if val[0] == 'wCB': return 2
        if val[0] == 'WNOS': return 3
        if val[0] == 'WNSSS': return 4
        if val[0] == 'wCw': return 5
        return 100

    # for code in sorted(rating_dict.keys(), key = customSort):
    for folder_name in sorted(folder_dict.keys(), key=folderSort):
        ability_dict = folder_dict[folder_name]
        top_level_folder = create_folder(compilations, folder_name)

        for ability, code_dict in sorted(ability_dict.items(), key=abilitySort):
            if folder_name == hypotheticals_folder_name:
                ability_folder = top_level_folder
            else:
                ability_folder = create_folder(top_level_folder, ability)

            for code, block_dict in code_dict.items():
                code_folder = create_folder(ability_folder, code)

                # Create category folders
                np_lines = []
                hm_lines = []
                nw_lines = []
                hyp_lines = []

                for block, ratings in block_dict.items():
                    rating = calculate_rating(ratings, ability)
                    color = get_color_string(rating)

                    if color not in color_dict:
                        append_line_style(document, "color_" + color, color, 2)
                        append_style_map(document, "Color-" + color, "color_" + color, "highlight")
                        color_dict[color] = "Color-" + color

                    for line in block.lines:
                        if rating == 1.0:
                            nw_lines.append([block.name, line])
                        elif rating == 2.0:
                            hm_lines.append([block.name, line])
                        elif rating == 3.0:
                            np_lines.append([block.name, line])
                        elif rating == hypothetical_rating:
                            hyp_lines.append([block.name, line])
                        else:
                            print(block.name)

                # Only populate folders with children
                create_rating_subfolder(np_lines, code_folder, "NP", color_dict[3.0])
                create_rating_subfolder(hm_lines, code_folder, "HM", color_dict[2.0])
                create_rating_subfolder(nw_lines, code_folder, "NW", color_dict[1.0])

                # Populate Hypothetical street blocks
                for name, line in hyp_lines:
                    create_placemark(code_folder, name, line, color_dict[color])


def calculate_rating(ratings, code):
    modes = compute_mode(ratings)

    if code == "WNOS" or code == "BNCRC":
        return max(modes)

    if code == "WNSSS" or code == "BNAAS":
        return min(modes)

    if code == '':  # hypotheticals
        return max(modes)

    print("Unknown code for rating: " + code)
    return -1


def compute_mode(numbers):
    counts = {}
    modes = []
    maxcount = 0
    for number in numbers:
        if number not in counts:
            counts[number] = 0
        counts[number] += 1
        if counts[number] > maxcount:
            maxcount = counts[number]

    for number, count in counts.items():
        if count == maxcount:
            # print(number, count)
            modes.append(number)

    return modes


def create_gradient_compilation(document, compilations, conversations, color_dict):
    gradient_folder = create_folder(compilations, "Gradients")

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
            create_placemark(gradient_folder, block.name, line, color_dict[color])


def create_rating_subfolder(lines, parent_folder, folder_name, styleId):
    if lines != []:
        folder = create_folder(parent_folder, folder_name)

        for name, line in lines:
            create_placemark(folder, name, line, styleId)


def get_color_string(rating):
    """Convert a rating floating point value to a color string"""
    if rating == 1.0: return str(color_1)
    if rating == 2.0: return str(color_2)
    if rating == 3.0: return str(color_3)
    if rating == hypothetical_rating: return str(hyp_color)

    if rating < 2.0:
        return str(color_1.merge_color(color_2, rating - 1.0))

    if rating < 3.0:
        return str(color_2.merge_color(color_3, rating - 2.0))
