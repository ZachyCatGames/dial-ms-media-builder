import argparse
import csv
import struct
import sys
from cmn import *

BUILD_IMG_TBL_LOC = 0o7300 * BYTES_PER_WORD
BUILD_IMG_TBL_LEN = 0o100 * BYTES_PER_WORD

def concat_spec(specs: list):
    csv_dat = ""
    for arg in specs:
        try:
            with open(arg, "r", newline='') as fp:
                csv_dat += fp.read()
        except Exception as excpt:
            print("Failed to open spec file {}: {}".format(arg, excpt))
    return csv_dat

def gen_table_group(csv_data):
    reader = csv.reader(csv_data.splitlines())
    entries = bytearray(BUILD_IMG_TBL_LEN)
    offset = 0
    for row in reader:
        struct.pack_into("<HHH", entries, offset, int(row[0], 8), int(row[1], 8), int(row[2], 8))
        offset += 3*2

    # Add terminator + constant for patched booter.
    print(offset)
    struct.pack_into("<H", entries, offset, 0o7777)
    struct.pack_into("<H", entries, 0o77*BYTES_PER_WORD, 0o7775)

    return entries

def gen_write_new_table(csv_data, controller_block: memoryview):
    # Get new table.
    tbl = gen_table_group(csv_data)
    assert(len(tbl) == 0o200)

    # Shove them back into the block.
    controller_block[0o300*BYTES_PER_WORD:] = tbl

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='dial-media-builder', description='Build DIAL-MS media for various media types from a reference DIAL-MS LINCtape image')
    parser.add_argument("spec", nargs="*")
    parser.add_argument("-o", "--output-path", required=True)
    parser.add_argument("-i", "--input-path", required=True)
    print(sys.argv[1:])
    parsed = parser.parse_args(sys.argv[1:])

    # Create a copy of our input and open it for reading & writing.
    image_file = copy_open_file(parsed.output_path, parsed.input_path, "rb+")

    # Read controller block.
    controller_block = memoryview(read_tape_block(image_file, IO_ROUTINES_BLOCK))
    assert(len(controller_block) == 0o1000)

    # Read in each spec csvs
    csv_dat = concat_spec(parsed.spec)

    # Generate and write new table.
    gen_write_new_table(csv_dat, controller_block)

    # Write it back.
    write_tape_block(image_file, controller_block, IO_ROUTINES_BLOCK)

    sys.exit(0)
