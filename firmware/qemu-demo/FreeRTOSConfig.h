/*
 * FreeRTOSConfig.h for the QEMU mps2-an385 (Cortex-M3) trace-shim demo.
 * The only line the shim strictly needs is configUSE_TRACE_FACILITY = 1
 * (required by uxTaskGetSystemState); the rest is a conventional CM3 setup.
 */
#ifndef FREERTOS_CONFIG_H
#define FREERTOS_CONFIG_H

#define configUSE_PREEMPTION                    1
#define configUSE_IDLE_HOOK                     0
#define configUSE_TICK_HOOK                     0
#define configCPU_CLOCK_HZ                      ( 25000000UL )
#define configTICK_RATE_HZ                      ( 1000 )
#define configMAX_PRIORITIES                    ( 5 )
/* The trace shim builds a TRACE_MAX_TASKS-entry TaskStatus_t array plus a line
 * buffer on its task stack (configMINIMAL_STACK_SIZE * 2). Size the minimal
 * stack so that has comfortable headroom. */
#define configMINIMAL_STACK_SIZE               ( 256 )
#define configTOTAL_HEAP_SIZE                  ( ( size_t ) ( 60 * 1024 ) )
#define configMAX_TASK_NAME_LEN                 ( 16 )
#define configUSE_16_BIT_TICKS                  0
#define configIDLE_SHOULD_YIELD                 1
#define configUSE_MUTEXES                       1
#define configUSE_RECURSIVE_MUTEXES             0
#define configUSE_COUNTING_SEMAPHORES           1
#define configQUEUE_REGISTRY_SIZE               0
#define configUSE_TASK_NOTIFICATIONS            1

/* Required by the trace shim's uxTaskGetSystemState(). */
#define configUSE_TRACE_FACILITY                1
#define configUSE_STATS_FORMATTING_FUNCTIONS    0

/* Memory allocation. */
#define configSUPPORT_STATIC_ALLOCATION         0
#define configSUPPORT_DYNAMIC_ALLOCATION        1

/* Hook / check functions. Stack-overflow checking is on so an undersized trace
 * task stack fails loudly (see vApplicationStackOverflowHook in main.c) instead
 * of silently corrupting memory. */
#define configCHECK_FOR_STACK_OVERFLOW          2
#define configUSE_MALLOC_FAILED_HOOK            0

/* Co-routines: off. */
#define configUSE_CO_ROUTINES                   0
#define configMAX_CO_ROUTINE_PRIORITIES         1

/* Software timers: off (not needed by the demo). */
#define configUSE_TIMERS                        0

/* Optional API functions. */
#define INCLUDE_vTaskPrioritySet                1
#define INCLUDE_uxTaskPriorityGet               1
#define INCLUDE_vTaskDelete                     1
#define INCLUDE_vTaskSuspend                    1
#define INCLUDE_vTaskDelayUntil                 1
#define INCLUDE_vTaskDelay                      1
#define INCLUDE_xTaskGetSchedulerState          1
#define INCLUDE_uxTaskGetStackHighWaterMark     1

/* Cortex-M3 interrupt priority configuration (mps2-an385 = 3 priority bits). */
#define configPRIO_BITS                         3
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY        0x7
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY   0x5

#define configKERNEL_INTERRUPT_PRIORITY \
    ( configLIBRARY_LOWEST_INTERRUPT_PRIORITY << (8 - configPRIO_BITS) )
#define configMAX_SYSCALL_INTERRUPT_PRIORITY \
    ( configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << (8 - configPRIO_BITS) )

/* The vector table (startup.c) references the FreeRTOS port handler names
 * (vPortSVCHandler / xPortPendSVHandler / xPortSysTickHandler) directly, so no
 * CMSIS-style handler-name remap is required here. */

#define configASSERT( x ) if( ( x ) == 0 ) { taskDISABLE_INTERRUPTS(); for( ;; ); }

#endif /* FREERTOS_CONFIG_H */
