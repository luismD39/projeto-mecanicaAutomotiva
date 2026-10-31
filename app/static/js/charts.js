// Gráficos de linha dos sensores (Chart.js, arquivo local em static/vendor).
// Uma série por gráfico: grandezas diferentes ficam em gráficos separados, sem dois eixos Y.
"use strict";

const LiveCharts = (() => {
  const MAX_POINTS = 60; // 60 leituras = ~1 minuto com atualização a cada 1 s
  const SERIES_COLOR = "#0EA5E9";
  const GRID_COLOR = "rgba(55, 65, 81, 0.6)";

  Chart.defaults.color = "#9CA3AF";
  Chart.defaults.font.family = getComputedStyle(document.documentElement).fontFamily;

  // `labels`/`values` permitem começar já com o histórico guardado pela página.
  function create(canvas, { label, unit, decimals = 0, suggestedMin, suggestedMax }, labels = [], values = []) {
    return new Chart(canvas, {
      type: "line",
      data: {
        labels: [...labels],
        datasets: [{
          label,
          data: [...values],
          borderColor: SERIES_COLOR,
          backgroundColor: SERIES_COLOR,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverBorderColor: "#1F2937",
          pointHoverBorderWidth: 2,
          tension: 0.25,
          spanGaps: false, // leitura inválida aparece como falha na linha
        }],
      },
      options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false }, // uma série só: o título do cartão já diz o que é
          tooltip: {
            displayColors: false,
            callbacks: {
              label: (ctx) => (ctx.parsed.y === null ? "Sem leitura" : `${AutoScan.formatNumber(ctx.parsed.y, decimals)} ${unit}`),
            },
          },
        },
        scales: {
          x: { ticks: { maxTicksLimit: 6, maxRotation: 0 }, grid: { display: false } },
          y: {
            suggestedMin,
            suggestedMax,
            title: { display: true, text: unit },
            grid: { color: GRID_COLOR },
            border: { display: false },
            ticks: { callback: (v) => AutoScan.formatNumber(v, 0) },
          },
        },
      },
    });
  }

  function push(chart, label, value) {
    const { labels } = chart.data;
    const { data } = chart.data.datasets[0];
    labels.push(label);
    data.push(value);
    if (labels.length > MAX_POINTS) {
      labels.shift();
      data.shift();
    }
    chart.update();
  }

  return { create, push, MAX_POINTS };
})();
