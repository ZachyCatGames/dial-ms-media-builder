import sys
from dataclasses import dataclass

WORDS_PER_BLOCK = 0o400
BYTES_PER_BLOCK = WORDS_PER_BLOCK * 2
BYTES_PER_WORD = 2

IO_ROUTINES_BLOCK = 0o322
IO_ROUTINES_SIZE = 2

IO_CONTROLLER_BLOCK = 0o345
IO_CONTROLLER_SIZE = 1

IO_MASTERS_BLOCK = 0o365
IO_MASTERS_SIZE = 2
IO_MASTERS_BLOCK_2 = 0o366
IO_MASTERS_SIZE_2 = 2

BLOCK_COUNT = 0o1000

HANDLER_LEN = 0o150 * BYTES_PER_WORD

def splice_bytes(original: bytes, new: bytes, offset: int):
    return original[0:offset] + new + original[offset+len(new):]

def splice_words(original: bytes, new: bytes, offset: int):
    return splice_bytes(original, new, offset * BYTES_PER_WORD)

def open_file(path: str, mode: str):
    # Open image for reading.
    try:
        return open(path, mode)
    except Exception as excpt:
        print("Failed to open file {}: {}".format(path, excpt))
        sys.exit(-1)

def copy_open_file(out_path: str, in_path: str, mode: str):
    # Read input file.
    try:
        with open(in_path, "rb") as fp:
            data = fp.read()
    except Exception as excpt:
        print("Failed to open input file {}: {}".format(in_path, excpt))

    # Create the copy.
    try:
        with open(out_path, "wb") as fp:
            fp.write(data)
    except Exception as excpt:
        print("Faild to write output file {}: {}".format(out_path, excpt))

    # Open it as the user wishes.
    try:
        return open(out_path, mode)
    except Exception as excpt:
        print("Failed to open output file {}: {}".format(out_path, excpt))

def read_file_oneshot(path: str, mode: str):
    with open_file(path, mode) as fp:
        try:
            return fp.read()
        except Exception as excpt:
            print("Failed to read file: {}".format(excpt))

def write_file_oneshot(path: str, mode: str, data: bytes):
    with open_file(path, mode) as fp:
        try:
            return fp.write(data)
        except Exception as excpt:
            print("Failed to write file: {}".format(excpt))

def read_handler_image_oneshot(path: str):
    with open_file(path, "rb") as fp:
        try:
            fp.seek(0o230 * BYTES_PER_WORD, 0)
            return fp.read(0o150 * BYTES_PER_WORD)
        except Exception as excpt:
            print("Failed to read handler image: {}".format(excpt))

def read_tape_block(tape_image, start: int, num: int = 1):
    data = bytearray(num * BYTES_PER_BLOCK)
    print(type(data))
    try:
        tape_image.seek(start * BYTES_PER_BLOCK, 0)
        tape_image.readinto(data)
        return data
    except Exception as excpt:
        print("Failed to read tape image block: {}".format(excpt))

def write_tape_block(tape_image, block: bytes, start: int, num: int = 1):
    try:
        tape_image.seek(start * BYTES_PER_BLOCK, 0)
        tape_image.write(block)
    except Exception as excpt:
        print("Failed to write tape image block: {}".format(excpt))
