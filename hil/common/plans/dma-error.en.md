# DMA error validation

WeAct F103CB/PB2, local OpenOCD/ST-Link. No firmware changes or hooks.
Start with one real accepted block. Stop in the next real DMA IRQ after reading ISR and stopping DMA;
replace local status with TEIF1 or TEIF1|TCIF1. Never write ISR or invalid DMA addresses.
Expect one error, no new ready/accepted/TC count, stopped ADC/DMA, cleared flags and fault state.
Next two real blocks must restore normal with exactly one acceptance and IRQ each.
Finally reset/reach(loop) checks cleanup. Three scenario corrections maximum; one environment diagnosis.
Stop on USB/identity/recovery errors. Preserve all attempts under build/ddtt-dma-error-*.
First run may PASS: no known firmware defect and no artificial red mutation.
Run prepare/traceability before hardware, full hardware regression and fresh DDTT export afterwards.
Limits: injected software status, not a physical DMA bus fault or a partial hardware transfer.

Validated on 2026-10-15: WeAct F103CB/OpenOCD, 25/25 hardware PASS with saved captures; F103CB host preparation 26/26 PASS. Four DDTT exporter/report unit tests passed. Fresh map: 82 CONFIRMED links across 68 lines, no FAILED/UNKNOWN. The firmware needed no correction. Other hardware profiles were not tested in this stage.
