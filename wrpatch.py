import argparse
import sys
from cmn import *
import bin2img as bn

_PATCHED_IMAGE_PATH = "build-patched.bin"

# Copy patched BOOTER routine from bundled build image to provided control block.
def apply_patches(handler_blocks):
    assert(len(handler_blocks) >= BYTES_PER_BLOCK * 2)

    # Attempt to open the patched build image.
    patched_build = bn.bin_to_core_image(open_file(_PATCHED_IMAGE_PATH, "rb"))

    # Patch things before unit table.
    handler_blocks[0:0o300*BYTES_PER_WORD] = patched_build[0o7000*BYTES_PER_WORD:0o7300*BYTES_PER_WORD]

    # After but before the handlers...
    handler_blocks[0o400*BYTES_PER_WORD:0o430*BYTES_PER_WORD] = patched_build[0o7400*BYTES_PER_WORD:0o7430*BYTES_PER_WORD]

    # Mini loader between the handlers...
    handler_blocks[0o600*BYTES_PER_WORD:0o630*BYTES_PER_WORD] = patched_build[0o7600*BYTES_PER_WORD:0o7630*BYTES_PER_WORD]

    # And lastly, the syscom areas.
    handler_blocks[0o570*BYTES_PER_WORD:0o600*BYTES_PER_WORD] = patched_build[0o7570*BYTES_PER_WORD:0o7600*BYTES_PER_WORD]
    handler_blocks[0o770*BYTES_PER_WORD:0o1000*BYTES_PER_WORD] = patched_build[0o7770*BYTES_PER_WORD:0o10000*BYTES_PER_WORD]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='DIAL-MS Rebootstrap Patch Writer', description='Apply a patch to the DIAL-MS BOOTER routine to make it use the system device handler (instead of the LINCtape instructions) when reading in the boot blocks')
    parser.add_argument("-o", "--output-path", required=True, help="Output path.")
    parser.add_argument("-i", "--input-path", required=True, help="Input path.")
    parsed = parser.parse_args(sys.argv[1:])

    # Open and copy input file.
    image_file = copy_open_file(parsed.output_path, parsed.input_path, "rb+")

    # Read both handler blocks.
    try:
        handler_blocks = memoryview(read_tape_block(image_file, IO_ROUTINES_BLOCK, 2))
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
