import argparse
import sys
from cmn import *

_PATCHED_IMAGE_PATH = "build-patched.img"

_BUILD_IMG_BOOTER_LOC = 0o7200 * BYTES_PER_WORD
_BUILD_IMG_BOOTER_LEN = 0o100 * BYTES_PER_WORD

def apply_patches(control_block):
    # Attempt to open the patched build image.
    try:
        pat_build_file = open(_PATCHED_IMAGE_PATH, "rb")
    except Exception as excpt:
        print("Failed to open file {}: {}".format(_PATCHED_IMAGE_PATH, excpt))
        return -1

    # Read patched BOOTER block.
    try:
        pat_build_file.seek(_BUILD_IMG_BOOTER_LOC)
        patched_booter = pat_build_file.read(_BUILD_IMG_BOOTER_LEN)
    except Exception as excpt:
        print("Failed to read patched BOOTER routine: {}".format(excpt))
        return -1

    # Pull second half of the block from the previously read I/O controller block.
    start = 0o200 * BYTES_PER_WORD
    control_block[start:start + _BUILD_IMG_BOOTER_LEN] = patched_booter

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='dial-media-builder', description='Build DIAL-MS media for various media types from a reference DIAL-MS LINCtape image')
    parser.add_argument("-o", "--output-path", required=True)
    parser.add_argument("-i", "--input-path", required=True)
    parsed = parser.parse_args(sys.argv[1:])

    # Open and copy input file.
    image_file = copy_open_file(parsed.output_path, parsed.input_path, "rb+")

    # Read both handler blocks.
    handler_blocks = memoryview(read_tape_block(image_file, IO_ROUTINES_BLOCK))

    # Insert the new handler(s).
    apply_patches(handler_blocks)
    print(type(handler_blocks))

    # Write them back.
    write_tape_block(image_file, handler_blocks, IO_ROUTINES_BLOCK, 2)

    sys.exit(0)
