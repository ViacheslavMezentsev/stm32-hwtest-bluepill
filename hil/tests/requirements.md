# Требования HIL stm32-hwtest-bluepill

Требования общие для обеих плат; плата выбирается сборкой (пресеты HIL_F103C8 и
HIL_F103CB) и описанием MCU в hil/profiles/<BOARD>.toml.

## HW_BOOT
После сброса прошивка доходит до main(). DEV_ID кристалла — 0x410 (STM32F103 medium
density; проверка описания MCU при политике strict). Ядро работает от HSI 8 МГц:
источник SYSCLK — HSI, SystemCoreClock = 8 000 000.

## HW_BOOT_CMSIS
То же, что HW_BOOT, в терминах CMSIS: при входе в board::init() HSI готов (RCC_CR_HSIRDY),
PLL выключен (RCC_CR_PLLON), источник SYSCLK — RCC_CFGR_SWS_HSI, DEV_ID
(DBGMCU->IDCODE & DBGMCU_IDCODE_DEV_ID) равен 0x410, размер Flash по FLASHSIZE_BASE — 64 или
128 КиБ, SystemCoreClock = 8 000 000. Макросы CMSIS доступны в отладочной информации ELF
(контракт cmsis_boot_macros).

## HW_SETUP_DONE
setup() завершается и управление доходит до loop(): g_app.setup_done = 1, SysTick
включён с периодом 1 мс при 8 МГц (RELOAD = 7999).

## HW_POST
POST в setup() измерил VREFINT и датчик температуры: g_post.status = PostOk (1),
VDDA от 2900 до 3600 мВ, температура кристалла от −10 до +85 °C.

## HW_BLINK
loop() переключает светодиод пользователя: между двумя вызовами board::ledToggle()
состояние вывода меняется, а счётчик g_app.blink_count растёт на 1.
