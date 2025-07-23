import argparse
import sys
import struct
import os

from cmn import *

@dataclass
class MediaAttributes:
    block_count: int
    block_size: int
    sides: int

MEDIA_ATTRIBUTES = {
    'linc': MediaAttributes(512, 256, 1), #Usually
    'rk08': MediaAttributes(3248, 256, 1),
    'rk01': MediaAttributes(3248, 256, 1),
    'rk05': MediaAttributes(3248, 256, 2),
    'sdsk': MediaAttributes(3248, 256, 2),  # Uses rk05 DSK format
}

def _erase_data_range(image: bytearray, start: int, end: int):
    zero_block = bytearray(BYTES_PER_BLOCK)
    for i in range(start * BYTES_PER_BLOCK, end * BYTES_PER_BLOCK, BYTES_PER_BLOCK):
        image[i:i+BYTES_PER_BLOCK] = zero_block

def copy_dial_media(out_path: str, in_image, in_media_type: str, out_media_type: str, copy_index: bool):
    assert(out_path != None and out_path != "")
    assert(in_image != None)
    assert(media_type_valid(in_media_type))
    assert(media_type_valid(out_media_type))

    # Determine how large the input is and create input buffer.
    in_image.seek(0, os.SEEK_END)
    img_size = in_image.tell()
    if(img_size > 0x1000000):
        # Cap at 16MiB.
        img_size = 0x1000000
    data = bytearray(img_size)

    # Read up to 16MiB of input.
    try:
        in_image.seek(0, os.SEEK_SET)
        in_image.readinto(data)
    except OSError as excpt:
        sys.exit("Failed to read input image: {}".format(excpt))

    # Format specific parsing.
    if in_media_type == 'linc':
        # We need to deal with start & end padding.
        # These plus block length are apparently described by the last six words.
        blk_len, start_pad, end_pad = struct.unpack_from("<HHH", data, len(data) - 6)

        # Block length must be 256 and total image size sans the last six words should be a multiple of 256.
        if(blk_len != 0o400):
            sys.exit("Input LINCtape doesn't contain 256 word blocks! {}".format(blk_len))
        if(len(data) % blk_len != 6):
            sys.exit("Input LINCtape image contains incomplete blocks!")

        # But negated for some reason
        start_pad *= -1
        end_pad *= -1

        # Trim off padding + six end words
        data = memoryview(data)[start_pad * BYTES_PER_BLOCK:(len(data) - 6) - end_pad * BYTES_PER_BLOCK]

    # Must have blocks up to start of beginning of work area.
    block_count = int(len(data) / BYTES_PER_BLOCK)
    if(block_count < 0o370):
        raise ValueError("Input image missing parts of system area")

    # Calculate total media size.
    attribs = MEDIA_ATTRIBUTES[out_media_type]
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
            if(fp.tell() < media_size):
                try:
                    fp.seek(media_size - 1)
                    fp.write(bytes(1))
                except OSError as excpt:
                    sys.exit("Failed to expand image '{}': {}".format(out_path, excpt))

            # Add block size & padding information for LINCtapes
            if(out_media_type == 'linc'):
                fmt_info = struct.pack("<HHH", WORDS_PER_BLOCK, 0, 0) # No padding
                try:
                    fp.write(fmt_info)
                except OSError as excpt:
                    sys.exit("Failed to write LINCtape block and padding information to '{}': {}".format(out_path, excpt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='DIAL-MS Media Copier', description='Copy DIAL-MS data from one image type to another.')
    parser.add_argument("-o", "--output-path", required=True, help="Output image path.")
    parser.add_argument("-i", "--input-path", required=True, help="Input image path.")
    parser.add_argument("-m", "--input-media", required=True, help="Input media type.", choices=VALID_MEDIA_TYPES)
    parser.add_argument("-n", "--output-media", required=True, help="Output media type.", choices=VALID_MEDIA_TYPES)
    parser.add_argument("-i", "--preserve-index", action="store_const", const=True, help="Preserve the DIAL file index; if not set (default), the index and entire file area are zeroed in both output images.")
    parsed = parser.parse_args(sys.argv[1:])

    # Open the input.
    input_image = open_file(parsed.input_path, "rb")

    # Check media type.
    if(not media_type_valid(parsed.input_media)):
        sys.exit("Invalid input media type: {}".format(parsed.input_media))
    if(not media_type_valid(parsed.output_media)):
        sys.exit("Invalid output media type: {}".format(parsed.output_media))

    # And copy it :)
    try:
        copy_dial_media(parsed.output_path, input_image, parsed.input_media, parsed.output_media, parsed.preserve_index != None)
    except OSError as excpt:
        sys.exit("Failed to copy input {} to output {}: {}".format(parsed.input_path, parsed.output_path, ))
    except ValueError as excpt:
        sys.exit("Input image {} improperly formatted: {}".format(parsed.input_path, excpt))
