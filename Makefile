# This Makefile downloads the OpenWRT Image Builder and builds an image
# for the TL-WPA8630 v2 with a custom partition layout and DTS file.

ALL_CURL_OPTS := $(CURL_OPTS) -L --fail --create-dirs -s

VERSION := 21.02.3
GCC_VERSION := 8.4.0_musl
BOARD := ath79
SUBTARGET := generic
SOC := qca9563
ARCH := mips_24kc
BUILDER := openwrt-imagebuilder-$(VERSION)-$(BOARD)-$(SUBTARGET).Linux-x86_64
SDK := openwrt-sdk-$(VERSION)-$(BOARD)-$(SUBTARGET)_gcc-$(GCC_VERSION).Linux-x86_64
PROFILE := dlink_covr-p2500-a1
DEVICE_DTS := $(SOC)_$(PROFILE)
PACKAGES := luci
EXTRA_IMAGE_NAME := custom

TOPDIR := $(CURDIR)/$(BUILDER)
SDKDIR := $(CURDIR)/$(SDK)
KDIR := $(TOPDIR)/build_dir/target-mips_24kc_musl/linux-$(BOARD)_$(SUBTARGET)
PATH := $(TOPDIR)/staging_dir/host/bin:$(SDKDIR)/staging_dir/toolchain-$(ARCH)_gcc-$(GCC_VERSION)/bin:$(PATH)
LINUX_VERSION = $(shell sed -n -e '/Linux-Version: / {s/Linux-Version: //p;q}' $(BUILDER)/.targetinfo)


all: images

$(BUILDER).tar.xz:
	curl $(ALL_CURL_OPTS) -O https://downloads.openwrt.org/releases/$(VERSION)/targets/$(BOARD)/$(SUBTARGET)/$(BUILDER).tar.xz

firmware-utils-master.tar.gz:
	curl $(ALL_CURL_OPTS) "https://git.openwrt.org/?p=project/firmware-utils.git;a=snapshot;h=refs/heads/master;sf=tgz" -o firmware-utils-master.tar.gz

$(BUILDER): $(BUILDER).tar.xz firmware-utils-master.tar.gz
	rm -rf $(BUILDER).tmp
	mkdir $(BUILDER).tmp
	tar -xf $(BUILDER).tar.xz -C $(BUILDER).tmp --strip-components=1

	# Fetch firmware utility sources to apply patches
	mkdir -p $(BUILDER).tmp/tools/firmware-utils
	tar -xf firmware-utils-master.tar.gz -C $(BUILDER).tmp/tools/firmware-utils --strip-components=1

	# Apply all patches
	$(foreach file, $(sort $(wildcard patches/*.patch)), patch -d $(BUILDER).tmp -p1 < $(file);)
	cd $(BUILDER).tmp/tools/firmware-utils \
		&& cmake . \
		&& make dlink-sge-image
	mv $(BUILDER).tmp/tools/firmware-utils/dlink-sge-image $(TOPDIR).tmp/staging_dir/host/bin/dlink-sge-image

	# Regenerate .targetinfo
	cd $(BUILDER).tmp && make -f include/toplevel.mk TOPDIR="$(TOPDIR).tmp" prepare-tmpinfo || true
	cp -f $(BUILDER).tmp/tmp/.targetinfo $(BUILDER).tmp/.targetinfo
	mv $(BUILDER).tmp $(BUILDER)

$(SDK).tar.xz:
	curl $(ALL_CURL_OPTS) -O https://downloads.openwrt.org/releases/$(VERSION)/targets/$(BOARD)/$(SUBTARGET)/$(SDK).tar.xz

$(SDK): $(SDK).tar.xz
	tar -xf $(SDK).tar.xz

linux-include: $(BUILDER)
	# Fetch DTS include dependencies
	curl $(ALL_CURL_OPTS) "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/plain/include/dt-bindings/clock/ath79-clk.h?h=v$(LINUX_VERSION)" -o linux-include.tmp/dt-bindings/clock/ath79-clk.h
	curl $(ALL_CURL_OPTS) "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/plain/include/dt-bindings/gpio/gpio.h?h=v$(LINUX_VERSION)" -o linux-include.tmp/dt-bindings/gpio/gpio.h
	curl $(ALL_CURL_OPTS) "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/plain/include/dt-bindings/input/input.h?h=v$(LINUX_VERSION)" -o linux-include.tmp/dt-bindings/input/input.h
	curl $(ALL_CURL_OPTS) "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/plain/include/uapi/linux/input-event-codes.h?h=v$(LINUX_VERSION)" -o linux-include.tmp/dt-bindings/input/linux-event-codes.h
	curl $(ALL_CURL_OPTS) "https://github.com/openwrt/openwrt/raw/v$(VERSION)/target/linux/generic/files/include/dt-bindings/mtd/partitions/uimage.h" -o linux-include.tmp/dt-bindings/mtd/partitions/uimage.h
	mv -T linux-include.tmp linux-include


$(KDIR)/$(PROFILE)-kernel.bin: $(BUILDER) $(SDK) linux-include
	# Build this device's DTB and firmware kernel image. Uses the official kernel build as a base.
	cp -Trf linux-include $(KDIR)/linux-$(LINUX_VERSION)/include
	cd $(BUILDER) && env PATH=$(PATH) make --trace -C target/linux/$(BOARD)/image $(KDIR)/$(PROFILE)-kernel.bin \
		TOPDIR="$(TOPDIR)" \
		INCLUDE_DIR="$(TOPDIR)/include" \
		TARGET_BUILD=1 \
		BOARD="$(BOARD)" \
		SUBTARGET="$(SUBTARGET)" \
		PROFILE="$(PROFILE)" \
		DEVICE_DTS="$(DEVICE_DTS)" \
		LOADER_TYPE="bin" \
		LOADER_FLASH_OFFS="0x050000" \
		LOADER_KERNEL_MAGIC="0x68737173" \
		COMPILE="loader-$(PROFILE).bin loader-$(PROFILE).uImage" \
		COMPILE/loader-$(PROFILE).bin=loader-okli-compile \
		COMPILE/loader-$(PROFILE).uImage="append-loader-okli $(PROFILE) | pad-to 64k | lzma | uImage lzma" \
		KERNEL="kernel-bin | append-dtb | lzma | uImage lzma -M 0x68737173" \
		IMAGE_SIZE="14528k"


images: $(BUILDER) $(KDIR)/$(PROFILE)-kernel.bin
	# Use ImageBuilder as normal
	cd $(BUILDER) && make image PROFILE="$(PROFILE)" EXTRA_IMAGE_NAME="$(EXTRA_IMAGE_NAME)" PACKAGES="$(PACKAGES)" FILES="$(TOPDIR)/target/linux/$(BOARD)/$(SUBTARGET)/base-files/" FORCE=1
	cat $(BUILDER)/bin/targets/$(BOARD)/$(SUBTARGET)/sha256sums
	ls -hs $(BUILDER)/bin/targets/$(BOARD)/$(SUBTARGET)/openwrt-*.bin


clean:
	rm -rf openwrt-imagebuilder-*
	rm -rf openwrt-sdk-*
	rm -f firmware-utils-master.tar.gz
	rm -rf linux-include
