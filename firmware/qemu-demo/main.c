/*
 * QEMU FreeRTOS demo for freeRTOS-visualizer.
 *
 * Creates a handful of representative tasks that move through Running / Ready /
 * Blocked / Suspended states, then starts trace_shim's periodic snapshot task.
 * The shim emits the exact host protocol over UART0:
 *
 *     Task:<name>,State:<code>,Tick:<n>\r\n
 *
 * Build + run with the Makefile in this directory, then point the host at the
 * QEMU serial socket. This is the end-to-end proof that trace_shim.c produces
 * what the Python visualizer consumes.
 */
#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"

#include "trace_shim.h"

void uart_init(void);
void trace_serial_write(const char *line);

/* Stack-overflow hook (configCHECK_FOR_STACK_OVERFLOW): make the failure
 * observable on the same UART the visualizer reads, then halt. */
void vApplicationStackOverflowHook(TaskHandle_t task, char *name)
{
    (void) task;
    trace_serial_write("ERROR:StackOverflow,Task:");
    trace_serial_write(name ? name : "?");
    trace_serial_write("\r\n");
    taskDISABLE_INTERRUPTS();
    for (;;) { }
}

/* A semaphore the worker blocks on, so the visualizer shows a real Blocked task
 * that periodically wakes (rather than everything just delaying). */
static SemaphoreHandle_t xWork;

/* Busy-spin to make a task observably "Running" between blocking points. */
static void burn_cycles(volatile uint32_t n)
{
    while (n-- > 0) {
        __asm volatile ("nop");
    }
}

static void vBlink(void *arg)
{
    (void) arg;
    const TickType_t period = pdMS_TO_TICKS(200);
    TickType_t last = xTaskGetTickCount();
    for (;;) {
        burn_cycles(20000);
        vTaskDelayUntil(&last, period);   /* -> Blocked between blinks */
    }
}

static void vSensor(void *arg)
{
    (void) arg;
    for (;;) {
        burn_cycles(40000);
        xSemaphoreGive(xWork);            /* wake the worker */
        vTaskDelay(pdMS_TO_TICKS(100));   /* -> Blocked */
    }
}

static void vWorker(void *arg)
{
    (void) arg;
    for (;;) {
        /* Block until the sensor produces something to process. */
        if (xSemaphoreTake(xWork, portMAX_DELAY) == pdTRUE) {
            burn_cycles(60000);
        }
    }
}

/* Runs once, suspends itself, and is later resumed — exercises Suspended (3). */
static void vMaintenance(void *arg)
{
    (void) arg;
    for (;;) {
        burn_cycles(10000);
        vTaskSuspend(NULL);               /* -> Suspended until resumed */
    }
}

int main(void)
{
    uart_init();

    xWork = xSemaphoreCreateBinary();

    xTaskCreate(vBlink,       "LED_Blink",   configMINIMAL_STACK_SIZE,     NULL, 2, NULL);
    xTaskCreate(vSensor,      "SensorRead",  configMINIMAL_STACK_SIZE,     NULL, 3, NULL);
    xTaskCreate(vWorker,      "Worker",      configMINIMAL_STACK_SIZE,     NULL, 2, NULL);
    xTaskCreate(vMaintenance, "Maintenance", configMINIMAL_STACK_SIZE,     NULL, 1, NULL);

    /* The actual shim under test: emits the protocol every TRACE_PERIOD_MS. */
    trace_shim_start();

    vTaskStartScheduler();

    /* Only reached if there was not enough heap to start the scheduler. */
    for (;;) { }
    return 0;
}
