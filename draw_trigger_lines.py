"""Script to draw trigger lines for a given street blocks KML"""

from __future__ import print_function
from lxml import etree
import xml_utils as xu
import datetime

# Pull in mappings.kml file
doc = etree.parse('mappings.kml')

# Read street blocks from KML file
__street_blocks__ = list(xu.read_street_blocks(doc))
print('Street blocks read.')

# Initialize lines on each street block
for block in __street_blocks__:
    block.populate_trigger_lines(0.0002)
print('Trigger lines populated on street blocks.')

# Write out trigger line KML
xu.write_trigger_lines_kml('trigger_lines.kml', __street_blocks__)
print('Trigger lines KML written.')

# Read in paths and color (i.e. rating)
__all_conversations__ = list(xu.read_conversations(doc, __street_blocks__))
print('Hand drawn conversations read and street blocks assigned.')

# Write out resident street blocks and compilations
d = datetime.datetime.today()
xu.write_final_kml('final_output_' + d.strftime("%d%b%Y") + '.kml', __all_conversations__)
print('Python conversations and compilations written.')


# handle hypothetical better -> street blocks
