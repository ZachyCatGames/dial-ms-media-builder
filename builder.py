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
    'rk05': "specs/rk08-spec.pri-std.csv"
}

# Secondary unit specifications.
UNIT_TALBE_SPECS_SEC = {
    'linc': "specs/linctape-spec.sec-std.csv",
    'rk08': "specs/rk08-spec.sec-std.csv",
    'rk05': "specs/rk08-spec.sec-std.csv"
}

# System unit specifications.
SYSTEM_PRI_SPEC = "specs/sys-spec.pri-std.csv"
SYSTEM_SND_SPEC = "specs/sys-spec.sec-std.csv"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='dial-media-builder', description='Build DIAL-MS media for various media types from a reference DIAL-MS LINCtape image')
    parser.add_argument("-o", "--output-path", required=True)
    parser.add_argument("-i", "--input-path", required=True)
    parser.add_argument("-m", "--media", required=True)
    parser.add_argument("-d", "--preserve-index", action="store_const", const=True)
    parser.add_argument("--override-first")
    parser.add_argument("-s", "--second-system", action="store_const", const=True)
    parser.add_argument("-p", "--enable-patches", action="store_const", const=True)
    parsed = parser.parse_args(sys.argv[1:])

    # Determine output paths.
    out_lt_path = "{}.linc".format(parsed.output_path)
    out_alt_path = "{}.{}".format(parsed.output_path, parsed.media)
    preserve_index = parsed.preserve_index != None
    patch_enb = parsed.enable_patches != None
    media_type = parsed.media

    # Create a copy of our input for writing.
    with open_file(parsed.input_path, "rb") as fp:
        cpm.copy_dial_media(out_lt_path, fp, "linc", preserve_index)
    lt_image = open_file(out_lt_path, "rb+")
    # Read in the control block, starting with a fresh master copy.
    control_block = memoryview(read_tape_block(lt_image, IO_CONTROLLER_BLOCK))

    # Are patches enabled? Apply them if yes.
    if(patch_enb):
        wp.apply_patches(control_block)

    # Determine what type we have in the primary slot.
    primary_type = "linc" # default to LINCtape
    if(parsed.override_first != None):
        primary_type = parsed.override_first

    # Determine what type we have in the secondary slot.
    secondary_type = media_type # media type by default
    if(media_type == "linc"):
        secondary_type = None # No sense in having two LINCtapes...

    # Get specs for system, primary, and secondary.
    sys_spec = SYSTEM_SND_SPEC if parsed.second_system != None else SYSTEM_PRI_SPEC
    primary_spec = UNIT_TABLE_SPECS_PRI[primary_type]
    secondary_spec = UNIT_TALBE_SPECS_SEC[secondary_type]

    # Concat specs together
    spec_concat = wt.concat_spec([primary_spec, sys_spec, secondary_spec])

    # Build + write new table.
    wt.gen_write_new_table(spec_concat, control_block)

    # We're now done with the controller block, write it to its new home.
    write_tape_block(lt_image, control_block, IO_ROUTINES_BLOCK)

    # Read a fresh copy of the handlers block.
    handler_block = memoryview(read_tape_block(lt_image, IO_MASTERS_BLOCK))

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
    write_tape_block(lt_image, handler_block, IO_ROUTINES_BLOCK+1)

    # ...and finally, create a copy of our targetted media type.
    cpm.copy_dial_media(out_alt_path, lt_image, media_type, preserve_index)

    lt_image.close()
