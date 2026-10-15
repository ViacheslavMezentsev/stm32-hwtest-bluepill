# Measurement indication: DDTT plan

WeAct BluePill-Plus F103CB/PB2, local OpenOCD/ST-Link, internal ADC channels and onboard LED only.
Pending: LED off. Normal: 500 ms half-period blink. Invalid block, filtered values outside
limits, timeout or DMA TE: steady on. Each valid result re-evaluates health; error counters remain history.

Run HW_INDICATOR_INVALID on the original ELF first: expect the fault indication assertion to FAIL.
Inject only at monitor::process with DMA stopped; snapshot and verify the 32-byte buffer,
restore it immediately after processing; finally reset/reach(loop) removes injected state.
Repeat unchanged, test range fault/recovery and the entire hardware suite.
Host: processing/error vectors. Renode without ADC/DMA must indicate fault, not healthy blinking.
Injections do not prove physical failures or free-running timing.

Keep immutable attempts in build/ddtt-led-*; bind the map to the new ELF SHA.
Budget: three code/scenario fixes and one environment diagnostic retry. Stop on identity/USB/recovery failures.
Leave the new firmware running normally. No mass erase or option bytes.
