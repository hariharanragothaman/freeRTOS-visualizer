/*
 * CMSDK APB UART driver for QEMU's mps2-an385. UART0 is the board's console;
 * with `-serial`/`-nographic` QEMU forwards it to stdio or a TCP socket.
 *
 * This file is the "provide a serial writer for your board" step from the shim
 * README: it implements trace_serial_write() that trace_shim.c calls.
 */
#include <stdint.h>

#define CMSDK_UART0_BASE 0x40004000UL

typedef struct {
    volatile uint32_t DATA;       /* 0x00 RW data */
    volatile uint32_t STATE;      /* 0x04 RW state (bit0 = TX buffer full) */
    volatile uint32_t CTRL;       /* 0x08 RW control (bit0 = TX enable) */
    volatile uint32_t INTSTATUS;  /* 0x0C */
    volatile uint32_t BAUDDIV;    /* 0x10 baud divider (>= 16) */
} CMSDK_UART_t;

#define UART0 ((CMSDK_UART_t *) CMSDK_UART0_BASE)

void uart_init(void)
{
    UART0->BAUDDIV = 16;   /* QEMU ignores the rate but the model requires >= 16 */
    UART0->CTRL = 1u;      /* enable transmitter */
}

static void uart_putc(char c)
{
    while (UART0->STATE & 1u) {
        /* spin while TX buffer is full */
    }
    UART0->DATA = (uint32_t) (unsigned char) c;
}

/* Called by trace_shim.c — one already-newline-terminated protocol line. */
void trace_serial_write(const char *line)
{
    for (const char *p = line; *p != '\0'; ++p) {
        uart_putc(*p);
    }
}
