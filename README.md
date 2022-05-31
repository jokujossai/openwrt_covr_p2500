# OpenWRT image for D-Link COVR-P2500 A1

## Overview

This repository adds a build profile for D-Link COVR-P2500.  
Device configuration from [s-2's covr-2500_plctest branch](https://github.com/s-2/openwrt/tree/covr-2500_plctest).  
Build script based on [jwmullay's openwrt_wpa8630p_v2_fullmem](https://github.com/jwmullally/openwrt_wpa8630p_v2_fullmem).  

## Supported Devices

| Hardware Version |
| --- |
| `Model: COVR-P2500 Rev A1` |


## Building

Clone repository and run `make`

## Installing

### OEM Web UI
Login to http://covr.local/ (or with IP address). Navigate to Management -> Upgrade and upload factory.bin.

OEM configuration is not compatible with OpenWRT so the device can't be accessed before reset. Wait long enough to make sure upgrade is finished and reset device with reset button. Use ethernet port 1 or 2 (in the middle of the device) to access LUCI Web UI on http://192.168.1.1/.

### OEM Recovery UI (Not working)
Hold reset while powering device and access the Recovery UI on http://192.168.0.50/. Upload recovery.bin

### From OpenWRT 18.06-SNAPSHOT r7704-9ee8c8daf4 (http://www.netadair.de/openwrt/)
!!! DO NOT FORCE FLASH sysupgrade.bin

Release is not compatible with old loader. Force flash with sysupgrade-openwrt1806.bin that contains also new loader.
```
sysupgrade -n -F sysupgrade-openwrt1806.bin
```

### u-boot serial recovery
Setup tftpd server on 192.168.0.100 with recovery.bin named as 3200A8C0.img.
Start device with serial console attached and access u-boot console by pressing any key when promted.
Install image with commands:
```
tftpboot
erase 0x9f050000 +$filesize
cp.b $fileaddr 0x9f050000 $filesize
reset
```

## PLC

SSH to device and run `/etc/init.d/plc setup`. Make selections and start PLC with `/etc/init.d/plc start`. Alternatively you can download plc scripts from [netadair.de](http://www.netadair.de/openwrt/)

## Serial
Remove 4 skrews and open the device. There is 4 holes for serial port header with labels U-RX, U-TX, GND and P3V3.
Remove 3 skrews holding upper circuit board and solder 4 or 3 pin (P3V3 not used) header.
Put the board back to device without cover and connect USB-TTL adapter to header (GND -> GND, RX -> U-TX, TX -> U-RX).
Power on device and you should see output when using baud rate 115200.

For some reason bootloader output was not readable so I attached another USB-TTL adapter to only receive (GND -> GND, RX -> U-TX) with configuration 115200,cs7,cstopb. With that configuration I got almost readable output and used another adapter to send commands.
