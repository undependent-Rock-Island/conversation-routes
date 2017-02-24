"""Working with trigger lines"""

from __future__ import print_function
from xml_utils import read_street_blocks, write_trigger_lines_kml

# Read street blocks from KML file
__street_blocks__ = list(read_street_blocks('doc.kml'))

# Initialize lines on each street block
for block in __street_blocks__:
    block.populate_trigger_lines(0.0002)

# Write out trigger line KML
write_trigger_lines_kml('trigger_lines.kml', __street_blocks__)
print('Finished')
