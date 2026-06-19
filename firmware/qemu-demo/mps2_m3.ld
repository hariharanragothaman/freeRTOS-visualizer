/*
 * Linker script for QEMU's mps2-an385 (ARM Cortex-M3).
 * Memory map matches the FreeRTOS CORTEX_MPS2_QEMU_GCC reference demo.
 */
MEMORY
{
    FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 0x00400000  /* 4 MB code   */
    RAM   (rwx): ORIGIN = 0x20000000, LENGTH = 0x00400000  /* 4 MB SRAM   */
}

/* Top of stack used by the Reset_Handler / main() before the scheduler runs. */
_estack = ORIGIN(RAM) + LENGTH(RAM);

ENTRY(Reset_Handler)

SECTIONS
{
    .isr_vector :
    {
        KEEP(*(.isr_vector))
    } > FLASH

    .text :
    {
        . = ALIGN(4);
        *(.text)
        *(.text*)
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
        _etext = .;
    } > FLASH

    /* Initialised data: load from FLASH, run from RAM. */
    _sidata = LOADADDR(.data);
    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > RAM AT > FLASH

    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        __bss_start__ = _sbss;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
        __bss_end__ = _ebss;
    } > RAM

    /* newlib-nano sbrk heap (snprintf etc. do not use it, but link it anyway). */
    .heap (NOLOAD) :
    {
        . = ALIGN(8);
        PROVIDE(end = .);
        PROVIDE(_end = .);
        . = . + 0x1000;
        . = ALIGN(8);
    } > RAM
}
