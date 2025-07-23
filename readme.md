# DIAL-MS Media Builder
LAP6-DIAL-MS (DIAL-MS) Media Builder consists of several tools that allow creating and customizing new DIAL-MS images in several formats (LINCtape, RK08, RK05, SerialDisk) from a base DIAL-MS LINCtape image.

The main tool, `builder`, is an all-in-one tool capable of building images suitable for most usecases with a single command.

The other tools, `cpmedia`, `wrhndlr`, `wrpatch`, and `wrtbl` provide the same functionality as `builder`, but as individual commands with more flexibility;
`builder` is essentially a fancy wrapper for the other tools.

## Builder
Builder can be used to generate DIAL-MS system images for various types of PDP-8/12 media from a base LINCtape image, two new images will be generated in the process.
One image will be a new LINCtape image with all modifications applied (new handlers, etc);
the second image will have identical contents to the new LINCtape image, but will be formatted according to the specified media type (the second image will not be generated if selected media type is LINCtape).
In some cases one of these images may be discarded if it's not needed, see [Using the Disk Images](#Using the Disk Images)

Builder will automatically setup both images so they're usable without any further modification:
correct handlers will be installed, unit table correctly setup, etc.

The specified device type will have its handler setup as the secondary handler ([Primary Handler? Secondary Handler? System Handler?](#Primary-Handler-Secondary-Handler-System-Handler)) and possibly as the system handler.
By default, the primary handler will be left as the LINCtape handler, but can be replaced with a different one as well.
It's also possible to choose to preserve the files from the base image, or to start with a clean slate (i.e., no files).

There's also an option to install a rebootstrap patch.
If the patch is enabled, it'll be possible to quickly restart DIAL-MS after executing a program from location 017757.

More detailed information on usage is presented in [Usage](#Usage) and the sections following it.

Feature tldr:
* Building RK08, RK05, Serial Disk, and LINCtape images from a base LINCtape image. ([Here](#Media-Types))
    * The secondary device handler will automatically be replaced with the handler for the specified media type.
    * A LINCtape image will also always be automatically generated containing the appropriate handlers, this may be used as boot media or be discarded if it isn't needed.
* A LINCtape-less rebootstrap patch allows restarting DIAL-MS from location 017757. ([Here](#Rebootstrap-Patch))
* Ability to destroy or preserve the DIAL index and file areas. ([Here](#Preserve/Destroy-DIAL-File-Index))
* Option to make the secondary device the system device. ([Here](#Secondary-Device-as-System))
* Option to replace the primary/LINCtape handler with some other handler. ([Here](#Replace-the-Primary-Handler))
    * **WARNING**: This will remove the ability to the LINCtape units in DIAL-MS. Only use this option if you have no plans to use the LINCtape units.
    * LINCtape may still be used for booting, and will be used for rebootstrapping in some cases if the rebootstrap patch is not also applied.

### Usage
```
usage: builder [-h] -o OUTPUT_PATH -i INPUT_PATH -m {linc,rk08,rk05,sdsk} [-d]
                          [--replace-first {linc,rk08,rk05,sdsk}] [-s] [-p]

Build DIAL-MS media for various media types from a reference DIAL-MS LINCtape image.

options:
  -h, --help            show this help message and exit
  -o, --output-path OUTPUT_PATH
                        Output path excluding file extension, used for both the output LINCtape and output $MEDIA
                        images.
  -i, --input-path INPUT_PATH
                        Input LINCtape image path.
  -m, --media {linc,rk08,rk05,sdsk}
                        Media type.
  -d, --preserve-index  Preserve the DIAL file index; if not set (default), the index and entire file area are
                        zeroed in both output images.
  --replace-first {linc,rk08,rk05,sdsk}
                        Replace the default LINCtape handler with a different handler.
  -s, --second-system   Configure system units to use the secondary device handler.
  -p, --enable-patches  Apply patches to allow rebooting DIAL-MS without the use of any LINCtape instructions.
```

Some example uses are provided below.

#### Building a basic Serial Disk image
The following will build new serial disk and LINCtape images to `out.sdsk` and `out.linc`, respectively, from a base `in.linc` LINCtape image.
Both will contain the serial disk handler and their file areas will be erased.
LINCtape will be configured as the system device.
```
python builder.py --input-path in.linc --output-path out --media sdsk
```

#### Building a RK08 image with preserved file areas
The following will build new RK08 and LINCtape images to `out.rk08` and `out.linc`, respectively, from a base `in.linc` LINCtape image.
Both will contain the RK08 handler and their file areas will be directly copied from `in.linc`.
LINCtape will be configured as the system device.
```
python builder.py --input-path in.linc --output-path out --media rk08 --preserve-index
```

#### Building a Serial Disk image for use as the system device with rebootstrap patches
The following will build new serial disk and LINCtape images to `out.sdsk` and `out.linc`, respectively, from a base `in.linc` LINCtape image.
Both will contain the serial disk handler and their file areas will be erased.
Serial Disk will be configured as the system device and it'll be possible to reboot DIAL-MS entirely from Serial Disk after executing a program by starting execution at location 017757 (assuming the final page of field 1 wasn't overwritten).
```
python builder.py --input-path in.linc --output-path out --media sdsk --second-system --enable-patches
```

### Primary Handler? Secondary Handler? System Handler?
DIAL-MS supports having two device handlers installed at a given time (well, you can have more, but good luck).
One slot is located at 07630 and spans 0150 words, this will typically contain the LINCtape handler.
The other slot is located at 07430 and also spans 0150 words, this slot typically contains the handler for whatever other device, if one exists, is being used (RK05, DF32, whatever).

The two slots aren't treated any differently and can both handle accesses to any unit number, but typically the 07630 slot handles `0x` unit numbers while the 07430 slot handles `01x` unit numbers.
For consistency, I'm continuing this convention and will also be referring to the 07630 slot as the "primary" handler and the 07430 slot as the "secondary" handler, since the "primary" handler always exists and is given earlier unit numbers.

The "system" handler is whatever handler is responsible for taking requests to the DIAL-MS system and work areas.
This may be eithe the primary or secondary handler.

### Using the Disk Images
As may come as no shock, the produced images are intended to be written to their respective media (or given to os8diskserver-dial, for Serial Disk).
But there are cases where one of the images may or may not be strictly needed.
Although I recommend using both where possible.

#### Rebootstrap
If the rebootstrap patch is being used, all devices must have consistent I/O routine blocks.
The I/O routines contain the device handlers, unit information, and information on what device is the system device (which is actually just more unit info but anyway).
When the rebootstrap is used, the I/O routines will be read from whatever device the previous loaded program was loaded from and used to restart DIAL-MS.
If that device is configured differently from your system device, the rebootstrap could result in DIAL-MS being loaded from some other device. 

#### LINCtape as System
If LINCtape is being used as system device and the rebootstrap patch isn't being used, the other RK08/RK05/whatever image may be discarded and whatever other media of the chosen type may be used.
In this case, the secondary device isn't being used for any system operations and doesn't need to match the LINCtape's system configuration.

#### No LINCtape :(
If no LINCtape units are being used, the LINCtape image may be discarded.

This also goes for other media types...
but why install $HANDLER if you aren't going to use $HANDLER.

### Unit Numbers
DIAL-MS implements a set of I/O routines that abstract away direct device accesses for the user.
These routines take in a "unit number" value that indicates what device (or device partition) is being accessed, and each device (or device partition) has its own unique unit number.

Builder will assign unit number 00 through 07 to the primary device (typically LINCtape units);
the secondary device (usually the chosen media type) will be assigned unit numbers 10 to 17.
Some unit numbers may not be usable depending on the device being used.
E.g., LINCtape devices are able to use all eight available units, but RK08s can only use up to six units.

Also, DIAL-MS only supports block devices containing 512 blocks containing 256 words each.
Larger devices must be split into 512 block partitions that are each assigned their own unit number (builder takes care of this).
So, e.g., a single RK08 disk provides storage for 6 units.

For each media type, unit numbers are assigned as follows.
`n` is a placeholder that is to be filled in with 0 or 1 when the device is the primary or secondary device, respectively.

RK08, RK05, and Serial Disk:
* `n0` - blocks 0 to 01000 (not including 01000)
* `n1` - blocks 01000 to 02000
* ...
* `n5` - blocks 05000 to 06000

LINCtape:
* `n0` - LINCtape unit 0
* `n1` - LINCtape unit 1
* ...
* `n7` - LINCtape unit 7

### Input and Output Options
The `-i NAME` or `--input NAME` flag is used to specify the base LINCtape image's path (`NAME`).
The input image must be a valid LINCtape image containing a DIAL-MS system.

The `-o NAME` or `--output NAME` flag is used to specify the out image paths (`NAME`).
The given path should not include a file extenion, builder will automatically add one.
In most cases, two output images will be produced, one named `NAME.linc` and another named `NAME.MEDIA`, where `NAME` and `MEDIA` is the provided path and media type, respectively.
The only exception is if provided media type is `linc`, in which case only `NAME.linc` will be produced.

### Output Format
Output LINCtape images will use the `linc` format with 512 blocks containing 256 words each and no start nor end leader.

RK08, RK05, and SDSK images will use the DSK format:
* `rk08` - 3248 blocks containing 256 words each
* `rk05` - 6496 blocks containing 256 words each
* `sdsk` - Same as `rk05`

### Media Types
Builder can currently build images for RK08, RK05, Serial Disk, and LINCtape.
The media type, `TYPE`,  may be specified using the `--media TYPE` option with the valid types being:
* `rk08` - RK08
* `rk05` - RK05
* `sdsk` - Serial Disk (disk format identical to RK05)
* `linc` - LINCtape

For all media types except LINCtape, the secondary device handler will always be the correct handler for the chosen media type;
the LINCtap handler will be the primary handler.

If `linc` is chosen and the primary handler is not overridden (see: [Replace the Primary Handler]), the secondary device handler will be 0'd and the primary handler will be the LINCtape handler.
If the primary handler is overridden, the LINCtape handler will be the secondary handler and the primary handler will be that specified by the override option.

### Rebootstrap Patch
Builder provides a patch that allows restarting DIAL-MS without any LINCtape dependency.
The system can be restarted by starting at location 017757, assuming the final page of field 1 hadn't been overwritten.
The patch may be applied using the `-p` or `--enable-patches` flag.

NOTE: This will restart the system from whatever device was previously used to load a program.


#### Longer Explaination
The reboostrap patch option does two things.

DIAL-MS doesn't have a usable core resident routine restarting the system, unlike OS/8 and friends.
But after loading programs, the handler used to load the program _is_ left in the final page of field 1.
On its own, this handler cannot be used for a quick & easy restart entry, but it can be used to implement one.
What I did is implement a small rebootstrap program that can be inserted into most/all DIAL-MS device handlers.
It will read the I/O routines into field 0 using the leftover handler then jump to the restart routine.
Since the rebootstrap is technically part of the handlers, it also gets leftover in core after loading a program and can be quickly executed using the console switches.
In all currently implementations, the reboostrap will be located at 017757 after loading a program.

But there is a another issue.
The afforementioned restart routine in the I/O routines will mostly use the device-agnostic I/O routines when reading blocks.
However, the restart routine requires that it's located in field 1; if it's not, it will re-read the I/O routines into field 1 using LINCtape read instructions and jump to the restart routine in field 1.
This creates an LINCtape dependency when restarting the system from field 0.

As far as I can tell, there's no technical need for the use of LINCtape instructions here, and they can be trivially replaced to an equivalent call to the READ I/O routine.
So... that's what I did.

### Secondary Device as System
The secondary device (chosen via media type) can be be used as the system device using the `-s` or `--second-system` flag.
This will make DIAL-MS depend on the secondary device for doing anything.

#### Longer Explaination
DIAL-MS internally accesses its system and work areas using special unit number (100, 110, 111) through the standard I/O routines.
Since the I/O routines are used for accessing these areas, any device can be used as the system device.
DEC's system build tool will setup the system to the use the secondary device as the system device if a secondary device is available and doesn't provide an option to keep LINCtape as the system device in such cases.
Builder deviates from this and instead defaults to using LINCtape as the system device, with an optional flag for using the secondary device as the system device.
My intent with this is to provide better hardware compatibility by default since all fully functioning and intact PDP-12 systems will have LINCtape transports.

### Preserve/Destroy DIAL File Index
Builder provides an option for preserving or destroying the DIAL file index and storage areas when copying the base image.
Destroying the file index may be desirable if you're attempting to build a clean & prestine system;
preserving it may be desirable if your goal is format conversion or similar.
The file areas may be preserved using the `-d` or `--preserve-index` flag, otherwise the file areas will be destroyed (default).

If the file index and storage areas are to be destroyed (default), the following blocks will be 0'd when copying the base image:
* 00 to 0300 (beginning file storage area)
* 0370 to 01000 (end file storage area)
* 0346 and 0347 (file index area)

These areas will be copied without modification if they're to be preserved.

### Replace the Primary Handler
The `--replace-primary hndlr` option can be used to replace the primary device handler with the handler `hndlr`.

[Secondary Device as System](#Secondary-Device-as-System) still functions as usual when this is used.

#### Longer Explaination
DIAL-MS supports having two installed device handlers.
Typically, one of these will the LINCtape handler and the other will be a handler for some other storage device.
By default, builder will mirro this setup, leaving the LINCtape handler in the primary handler slot and adding whatever other handler in the secondary slot.

In some cases it may be desirable to replace the LINCtape handler with another handler as well.
For this reason, builder supports replacing the primary LINCtape handler with another supported handler.

