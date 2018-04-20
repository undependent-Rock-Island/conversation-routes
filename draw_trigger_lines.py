"""Script to draw trigger lines for a given street blocks KML"""

from __future__ import print_function
from xml_utils import read_street_blocks, write_trigger_lines_kml
import xml_utils as xu

# Read street blocks from KML file
__street_blocks__ = list(read_street_blocks('doc.kml'))

# Initialize lines on each street block
for block in __street_blocks__:
    block.populate_trigger_lines(0.0002)

# Write out trigger line KML
write_trigger_lines_kml('trigger_lines.kml', __street_blocks__)
print('Trigger lines written.')

# Read in paths and color (i.e. rating)
__all_conversations__ = list(xu.read_conversations('hdRESIDENTS.kml', __street_blocks__))

#Write out resident street blocks and compilations
print('hi')
#for route in __17_tanner__:
#    print(route.rating)
