import argparse
import cpmedia as cpm
import wrhndlr as wh
import wrpatch as wp
import wrtbl as wt
from cmn import *

HANDLER_PATHS = {
    'linc': "handlers/linctape-handler.img",
    'rk08': "handlers/rk08-handler.img",
    'rk05': "handlers/rk08-handler.img",
    'sdsk': "handlers/sdsk-handler.img"
}

PATCHED_HANDLER_PATHS = {
    'linc': "handlers/linctape-handler-patched.img",
    'rk08': "handlers/rk08-handler-patched.img",
    'rk05': "handlers/rk08-handler-patched.img",
    'sdsk': "handlers/sdsk-handler.img" # Serial disk handler has the reboot-strap patch applied.
}

TAPE_HANDLER_ADDRS = {
    'rf08': (IO_MASTERS_BLOCK,   0o30),
    'linc': (IO_MASTERS_BLOCK,   0o230),
    'rk08': (IO_MASTERS_BLOCK_2, 0o30),
    'rk05': (IO_MASTERS_BLOCK_2, 0o30),
    'df32': (IO_MASTERS_BLOCK_2, 0o230)
}

# Secondary unit specifications.
UNIT_TABLE_SPECS_PRI = {
    'linc': "specs/linctape-spec.pri-std.csv",
    'rk08': "specs/rk08-spec.pri-std.csv",
    'rk05': "specs/rk08-spec.pri-std.csv",
    'sdsk': "specs/rk08-spec.pri-std.csv"
}

# Secondary unit specifications.
UNIT_TALBE_SPECS_SEC = {
    'linc': "specs/linctape-spec.sec-std.csv",
    'rk08': "specs/rk08-spec.sec-std.csv",
    'rk05': "specs/rk08-spec.sec-std.csv"
}

# System unit specifications.
SYSTEM_PRI_SPEC = {
    'linc': "specs/sys-spec.pri-std.csv",
    'rk08': "specs/sys-spec.pri-std.csv",
    'rk05': "specs/sys-spec.pri-std.csv"
}
SYSTEM_SND_SPEC = {
    'linc': "specs/sys-spec.sec-std.csv",
    'rk08': "specs/sys-spec.sec-std.csv",
    'rk05': "specs/sys-spec.sec-std.csv"
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='dial-media-builder', description='Build DIAL-MS media for various media types from a reference DIAL-MS LINCtape image.')
    parser.add_argument("-o", "--output-path", required=True, help="Output path excluding file extension, used for both the output LINCtape and output $MEDIA images.")
    parser.add_argument("-i", "--input-path", required=True, help="Input LINCtape image path.")
    parser.add_argument("-m", "--media", required=True, choices=VALID_MEDIA_TYPES, help="Media type.")
    parser.add_argument("-d", "--preserve-index", action="store_const", const=True, help="Preserve the DIAL file index; if not set (default), the index and entire file area are zeroed in both output images.")
    parser.add_argument("--replace-first", choices=VALID_MEDIA_TYPES, help="Replace the default LINCtape handler with a different handler.")
    parser.add_argument("-s", "--second-system", action="store_const", const=True, help="Configure system units to use the secondary device handler.")
    parser.add_argument("-p", "--enable-patches", action="store_const", const=True, help="Apply patches to allow rebooting DIAL-MS without the use of any LINCtape instructions.")
    parsed = parser.parse_args(sys.argv[1:])

    # Determine output paths.
    out_lt_path = "{}.linc".format(parsed.output_path)
    out_alt_path = "{}.{}".format(parsed.output_path, parsed.media)
    preserve_index = parsed.preserve_index != None
    patch_enb = parsed.enable_patches != None
    media_type = parsed.media

    # Create a copy of our input for writing.
    with open_file(parsed.input_path, "rb") as fp:
        try:
            cpm.copy_dial_media(out_lt_path, fp, "linc", preserve_index)
        except OSError as excpt:
            sys.exit("Failed to copy input image ''{}' to '{}': {}".format(parsed.input_path, out_lt_path, excpt))
        except ValueError as excpt:
            sys.exit("Input image '{}' is improperly formatted: {}".format(parsed.input_path, excpt))
    lt_image = open_file(out_lt_path, "rb+")

    # Read in the control block, starting with a fresh master copy.
    try:
        control_block = memoryview(read_tape_block(lt_image, IO_CONTROLLER_BLOCK))
    except OSError as excpt:
        sys.exit("Failed to read control block from ''{}': {}".format(out_lt_path, excpt))
    if(len(control_block) != BYTES_PER_BLOCK):
        sys.exit("Only read partial control block from input!")

    # Are patches enabled? Apply them if yes.
    if(patch_enb):
        wp.apply_patches(control_block)

    # Determine what type we have in the primary slot.
    primary_type = "linc" # default to LINCtape
    if(parsed.override_first != None):
        primary_type = parsed.override_first

    # Check that primary type is valid.
    assert(primary_type != None)    # Cannot be none
    if(not media_type_valid(primary_type)):
        sys.exit("Invalid primary media type: {}".format(primary_type))

    # Determine what type we have in the secondary slot.
    secondary_type = media_type # media type by default
    if(media_type == "linc"):
        secondary_type = None # No sense in having two LINCtapes...

    if(secondary_type != None and not media_type_valid(secondary_type)):
        sys.exit("Invalid secondary media type: {}".format(secondary_type))

    # Get specs for system, primary, and secondary.
    sys_spec = SYSTEM_SND_SPEC[primary_type] if parsed.second_system != None else SYSTEM_PRI_SPEC[secondary_type]
    primary_spec = UNIT_TABLE_SPECS_PRI[primary_type]
    secondary_spec = UNIT_TALBE_SPECS_SEC[secondary_type]

    # Build + write new table.
    specfile_list = [primary_spec, sys_spec, secondary_spec]
    wt.parse_spec_file_list_by_path(control_block[wt.UNIT_TABLE_OFFSET:wt.UNIT_TABLE_END], specfile_list)

    # We're now done with the controller block, write it to its new home.
    try:
        written = write_tape_block(lt_image, control_block, IO_ROUTINES_BLOCK)
    except OSError as excpt:
        sys.exit("Failed to write control block to '{}': {}".format(out_lt_path, excpt))
    if(written != BYTES_PER_BLOCK):
        sys.exit("Failed to write entire control block to '{}' (wrote {}).".format(out_lt_path, written))

    # Read a fresh copy of the handlers block.
    try:
        handler_block = memoryview(read_tape_block(lt_image, IO_MASTERS_BLOCK))
    except OSError as excpt:
        sys.exit("Failed to read handler block from {}: {}".format(out_lt_path, excpt))
    if(len(handler_block) != BYTES_PER_BLOCK):
        sys.exit("Only read partial handler block from input!")

    # Determine where the new handlers are. Patched handlers are for use with the --enable-patches option.
    if(patch_enb):
        primary_handler_path = PATCHED_HANDLER_PATHS[primary_type]
        secondary_handler_path = PATCHED_HANDLER_PATHS[secondary_type]
    else:
        primary_handler_path = HANDLER_PATHS[primary_type]
        secondary_handler_path = HANDLER_PATHS[secondary_type]

    # Insert the new handlers.
    wh.write_handlers(handler_block, primary_handler_path, secondary_handler_path)

    # Write the handler block back.
    try:
        written = write_tape_block(lt_image, handler_block, IO_ROUTINES_BLOCK+1)
    except OSError as excpt:
        sys.exit("Failed to write handler block to {}: {}".format(out_lt_path, excpt))
    if(written != BYTES_PER_BLOCK):
        sys.exit("Failed to write entire handler block to {}.".format(out_lt_path))

    # ...and finally, create a copy of our targetted media type.
    try:
        cpm.copy_dial_media(out_alt_path, lt_image, media_type, preserve_index)
    except OSError as excpt:
        sys.exit("Failed to copy LINCtape image '{}' to {} image '{}': {}".format(parsed.out_lt_path, secondary_type, out_alt_path, excpt))
    except ValueError as excpt:
        sys.exit("LINCtape image '{}' is improperly formatted: {}".format(parsed.out_lt_path, excpt))

    lt_image.close()
