include ./Makefile

$(KDIR)/$(PROFILE)-kernel.bin:
	env PATH=$(PATH) make --trace -C $(TOPDIR)/target/linux/$(BOARD)/image \
		$(KDIR)/$(PROFILE)-kernel.bin \
		TOPDIR="$(TOPDIR)" \
		INCLUDE_DIR="$(TOPDIR)/include" \
		TARGET_BUILD=1 \
		BOARD="$(BOARD)" \
		SUBTARGET="$(SUBTARGET)" \
		PROFILE="$(PROFILE)" \
		DEVICE_DTS="$(DEVICE_DTS)" \
		LOADER_TYPE="$(LOADER_TYPE)" \
		LOADER_FLASH_OFFS="$(LOADER_FLASH_OFFS)" \
		LOADER_KERNEL_MAGIC="$(LOADER_KERNEL_MAGIC)" \
		COMPILE="$(COMPILE)" \
		KERNEL="$(KERNEL)" \
		IMAGE_SIZE="$(IMAGE_SIZE)"
