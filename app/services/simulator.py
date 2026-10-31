"""Simulador didático de ECU.

Nenhum valor vem de um veículo real. O simulador mantém um estado interno (velocidade,
borboleta, temperatura, tensão...) que evolui com o tempo, de acordo com o modo de condução
e os cenários de falha ativos. As leituras são derivadas desse estado, para que fiquem
coerentes entre si (ex.: RPM acompanha velocidade e marcha).

Todos os parâmetros abaixo são DIDÁTICOS/ILUSTRATIVOS, não especificações de um veículo.
"""

import random
import threading
import time
from datetime import datetime, timezone

from app.services.errors import ConflictError, NotFoundError, ValidationError

MODES = {
    "idle": "Marcha lenta (parado)",
    "accelerating": "Aceleração",
    "decelerating": "Desaceleração",
}

# Parâmetros ilustrativos de um motor 1.6 com câmbio de 5 marchas.
PARAMS = {
    "idle_rpm": 800,
    "kmh_per_1000rpm": [8, 14, 21, 28, 35],  # velocidade a 1000 rpm em cada marcha (1ª a 5ª)
    "gear_up_kmh": [15, 30, 50, 75],  # velocidade em que passa para a próxima marcha
    "max_speed_kmh": 110,
    "accel_kmh_s": 4.0,
    "decel_kmh_s": 3.0,
    "brake_kmh_s": 6.0,  # modo parado: freia até 0 km/h
    "accel_throttle_pct": 45,
    "engine_liters": 1.6,
    "ect_normal_c": 90,
    "ect_overheat_c": 125,
    "ect_time_constant_s": 25,
    "fan_on_c": 98,
    "fan_off_c": 93,
    "voltage_charging_v": 14.1,
    "voltage_low_v": 11.6,
    "ltft_normal_pct": 1.5,
    "ltft_lean_pct": 16,
    "stft_lean_pct": 12,
}

# chave: (nome exibido, unidade)
SENSORS = {
    "rpm": ("Rotação do motor", "rpm"),
    "coolant_temperature": ("Temperatura do líquido de arrefecimento (ECT)", "°C"),
    "vehicle_speed": ("Velocidade do veículo (VSS)", "km/h"),
    "engine_load": ("Carga calculada do motor", "%"),
    "throttle_position": ("Posição da borboleta (TPS)", "%"),
    "maf": ("Fluxo de ar (MAF)", "g/s"),
    "battery_voltage": ("Tensão do módulo", "V"),
    "short_term_fuel_trim": ("Correção de combustível de curto prazo (STFT B1)", "%"),
    "long_term_fuel_trim": ("Correção de combustível de longo prazo (LTFT B1)", "%"),
}

SCENARIOS = {
    "overheating": {
        "name": "Superaquecimento",
        "description": "A ventoinha não liga e a temperatura do motor sobe acima do normal.",
        "dtcs": [],
    },
    "low_voltage": {
        "name": "Tensão baixa",
        "description": "O sistema de carga não fornece tensão suficiente; a tensão cai abaixo de 12 V.",
        "dtcs": [],
    },
    "ect_disconnected": {
        "name": "Sensor ECT desconectado",
        "description": "O sinal do sensor de temperatura fica inválido. A ECU liga a ventoinha por segurança.",
        "dtcs": ["P0115"],
    },
    "misfire_cyl1": {
        "name": "Falha de combustão no cilindro 1",
        "description": "A marcha lenta fica irregular: a rotação oscila mais que o normal.",
        "dtcs": ["P0301"],
    },
    "lean_mixture": {
        "name": "Mistura pobre",
        "description": "A ECU adiciona combustível para compensar: as correções de combustível ficam positivas.",
        "dtcs": ["P0171"],
    },
    "vss_failure": {
        "name": "Falha no sensor de velocidade",
        "description": "A velocidade informada fica em 0 km/h mesmo com o veículo em movimento.",
        "dtcs": ["P0500"],
    },
}

# Cenários que não podem ficar ativos juntos, com o motivo.
CONFLICTS = [
    ({"overheating", "ect_disconnected"},
     "com o sensor ECT desconectado, a temperatura não pode ser lida e o superaquecimento não seria observado."),
]

STEP_S = 0.1  # passo de integração
MAX_GAP_S = 30  # se ninguém consultar por muito tempo, simula no máximo 30 s de uma vez


class EcuSimulator:
    """Uma instância por aplicação. `clock` e `seed` permitem testes determinísticos."""

    def __init__(self, clock=time.monotonic, seed: int | None = None):
        self._clock = clock
        self._seed = seed
        self._lock = threading.Lock()
        self._reset_state()

    # ---------- API pública ----------

    def snapshot(self) -> dict:
        with self._lock:
            self._advance_to_now()
            return self._read()

    def set_mode(self, mode) -> dict:
        if mode not in MODES:
            raise ValidationError(
                "Modo inválido. Use idle, accelerating ou decelerating.",
                fields={"mode": "Escolha um modo válido."},
            )
        with self._lock:
            self._advance_to_now()
            self.mode = mode
        return self.status()

    def activate(self, scenario_id: str) -> dict:
        self._check_scenario(scenario_id)
        with self._lock:
            for pair, reason in CONFLICTS:
                active_rival = (pair - {scenario_id}) & self.scenarios
                if scenario_id in pair and active_rival:
                    other_name = SCENARIOS[active_rival.pop()]["name"]
                    raise ConflictError(
                        f"Não é possível ativar \"{SCENARIOS[scenario_id]['name']}\" junto com "
                        f"\"{other_name}\": {reason}",
                        code="SCENARIO_CONFLICT",
                    )
            self._advance_to_now()
            self.scenarios.add(scenario_id)
        return self.status()

    def deactivate(self, scenario_id: str) -> dict:
        self._check_scenario(scenario_id)
        with self._lock:
            self._advance_to_now()
            self.scenarios.discard(scenario_id)
        return self.status()

    def reset(self) -> dict:
        with self._lock:
            self._reset_state()
        return self.status()

    def status(self) -> dict:
        with self._lock:
            active = set(self.scenarios)
            mode = self.mode
        scenarios = []
        for sid, info in SCENARIOS.items():
            conflicts = sorted(s for pair, _ in CONFLICTS if sid in pair for s in pair - {sid})
            scenarios.append({"id": sid, **info, "active": sid in active, "conflicts_with": conflicts})
        return {"mode": mode, "mode_label": MODES[mode], "modes": MODES, "scenarios": scenarios}

    # ---------- Estado interno ----------

    def _reset_state(self) -> None:
        self._rng = random.Random(self._seed)
        self.mode = "idle"
        self.scenarios: set[str] = set()
        self._speed = 0.0
        self._throttle = 0.0
        self._ect = float(PARAMS["ect_normal_c"])
        self._fan_on = False
        self._voltage = PARAMS["voltage_charging_v"]
        self._ltft = PARAMS["ltft_normal_pct"]
        self._last = self._clock()

    def _check_scenario(self, scenario_id: str) -> None:
        if scenario_id not in SCENARIOS:
            raise NotFoundError("Cenário não encontrado.")

    def _advance_to_now(self) -> None:
        now = self._clock()
        elapsed = min(max(now - self._last, 0.0), MAX_GAP_S)
        self._last = now
        while elapsed > 1e-9:
            dt = min(STEP_S, elapsed)
            self._step(dt)
            elapsed -= dt

    def _step(self, dt: float) -> None:
        p = PARAMS
        s = self.scenarios

        # Borboleta: abre na aceleração, fecha nos outros modos (resposta de ~0,5 s).
        target_tps = p["accel_throttle_pct"] if self.mode == "accelerating" else 0.0
        self._throttle += (target_tps - self._throttle) * min(1.0, dt / 0.5)

        # Velocidade
        if self.mode == "accelerating":
            self._speed += p["accel_kmh_s"] * (1 - self._speed / p["max_speed_kmh"]) * dt
        elif self.mode == "decelerating":
            self._speed = max(0.0, self._speed - p["decel_kmh_s"] * dt)
        else:
            self._speed = max(0.0, self._speed - p["brake_kmh_s"] * dt)

        # Temperatura do motor e ventoinha
        target_ect = p["ect_overheat_c"] if "overheating" in s else p["ect_normal_c"]
        self._ect += (target_ect - self._ect) * dt / p["ect_time_constant_s"]
        if "overheating" in s:
            self._fan_on = False  # cenário: a ventoinha não aciona
        elif "ect_disconnected" in s:
            self._fan_on = True  # sem leitura de temperatura, a ECU liga a ventoinha por segurança
        elif self._ect >= p["fan_on_c"]:
            self._fan_on = True
        elif self._ect <= p["fan_off_c"]:
            self._fan_on = False
        if self._fan_on and "overheating" not in s:
            self._ect -= 0.3 * dt

        # Tensão: alternador carregando ou falha no sistema de carga
        target_v = p["voltage_low_v"] if "low_voltage" in s else p["voltage_charging_v"] - (0.2 if self._fan_on else 0)
        self._voltage += (target_v - self._voltage) * dt / 5

        # Correção de longo prazo aprende devagar
        target_ltft = p["ltft_lean_pct"] if "lean_mixture" in s else p["ltft_normal_pct"]
        self._ltft += (target_ltft - self._ltft) * dt / 10

    # ---------- Leituras ----------

    def _rpm(self) -> float:
        p = PARAMS
        gear = sum(self._speed >= limit for limit in p["gear_up_kmh"])
        return max(p["idle_rpm"], self._speed / p["kmh_per_1000rpm"][gear] * 1000)

    def _read(self) -> dict:
        p = PARAMS
        s = self.scenarios
        noise = self._rng.gauss

        misfire = "misfire_cyl1" in s
        rpm = self._rpm() + noise(0, 60 if misfire else 8)
        if self.mode == "decelerating" and self._speed > 5 and self._throttle < 2:
            load = 12.0  # desaceleração com borboleta fechada: corte de combustível
        else:
            load = 20 + 0.9 * self._throttle + (4 if misfire else 0)
        load += noise(0, 0.8)
        maf = rpm * load / 100 * p["engine_liters"] * 1.2 / 120  # aproximação: rotação x carga x cilindrada
        stft = (p["stft_lean_pct"] if "lean_mixture" in s else 0) + noise(0, 1.5)

        values = {
            "rpm": round(rpm),
            "coolant_temperature": None if "ect_disconnected" in s else round(self._ect + noise(0, 0.2), 1),
            "vehicle_speed": 0 if "vss_failure" in s else round(self._speed),
            "engine_load": round(_clamp(load, 0, 100), 1),
            "throttle_position": round(_clamp(self._throttle + noise(0, 0.2), 0, 100), 1),
            "maf": round(maf, 1),
            "battery_voltage": round(self._voltage + noise(0, 0.03), 2),
            "short_term_fuel_trim": round(stft, 1),
            "long_term_fuel_trim": round(self._ltft, 1),
        }
        sensors = {
            key: {
                "label": label,
                "value": values[key],
                "unit": unit,
                "validity": "invalid" if values[key] is None else "valid",
            }
            for key, (label, unit) in SENSORS.items()
        }
        dtcs = sorted({code for sid in s for code in SCENARIOS[sid]["dtcs"]})
        return {
            "source": "simulation",
            "notice": "Dados simulados: não representam leitura de um veículo real.",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "mode": self.mode,
            "mode_label": MODES[self.mode],
            "active_scenarios": sorted(s),
            "sensors": sensors,
            "fan": {"on": self._fan_on},
            "dtcs": dtcs,
        }


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)
