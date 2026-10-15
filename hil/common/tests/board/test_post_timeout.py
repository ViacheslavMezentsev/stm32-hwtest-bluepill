"""
RU: Таймауты RSTCAL/CAL/EOC: граница 10/11 мс, общий отказ и очистка ADC.
EN: RSTCAL/CAL/EOC timeouts: 10/11 ms boundary, failure propagation and ADC cleanup.
"""
from pathlib import Path
import re
import gdb
from stm32_gdbtest import case


# Находим однозначную строку в текущем исходнике, без постоянных адресов Flash.
def source_line(anchor):
    lines = (Path(__file__).resolve().parents[4] / "src/post.cpp").read_text(encoding="utf-8").splitlines()
    found = [i + 1 for i, line in enumerate(lines) if line.strip() == anchor]
    if len(found) != 1:
        raise RuntimeError("POST source anchor changed")
    return f"post.cpp:{found[0]}"


# Узкий контракт машинного кода: два чтения, TST и условный выход из ожидания.
def wait_point(anchor, mask, offset, exit_branch):
    _, locations = gdb.decode_line(source_line(anchor))
    pcs = {int(location.pc) for location in locations}
    if len(pcs) != 1:
        raise RuntimeError("POST wait has ambiguous DWARF address")
    instructions = gdb.selected_frame().architecture().disassemble(pcs.pop(), count=4)
    asm = [item["asm"].split(";")[0].split("@")[0].strip() for item in instructions]
    match = re.fullmatch(r"tst(?:\.w)?\s+(r[0-9]+),\s*#([0-9]+)", asm[2])
    if not match or int(match[2]) != mask:
        raise RuntimeError(f"POST TST contract changed: {asm}")
    register = match[1]
    if not re.fullmatch(rf"ldr\s+{register},\s*\[pc,\s*#[0-9]+\]", asm[0]):
        raise RuntimeError(f"POST pointer load changed: {asm}")
    if not re.fullmatch(rf"ldr\s+{register},\s*\[{register},\s*#{offset}\]", asm[1]):
        raise RuntimeError(f"POST MMIO load changed: {asm}")
    if not asm[3].startswith(exit_branch + "."):
        raise RuntimeError(f"POST branch changed: {asm}")
    return instructions[2]["addr"], register, asm


# resume проверяет именно нашу точку; reach(file:line) в закреплённом API не используется.
def resume_at(t, point):
    stop = t.resume()["stop"]
    t.check("POST expected breakpoint", point.number in stop.get("breakpoints", []))


# Подменяем прочитанное значение CPU, не записываем аппаратные CAL/RSTCAL/EOC.
def timeout(t, kind, anchor, mask_name, offset, exit_branch, busy):
    point = None
    cleanup = None
    try:
        t.reach("post::run")
        mask = t.evaluate(mask_name)
        adc = t.evaluate("(unsigned int)&ADC1->CR2")
        enables = t.evaluate("ADC_CR2_ADON | ADC_CR2_TSVREFE")
        address, register, asm = wait_point(anchor, mask, offset, exit_branch)
        t.record("post.timeout.preflight", {"kind": kind, "address": address, "register": register, "asm": asm})
        point = t.breakpoint(f"*{address}")
        resume_at(t, point)
        start = t.evaluate("start")

        # 10 мс ещё допустимы; следующий приход к той же проверке доказывает продолжение цикла.
        for elapsed in (10, 11):
            t.check("POST wait frame", "convert" in gdb.newest_frame().name() if kind == "EOC"
                    else "adcInit" in gdb.newest_frame().name())
            value = t.evaluate(f"${register}")
            injected = value | mask if busy else value & ~mask
            t.write(f"${register}", injected)
            t.check("POST status readback", t.evaluate(f"${register}"), injected)
            t.reach("board::millis")
            t.ret((start + elapsed) & 0xffffffff)
            t.record("post.timeout.clock", {"kind": kind, "elapsed": elapsed, "start": start})
            if elapsed == 10:
                resume_at(t, point)
                t.check("10 ms still waiting", t.evaluate("start"), start)
        point.remove()
        point = None
        cleanup = t.breakpoint(source_line("ADC1->CR2     &= ~( ADC_CR2_ADON | ADC_CR2_TSVREFE );"))
        resume_at(t, cleanup)
        t.check("timeout propagated to POST", gdb.newest_frame().name(), "post::run")
        t.check("timed function returned false", t.evaluate("$r0"), 0)
        cleanup.remove()
        cleanup = None
        t.reach("loop")
        cr2 = t.evaluate(f"*(unsigned int *){adc}")
        t.record("post.timeout.result", {"kind": kind, "status": t.read("g_post.status"), "cr2": cr2})

        # Отказ не выдаёт ложных измерений и не блокирует запуск приложения.
        t.check([
            ("POST timeout status", "g_post.status", "PostAdcTimeout"),
            ("POST timeout permits setup", "g_app.setup_done", 1),
            ("timeout publishes no reference", "g_post.vrefint_raw", 0),
            ("timeout publishes no temperature", "g_post.temp_raw", 0)
        ])
        t.check("timeout releases ADC sensors", cr2 & enables, 0)
    finally:
        if point is not None:
            point.remove()
        if cleanup is not None:
            cleanup.remove()
        t.reset()
        t.reach("loop")
        t.check("POST recovers after injection", t.read("g_post.status"), t.evaluate("PostOk"))


# Незавершённый сброс калибровки.
@case("HW_POST_RSTCAL_TIMEOUT", timeout_s=25, labels=("post", "adc", "injection"))
def rstcal(t):
    timeout(t, "RSTCAL", "while ( ( ADC1->CR2 & ADC_CR2_RSTCAL ) != 0 )", "ADC_CR2_RSTCAL", 8, "beq", True)


# Незавершённая калибровка после штатного RSTCAL.
@case("HW_POST_CAL_TIMEOUT", timeout_s=25, labels=("post", "adc", "injection"))
def calibration(t):
    timeout(t, "CAL", "while ( ( ADC1->CR2 & ADC_CR2_CAL ) != 0 )", "ADC_CR2_CAL", 8, "beq", True)


# Первый VREFINT не завершён; результат не должен публиковаться.
@case("HW_POST_EOC_TIMEOUT", timeout_s=25, labels=("post", "adc", "injection"))
def conversion(t):
    timeout(t, "EOC", "while ( ( ADC1->SR & ADC_SR_EOC ) == 0 )", "ADC_SR_EOC", 0, "bne", False)
