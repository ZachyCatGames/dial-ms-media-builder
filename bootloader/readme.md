## LAP6-DIAL-MS Bootloaders
These bootloader allow fully booting LAP6-DIAL-MS (DIAL-MS) from non-LINCtape media.
They may be useful in cases where a system doesn't have functioning LINCtape units, but does have a functioning, e.g., RK08 controller & disk(s).

Each media type has its own bootloader, for example `sdsk-bootloader.rim` is the bootloader for Serial Disk.

All of the bootloaders are used the same way:
1) Load the standard RIM loader and send the `$MEDIA-bootloader.rim` file.
2) Stop the RIN loader by depressing then un-depressing the `STOP` switch.
3) Make sure `MODE` is set to `8`.
4) Depress `I/O PRESET`.
5) Make sure $MEDIA is loaded available for use.
    * Exact procedure varies between media types.
6) Depress `START 20`
    * These also support being started at location 0200.
7) After a short wait, the PDP-12 should be booted in DIAL-MS

