import argparse
import sys
from cmn import *

_PATCHED_IMAGE_PATH = "build-patched.img"

_BUILD_IMG_BOOTER_LOC = 0o7200 * BYTES_PER_WORD
_BUILD_IMG_BOOTER_LEN = 0o100 * BYTES_PER_WORD

# Copy patched BOOTER routine from bundled build image to provided control block.
def apply_patches(control_block):
    assert(len(control_block) >= BYTES_PER_BLOCK)

    # Attempt to open the patched build image.
    pat_build_file = open_file(_PATCHED_IMAGE_PATH, "rb")

    # Read patched BOOTER block.
    try:
        pat_build_file.seek(_BUILD_IMG_BOOTER_LOC)
        patched_booter = pat_build_file.read(_BUILD_IMG_BOOTER_LEN)
    except Exception as excpt:
        sys.exit("Failed to read patched BOOTER routine from {}: {}".format(_PATCHED_IMAGE_PATH, excpt))

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
    try:
        handler_blocks = memoryview(read_tape_block(image_file, IO_ROUTINES_BLOCK))
    except OSError as excpt:
        sys.exit("Failed to read I/O routine block from '{}': {}".format(parsed.output_path, excpt))
    if(len(handler_blocks) != BYTES_PER_BLOCK):
        sys.exit("Only read partial I/O routine block from '{}': {}".format(parsed.output_path, excpt))

    # Insert the new handler(s).
    apply_patches(handler_blocks)

    # Write them back.
    try:
        written = write_tape_block(image_file, handler_blocks, IO_ROUTINES_BLOCK)
    except OSError as excpt:
        sys.exit("Failed to read I/O routine block from '{}': {}".format(parsed.output_path, excpt))
    if(written != BYTES_PER_BLOCK):
        sys.exit("Only read partial I/O routine block from '{}': {}".format(parsed.output_path, excpt))

    sys.exit(0)
