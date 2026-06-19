/*
 * Minimal Cortex-M3 startup for QEMU mps2-an385.
 * Provides the vector table, reset handler (.data/.bss init), and routes the
 * SVC/PendSV/SysTick exceptions to the FreeRTOS ARM_CM3 port handlers.
 */
#include <stdint.h>

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;

extern int main(void);

/* FreeRTOS ARM_CM3 port handlers. */
extern void vPortSVCHandler(void);
extern void xPortPendSVHandler(void);
extern void xPortSysTickHandler(void);

void Reset_Handler(void)
{
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }
    for (dst = &_sbss; dst < &_ebss; ) {
        *dst++ = 0;
    }
    main();
    for (;;) { }
}

void Default_Handler(void)
{
    for (;;) { }
}

void HardFault_Handler(void)
{
    for (;;) { }
}

/* Weak aliases so unused exceptions fall through to Default_Handler. */
#define ALIAS __attribute__((weak, alias("Default_Handler")))
void NMI_Handler(void) ALIAS;
void MemManage_Handler(void) ALIAS;
void BusFault_Handler(void) ALIAS;
void UsageFault_Handler(void) ALIAS;
void DebugMon_Handler(void) ALIAS;

typedef void (*vector_t)(void);

__attribute__((section(".isr_vector"), used))
const vector_t g_vectors[] = {
    (vector_t) &_estack,        /*  0: initial stack pointer */
    Reset_Handler,              /*  1: reset                 */
    NMI_Handler,                /*  2 */
    HardFault_Handler,          /*  3 */
    MemManage_Handler,          /*  4 */
    BusFault_Handler,           /*  5 */
    UsageFault_Handler,         /*  6 */
    0, 0, 0, 0,                 /*  7-10: reserved */
    vPortSVCHandler,            /* 11: SVCall   -> FreeRTOS */
    DebugMon_Handler,           /* 12 */
    0,                          /* 13: reserved */
    xPortPendSVHandler,         /* 14: PendSV   -> FreeRTOS */
    xPortSysTickHandler,        /* 15: SysTick  -> FreeRTOS */
};
