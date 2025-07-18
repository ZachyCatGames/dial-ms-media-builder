import sys
import struct

def bin_to_core_image(bin_file):
    # Skip over the leader.
    b = 0x80
    while(b == 0x80):
        b = int(bin_file.read(1)[0])

    bin_file.seek(-1, 1)

    data = bytearray(0o10000)
    skip = False
    address = 0
    while(True):
        b = int(bin_file.read(1)[0])

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
        b2 = int(bin_file.read(1)[0])
        full = ((b & 0x3F) << 6) | (b2 & 0x3F)
        if(b & 0x40):
            address = full
        else:
            # Otherwise? Just a regular word.
            struct.pack_into("<H", data, address * 2, full)
            address += 1
            if(address >= 0o10000): #address wrap around
                address = 0

    return data

#if __name__ == "__main__":
#    exit(main(sys.argv))
