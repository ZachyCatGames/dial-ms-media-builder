import sys
import struct

def main(argv):
    fp = open(argv[1], "rb")
    out = open(argv[2], "wb")

    # Skip over the leader.
    b = 0x80
    while(b == 0x80):
        b = int(fp.read(1)[0])

    fp.seek(-1, 1)

    data: list = [0] * 0o10000
    skip = False
    address = 0
    while(True):
        b = int(fp.read(1)[0])

        # Are all bits set? If yes, activate or deactivate skip mode.
        if(b == 0xFF):
            skip = not skip
            continue

        # Do nothing if in skip mode, we're skipping everything.
        if(skip):
            continue

        # If both bits 7 and 8 are set, this means the data field should be updated
        # But we're not going to worry about that.
        if(b & 0xC0 == 0xC0):

            continue

        # If we encounter a leader (exclusively bit 7 set), we're done and should exit.
        if(b & 0x80):
            break

        # If we encounter a byte with bit 6 set, update the current address.
        b2 = int(fp.read(1)[0])
        full = ((b & 0x3F) << 6) | (b2 & 0x3F)
        if(b & 0x40):
            address = full
        else:
            # Otherwise? Just a regular word.
            data[address] = full
            address += 1
            if(address >= 0o10000): #address wrap around
                address = 0

    for num in data:
        bs = struct.pack("<H", num)
        out.write(bs)

if __name__ == "__main__":
    exit(main(sys.argv))
