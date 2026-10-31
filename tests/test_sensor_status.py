import pytest

from app.services.sensor_status import THRESHOLDS, annotate, classify
from app.services.simulator import SENSORS, EcuSimulator


@pytest.mark.parametrize(
    "key, value, expected",
    [
        ("coolant_temperature", 90, "normal"),
        ("coolant_temperature", 104.9, "normal"),
        ("coolant_temperature", 105, "warn"),
        ("coolant_temperature", 115, "crit"),
        ("battery_voltage", 14.1, "normal"),
        ("battery_voltage", 13.0, "warn"),
        ("battery_voltage", 11.6, "crit"),
        ("battery_voltage", 15.0, "warn"),
        ("long_term_fuel_trim", 16, "warn"),
        ("long_term_fuel_trim", -21, "crit"),
        ("vehicle_speed", 0, "normal"),  # sem limite definido
        ("coolant_temperature", None, "invalid"),
    ],
)
def test_classify(key, value, expected):
    assert classify(key, value)[0] == expected


def test_classify_explains_the_limit_in_portuguese():
    status, note = classify("coolant_temperature", 118, "°C")
    assert status == "crit"
    assert note == "Acima do limite crítico (115 °C)"
    assert classify("battery_voltage", 12.5, "V")[1] == "Abaixo do limite de atenção (13 V)"
    assert classify("rpm", 800)[1] is None


def test_thresholds_only_reference_known_sensors():
    assert set(THRESHOLDS) <= set(SENSORS)


def snapshot_after(seconds, *scenarios):
    clock = [0.0]
    sim = EcuSimulator(clock=lambda: clock[0], seed=5)
    for s in scenarios:
        sim.activate(s)
    for _ in range(seconds):  # avança de 1 em 1 s, como a tela faz
        clock[0] += 1
        snap = sim.snapshot()
    return annotate(snap)


def test_normal_simulation_has_no_alerts():
    snap = snapshot_after(60)
    assert snap["alerts"] == []
    assert all(r["status"] == "normal" for r in snap["sensors"].values())
    assert "didáticos" in snap["thresholds_notice"]


def test_overheating_becomes_critical_alert():
    snap = snapshot_after(60, "overheating")
    assert snap["sensors"]["coolant_temperature"]["status"] == "crit"
    assert snap["alerts"][0]["sensor"] == "coolant_temperature"
    assert snap["alerts"][0]["message"].startswith("Temperatura do líquido de arrefecimento (ECT): Acima do limite crítico")


def test_low_voltage_and_lean_mixture_alerts_sorted_by_severity():
    snap = snapshot_after(60, "low_voltage", "lean_mixture")
    statuses = [a["status"] for a in snap["alerts"]]
    assert statuses[0] == "crit"
    assert {a["sensor"] for a in snap["alerts"]} >= {"battery_voltage", "long_term_fuel_trim"}
    assert statuses == sorted(statuses, key=["crit", "invalid", "warn"].index)


def test_disconnected_sensor_is_flagged_without_reading():
    snap = snapshot_after(5, "ect_disconnected")
    reading = snap["sensors"]["coolant_temperature"]
    assert reading["status"] == "invalid"
    assert reading["status_label"] == "Sem leitura"
