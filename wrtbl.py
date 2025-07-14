import argparse
import csv
import struct
import sys
from cmn import *

UNIT_TABLE_OFFSET = 0o300 * BYTES_PER_WORD
UNIT_TABLE_SIZE = 0o100 * BYTES_PER_WORD
UNIT_TABLE_END = UNIT_TABLE_OFFSET + UNIT_TABLE_SIZE

# Packs unit table entries provided within specfile csv to a memory buffer.
# Returns numbers of bytes written.
def parse_spec_file_by_file(buff: memoryview, specfile: str):
    assert(specfile != None and buff != None)

    reader = csv.reader(specfile)
    offset = 0
    for row in reader:
        # Is this row valid?
        if(len(row) < 3):
            raise ValueError("Row {} contains fewer than 3 values ({})".format(offset / (3*2), len(row)))

        # Pack the new entry into the table
        struct.pack_into("<HHH", buff, offset, int(row[0], 8), int(row[1], 8), int(row[2], 8))
        offset += 3*2

        # Check if we're going out of bounds.
        if(offset > len(buff)):
            raise IndexError("Unit entries extend past end of buffer")

    return offset

def parse_spec_file_by_path(buff: memoryview, specfile_path: str):
    assert(buff != None and specfile_path != None)

    # Try to parse file at provided path.
    try:
        with open(specfile_path, "r", newline='') as fp:
            return parse_spec_file_by_file(buff, fp)
    except OSError as excpt:
        sys.exit("Failed to open spec file {}: {}".format(arg, excpt))
    except ValueError as excpt:
        sys.exit("Failed to parse spec file text {}: {}".format(arg, excpt))

def parse_spec_file_list_by_path(buff: memoryview, specfile_paths: list):
    assert(buff != None and specfile_paths != None)

    # Produce a warning if no specfile paths were provided.
    # This is _fine_, it won't break anything, but is kinda weird.
    if(len(specfile_paths) == 0):
        print("WARN: No specfile paths provided.")

    # Parse all provided specfiles into buffer.
    offset = 0
    for path in specfile_paths:
        stride = parse_spec_file_by_path(buff[offset:], path)
        if(stride == 0):
            print("WARN: Specfile '{}' contains no unit table entries.".format(path))
        offset += stride

        # Check if we're going out of bounds.
        if(offset > UNIT_TABLE_SIZE):
            sys.exit("Attempting to write too many unit table entries!")

    # Add a terminator + patched loader constant.
    struct.pack_into("<H", buff, offset, 0o7777)
    struct.pack_into("<H", buff, 0o77*BYTES_PER_WORD, 0o7775)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='DIAL-MS Unit Table Writer', description='Setup the unit table in a DIAL-MS image using CSV config files.')
    parser.add_argument("spec", nargs="*", help="Unit table CSV specification file path(s).")
    parser.add_argument("-o", "--output-path", required=True, help="Output image path.")
    parser.add_argument("-i", "--input-path", required=True, help="Input image path.")
    parsed = parser.parse_args(sys.argv[1:])

    # Create a copy of our input and open it for reading & writing.
    image_file = copy_open_file(parsed.output_path, parsed.input_path, "rb+")

    # Read controller block.
    try:
        controller_block = memoryview(read_tape_block(image_file, IO_ROUTINES_BLOCK))
    except OSError as excpt:
        sys.exit("Failed to read controller block from {}: {}".format(parsed.output_path, excpt))
    if(len(controller_block != BYTES_PER_BLOCK)):
        sys.exit("Failed to read full controller block from {}".format(parsed.output_path))

    # Generate and write new table.
    parse_spec_file_list_by_path(controller_block[UNIT_TABLE_OFFSET:UNIT_TABLE_END], parsed.spec)

    # Write it back.
    try:
        written = write_tape_block(image_file, controller_block, IO_ROUTINES_BLOCK)
    except OSError as excpt:
        sys.exit("Failed to write controller block back to {}: {}".format(parsed.output_path, excpt))
    if(written != BYTES_PER_BLOCK):
        sys.exit("Failed to write full controller block back to {}: {}".format(parsed.output_path, excpt))

    sys.exit(0)
