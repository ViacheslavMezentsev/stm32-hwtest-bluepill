# Startup DDTT — plan

WeAct BluePill-Plus F103CB_PB2, PB2 active high, local OpenOCD/ST-Link. Normal image loading
and execution are authorized; no mass erase, option bytes or external loads. Firmware unchanged.
Observe HW_STARTUP_ORDER, HW_SYSTICK_PROGRESS and HW_ADC_INITIALIZATION (requirements.md).
Before hardware: syntax/style/traceability/prepare and both builds. Run the three new cases,
then all 15 on CB. Preserve every attempt. Up to three scenario corrections; stop on identity
or USB failure. No injections or repeated init calls: use reach/frames/read/record on normal boot.
Record evidence before checks; evaluate CMSIS in its compilation unit. Final image stays the
original demo; no injected state needs restoration. Map exact assertion names to reviewed source
anchors, bind source/ELF hashes after building. Green means confirmed expectation, not execution
trace. Missing evidence is unknown. Debugger stops do not measure real-time timing.
