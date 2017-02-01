from lxml import etree

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
