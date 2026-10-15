# WeAct button and current DDTT highlighting

[Русский](BUTTON.md) · [Environment](DEVELOPER_ENVIRONMENT.en.md)

## Behavior

On WeAct BluePill-Plus V1.1, KEY (SW2) connects through R4 330 ohms to PA0 and
supplies 3.3 V when pressed: active high. There is no external pull-down;
firmware enables the internal pull-down. See the [official schematic](https://github.com/WeActStudio/BluePill-Plus/blob/master/HDK/BluePillPlus_V11_SchDoc.pdf).
Earlier floating-input measurements did not establish polarity.

After a stable 30 ms press, PB2 LED stays on regardless of measurement state.
Holding does not repeat the event and blinking cannot turn the LED off.
After a stable 30 ms release, measurement indication returns:
pending means off, normal means blinking, fault means steady on.
F103C8 declares no user KEY; both button scenarios return SKIP.

For a manual check, set a breakpoint on `++presses` in [button.cpp](../src/button.cpp):
it stops once per accepted press. Inspect `g_button.candidate`, `stable`, `changed_ms`
and `presses`. GDB stops affect timing; this does not measure physical contact bounce.

## Validation on 2026-10-15

- Native C++ checks the 29/30 ms boundary, bounce, hold, release, second press and timer wrap.
- `HW_BUTTON_CONFIG` checks GPIO and the actual released input before injection.
- `HW_BUTTON_VIRTUAL` replaces the return of `board::buttonPressed()` using `ret`,
  sets the time argument of `ButtonState::update`, and checks LED and event count.
  It does not write IDR. `finally` resets firmware and checks injection cleanup.
- WeAct F103CB, OpenOCD/ST-Link: **23/23 PASS**, capture SAVED. Both profiles:
  **24/24 host PASS**; Renode smoke PASS. F103CB Debug/HIL/Release and F103C8 HIL builds passed.
- Map: **74 CONFIRMED across 65 lines**, no FAILED/UNKNOWN. These are selected
  assertion-to-code links, not a percentage of the entire firmware. C8 hardware was not tested.

Scenarios: [test_button.py](../hil/common/tests/board/test_button.py).
Plan: [button.en.md](../hil/common/plans/button.en.md). Presses are virtual;
the developer separately checks physical presses with the new configuration.

## Refreshing highlighting

Source changes require rebuilding and a fresh hardware campaign.
Then use VS Code → Run Task → **HIL: DDTT report (F103CB)** and select the campaign's
`runs` directory. Equivalent command from the project root:

```powershell
python hil/tools/ddtt_export.py --runs build/<campaign>/runs
```

The command rebinds the map, exports LCOV and creates HTML. Old highlighting is
cleared before generation. Comment-only `//`, `/* ... */` and blank lines are rejected;
code with a trailing comment is allowed. Checks cover unique anchors, matching lines
and source SHA-256 when reading evidence. A comment check alone would miss a shift
to another code line, hence both checks are necessary. This is a lightweight lexical
check, not C++ executable-statement analysis.

Report: `build/ddtt-view/index.html`; highlighting: `build/ddtt-view/lcov.info`.
Checks run during export, not on every IDE edit. After editing, use Coverage Gutters:
Remove Coverage; after exporting, enable Watch/Display Coverage. Preserve old logs
but do not present them as a new run. Use this project wrapper instead of calling
the submodule exporter directly: the additional comment checks belong to this project.
