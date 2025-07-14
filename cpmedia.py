import argparse
import sys

from cmn import *

@dataclass
class MediaAttributes:
    block_count: int
    block_size: int
    sides: int

MEDIA_ATTRIBUTES = {
    'linc': MediaAttributes(512, 256, 1), #Usually
    'rk08': MediaAttributes(3248, 256, 1),
    'rk05': MediaAttributes(3248, 256, 2)
}

def _erase_data_range(image: memoryview, start: int, end: int):
    zero_block = bytearray(BYTES_PER_BLOCK)
    for i in range(start * BYTES_PER_BLOCK, end * BYTES_PER_BLOCK, BYTES_PER_BLOCK):
        image[i:i+BYTES_PER_BLOCK] = zero_block

def copy_dial_media(out_path: str, in_image, media_type: str, copy_index: bool):
    assert(out_path != None and out_path != "")
    assert(in_image != None)
    assert(media_type_valid(media_type))

    # We can simply copy the input over then expand the output.
    data = memoryview(read_tape_block(in_image, 0, TAPE_SIZE_BLOCKS))

    # Must have blocks up to start of beginning of work area.
    block_count = int(len(data) / BYTES_PER_BLOCK)
    if(block_count < 0o370):
        raise ValueError("Input image missing parts of system area")

    # Calculate total media size.
    attribs = MEDIA_ATTRIBUTES[media_type]
    media_size = attribs.block_count * attribs.block_size * attribs.sides * BYTES_PER_WORD

    # Are we preserving the index?
    if(not copy_index):
        # No, kill him.
        _erase_data_range(data, 0, 0o300)

        # Again.
        _erase_data_range(data, 0o370, block_count)

        # AGAIN!
        _erase_data_range(data, 0o346, 0o350) #not including 350

    # Open output file and send it.
    with open_file(out_path, "wb") as fp:
            # Write source image data data.
            try:
                fp.write(data)
            except OSError as excpt:
                sys.exit("Failed to media data to {}: {}".format(excpt))

            # Expand the new image to its correct size if needed.
            if(fp.tell() < TAPE_SIZE_BYTES):
                try:
                    fp.seek(media_size - 1)
                    fp.write(bytes(1))
                except OSError as excpt:
                    sys.exit("Failed to expand image '{}': {}".format(out_path, excpt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='DIAL-MS Media Copier', description='Copy DIAL-MS data from one media type to another.')
    parser.add_argument("-o", "--output-path", required=True, help="Output image path.")
    parser.add_argument("-i", "--input-path", required=True, help="Input image path.")
    parser.add_argument("-m", "--media", required=True, help="Media type.", choices=VALID_MEDIA_TYPES)
    parser.add_argument("-i", "--preserve-index", action="store_const", const=True, help="Preserve the DIAL file index; if not set (default), the index and entire file area are zeroed in both output images.")
    parsed = parser.parse_args(sys.argv[1:])

    # Open the input.
    input_image = open_file(parsed.input_path, "rb")

    # Check media type.
    if(not media_type_valid(parsed.media)):
        sys.exit("Invalid media type: {}".format(parsed.media))

    # And copy it :)
    try:
        copy_dial_media(parsed.output_path, input_image, parsed.media, parsed.preserve_index != None)
    except OSError as excpt:
        sys.exit("Failed to copy input {} to output {}: {}".format(parsed.input_path, parsed.output_path, ))
    except ValueError as excpt:
        sys.exit("Input image {} improperly formatted: {}".format(parsed.input_path, excpt))
