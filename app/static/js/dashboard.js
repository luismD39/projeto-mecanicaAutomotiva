// Dashboard: indicadores, gráficos, alertas e estado da ECU simulada (atualiza a cada 1 s).
"use strict";

(() => {
  const tiles = [...document.querySelectorAll(".kpi[data-sensor]")];
  const alertsBox = document.getElementById("alerts");
  const lastUpdate = document.getElementById("last-update");
  const charts = {
    rpm: LiveCharts.create(document.getElementById("chart-rpm"),
      { label: "Rotação", unit: "rpm", decimals: 0, suggestedMin: 0, suggestedMax: 3500 }),
    coolant_temperature: LiveCharts.create(document.getElementById("chart-ect"),
      { label: "Temperatura", unit: "°C", decimals: 1, suggestedMin: 70, suggestedMax: 120 }),
  };
  let failures = 0;
  let lastAlertsKey = null;

  function setText(id, text) {
    document.getElementById(id).textContent = text;
  }

  function renderAlerts(alerts) {
    // Só redesenha quando muda: a região é lida por leitores de tela (aria-live).
    const key = JSON.stringify(alerts.map((a) => [a.status, a.message]));
    if (key === lastAlertsKey) return;
    lastAlertsKey = key;
    if (!alerts.length) {
      AutoScan.showState(alertsBox, "empty", "Nenhum alerta", {
        detail: "Todos os parâmetros estão dentro dos limites didáticos.",
      });
      return;
    }
    const list = document.createElement("ul");
    list.className = "alert-list";
    for (const alert of alerts) {
      const li = document.createElement("li");
      const text = document.createElement("span");
      text.textContent = alert.message;
      li.append(AutoScan.statusBadge(alert.status, alert.status_label), text);
      list.append(li);
    }
    alertsBox.replaceChildren(list);
  }

  function render(snap) {
    for (const tile of tiles) AutoScan.renderTile(tile, snap.sensors[tile.dataset.sensor]);

    const time = AutoScan.timeLabel(snap.timestamp);
    for (const [key, chart] of Object.entries(charts)) LiveCharts.push(chart, time, snap.sensors[key].value);

    renderAlerts(snap.alerts);
    document.getElementById("ecu-connection").replaceChildren(AutoScan.badge("ok", "Conectada (simulação)"));
    setText("ecu-mode", snap.mode_label);
    setText("ecu-scenarios", snap.active_scenarios.length ? String(snap.active_scenarios.length) : "Nenhum");
    setText("ecu-fan", snap.fan.on ? "Ligada" : "Desligada");
    lastUpdate.textContent = `última leitura às ${time}`;
  }

  async function update() {
    try {
      render(await AutoScan.api.get("/api/sensors/live"));
      failures = 0;
    } catch (err) {
      failures += 1;
      document.getElementById("ecu-connection").replaceChildren(AutoScan.badge("crit", "Sem resposta"));
      lastUpdate.textContent = "sem resposta do servidor";
      // Avisa uma vez só, e não a cada segundo enquanto o servidor estiver fora.
      if (failures === 1) AutoScan.notify(err.message, "crit");
    }
  }

  AutoScan.poll(update, 1000);
})();
