# Portable DDTT report for GitHub Pages

[Русский](DDTT_PAGES.md)

`hil/tools/ddtt_pages.py` builds a local static package in `build/ddtt-pages`.
It does not publish anything, connect GitHub Apps or change repository settings.
Open index.html: full source, line numbers, file selection, mapped-line filter and a
side panel with assertions and source/scenario links pinned to a full SHA. Dark/light/auto themes.

Green means all mapped assertions are confirmed; red means at least one FAIL;
yellow means UNKNOWN without FAIL. Unmapped lines are uncolored. A condition may be green
for one selected expectation, not every branch: inspect the listed assertions.

## Public package

- index.html embeds verified source, CSS and JS without CDN dependencies;
- public-data.json contains allowlisted map fields, Boolean outcomes, UTC, SHA and links;
- lcov.info uses relative SF paths and Boolean DA values;
- coverage.xml carries the same lines in Cobertura format;
- .nojekyll prepares the static files for future hosting.

Raw result/records/run/config, stand files, UID/serials, server addresses, personal paths
and arbitrary actual/expected values are excluded. Tracked source and check names are
public content and must themselves be publishable. Full evidence stays local. This is
not a signed attestation and cannot defend against deliberate forgery of all local inputs.

UNKNOWN never becomes DA=0. A mixed CONFIRMED/UNKNOWN line without FAIL is excluded
from both numeric formats. Numbers describe selected reliable assertions, not all firmware.
The JSON summary retains unknown links.

## Binding the tested revision

Older results did not hash Python scenarios; do not retroactively claim that assurance.
`ddtt_provenance.py begin` snapshots inputs before a campaign; `seal` checks them afterwards
and records result hashes. Export checks source/scenario/map/config against the requested
Git SHA, result inventory/hashes, recalculated DDTT states and selected scenario definitions.
Only Git-blob comparisons normalize CRLF/LF; local evidence hashes remain exact.
Do not edit inputs during a campaign. Before/after snapshots cannot detect a temporary
edit that was reverted. Unrelated documentation changes do not invalidate the tested revision.
Use a separate build directory containing only the five output files. Unrelated files are
rejected; validation failure clears old highlighting and public data.

## Local workflow

Commit/agree the tested revision, build f103cb-hil and run the host preset first.
Use a new campaign directory. The [Russian guide](DDTT_PAGES.md#повторить-локально)
contains the complete PowerShell sequence; the steps are:

1. Save the full SHA with git rev-parse HEAD and create an empty campaign/runs.
2. Run `ddtt_provenance.py begin --revision SHA --runs RUNS --out CAMPAIGN_JSON`.
3. Copy the generated session.json, set its out to RUNS and run the scenarios against that session.
4. Run `ddtt_provenance.py seal --runs RUNS --out CAMPAIGN_JSON`.
5. Run `ddtt_export.py --runs RUNS`.
6. Run the command below; stop on preparation/sealing/export errors.

```powershell
python hil/tools/ddtt_pages.py --runs build/<campaign>/runs --provenance build/<campaign>/campaign.json --revision <full-SHA> --repository ViacheslavMezentsev/stm32-hwtest-bluepill
```

After regular export, VS Code task **HIL: DDTT portable report (no publish)** asks for
RUNS, campaign.json and its full SHA. Future publication must upload only build/ddtt-pages,
not ddtt-view or the full build directory. HTML works as a standalone file; JSON/LCOV/XML
download links require the other files beside it.

## GitHub and Renode/GDB

GitHub does not discover LCOV files automatically. Built-in Code Quality requires a separate
Cobertura upload action; its docs describe PR percentages and per-file deltas, not green
markers in the normal blob view. Team/Enterprise Cloud are listed:
[setup](https://docs.github.com/en/code-security/how-tos/maintain-quality-code/set-up-code-coverage),
[display reference](https://docs.github.com/en/enterprise-cloud@latest/code-security/reference/code-quality/code-coverage).
[Checks annotations](https://docs.github.com/en/rest/checks/runs) can attach messages to lines,
but are not a map of green lines. Our full source view can be hosted on
[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

Renode/GDB CI can produce LCOV/Cobertura with DDTT semantics. Choose expectations supported
by the model, capture evidence, label it emulator and do not merge it with hardware implicitly.
The current generator accepts hardware campaigns; emulator support and GitHub upload are not
implemented. A Renode smoke PASS alone is not a map. A first small example could check main,
setup/loop ordering and the UART banner; ADC/DMA remain separate hardware evidence.

Validated locally on 2026-10-15: fresh WeAct campaign 28/28 PASS; 94 confirmed links across 72 lines, pinned to 9650ec50120c1e61b778a5f1ef113c45cbaf6d12. Thirteen host tests passed, including privacy, stale inputs, HTML escaping, source navigation and theme. Public package privacy scan and LCOV/Cobertura line agreement passed. GitHub upload/Pages deployment and native GitHub rendering have not been tested or enabled.
