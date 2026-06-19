/*
 * freeRTOS-visualizer trace shim — public API.
 * See trace_shim.c for details and FreeRTOSConfig.h requirements.
 */
#ifndef FREERTOS_VISUALIZER_TRACE_SHIM_H
#define FREERTOS_VISUALIZER_TRACE_SHIM_H

#ifdef __cplusplus
extern "C" {
#endif

/* Implement this for your board: write one newline-terminated line to the same
 * serial transport the host visualizer reads. Must be callable from a task. */
extern void trace_serial_write(const char *line);

/* Emit one snapshot (one line per task) immediately. */
void trace_emit_snapshot(void);

/* Create the periodic trace task (emits a snapshot every TRACE_PERIOD_MS). */
void trace_shim_start(void);

#ifdef __cplusplus
}
#endif

#endif /* FREERTOS_VISUALIZER_TRACE_SHIM_H */
