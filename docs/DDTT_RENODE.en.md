# DDTT with Renode/GDB and GitHub Pages

[Русский](DDTT_RENODE.md). This route never accesses boards. It has a separate map,
`hil/ddtt-renode.template.json`, and scenario, `tools/renode_gdb_checks.py`.

## Interpretation

Ten links on seven lines in main.cpp/app.cpp cover main entry, the initial setup_done,
setup → board::init → uart::init → post::run → loop order, setup completion, the expected
PostAdcTimeout and board UART banner. These assertions describe this model, not electrical
behavior or complete function coverage.

Renode 1.17 models the CPU, memory, SysTick and USART1. ADC is a RAM stub; DMA is not modeled.
Thus `POST: ... FAIL` in UART is expected; `model ADC timeout` asserts exactly that limited
outcome. Do not merge emulator evidence with hardware evidence implicitly.

The runner builds a new F103CB Debug ELF in a unique build directory, starts its own Renode,
connects Python-enabled GDB, stops at functions and reads state. It closes its processes.
Build inputs, model, scenario, map and renderer are compared with a full Git SHA before and
after the run. Commit these inputs first; unrelated documentation and .clang-format changes
are allowed. Add new sources to Git first. Do not edit inputs during a run. Before/after
snapshots are not a cryptographic attestation.

## Local use

```powershell
python tools/renode_ddtt.py --revision (git rev-parse HEAD) --gdb "$HOME/xpack-arm-none-eabi-gcc-14.2.1-1.1/bin/arm-none-eabi-gdb-py3.exe" --annotations
```

Renode lookup: RENODE_BINARY, PATH, Windows default, or explicit --renode. CMake uses
ARM_TOOLCHAIN_ROOT or its normal toolchain lookup. Limits: configure/build 120 s each,
Renode readiness 30 s, GDB 60 s, remote response 10 s. This is an automated smoke test,
not an interactive debugging session.

Open build/ddtt-renode-pages/index.html, select a source and click a colored line for
assertions and source/scenario links at the exact SHA. GitHub links work after that SHA
is pushed. Dark/light/auto themes are available. Copy the five public files, not build.
LCOV/Cobertura use relative paths and boolean marks. UNKNOWN is omitted from numeric
coverage; ERROR makes the entire incomplete attempt UNKNOWN. Explicit FAIL yields zero/red.
Raw results/logs remain separately in build/renode-ddtt-*; later attempts do not overwrite them.

## CI and annotations

Normal CI runs this in build (f103cb-debug). Actions shows a summary and the
**ddtt-renode-pages** artifact: download, extract and open index.html.
**ddtt-renode-diagnostics** is a separate diagnostic artifact, never a Pages input.

Notice = confirmed, error = false assertion, warning = unknown. File/line annotations appear
in Checks/Actions for the tested revision; they are not persistent green gutters in the
repository source browser. The HTML provides full interactive coloring. These are standard
[workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands).
An annotation does not replace the exit code: FAIL/ERROR also return a nonzero runner status.

## Viewing Pages later

Push does not deploy. The workflow is prepared only; the agent does not change GitHub
settings or publish anything.

1. After CI and land, set **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Open **Actions → CI → Run workflow**, select **main**, check **publish_pages**.
3. This run rebuilds and tests the firmware. The pages job requires successful format and
   all build jobs, then deploys only the portable emulator package.
4. Open the **github-pages** environment URL in the pages job or **Visit site** in Settings.
   The default URL is `https://ViacheslavMezentsev.github.io/stm32-hwtest-bluepill/`.
5. Select a source and click a line. Repeat the manual main run to update the site.

There is no site before the first successful deployment. Regular CI updates the artifact,
not the site; check the SHA in the Pages header. Deployment replaces the repository's
previous site entirely, rather than adding a section to a hardware site. If Pages already
hosts other content, agree on the site structure first. This workflow does not publish
hardware evidence. See [custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Local validation

2026-10-16: actual Renode/GDB runs with fresh builds passed on Windows and Linux
in a Docker volume: 10/10 assertions, 7 lines. Tested input revision:
`e6c4227e81df33717f6975b5cdc3ecc8eef9542f`. Host regressions: 19/19, including
UNKNOWN/FAIL, annotations, unchanged hardware export, package privacy and matching
LCOV/Cobertura. Original unsuccessful attempts remain locally available.
GitHub CI for the final branch and Pages deployment still require owner validation.
