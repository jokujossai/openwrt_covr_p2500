# This Makefile downloads the OpenWRT Image Builder and builds an image
# for the COVR P2500 with a custom partition layout, DTS file and factory image.

ALL_CURL_OPTS := $(CURL_OPTS) -L --fail --create-dirs -s

VERSION := 23.05.2
GCC_VERSION := 12.3.0_musl
BOARD := ath79
SUBTARGET := generic
ARCH := mips_24kc
BUILDER := openwrt-imagebuilder-$(VERSION)-$(BOARD)-$(SUBTARGET).Linux-x86_64
SDK := openwrt-sdk-$(VERSION)-$(BOARD)-$(SUBTARGET)_gcc-$(GCC_VERSION).Linux-x86_64
PROFILES := dlink_covr-p2500-a1
PACKAGES := luci squashfs-tools-unsquashfs
EXTRA_IMAGE_NAME := custom

BUILDER_URL := https://downloads.openwrt.org/releases/$(VERSION)/targets/$(BOARD)/$(SUBTARGET)/$(BUILDER).tar.xz
SDK_URL := https://downloads.openwrt.org/releases/$(VERSION)/targets/$(BOARD)/$(SUBTARGET)/$(SDK).tar.xz

# Snapshot build
#BUILDER := openwrt-imagebuilder-ath79-generic.Linux-x86_64
#SDK := openwrt-sdk-ath79-generic_gcc-12.3.0_musl.Linux-x86_64
#BUILDER_URL := https://downloads.openwrt.org/snapshots/targets/$(BOARD)/$(SUBTARGET)/$(BUILDER).tar.xz
#SDK_URL := https://downloads.openwrt.org/snapshots/targets/$(BOARD)/$(SUBTARGET)/$(SDK).tar.xz

TOPDIR := $(CURDIR)/$(BUILDER)
SDKDIR := $(CURDIR)/$(SDK)
KDIR := $(TOPDIR)/build_dir/target-$(ARCH)_musl/linux-$(BOARD)_$(SUBTARGET)
BUILDER_PATH := $(TOPDIR)/staging_dir/host/bin:$(SDKDIR)/staging_dir/toolchain-$(ARCH)_gcc-$(GCC_VERSION)/bin:$(PATH)
LINUX_VERSION = $(shell sed -n -e '/Linux-Version: / {s/Linux-Version: //p;q}' $(BUILDER)/.targetinfo)
all: images

$(BUILDER).tar.xz:
	curl $(ALL_CURL_OPTS) -O $(BUILDER_URL)

firmware-utils-master.tar.gz:
	curl $(ALL_CURL_OPTS) "https://git.openwrt.org/?p=project/firmware-utils.git;a=snapshot;h=refs/heads/master;sf=tgz" -o firmware-utils-master.tar.gz

$(BUILDER): $(BUILDER).tar.xz firmware-utils-master.tar.gz patches/*.patch $(SDK)
	rm -rf $(BUILDER) $(BUILDER).tmp
	mkdir $(BUILDER).tmp
	tar -xf $(BUILDER).tar.xz -C $(BUILDER).tmp --strip-components=1

	# Fetch firmware utility sources to apply patches
	mkdir -p $(BUILDER).tmp/tools/firmware-utils
	tar -xf firmware-utils-master.tar.gz -C $(BUILDER).tmp/tools/firmware-utils --strip-components=1

	# Apply all patches
	$(foreach file, $(sort $(wildcard patches/*.patch)), echo Applying patch $(file); patch -d $(BUILDER).tmp -p1 < $(file);)
	cd $(BUILDER).tmp/tools/firmware-utils \
		&& cmake . \
		&& make dlink-sge-image
	mv $(BUILDER).tmp/tools/firmware-utils/dlink-sge-image $(TOPDIR).tmp/staging_dir/host/bin/dlink-sge-image

	# Update .targetinfo
	cp -f $(SDK)/.targetinfo $(BUILDER).tmp/.targetinfo
	mv $(BUILDER).tmp $(BUILDER)

$(SDK).tar.xz:
	curl $(ALL_CURL_OPTS) -O $(SDK_URL)

$(SDK): $(SDK).tar.xz firmware-utils-master.tar.gz patches/*.patch
	rm -rf $(SDK) $(SDK).tmp
	mkdir $(SDK).tmp
	tar -xf $(SDK).tar.xz -C $(SDK).tmp --strip-components=1

	# Fetch firmware utility sources to apply patches
	mkdir -p $(SDK).tmp/tools/firmware-utils
	tar -xf firmware-utils-master.tar.gz -C $(SDK).tmp/tools/firmware-utils --strip-components=1

	# Apply all patches
	$(foreach file, $(sort $(wildcard patches/*.patch)), echo Applying patch $(file); patch -d $(SDK).tmp -p1 < $(file);)
	cd $(SDK).tmp/tools/firmware-utils \
		&& cmake . \
		&& make dlink-sge-image
	mv $(SDK).tmp/tools/firmware-utils/dlink-sge-image $(SDKDIR).tmp/staging_dir/host/bin/dlink-sge-image

	# Regenerate .targetinfo
	cd $(SDK).tmp && make -f include/toplevel.mk TOPDIR="$(SDKDIR).tmp" prepare-tmpinfo || true
	cp -f $(SDK).tmp/tmp/.targetinfo $(SDK).tmp/.targetinfo
	mv $(SDK).tmp $(SDK)

linux-include: $(BUILDER)
	# Fetch DTS include dependencies
	curl $(ALL_CURL_OPTS) "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/plain/include/dt-bindings/clock/ath79-clk.h?h=v$(LINUX_VERSION)" -o linux-include.tmp/dt-bindings/clock/ath79-clk.h
	curl $(ALL_CURL_OPTS) "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/plain/include/dt-bindings/gpio/gpio.h?h=v$(LINUX_VERSION)" -o linux-include.tmp/dt-bindings/gpio/gpio.h
	curl $(ALL_CURL_OPTS) "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/plain/include/dt-bindings/input/input.h?h=v$(LINUX_VERSION)" -o linux-include.tmp/dt-bindings/input/input.h
	curl $(ALL_CURL_OPTS) "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/plain/include/uapi/linux/input-event-codes.h?h=v$(LINUX_VERSION)" -o linux-include.tmp/dt-bindings/input/linux-event-codes.h
	curl $(ALL_CURL_OPTS) "https://github.com/openwrt/openwrt/raw/v$(VERSION)/target/linux/generic/files/include/dt-bindings/mtd/partitions/uimage.h" -o linux-include.tmp/dt-bindings/mtd/partitions/uimage.h
	rm -rf linux-include
	mv -T linux-include.tmp linux-include

kernel: $(BUILDER) $(SDK) linux-include
	# Build this device's DTB and firmware kernel image. Uses the official kernel build as a base.
	cp -Trf linux-include $(KDIR)/linux-$(LINUX_VERSION)/include

	cd $(BUILDER) && $(foreach PROFILE,$(PROFILES),\
		env PATH=$(BUILDER_PATH) make --trace -C $(TOPDIR)/target/linux/$(BOARD)/image \
			$(KDIR)/$(PROFILE)-kernel.bin \
			TOPDIR="$(TOPDIR)" \
			INCLUDE_DIR="$(TOPDIR)/include" \
			TARGET_BUILD=1 \
			BOARD="$(BOARD)" \
			SUBTARGET="$(SUBTARGET)" \
			PROFILE="$(PROFILE)" \
			TARGET_DEVICES="$(PROFILE)" \
	;)

images: $(BUILDER) kernel

	# Use ImageBuilder as normal
	cd $(BUILDER) && $(foreach PROFILE,$(PROFILES),\
		make image PROFILE="$(PROFILE)" EXTRA_IMAGE_NAME="$(EXTRA_IMAGE_NAME)" PACKAGES="$(PACKAGES)" FILES="$(TOPDIR)/target/linux/$(BOARD)/$(SUBTARGET)/base-files/"\
	;)
	cat $(BUILDER)/bin/targets/$(BOARD)/$(SUBTARGET)/sha256sums
	ls -hs $(BUILDER)/bin/targets/$(BOARD)/$(SUBTARGET)/openwrt-*.bin


clean:
	rm -rf openwrt-imagebuilder-*
	rm -rf openwrt-sdk-*
	rm -f firmware-utils-master.tar.gz
	rm -rf linux-include
