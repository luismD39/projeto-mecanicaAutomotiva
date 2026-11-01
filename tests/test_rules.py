import pytest

from app.services import rules
from app.services.sensor_status import annotate
from app.services.simulator import SENSORS, EcuSimulator

NORMAL = {
    "rpm": 800, "coolant_temperature": 90, "vehicle_speed": 0, "engine_load": 20, "throttle_position": 0,
    "maf": 2.6, "battery_voltage": 14.1, "short_term_fuel_trim": 0.5, "long_term_fuel_trim": 1.5,
}


def snapshot(dtcs=(), fan=False, **values):
    """Monta uma leitura sob medida para testar uma regra isoladamente."""
    merged = {**NORMAL, **values}
    sensors = {
        key: {"label": label, "unit": unit, "value": merged[key],
              "validity": "invalid" if merged[key] is None else "valid"}
        for key, (label, unit) in SENSORS.items()
    }
    return annotate({"sensors": sensors, "dtcs": sorted(dtcs), "fan": {"on": fan}})


def ids(findings):
    return [f["rule_id"] for f in findings]


def find(findings, rule_id):
    return next(f for f in findings if f["rule_id"] == rule_id)


# ---------- Condição normal ----------

def test_normal_reading_triggers_no_rule():
    assert rules.evaluate(snapshot()) == []


def test_every_finding_has_the_required_fields():
    findings = rules.evaluate(snapshot(dtcs={"P0301", "P0171", "P0420"}, coolant_temperature=118,
                                       battery_voltage=11.5, long_term_fuel_trim=16))
    assert findings
    for f in findings:
        assert f["title"] and f["rule_id"].startswith("R-")
        assert f["level"] in {"info", "warn", "crit"} and f["level_label"]
        assert f["evidence"] and f["hypotheses"] and f["checks"]
        assert "didática" in f["disclaimer"]


def test_findings_are_sorted_by_severity():
    findings = rules.evaluate(snapshot(dtcs={"P0420"}, coolant_temperature=118, battery_voltage=12.8))
    levels = [f["level"] for f in findings]
    assert levels == sorted(levels, key=["crit", "warn", "info"].index)
    assert levels[0] == "crit" and levels[-1] == "info"


# ---------- Temperatura e ventoinha ----------

@pytest.mark.parametrize("ect, expected", [(104.9, None), (105, "warn"), (114.9, "warn"), (115, "crit"), (125, "crit")])
def test_ect_high_limits(ect, expected):
    findings = rules.evaluate(snapshot(coolant_temperature=ect, fan=True))
    levels = [f["level"] for f in findings if f["rule_id"] == "R-ECT-ALTA"]
    assert levels == ([expected] if expected else [])


def test_ect_evidence_shows_value_and_didactic_limit():
    f = find(rules.evaluate(snapshot(coolant_temperature=108.4, fan=True)), "R-ECT-ALTA")
    assert f["evidence"] == ["Temperatura do líquido de arrefecimento (ECT): 108,4 °C (limite didático: 105 °C)"]


def test_fan_off_with_high_temperature():
    findings = rules.evaluate(snapshot(coolant_temperature=108, fan=False))
    assert find(findings, "R-VENTOINHA")["level"] == "warn"
    assert "Ventoinha: desligada" in find(findings, "R-VENTOINHA")["evidence"]
    assert find(rules.evaluate(snapshot(coolant_temperature=118)), "R-VENTOINHA")["level"] == "crit"


def test_fan_on_does_not_trigger_fan_rule():
    assert "R-VENTOINHA" not in ids(rules.evaluate(snapshot(coolant_temperature=108, fan=True)))


def test_fan_rule_waits_for_expected_temperature():
    assert "R-VENTOINHA" not in ids(rules.evaluate(snapshot(coolant_temperature=99, fan=False)))


def test_invalid_ect_with_p0115():
    findings = rules.evaluate(snapshot(dtcs={"P0115"}, fan=True, coolant_temperature=None))
    assert ids(findings) == ["R-ECT-SINAL"]  # sem leitura, não dispara regra de temperatura alta
    f = findings[0]
    assert "DTC P0115 armazenado (circuito do sensor ECT)" in f["evidence"]
    assert any("Ventoinha ligada" in e for e in f["evidence"])
    assert f["related_dtcs"] == ["P0115"]


# ---------- Tensão ----------

@pytest.mark.parametrize("volts, expected", [(13.5, None), (13.0, "warn"), (12.4, "warn"), (12.0, "crit"), (11.2, "crit")])
def test_low_voltage_limits(volts, expected):
    findings = rules.evaluate(snapshot(battery_voltage=volts))
    levels = [f["level"] for f in findings if f["rule_id"] == "R-TENSAO-BAIXA"]
    assert levels == ([expected] if expected else [])


def test_low_voltage_ignored_with_engine_off():
    # 12,4 V com motor desligado é tensão normal de bateria em repouso.
    assert rules.evaluate(snapshot(battery_voltage=12.4, rpm=0)) == []


def test_high_voltage():
    assert find(rules.evaluate(snapshot(battery_voltage=15.6)), "R-TENSAO-ALTA")["level"] == "crit"


# ---------- Combustão e mistura ----------

def test_misfire_dtc_points_to_investigation_not_to_a_part():
    f = find(rules.evaluate(snapshot(dtcs={"P0301"})), "R-COMBUSTAO")
    assert f["level"] == "warn"
    assert f["evidence"] == ["DTC P0301 armazenado (cilindro 1)"]
    text = " ".join(f["hypotheses"])
    assert "Ignição" in text and "Injeção" in text and "mecânica" in text
    assert "não confirma a peça" in f["checks"][0]


def test_misfire_with_lean_mixture_suggests_investigating_mixture_first():
    findings = rules.evaluate(snapshot(dtcs={"P0301", "P0171"}, short_term_fuel_trim=14, long_term_fuel_trim=16))
    misfire = find(findings, "R-COMBUSTAO")
    assert misfire["hypotheses"][0].startswith("Mistura pobre pode estar contribuindo")
    assert misfire["related_dtcs"] == ["P0171", "P0301"]
    assert find(findings, "R-MISTURA-POBRE")["level"] == "warn"


def test_lean_dtc_with_positive_trims():
    f = find(rules.evaluate(snapshot(dtcs={"P0171"}, short_term_fuel_trim=14, long_term_fuel_trim=16)), "R-MISTURA-POBRE")
    assert f["title"] == "Mistura pobre com correção de combustível positiva"
    assert "Soma das correções: 30 %" in f["evidence"]


def test_high_trims_without_dtc():
    findings = rules.evaluate(snapshot(long_term_fuel_trim=12))
    assert ids(findings) == ["R-CORRECAO-ALTA"]


def test_lean_dtc_without_high_trims_is_informative():
    f = find(rules.evaluate(snapshot(dtcs={"P0171"})), "R-MISTURA-POBRE")
    assert f["level"] == "info"
    assert any("intermitente" in e for e in f["evidence"])


# ---------- Velocidade ----------

def test_vss_dtc():
    f = find(rules.evaluate(snapshot(dtcs={"P0500"})), "R-VELOCIDADE")
    assert f["evidence"] == ["DTC P0500 armazenado (sensor de velocidade)"]


def test_zero_speed_while_engine_indicates_movement():
    f = find(rules.evaluate(snapshot(vehicle_speed=0, rpm=2200, throttle_position=45)), "R-VELOCIDADE")
    assert "Rotação e borboleta indicam movimento, mas a velocidade informada é zero" in f["evidence"]


def test_stopped_vehicle_at_idle_is_not_incoherent():
    assert rules.evaluate(snapshot(vehicle_speed=0, rpm=800, throttle_position=0)) == []


# ---------- Outros códigos ----------

def test_code_without_specific_rule_gets_generic_finding():
    f = find(rules.evaluate(snapshot(dtcs={"P0420"})), "R-DTC-GERAL")
    assert f["level"] == "info"
    assert f["related_dtcs"] == ["P0420"]


# ---------- Com o simulador ----------

def simulate(seconds, *scenarios, mode="idle"):
    clock = [0.0]
    sim = EcuSimulator(clock=lambda: clock[0], seed=11)
    sim.set_mode(mode)
    for s in scenarios:
        sim.activate(s)
    for _ in range(seconds):
        clock[0] += 1
        snap = sim.snapshot()
    return rules.evaluate(annotate(snap))


def test_simulated_normal_engine_has_no_findings():
    assert simulate(60) == []
    assert simulate(20, mode="accelerating") == []


def test_simulated_overheating_is_critical_with_fan_hypothesis():
    findings = simulate(60, "overheating")
    assert ids(findings)[:2] == ["R-ECT-ALTA", "R-VENTOINHA"]
    assert all(f["level"] == "crit" for f in findings[:2])


def test_simulated_low_voltage_is_critical():
    assert find(simulate(30, "low_voltage"), "R-TENSAO-BAIXA")["level"] == "crit"


def test_simulated_vss_failure_while_accelerating():
    f = find(simulate(15, "vss_failure", mode="accelerating"), "R-VELOCIDADE")
    assert len(f["evidence"]) > 1  # DTC + incoerência entre rotação e velocidade
