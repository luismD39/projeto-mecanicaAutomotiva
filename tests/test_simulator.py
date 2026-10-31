import math
import statistics

import pytest

from app.services.errors import ConflictError, NotFoundError, ValidationError
from app.services.simulator import SCENARIOS, SENSORS, EcuSimulator


class FakeClock:
    """Relógio controlado pelo teste, para não depender do tempo real."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def ecu(clock):
    return EcuSimulator(clock=clock, seed=42)


def run(ecu, clock, seconds):
    clock.now += seconds
    return ecu.snapshot()


def value(snapshot, key):
    return snapshot["sensors"][key]["value"]


# ---------- Modo normal ----------

def test_idle_readings_are_valid_and_plausible(ecu, clock):
    snap = run(ecu, clock, 5)
    assert snap["source"] == "simulation"
    assert set(snap["sensors"]) == set(SENSORS)
    for key, reading in snap["sensors"].items():
        assert reading["validity"] == "valid", key
        assert reading["unit"] and reading["label"]
        assert math.isfinite(reading["value"])
    assert 700 <= value(snap, "rpm") <= 900
    assert value(snap, "vehicle_speed") == 0
    assert 85 <= value(snap, "coolant_temperature") <= 95
    assert 13.5 <= value(snap, "battery_voltage") <= 14.5
    assert value(snap, "throttle_position") < 2
    assert 1.5 <= value(snap, "maf") <= 5
    assert snap["fan"]["on"] is False
    assert snap["dtcs"] == []


def test_normal_temperature_stays_stable(ecu, clock):
    for _ in range(10):
        snap = run(ecu, clock, 30)
    assert 85 <= value(snap, "coolant_temperature") <= 95


# ---------- Modos de condução ----------

def test_accelerating_raises_rpm_tps_speed_and_load(ecu, clock):
    idle = run(ecu, clock, 2)
    ecu.set_mode("accelerating")
    accel = run(ecu, clock, 5)
    assert value(accel, "throttle_position") > 40
    assert value(accel, "rpm") > value(idle, "rpm") + 300
    assert value(accel, "vehicle_speed") > 10
    assert value(accel, "engine_load") > value(idle, "engine_load") + 20
    assert value(accel, "maf") > value(idle, "maf")


def test_speed_never_exceeds_limit_and_rpm_follows_gear(ecu, clock):
    ecu.set_mode("accelerating")
    snap = run(ecu, clock, 30)
    for _ in range(20):
        snap = run(ecu, clock, 30)
    assert value(snap, "vehicle_speed") <= 110
    assert 2500 <= value(snap, "rpm") <= 3500  # 5ª marcha perto de 110 km/h


def test_decelerating_reduces_rpm_and_tps(ecu, clock):
    ecu.set_mode("accelerating")
    before = run(ecu, clock, 20)
    ecu.set_mode("decelerating")
    during = run(ecu, clock, 2)
    assert value(during, "throttle_position") < 2
    assert value(during, "engine_load") < 15  # corte de combustível
    after = run(ecu, clock, 20)
    assert value(after, "rpm") < value(before, "rpm")
    assert value(after, "vehicle_speed") < value(before, "vehicle_speed")


def test_invalid_mode_is_rejected(ecu):
    with pytest.raises(ValidationError):
        ecu.set_mode("turbo")


# ---------- Cenários ----------

def test_overheating_raises_ect_with_fan_off(ecu, clock):
    ecu.activate("overheating")
    snap = run(ecu, clock, 30)
    assert value(snap, "coolant_temperature") > 105
    assert snap["fan"]["on"] is False
    assert snap["dtcs"] == []  # condição observada, sem DTC próprio


def test_low_voltage_reduces_voltage(ecu, clock):
    ecu.activate("low_voltage")
    snap = run(ecu, clock, 20)
    assert value(snap, "battery_voltage") < 12


def test_disconnected_ect_reports_invalid_not_a_number(ecu, clock):
    ecu.activate("ect_disconnected")
    snap = run(ecu, clock, 1)
    reading = snap["sensors"]["coolant_temperature"]
    assert reading["value"] is None
    assert reading["validity"] == "invalid"
    assert snap["fan"]["on"] is True  # modo de segurança
    assert snap["dtcs"] == ["P0115"]


def test_misfire_makes_idle_rpm_unstable(clock):
    def rpm_spread(scenario):
        sim = EcuSimulator(clock=clock, seed=7)
        if scenario:
            sim.activate(scenario)
        return statistics.pstdev(value(run(sim, clock, 1), "rpm") for _ in range(40))

    assert rpm_spread("misfire_cyl1") > 3 * rpm_spread(None)


def test_misfire_reports_p0301(ecu, clock):
    ecu.activate("misfire_cyl1")
    assert run(ecu, clock, 1)["dtcs"] == ["P0301"]


def test_lean_mixture_makes_fuel_trims_positive(ecu, clock):
    ecu.activate("lean_mixture")
    snap = run(ecu, clock, 40)
    assert value(snap, "long_term_fuel_trim") > 12
    assert value(snap, "short_term_fuel_trim") + value(snap, "long_term_fuel_trim") > 20
    assert snap["dtcs"] == ["P0171"]


def test_vss_failure_reports_zero_speed_while_moving(ecu, clock):
    ecu.activate("vss_failure")
    ecu.set_mode("accelerating")
    snap = run(ecu, clock, 15)
    assert value(snap, "vehicle_speed") == 0
    assert value(snap, "rpm") > 1200
    assert snap["dtcs"] == ["P0500"]


def test_compatible_scenarios_can_be_combined(ecu, clock):
    ecu.activate("misfire_cyl1")
    ecu.activate("lean_mixture")
    snap = run(ecu, clock, 1)
    assert snap["active_scenarios"] == ["lean_mixture", "misfire_cyl1"]
    assert snap["dtcs"] == ["P0171", "P0301"]


def test_contradictory_scenarios_are_rejected(ecu):
    ecu.activate("overheating")
    with pytest.raises(ConflictError) as exc:
        ecu.activate("ect_disconnected")
    assert exc.value.code == "SCENARIO_CONFLICT"
    active = [s["id"] for s in ecu.status()["scenarios"] if s["active"]]
    assert active == ["overheating"]


def test_activating_twice_is_harmless(ecu):
    ecu.activate("low_voltage")
    ecu.activate("low_voltage")
    assert sum(s["active"] for s in ecu.status()["scenarios"]) == 1


def test_unknown_scenario(ecu):
    with pytest.raises(NotFoundError):
        ecu.activate("explosao")
    with pytest.raises(NotFoundError):
        ecu.deactivate("explosao")


def test_deactivate_returns_to_normal(ecu, clock):
    ecu.activate("overheating")
    run(ecu, clock, 30)
    ecu.deactivate("overheating")
    snap = run(ecu, clock, 120)
    assert value(snap, "coolant_temperature") < 98


def test_reset_restores_normal_state(ecu, clock):
    ecu.set_mode("accelerating")
    for scenario in ("overheating", "low_voltage", "misfire_cyl1", "lean_mixture", "vss_failure"):
        ecu.activate(scenario)
    run(ecu, clock, 30)

    status = ecu.reset()
    assert status["mode"] == "idle"
    assert not any(s["active"] for s in status["scenarios"])

    snap = run(ecu, clock, 1)
    assert snap["dtcs"] == []
    assert 700 <= value(snap, "rpm") <= 900
    assert 85 <= value(snap, "coolant_temperature") <= 95
    assert value(snap, "battery_voltage") > 13.5


def test_demo_can_be_repeated(ecu, clock):
    for _ in range(3):
        ecu.activate("overheating")
        assert value(run(ecu, clock, 30), "coolant_temperature") > 105
        ecu.reset()
        assert value(run(ecu, clock, 1), "coolant_temperature") < 95


# ---------- Determinismo e robustez ----------

def test_same_seed_and_clock_give_same_readings():
    clock_a, clock_b = FakeClock(), FakeClock()
    a, b = EcuSimulator(clock=clock_a, seed=1), EcuSimulator(clock=clock_b, seed=1)
    for sim in (a, b):
        sim.set_mode("accelerating")
        sim.activate("lean_mixture")
    assert run(a, clock_a, 12)["sensors"] == run(b, clock_b, 12)["sensors"]


def test_long_gap_without_polling_is_bounded(ecu, clock):
    snap = run(ecu, clock, 10_000)
    assert all(r["value"] is None or math.isfinite(r["value"]) for r in snap["sensors"].values())


def test_scenarios_reference_real_catalog_codes():
    catalog = {"P0101", "P0115", "P0128", "P0171", "P0300", "P0301", "P0420", "P0500"}
    for info in SCENARIOS.values():
        assert set(info["dtcs"]) <= catalog
