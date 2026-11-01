"""Motor de regras do diagnóstico: regras explícitas em Python, sem inteligência artificial.

Cada regra recebe a leitura salva na varredura e, se suas condições forem atendidas,
devolve um resultado com evidências observadas, hipóteses possíveis e verificações
recomendadas. Hipótese NÃO é confirmação: indica o que investigar.

Limites usados aqui são DIDÁTICOS/ILUSTRATIVOS:
- faixas de sensores: sensor_status.THRESHOLDS (os mesmos do Dashboard);
- limites próprios das regras: RULE_LIMITS, abaixo.
"""

from app.services.sensor_status import THRESHOLDS

RULE_LIMITS = {
    "fan_expected_on_c": 100,  # acima disso, a ventoinha já deveria estar ligada
    "engine_running_rpm": 400,  # abaixo disso, considera motor desligado (tensão de bateria em repouso é normal)
    "fuel_trim_total_pct": 20,  # soma STFT + LTFT que reforça a hipótese de mistura pobre
    "moving_rpm": 1500,  # rotação e borboleta que indicam veículo em movimento
    "moving_throttle_pct": 10,
}

LEVEL_LABELS = {"info": "Informativo", "warn": "Atenção", "crit": "Crítico"}
_ORDER = {"crit": 0, "warn": 1, "info": 2}

DISCLAIMER = (
    "Orientação didática gerada por regra explícita a partir de dados simulados. "
    "Não substitui a avaliação de um profissional seguindo o procedimento do fabricante."
)

MISFIRE_CODES = {"P0300", "P0301"}


# ---------- Auxiliares ----------

def _fmt(value: float, unit: str) -> str:
    decimals = 0 if float(value).is_integer() else {"rpm": 0, "km/h": 0, "V": 2}.get(unit, 1)
    text = f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} {unit}"


class _Reading:
    """Acesso simples às leituras: r.value('rpm'), r.text('rpm') -> '2.100 rpm'."""

    def __init__(self, snapshot: dict):
        self.sensors = snapshot["sensors"]
        self.dtcs = set(snapshot.get("dtcs", []))
        self.fan_on = bool(snapshot.get("fan", {}).get("on"))

    def value(self, key):
        return self.sensors[key]["value"]

    def text(self, key) -> str:
        s = self.sensors[key]
        return f"{s['label']}: {_fmt(s['value'], s['unit'])}"


def _finding(rule_id, title, level, evidence, hypotheses, checks, dtcs=()):
    return {
        "rule_id": rule_id,
        "title": title,
        "level": level,
        "level_label": LEVEL_LABELS[level],
        "evidence": evidence,
        "hypotheses": hypotheses,
        "checks": checks,
        "related_dtcs": sorted(dtcs),
        "disclaimer": DISCLAIMER,
    }


# ---------- Regras ----------

def rule_ect_high(r: _Reading):
    """Temperatura do líquido de arrefecimento acima dos limites de atenção/crítico."""
    ect = r.value("coolant_temperature")
    limits = THRESHOLDS["coolant_temperature"]
    if ect is None or ect < limits["warn_high"]:
        return None
    level = "crit" if ect >= limits["crit_high"] else "warn"
    limit = limits["crit_high"] if level == "crit" else limits["warn_high"]
    return _finding(
        "R-ECT-ALTA", "Temperatura do motor elevada", level,
        [f"{r.text('coolant_temperature')} (limite didático: {_fmt(limit, '°C')})"],
        ["Nível baixo de líquido de arrefecimento ou vazamento",
         "Ventoinha não acionando",
         "Termostato travado fechado",
         "Circulação deficiente (bomba d'água, radiador obstruído)"],
        ["Com o motor FRIO, verificar o nível do líquido de arrefecimento (não abra o reservatório quente)",
         "Verificar se a ventoinha liga ao atingir a temperatura de acionamento",
         "Procurar vazamentos em mangueiras, radiador e bomba d'água",
         "Comparar a leitura do ECT com um termômetro confiável"],
    )


def rule_fan_not_on(r: _Reading):
    """Temperatura alta com a ventoinha desligada: possível falha no acionamento da ventoinha."""
    ect = r.value("coolant_temperature")
    if ect is None or r.fan_on or ect < RULE_LIMITS["fan_expected_on_c"]:
        return None
    level = "crit" if ect >= THRESHOLDS["coolant_temperature"]["crit_high"] else "warn"
    return _finding(
        "R-VENTOINHA", "Ventoinha desligada com temperatura alta", level,
        [r.text("coolant_temperature"), "Ventoinha: desligada",
         f"Acima de {_fmt(RULE_LIMITS['fan_expected_on_c'], '°C')} a ventoinha já deveria estar ligada (limite didático)"],
        ["Possível anomalia no comando ou no acionamento da ventoinha",
         "Relé ou fusível da ventoinha",
         "Motor elétrico da ventoinha",
         "Chicote ou conector do circuito da ventoinha"],
        ["Verificar fusível e relé da ventoinha",
         "Testar o motor da ventoinha alimentando-o conforme o manual",
         "Verificar se a ECU está comandando o acionamento (com equipamento adequado)"],
    )


def rule_ect_invalid(r: _Reading):
    """Sem leitura válida de temperatura do motor."""
    if r.sensors["coolant_temperature"]["validity"] != "invalid":
        return None
    evidence = ["Temperatura do líquido de arrefecimento (ECT): sem leitura válida"]
    if "P0115" in r.dtcs:
        evidence.append("DTC P0115 armazenado (circuito do sensor ECT)")
    if r.fan_on:
        evidence.append("Ventoinha ligada (comportamento comum de segurança quando a ECU perde a leitura de temperatura)")
    return _finding(
        "R-ECT-SINAL", "Sinal do sensor de temperatura inválido", "warn", evidence,
        ["Conector do sensor ECT solto ou oxidado",
         "Fiação do sensor rompida ou em curto",
         "Sensor ECT com defeito"],
        ["Inspecionar o conector e o chicote do sensor ECT",
         "Medir a resistência do sensor e comparar com a tabela do fabricante",
         "Verificar a tensão de referência e o aterramento do circuito"],
        dtcs={"P0115"} & r.dtcs,
    )


def rule_voltage(r: _Reading):
    """Tensão do módulo fora da faixa com o motor funcionando."""
    volts = r.value("battery_voltage")
    rpm = r.value("rpm")
    if volts is None or rpm is None or rpm < RULE_LIMITS["engine_running_rpm"]:
        return None
    t = THRESHOLDS["battery_voltage"]
    if volts <= t["warn_low"]:
        level = "crit" if volts <= t["crit_low"] else "warn"
        return _finding(
            "R-TENSAO-BAIXA", "Tensão de alimentação baixa com motor funcionando", level,
            [r.text("battery_voltage"), r.text("rpm"),
             f"Com o motor funcionando, o sistema de carga costuma manter a tensão acima de {_fmt(t['warn_low'], 'V')} (limite didático)"],
            ["Alternador não está carregando",
             "Correia do alternador frouxa ou rompida",
             "Bateria em fim de vida",
             "Terminais ou aterramentos oxidados ou soltos"],
            ["Medir a tensão na bateria com o motor desligado e funcionando",
             "Inspecionar a correia e os terminais da bateria",
             "Testar o alternador e o regulador de tensão",
             "Testar a bateria com equipamento adequado"],
        )
    if volts >= t["warn_high"]:
        level = "crit" if volts >= t["crit_high"] else "warn"
        return _finding(
            "R-TENSAO-ALTA", "Tensão de alimentação alta", level,
            [r.text("battery_voltage"), f"Limite didático de atenção: {_fmt(t['warn_high'], 'V')}"],
            ["Regulador de tensão do alternador com defeito"],
            ["Medir a tensão na bateria com o motor funcionando em diferentes rotações",
             "Testar o regulador de tensão do alternador"],
        )
    return None


def rule_misfire(r: _Reading):
    """DTC de falha de combustão. O código aponta o cilindro, não a peça."""
    codes = MISFIRE_CODES & r.dtcs
    if not codes:
        return None
    evidence = [f"DTC {c} armazenado" + (" (cilindro 1)" if c == "P0301" else " (aleatória/múltipla)")
                for c in sorted(codes)]
    hypotheses = ["Ignição: vela, bobina ou cabo",
                  "Injeção: bico injetor obstruído ou sem acionamento",
                  "Condição mecânica: compressão baixa (válvulas, anéis, junta)"]
    if "P0171" in r.dtcs:
        evidence.append("DTC P0171 (mistura pobre) também armazenado")
        hypotheses.insert(0, "Mistura pobre pode estar contribuindo para a falha de combustão: investigar a causa da mistura primeiro")
    return _finding(
        "R-COMBUSTAO", "Falha de combustão registrada", "warn", evidence, hypotheses,
        ["O código indica o cilindro, mas não confirma a peça: não substitua vela ou bobina sem testar",
         "Trocar a bobina de posição com outro cilindro e verificar se a falha acompanha a bobina",
         "Inspecionar a vela e verificar o acionamento do bico injetor",
         "Realizar teste de compressão no cilindro indicado"],
        dtcs=codes | ({"P0171"} & r.dtcs),
    )


def rule_fuel_trim(r: _Reading):
    """Mistura pobre: DTC P0171 e/ou correções de combustível positivas elevadas."""
    stft, ltft = r.value("short_term_fuel_trim"), r.value("long_term_fuel_trim")
    if stft is None or ltft is None:
        return None
    total = stft + ltft
    high = (ltft >= THRESHOLDS["long_term_fuel_trim"]["warn_high"]
            or total >= RULE_LIMITS["fuel_trim_total_pct"])
    has_dtc = "P0171" in r.dtcs
    if not high and not has_dtc:
        return None

    evidence = [r.text("short_term_fuel_trim"), r.text("long_term_fuel_trim"),
                f"Soma das correções: {_fmt(total, '%')}"]
    hypotheses = ["Entrada falsa de ar (mangueiras de vácuo, juntas do coletor, válvula PCV)",
                  "Pressão ou vazão de combustível baixa",
                  "Sensor MAF informando menos ar do que o motor admite"]
    checks = ["Comparar as correções em marcha lenta e em rotação mais alta",
              "Procurar entrada falsa de ar",
              "Medir a pressão de combustível",
              "Verificar a leitura do sensor MAF"]
    if has_dtc and high:
        return _finding("R-MISTURA-POBRE", "Mistura pobre com correção de combustível positiva", "warn",
                        ["DTC P0171 armazenado", *evidence], hypotheses, checks, dtcs={"P0171"})
    if high:
        return _finding("R-CORRECAO-ALTA", "Correção de combustível positiva elevada (sem DTC)", "warn",
                        evidence, hypotheses, checks)
    return _finding(
        "R-MISTURA-POBRE", "DTC de mistura pobre sem correção elevada no momento", "info",
        ["DTC P0171 armazenado", *evidence,
         "As correções estavam normais nesta leitura: a falha pode ser intermitente"],
        hypotheses, ["Repetir a leitura em diferentes condições de carga e rotação", *checks], dtcs={"P0171"},
    )


def rule_vss(r: _Reading):
    """Velocidade zero com o motor em condição de movimento, ou DTC P0500."""
    speed, rpm, tps = r.value("vehicle_speed"), r.value("rpm"), r.value("throttle_position")
    incoherent = (speed == 0 and rpm is not None and tps is not None
                  and rpm >= RULE_LIMITS["moving_rpm"] and tps >= RULE_LIMITS["moving_throttle_pct"])
    has_dtc = "P0500" in r.dtcs
    if not incoherent and not has_dtc:
        return None
    evidence = []
    if has_dtc:
        evidence.append("DTC P0500 armazenado (sensor de velocidade)")
    if incoherent:
        evidence += [r.text("vehicle_speed"), r.text("rpm"), r.text("throttle_position"),
                     "Rotação e borboleta indicam movimento, mas a velocidade informada é zero"]
    return _finding(
        "R-VELOCIDADE", "Sinal de velocidade ausente ou incoerente", "warn", evidence,
        ["Sensor de velocidade (VSS) com defeito",
         "Chicote ou conector do sensor danificado",
         "Falha de comunicação com o módulo que informa a velocidade (ex.: ABS)"],
        ["Comparar a velocidade nos dados ao vivo com a real, em local seguro",
         "Verificar códigos em outros módulos (ABS, transmissão, painel)",
         "Inspecionar conector e chicote do sensor"],
        dtcs={"P0500"} & r.dtcs,
    )


SPECIFIC_RULES = [rule_ect_high, rule_fan_not_on, rule_ect_invalid, rule_voltage,
                  rule_misfire, rule_fuel_trim, rule_vss]
COVERED_CODES = {"P0115", "P0171", "P0500"} | MISFIRE_CODES


def rule_other_dtcs(r: _Reading):
    """Códigos sem regra específica: registra para consulta no catálogo."""
    others = sorted(r.dtcs - COVERED_CODES)
    if not others:
        return None
    return _finding(
        "R-DTC-GERAL", "Código armazenado sem regra específica", "info",
        [f"DTC {c} armazenado" for c in others],
        ["Consulte o catálogo de códigos para as possíveis causas"],
        ["Seguir as verificações recomendadas no catálogo e no manual do fabricante"],
        dtcs=set(others),
    )


RULES = [*SPECIFIC_RULES, rule_other_dtcs]


def evaluate(snapshot: dict) -> list[dict]:
    """Executa todas as regras e devolve os resultados, do mais grave para o menos grave."""
    reading = _Reading(snapshot)
    findings = [f for rule in RULES if (f := rule(reading))]
    return sorted(findings, key=lambda f: _ORDER[f["level"]])
