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

```bash
make
```

## Installing
Setup tftpd server on 192.168.0.100 with recover.img named as 3200A8C0.img.
Start device with serial console attached and access u-boot console by pressing any key when promted.
Install image with commands:
```
tftpboot
erase 0x9f050000 +$filesize
cp.b $fileaddr 0x9f050000 $filesize
```

## Known problems
### Network not available after install
Switch ports 1 and 2 are assigned to eth0.1 but interface is not up. Setup interface:
```bash
ip link add link eth0 name eth0.1 type vlan id 1
ip link set dev eth0.1 up
brctl addif br-lan eth0.1
```
Access LUCI interafce on address 192.168.1.1
