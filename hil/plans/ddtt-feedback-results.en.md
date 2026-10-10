# DDTT development cycle results

Date: 2026-10-10. Module v0.4.0 (`9c3ff2d`), Windows/ST-Link/OpenOCD 0.12.0.

Requirement: release the ADC and internal sensors on the early POST failure path before loop.
Baseline `ADC_CR2 & (ADON | TSVREFE)` was `0x800001`; corrected firmware returns `0`.
The scenario substitutes a zero VREFINT sample after a real conversion, checks POST failure,
continued setup and released resources. This exercises a failure branch, not a physical ADC timeout.

Initial ERROR attempts are preserved: the watchpoint first trapped on initialization writing zero;
then ADC1 was unavailable in loop. The scenario now arms after initialization and resolves the
CMSIS address/mask in board.cpp. Target expectations were not weakened. After the confirmed FAIL,
the same algorithm and expectations passed with corrected firmware; only a style comment was added later.

F103CB/PB2: host 13/13; initial hardware regression 11 PASS + 1 ERROR in the existing VDDA injection.
Its watchpoint was also moved after initialization; repeated prepare and HW passed.
All 12 scenarios now have PASS evidence, with the original ERROR retained; BOOT/BLINK recovery 2/2 PASS.
No physical F103C8/PC13 verification. GCC 14.2.1, GDB 15.2.90.20241130-git/Python 3.12.8.
The retained `inferred_stop` warning means the module reconstructed watchpoint evidence from changed data.

| Build | Run ID | Verdict | Checks | ELF SHA-256 |
| --- | --- | --- | --- | --- |
| ddtt-baseline-f103cb | 20261010T113619.613385Z-HW_POST_ADC_CLEANUP-44872 | ERROR | 2 | `420be5e872fc9d3814999bf10e65cc39aeebbea70f97b60bb7f495f1b5dda889` |
| ddtt-baseline-f103cb | 20261010T113708.073555Z-HW_POST_ADC_CLEANUP-41328 | ERROR | 9 | `420be5e872fc9d3814999bf10e65cc39aeebbea70f97b60bb7f495f1b5dda889` |
| ddtt-baseline-f103cb | 20261010T113736.851468Z-HW_POST_ADC_CLEANUP-22732 | FAIL | 12 | `420be5e872fc9d3814999bf10e65cc39aeebbea70f97b60bb7f495f1b5dda889` |
| ddtt-candidate-f103cb | 20261010T113815.774749Z-HW_POST_ADC_CLEANUP-11424 | PASS | 12 | `45cd65c763701b0d236fde707cdde5973176731b90caaa7e29fd4016b8f691f0` |
| ddtt-candidate-f103cb | 20261010T113900.333368Z-HW_POST_ADC_CLEANUP-33188 | PASS | 12 | `45cd65c763701b0d236fde707cdde5973176731b90caaa7e29fd4016b8f691f0` |

Local evidence (not shipped in Git): `build/ddtt-feedback/` contains selection, export/index,
integrity.json, HTML report, hardware-summary.json and hashed baseline-inputs.
`build/ddtt-baseline-*` retains original ELF files and attempts; `build/ddtt-candidate-*` retains fixes.
Export, integrity verification and report generation have outcomes separate from scenario verdicts.
Boards are left with corrected firmware; reset_run is confirmed. This run does not establish
external electrical measurements or unattended operation of qwen/pi.

## Offline verification

Docker: Debug/Release/HIL for C8 and CB — 6 builds PASS, host 13/13 each; formatting PASS.
Renode/Windows: C8 and CB smoke tests 2/2 PASS (the model does not implement ADC).
The first Docker command bypassed its entrypoint and could not find cmake; the normal entrypoint passed.
All scenario style checks passed. Export/verify/report returned code 0, including retained FAIL/ERROR.
These checks use a hashed working snapshot, not GitHub CI; the owner performs push and land.
