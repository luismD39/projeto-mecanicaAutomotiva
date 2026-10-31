// Dados em tempo real: todos os sensores, modo de condução e gráfico com parâmetro escolhido.
"use strict";

(() => {
  const tiles = [...document.querySelectorAll(".kpi[data-sensor]")];
  const modeButtons = [...document.querySelectorAll(".segmented-btn")];
  const select = document.getElementById("chart-sensor");
  const canvas = document.getElementById("live-chart");
  const lastUpdate = document.getElementById("last-update");

  // Escala sugerida de cada gráfico (o eixo cresce se o valor passar disso).
  const CHART_RANGES = {
    rpm: [0, 3500, 0],
    coolant_temperature: [70, 120, 1],
    vehicle_speed: [0, 120, 0],
    engine_load: [0, 100, 1],
    throttle_position: [0, 100, 1],
    maf: [0, 30, 1],
    battery_voltage: [11, 15, 2],
    short_term_fuel_trim: [-25, 25, 1],
    long_term_fuel_trim: [-25, 25, 1],
  };

  // Histórico guardado no navegador enquanto a tela está aberta.
  const history = { labels: [], values: Object.fromEntries(Object.keys(CHART_RANGES).map((k) => [k, []])) };
  let scenarioNames = {};
  let chart = null;
  let failures = 0;

  function buildChart() {
    chart?.destroy();
    const key = select.value;
    const [suggestedMin, suggestedMax, decimals] = CHART_RANGES[key];
    const option = select.selectedOptions[0];
    chart = LiveCharts.create(
      canvas,
      { label: option.textContent, unit: option.dataset.unit, decimals, suggestedMin, suggestedMax },
      history.labels,
      history.values[key],
    );
  }

  function remember(time, sensors) {
    history.labels.push(time);
    for (const key of Object.keys(history.values)) history.values[key].push(sensors[key].value);
    if (history.labels.length > LiveCharts.MAX_POINTS) {
      history.labels.shift();
      for (const values of Object.values(history.values)) values.shift();
    }
  }

  function render(snap) {
    for (const tile of tiles) AutoScan.renderTile(tile, snap.sensors[tile.dataset.sensor]);

    const time = AutoScan.timeLabel(snap.timestamp);
    remember(time, snap.sensors);
    LiveCharts.push(chart, time, snap.sensors[select.value].value);

    for (const btn of modeButtons) btn.setAttribute("aria-pressed", String(btn.dataset.mode === snap.mode));
    const names = snap.active_scenarios.map((id) => scenarioNames[id] || id);
    document.getElementById("active-scenarios").textContent = names.length ? names.join(", ") : "nenhum";
    document.getElementById("fan-state").textContent = snap.fan.on ? "ligada" : "desligada";
    lastUpdate.textContent = `última leitura às ${time}`;
  }

  async function update() {
    try {
      render(await AutoScan.api.get("/api/sensors/live"));
      failures = 0;
    } catch (err) {
      failures += 1;
      lastUpdate.textContent = "sem resposta do servidor";
      if (failures === 1) AutoScan.notify(err.message, "crit");
    }
  }

  async function setMode(mode) {
    modeButtons.forEach((b) => (b.disabled = true));
    try {
      await AutoScan.api.post("/api/simulator/mode", { mode });
      poller.runNow(); // mostra o efeito sem esperar o próximo ciclo
    } catch (err) {
      AutoScan.notify(err.message, "crit");
    } finally {
      modeButtons.forEach((b) => (b.disabled = false));
    }
  }

  modeButtons.forEach((btn) => btn.addEventListener("click", () => setMode(btn.dataset.mode)));
  select.addEventListener("change", buildChart);

  buildChart();
  // Nomes dos cenários para exibir "Mistura pobre" em vez de "lean_mixture".
  AutoScan.api.get("/api/simulator/scenarios")
    .then((status) => { scenarioNames = Object.fromEntries(status.scenarios.map((s) => [s.id, s.name])); })
    .catch(() => {}); // sem os nomes, a tela mostra o identificador
  const poller = AutoScan.poll(update, 1000);
})();
