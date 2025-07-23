import argparse
import cpmedia as cpm
import wrhndlr as wh
import wrpatch as wp
import wrtbl as wt
from cmn import *

HANDLER_PATHS = {
    'linc': "handlers/linctape-handler.bin",
    'rk08': "handlers/rk08-handler.bin",
    'rk01': "handlers/rk08-handler.bin",
    'rk05': "handlers/rk08-handler.bin",
    'sdsk': "handlers/sdsk-handler.bin"
}

PATCHED_HANDLER_PATHS = {
    'linc': "handlers/linctape-handler-patched.bin",
    'rk08': "handlers/rk08-handler-patched.bin",
    'rk01': "handlers/rk08-handler-patched.bin",
    'rk05': "handlers/rk08-handler-patched.bin",
    'sdsk': "handlers/sdsk-handler.bin" # Serial disk handler always has the reboot-strap patch applied.
}

# Secondary unit specifications.
UNIT_TABLE_SPECS_PRI = {
    'linc': "unit-specs/linctape-units.pri-std.csv",
    'rk08': "unit-specs/rk08-units.pri-std.csv",
    'rk08': "unit-specs/rk01-units.pri-std.csv",
    'rk05': "unit-specs/rk08-units.pri-std.csv",
    'sdsk': "unit-specs/rk08-units.pri-std.csv"
}

# Secondary unit specifications.
UNIT_TALBE_SPECS_SEC = {
    'linc': "unit-specs/linctape-units.sec-std.csv",
    'rk08': "unit-specs/rk08-units.sec-std.csv",
    'rk01': "unit-specs/rk08-units.sec-std.csv",
    'rk05': "unit-specs/rk08-units.sec-std.csv",
    'sdsk': "unit-specs/rk08-units.sec-std.csv",
}

# System unit specifications.
SYSTEM_PRI_SPEC = {
    'linc': "unit-specs/sys-units.pri-std.csv",
    'rk08': "unit-specs/sys-units.pri-std.csv",
    'rk01': "unit-specs/sys-units.pri-std.csv",
    'rk05': "unit-specs/sys-units.pri-std.csv",
    'sdsk': "unit-specs/sys-units.pri-std.csv",
}
SYSTEM_SND_SPEC = {
    'linc': "unit-specs/sys-units.sec-std.csv",
    'rk08': "unit-specs/sys-units.sec-std.csv",
    'rk01': "unit-specs/sys-units.sec-std.csv",
    'rk05': "unit-specs/sys-units.sec-std.csv",
    'sdsk': "unit-specs/sys-units.sec-std.csv",
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
    # NOTE: The copy tool strips any padding from the input LINCtape and we rely on that (we assume there's no padding).
    with open_file(parsed.input_path, "rb") as fp:
        try:
            cpm.copy_dial_media(out_lt_path, fp, "linc", "linc", preserve_index)
        except OSError as excpt:
            sys.exit("Failed to copy input image ''{}' to '{}': {}".format(parsed.input_path, out_lt_path, excpt))
        except ValueError as excpt:
            sys.exit("Input image '{}' is improperly formatted: {}".format(parsed.input_path, excpt))
    lt_image = open_file(out_lt_path, "rb+")

    # Read in both I/O routine blocks, starting with fresh master copies.
    try:
        control_block = read_tape_block(lt_image, IO_CONTROLLER_BLOCK)
        handler_block = read_tape_block(lt_image, IO_MASTERS_BLOCK)
        routine_blocks = memoryview(control_block + handler_block)
    except OSError as excpt:
        sys.exit("Failed to read control block from ''{}': {}".format(out_lt_path, excpt))
    if(len(control_block) != BYTES_PER_BLOCK):
        sys.exit("Only read partial control block from input!")

    # Are patches enabled? Apply them if yes.
    if(patch_enb):
        wp.apply_patches(routine_blocks)

    # Determine what type we have in the primary slot.
    primary_type = "linc" # default to LINCtape
    if(parsed.replace_first != None):
        primary_type = parsed.replace_first

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
    wt.parse_spec_file_list_by_path(routine_blocks[wt.UNIT_TABLE_OFFSET:wt.UNIT_TABLE_END], specfile_list)

    # Determine where the new handlers are. Patched handlers are for use with the --enable-patches option.
    if(patch_enb):
        primary_handler_path = PATCHED_HANDLER_PATHS[primary_type]
        secondary_handler_path = PATCHED_HANDLER_PATHS[secondary_type]
    else:
        primary_handler_path = HANDLER_PATHS[primary_type]
        secondary_handler_path = HANDLER_PATHS[secondary_type]

    # Insert the new handlers into second block.
    wh.write_handlers(routine_blocks[BYTES_PER_BLOCK:BYTES_PER_BLOCK*2], primary_handler_path, secondary_handler_path)

    # Write the routine blocks back.
    try:
        written = write_tape_block(lt_image, routine_blocks, IO_ROUTINES_BLOCK)
    except OSError as excpt:
        sys.exit("Failed to write handler block to {}: {}".format(out_lt_path, excpt))
    if(written != BYTES_PER_BLOCK * 2):
        sys.exit("Failed to write entire handler block to {}.".format(out_lt_path))

    # ...and finally, create a copy of our targetted media type.
    try:
        cpm.copy_dial_media(out_alt_path, lt_image, "linc", media_type, preserve_index)
    except OSError as excpt:
        sys.exit("Failed to copy LINCtape image '{}' to {} image '{}': {}".format(parsed.out_lt_path, secondary_type, out_alt_path, excpt))
    except ValueError as excpt:
        sys.exit("LINCtape image '{}' is improperly formatted: {}".format(parsed.out_lt_path, excpt))

    lt_image.close()
