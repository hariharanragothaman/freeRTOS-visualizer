# QEMU FreeRTOS trace-shim demo (Cortex-M3 / mps2-an385).
#
#   make            # fetch kernel, build build/demo.elf
#   make run        # run in QEMU, protocol streams to your terminal (Ctrl-A X to quit)
#   make socket     # run in QEMU, expose the UART on TCP :12345 for the host tool
#   make verify     # build + run headless and assert the protocol parses (CI gate)
#   make clean      # remove build artifacts (keeps the fetched kernel)
#   make distclean  # also remove the fetched kernel

CROSS           ?= arm-none-eabi-
CC              := $(CROSS)gcc
OBJCOPY         := $(CROSS)objcopy
QEMU            ?= qemu-system-arm

KERNEL_VERSION  ?= V11.1.0
KERNEL_REPO     ?= https://github.com/FreeRTOS/FreeRTOS-Kernel.git
KERNEL_DIR      := FreeRTOS-Kernel
PORT_DIR        := $(KERNEL_DIR)/portable/GCC/ARM_CM3
MEMMANG_DIR     := $(KERNEL_DIR)/portable/MemMang

BUILD           := build
ELF             := $(BUILD)/demo.elf
SHIM_DIR        := ..

INCLUDES := \
	-I. \
	-I$(SHIM_DIR) \
	-I$(KERNEL_DIR)/include \
	-I$(PORT_DIR)

KERNEL_SRC := \
	$(KERNEL_DIR)/tasks.c \
	$(KERNEL_DIR)/queue.c \
	$(KERNEL_DIR)/list.c \
	$(PORT_DIR)/port.c \
	$(MEMMANG_DIR)/heap_4.c

APP_SRC := \
	main.c \
	uart.c \
	startup.c \
	$(SHIM_DIR)/trace_shim.c

SRC := $(APP_SRC) $(KERNEL_SRC)

CFLAGS := \
	-mcpu=cortex-m3 -mthumb \
	-Wall -Wextra -O2 -g3 -ffreestanding -ffunction-sections -fdata-sections \
	$(INCLUDES)

LDFLAGS := \
	-mcpu=cortex-m3 -mthumb \
	-T mps2_m3.ld -nostartfiles -Wl,--gc-sections \
	-specs=nano.specs -specs=nosys.specs -Wl,-Map=$(BUILD)/demo.map

.PHONY: all run socket verify clean distclean

all: $(ELF)

$(KERNEL_DIR):
	git clone --depth 1 --branch $(KERNEL_VERSION) $(KERNEL_REPO) $(KERNEL_DIR)

$(ELF): $(KERNEL_DIR) $(SRC) mps2_m3.ld FreeRTOSConfig.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(SRC) $(LDFLAGS) -o $(ELF)
	@echo "Built $(ELF)"

# Stream the protocol straight to the terminal. Quit QEMU with Ctrl-A then X.
run: $(ELF)
	$(QEMU) -machine mps2-an385 -cpu cortex-m3 -kernel $(ELF) -nographic

# Expose the target UART on TCP :12345 so the host visualizer can connect:
#   rtos-visualize --serial-url socket://localhost:12345 --view timeline
socket: $(ELF)
	$(QEMU) -machine mps2-an385 -cpu cortex-m3 -kernel $(ELF) \
		-display none -serial tcp::12345,server,nowait

# Headless end-to-end gate: boots QEMU, reads the UART, parses with the host code.
verify: $(ELF)
	python3 verify_qemu.py --elf $(ELF) --seconds 4

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -rf $(KERNEL_DIR)
