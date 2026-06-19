/*
 * freeRTOS-visualizer trace shim
 * ------------------------------
 * Drop-in C that makes a FreeRTOS target emit the exact protocol the host tool
 * consumes:
 *
 *     Task:<name>,State:<code>,Tick:<n>\r\n
 *
 * State codes mirror FreeRTOS eTaskState (task.h): eRunning=0 .. eInvalid=5.
 * The Tick is xTaskGetTickCount(), so the host keys timing off the *device*
 * clock instead of host read time.
 *
 * Requirements (FreeRTOSConfig.h):
 *     #define configUSE_TRACE_FACILITY    1   // needed by uxTaskGetSystemState
 *
 * Wiring:
 *   1. Implement trace_serial_write() for your board (write to the same UART /
 *      semihosting / TCP the visualizer reads).
 *   2. Call trace_shim_start() once after the scheduler is created (or create
 *      the task yourself).
 *
 * That's it — point `rtos-visualize --serial-url ...` at that port.
 */

#include "FreeRTOS.h"
#include "task.h"

#include <stdio.h>
#include <stddef.h>

#ifndef TRACE_MAX_TASKS
#define TRACE_MAX_TASKS 16
#endif

#ifndef TRACE_PERIOD_MS
#define TRACE_PERIOD_MS 50
#endif

/* Re-announce the tick metadata every N snapshots so a host that connects late
 * still learns the device clock (it is cheap: two short lines). */
#ifndef TRACE_META_EVERY
#define TRACE_META_EVERY 40
#endif

/* Tick counter width, so the host can unwrap wraparound. FreeRTOS uses 16-bit
 * ticks when configUSE_16_BIT_TICKS is set, otherwise 32-bit. */
#if defined(configUSE_16_BIT_TICKS) && (configUSE_16_BIT_TICKS == 1)
#define TRACE_TICK_BITS 16
#else
#define TRACE_TICK_BITS 32
#endif

/*
 * Provide this in your BSP. Writes one already-newline-terminated line to the
 * serial transport the host reads. Must be callable from a task context.
 */
extern void trace_serial_write(const char *line);

/* eTaskState already aligns 1:1 with the protocol; map explicitly so a future
 * FreeRTOS enum change can't silently desync the firmware from the host. */
static int trace_state_code(eTaskState state)
{
    switch (state)
    {
        case eRunning:   return 0;
        case eReady:     return 1;
        case eBlocked:   return 2;
        case eSuspended: return 3;
        case eDeleted:   return 4;
        default:         return 5; /* eInvalid */
    }
}

/* The protocol task name must be comma- and whitespace-free. FreeRTOS task
 * names may contain spaces, so copy into a safe, bounded buffer. */
static void trace_copy_name(char *dst, size_t dst_size, const char *src)
{
    size_t j = 0;
    for (size_t i = 0; src != NULL && src[i] != '\0' && (j + 1) < dst_size; i++)
    {
        char c = src[i];
        int safe = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                   (c >= '0' && c <= '9') || c == '_' || c == '-';
        dst[j++] = safe ? c : '_';
    }
    dst[j] = '\0';
}

/* Announce the device clock so the host can interpret ticks: TickRate gives the
 * ticks/second needed to convert to seconds, TickBits the counter width for
 * wraparound unwrapping. The host labels the timeline "Device ticks" until it
 * sees TickRate, so emitting this is what makes the axis read real seconds. */
void trace_emit_meta(void)
{
    char line[32];
    snprintf(line, sizeof line, "TickRate:%lu\r\n",
             (unsigned long) configTICK_RATE_HZ);
    trace_serial_write(line);
    snprintf(line, sizeof line, "TickBits:%d\r\n", TRACE_TICK_BITS);
    trace_serial_write(line);
}

/* Emit a snapshot of every task's current state. */
void trace_emit_snapshot(void)
{
    TaskStatus_t status[TRACE_MAX_TASKS];
    UBaseType_t count = uxTaskGetSystemState(status, TRACE_MAX_TASKS, NULL);
    TickType_t tick = xTaskGetTickCount();

    char name[configMAX_TASK_NAME_LEN + 1];
    char line[96];

    for (UBaseType_t i = 0; i < count; i++)
    {
        trace_copy_name(name, sizeof name, status[i].pcTaskName);
        snprintf(line, sizeof line, "Task:%s,State:%d,Tick:%lu\r\n",
                 name,
                 trace_state_code(status[i].eCurrentState),
                 (unsigned long) tick);
        trace_serial_write(line);
    }
}

/* Dedicated low-priority task that periodically dumps a snapshot. */
static void vTraceTask(void *arg)
{
    (void) arg;
    const TickType_t period = pdMS_TO_TICKS(TRACE_PERIOD_MS);
    TickType_t last = xTaskGetTickCount();
    unsigned snapshot = 0;

    for (;;)
    {
        /* Re-announce the clock metadata periodically (and on the first pass). */
        if ((snapshot % TRACE_META_EVERY) == 0)
        {
            trace_emit_meta();
        }
        trace_emit_snapshot();
        snapshot++;
        vTaskDelayUntil(&last, period);
    }
}

/* Call once after creating your other tasks, before/after vTaskStartScheduler()
 * per your platform's conventions. */
void trace_shim_start(void)
{
    xTaskCreate(vTraceTask, "Trace", configMINIMAL_STACK_SIZE * 2,
                NULL, tskIDLE_PRIORITY + 1, NULL);
}
