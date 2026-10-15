# ADC/DMA and processing — plan

WeAct F103CB_PB2, local OpenOCD/ST-Link. Normal image programming/execution authorized;
no option bytes, mass erase or external loads. Final image is the new demo. Keep POST/blinking.
At loop end, every 100 ms acquire 8 VREFINT(17)/temperature(16) pairs via ADC1/DMA1 Channel1,
normal halfword mode. ISR stops ADC/DMA before publishing readiness; CPU only reads a finished
block. 10 ms timeout and TE stop acquisition and count separately. No circular DMA.
Average 8 pairs, convert using F103 typical constants, scalar filters Q=1,R=4,Pinitial=1;
first measurement seeds the filter. Reject bad length, zero VREFINT or values >4095 before
filter changes. Normal range: 2900..3600 mV, -10..85 C. LED keeps its existing blink behaviour.

Build/prepare both profiles; host vectors for pure processing; hardware IRQ/buffer and three
normal blocks; deterministic GDB calls before DMA starts with full DWARF-sized RAM snapshot
restored in finally. Model a missing request by disabling ADC DMA requests after arm, then
observe normal timeout/retry; do not claim physical DMA failure. Three corrections per hypothesis;
stop on identity/USB/recovery error. Preserve attempts. The old ELF has no monitor, so no original
firmware FAIL is claimed. A deliberately wrong expectation tests FAIL reporting, not a firmware bug.
Map explicit checks with source/ELF hashes; HTML lists selected campaign attempts, LCOV stays Boolean.
Run the full regression suite afterwards.
