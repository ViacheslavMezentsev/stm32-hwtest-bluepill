# DMA error: TE and TE+TC

[Русский](DMA_ERROR.md) · [ADC/DMA](ADC_DMA.en.md)

`HW_DMA_ERROR` and `HW_DMA_ERROR_TC` in
[test_dma_error.py](../hil/common/tests/board/test_dma_error.py) check the handler
on WeAct F103CB using OpenOCD/ST-Link. Firmware and stm32-gdbtest core are unchanged.

After one real accepted block, the scenario stops in the next real DMA IRQ after reading
ISR and stopping transfer. It checks breakpoint identity, frame, exception, original TC,
stopped ADC/DMA and ready=0. Local `status` is replaced with TEIF1 or TEIF1|TCIF1 and read
back. Read-only ISR is not written; invalid DMA addresses are not used. The source anchor
is resolved rather than hardcoding a line number.

Before the next arm: dma_errors=1, ready=0, accepted=1, irq_count=1, normal=0,
MeasurementFault, stopped ADC/DMA, cleared channel flags and timeouts=0 are required.
Even simultaneous TC must not publish the erroneous block. Two subsequent real transfers
produce accepted/irq_count=2 and 3, restore normal and retain the single dma_errors event.
Finally, reset reaches loop and verifies monitor-state cleanup.

This tests decisions based on a status snapshot, not physical TE generation, stopping a
partially completed transfer or an IRQ/timeout race. Original hardware status contains TC;
this experiment does not generate the hardware TE flag.

The first attempt failed before injection: the pinned reach(file:line) checks the frame
against a function name. It was replaced by breakpoint/resume with explicit breakpoint
and frame checks. The original result is retained; this was a scenario error, not a DMA defect.

The map adds four links per case: TE priority, error count, fault publication and recovered
block acceptance. Missing ready publication and other assertions remain visible in the
detailed report even without their own highlighted line.

Repeat using the regular runner with `--test HW_DMA_ERROR` / `--test HW_DMA_ERROR_TC`,
or select these scenarios in the VS Code task. After a fresh campaign:

```powershell
python hil/tools/ddtt_export.py --runs build/<campaign>/runs
```

Validated on 2026-10-15: WeAct F103CB/OpenOCD, 25/25 hardware PASS with saved captures; F103CB host preparation 26/26 PASS. Four DDTT exporter/report unit tests passed. Fresh map: 82 CONFIRMED links across 68 lines, no FAILED/UNKNOWN. The firmware needed no correction. Other hardware profiles were not tested in this stage.
