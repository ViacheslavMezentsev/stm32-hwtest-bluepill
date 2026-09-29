# CMSIS (подмножество) · [English](#english)

Минимальный набор файлов CMSIS для STM32F103 (medium density, `STM32F103xB`), взятый без
изменений из [STM32CubeF1](https://github.com/STMicroelectronics/STM32CubeF1) v1.8.7:

| Файл | Источник | Версия |
| --- | --- | --- |
| `Core/Include/core_cm3.h`, `cmsis_compiler.h`, `cmsis_gcc.h`, `cmsis_version.h` | Arm CMSIS-Core(M) | 5.0.8 |
| `Device/ST/STM32F1xx/Include/stm32f1xx.h`, `stm32f103xb.h`, `system_stm32f1xx.h` | ST CMSIS Device F1 | 4.3.5 |
| `Device/ST/STM32F1xx/Source/system_stm32f1xx.c` | ST CMSIS Device F1 (шаблон) | 4.3.5 |
| `Device/ST/STM32F1xx/Source/gcc/startup_stm32f103xb.s` | ST CMSIS Device F1 (GCC) | 4.3.5 |

`mpu_armv7.h` не нужен: у STM32F103 нет MPU (`__MPU_PRESENT = 0`). Скрипт компоновщика
свой (`ld/stm32f103.ld.in`, MIT): шаблон из STM32CubeF1 распространяется на условиях Ac6.

Лицензия: Apache-2.0 ([LICENSE-Apache-2.0.md](LICENSE-Apache-2.0.md)), заголовки файлов
сохранены. Файлы не форматируются стилем проекта (`cmsis/.clang-format`). Чтобы обновить
версию, замените файлы из нового выпуска STM32CubeF1 и исправьте таблицу.

## English

A minimal CMSIS file set for STM32F103 (medium density, `STM32F103xB`), copied unchanged
from STM32CubeF1 v1.8.7 (table above). `mpu_armv7.h` is not needed: STM32F103 has no MPU.
The linker script is the project's own (`ld/stm32f103.ld.in`, MIT) because the
STM32CubeF1 template is distributed under Ac6 terms. License: Apache-2.0, file headers are
kept. The files are excluded from the project code style (`cmsis/.clang-format`).
