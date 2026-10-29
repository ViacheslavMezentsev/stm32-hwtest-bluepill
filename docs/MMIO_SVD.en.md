# MMIO/SVD in HIL

[Русский](MMIO_SVD.md)

This consumer pins stm32-gdbtest v0.6.1 (API_VERSION=3).
Neither the module core nor firmware changes here. All 28 scenarios remain ordinary
def functions: synchronous navigation is compatible and requires no await.

## Description scope

Both hil/F103C8/session.toml and hil/F103CB/session.toml select
../common/stm32f103-test.svd, relative to the session file. This is an authored
**test subset** of 35 registers, not a complete vendor SVD. Addresses and sizes are
compared against STM32CubeF1 v1.8.7 CMSIS in the current ELF; access rights and effects
follow RM0008 and PM0056. FACTORY.FLASH_SIZE is a project name for the 16-bit
Flash-size value; its width is checked separately because CMSIS only defines its address.

| Area | Use |
| --- | --- |
| RCC, GPIOA/B/C | Clock configuration, KEY and LED pin |
| SysTick | CTRL and LOAD |
| USART1 | SR, BRR, CR1; no DR reads |
| ADC1 | CR1/CR2, SMPR1, SQR1/SQR3; DR has an effect descriptor but scenarios do not read it |
| DMA1 / DMA1_Channel1 | ISR and channel configuration; WO/W1C IFCR for refusal tests |
| DBGMCU, FACTORY | Identity and Flash size |

The description does not qualify the board or model all register dependencies.
USART SR is conservatively read-only in this subset: scenarios do not clear flags
by writing, although the hardware register supports specific writes.

## Access and effects

- Use t.mmio.read("GPIOB.ODR") for registers. Evaluate CMSIS masks separately,
  without dereferencing peripherals. Use scalar check for Python values;
  tables remain for RAM and ordinary expressions.
- SysTick CTRL requires allow_effects=True because reads clear COUNTFLAG.
  HW_SETUP_DONE checks all three bits from one CTRL snapshot.
- USART SR explicitly permits initiating the SR→DR clearing sequence. The scenario
  does not read DR; subsequent firmware access is outside this guarantee.
- ADC CR2 requires consent to command effects. HW_DMA_TIMEOUT separates read
  and write and writes a previously computed integer. Its finally reads current
  CR2 and restores only DMA; an unchanged value is not written again.
  This is a project-specific operation at a known stop, **not generic safe RMW**.
- MMIO write acknowledges transport completion, with no hidden before/after read.
  Ambiguous replies are not retried automatically. Peripherals may run while the
  core is halted; stop selection and restoration remain scenario responsibilities.
- RAM (g_monitor, g_post), arguments, the DMA ISR local status copy and CPU
  registers retain read/write/memory/ret. &ADC1->DR computes an address only.
  The refused memory(USART1_DR, 4) remains a negative memory-window check.

Expert exception: monitor::process(&g_monitor.raw[0], count) still uses Python GDB
directly on its main thread, in a synchronous scenario with RAM snapshot/restore.
Public call() does not accept this namespace/pointer expression. Do not carry this
escape hatch into an async scenario; it is outside the MMIO contract.

## Offline checks

From the project root, repeat for f103c8-hil and f103cb-hil:

    cmake --preset f103cb-hil
    cmake --build --preset f103cb-hil
    ctest --preset f103cb-hil-host --output-on-failure
    python -m unittest discover -s hil/tools -p "test_*.py"
    python modules/stm32-gdbtest/stm32_gdbtest/cli.py inspect --session build/f103cb-hil/hwtest/session.json

Host suite: 28 prepare, traceability, MMIO regressions and SVD/ELF comparison
(31 CTest tests). host.svd_elf opens only the ELF in GDB, without target remote.
Linux uses the same commands with ARM_TOOLCHAIN_ROOT pointing to its toolchain.
CI also checks scenario style. pack captures SVD with configuration, so the source
SVD is not needed at the execution site. POST/DMA source-line lookup still needs
project sources: this is a checkout workflow, not a promise that every scenario
runs autonomously from ZIP.

DDTT scenario/check names are preserved. Old hardware results do not accept migrated
scenarios: a new campaign on an agreed board/revision is required before export.
Offline PASS does not validate GPIO/DMA on physical STM32 hardware.

SVD is part of DDTT campaign inputs: changing it after the campaign blocks portable
export even if firmware and check names are unchanged.

## Offline migration results

Checked on 2026-10-19 with module cb03e86616417a7f0f24202137fe751624cf043e:

| Route | Result |
| --- | --- |
| Windows, F103C8 and F103CB | Builds PASS; 31/31 CTest each |
| Linux Docker volume, GCC 14.2.1-1.1 | Builds PASS; 31/31 CTest each |
| Consumer Python regressions | Windows 34/34; Linux 32 PASS, 2 SKIP (Node.js absent for interactive HTML; covered on Windows) |
| SVD ↔ ELF | 35 registers, both profiles and operating systems |
| inspect from another cwd | VALID, 0 ERROR; expected WARN: no stand selected |
| pack relocated to a temporary directory | SVD SHA-256 preserved, 35 registers available from the capsule |
| DDTT map | 94 check labels preserved; no new hardware evidence |

This completes the consumer's offline migration portion of P5. Negative Renode models
and fresh hardware acceptance remain separate release-matrix rows; neither ran here.
