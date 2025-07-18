import argparse
import struct
import sys
from dataclasses import dataclass

from cmn import *
import bin2hndlr as bn

# Notes:
# Each word is two bytes in a DSK
# 256 word block -> 512 bytes per word

# I/O Routines are in blocks 322 and 323 -> addr = 0x1A400, size = 0x200
# Unit table is located at 0x1A480
# I/O Controller master copy is in block 345 -> addr = 0x1CA00, size = 0x100
# I/O handler routines mater copies are in blocks 365 and 366 -> addr = 0x1EA00, size = 0x200

# Second master routine block is the "base" for the second I/O routine block. By default it contains the LT and RF08 handlers.
#   - RF08 at 0o30
#   - LT at 0o230
# The first contains the DF32 and RK08 handlers.
#   - RK08 at 0o30
#   - DF32 at 0o230

# Media info
#   - RK08 disks contain 831488 words in 256 word blocks, making for 3248 blocks (http://bitsavers.org/pdf/dec/pdp8/disc/RK8_Maint_Vol1.pdf)
#   - RK05 disks appear to be similar to RK08s, but double sided (https://gunkies.org/wiki/RK05_disk_drive)
#   - LINCtape contain a variable number of blocks of variable sizes. Typical LINC formatted tapes contain 512 256 word blocks.


# Feature set:
#   - Support for creating multiple media types from a LINCtape image (--media)
#       - Can generate LINCtape images from LINCtape images.
#   - Automatically writes appropriate handler to secondary slot
#       - No secondary handler written if media type provided is LINCtape
#   - Override both primary and secondary handler. (--primary_handler & --secondary_handler)
#       - Primary handler is assumed to be LINCtape by default.
#       - Secondary handler is assumed to the appropriate media handler by default.
#   - Support for setting the system device to the secondary device (-n)
#       - Primary device is the system device by default
#   - Support for applying a patchset to enable re-bootstrapping without redoing the full boot sequence (-p)
#       - Valuable for non-LINCtape devices, where the whole rimloader etc sequence would otherwise need to be run after every program load.
#   - NOTE: This program does not automatically update the unit table, for this wrtbl is provided.

def write_handler(handler_block: memoryview, new_hndlr_path: str, addr: int):
    # Open handler binary and parse BIN data to a core image.
    with open_file(new_hndlr_path, "rb") as fp:
        hndlr_data = bn.bin_to_core_image(fp)[0o230 * BYTES_PER_WORD:0o370 * BYTES_PER_WORD]

    # Insert the new handler.
    start = addr*BYTES_PER_WORD
    handler_block[start:start + len(hndlr_data)] = hndlr_data

def write_handlers(handler_block: memoryview, primary_path: str, secondary_path: str):
    assert(len(handler_block) >= BYTES_PER_WORD)

    # Update primary handler if requested.
    if(primary_path != None):
        write_handler(handler_block, primary_path, 0o230)

    # Always override secondary handler if provided.
    if(secondary_path != None):
        write_handler(handler_block, secondary_path, 0o30)


# TODO: Support BIN images
if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='DIAL-MS Device Handler Writer', description="Setup/Assign/Replace DIAL-MS device handler slots from handler BIN files.")
    parser.add_argument("-o", "--output-path", required=True, help="Output image path.")
    parser.add_argument("-i", "--input-path", required=True, help="Input image path.")
    parser.add_argument("-p", "--primary-handler", required=True, help="Primary handler BIN file path.")
    parser.add_argument("-s", "--secondary-handler", required=True, help="Secondary handler BIN file path.")
    parsed = parser.parse_args(sys.argv[1:])

    # Open and copy input file.
    image_file = copy_open_file(parsed.output_path, parsed.input_path, "rb+")

    # Read both handler blocks.
    try:
        handler_blocks = memoryview(read_tape_block(image_file, IO_ROUTINES_BLOCK+1))
    except OSError as excpt:
        sys.exit("Failed to read handler block from {}: {}".format(parsed.output_path, excpt))
    if(len(handler_blocks) != BYTES_PER_BLOCK):
        sys.exit("Only read partial handler block from {}".format(parsed.output_path))

    # Insert the new handler(s).
    write_handlers(handler_blocks, parsed.primary_handler, parsed.secondary_handler)

    # Write them back.
    try:
        written = write_tape_block(image_file, handler_blocks, IO_ROUTINES_BLOCK+1)
    except OSError as excpt:
        sys.exit("Failed to write handler block back to {}: {}".format(parsed.output_path, excpt))
    if(written != BYTES_PER_BLOCK):
        sys.exit("Only wrote partial handler block back to {}".format(parsed.output_path))

    sys.exit(0)

