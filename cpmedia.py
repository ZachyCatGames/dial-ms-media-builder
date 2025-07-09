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
        print(i)
        print(len(zero_block))
        print(len(image[i:i+BYTES_PER_BLOCK]))
        image[i:i+BYTES_PER_BLOCK] = zero_block

def copy_dial_media(out_path: str, in_image, media_type: str, copy_index: bool):
    # We can simply copy the input over then expand the output.
    try:
        data = memoryview(read_tape_block(in_image, 0, BLOCK_COUNT))
        assert(len(data) == BLOCK_COUNT * BYTES_PER_BLOCK)
    except Exception as excpt:
        print("Failed to read input image: {}".format(excpt))
        sys.exit(-1)

    # Calculate total media size.
    attribs = MEDIA_ATTRIBUTES[media_type]
    media_size = attribs.block_count * attribs.block_size * attribs.sides * BYTES_PER_WORD

    # Are we preserving the index?
    if(not copy_index):
        # No, kill him.
        _erase_data_range(data, 0, 0o300)

        # Again.
        _erase_data_range(data, 0o370, BLOCK_COUNT)

        # AGAIN!
        _erase_data_range(data, 0o346, 0o350) #not including 350

    # Open output file and send it.
    try:
        with open(out_path, "wb") as fp:
            fp.write(data)
            fp.seek(media_size - 1)
            fp.write(bytes(1))
    except Exception as excpt:
        print("Failed to write media to {}: {}".format(out_path, excpt))
        sys.exit(-1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='dial-media-builder', description='Build DIAL-MS media for various media types from a reference DIAL-MS LINCtape image')
    parser.add_argument("-o", "--output-path", required=True)
    parser.add_argument("-i", "--input-path", required=True)
    parser.add_argument("-m", "--media", required=True)
    parser.add_argument("-i", "--preserve-index", action="store_const", const=True)
    parsed = parser.parse_args(sys.argv[1:])

    # Open the input.
    input_image = open_file(parsed.input_path, "rb")

    # And copy it :)
    copy_dial_media(parsed.output_path, input_image, parsed.media, parsed.preserve_index != None)

