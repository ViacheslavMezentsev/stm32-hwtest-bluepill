# KEY and DDTT map integrity

WeAct F103CB/PB2, OpenOCD/ST-Link. V1.1 SW2 connects PA0 through 330 ohms to 3.3 V: use pull-down.
Earlier floating-input measurements did not establish polarity; PB5 was rejected. Owner identified
this board by doubled blinking. Stable hold forces LED on; release restores measurement indication.
Debounce both edges for 30 ms, count once per press. Native vectors: boundaries, bounce, hold,
release/repress and wrap. MCU: GPIO config, ret-injected buttonPressed and update timestamp vectors.
Finally reset/reach(loop) clears injection state. Not a physical debounce timing measurement.
No original hardware FAIL exists for the previously absent handler; Missing symbol is not one.
Full hardware regression and fresh single-ELF map. Clear stale LCOV before export; reject blank,
comment-only and ambiguous anchors; test rejection on host. Keep all attempts in build/ddtt-button-*.
No module core changes, mass erase or option bytes. Three fixes/one diagnostic retry maximum;
stop for USB, identity or recovery errors.

Result: 23/23 WeAct hardware PASS; both host profiles 24/24; native vectors and Renode PASS. Fresh map: 74 confirmed links / 65 lines. Comment and stale-source controls passed. Physical press confirmation remains manual.
