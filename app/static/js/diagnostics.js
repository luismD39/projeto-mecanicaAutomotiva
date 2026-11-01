// Tela Diagnósticos: carrega um diagnóstico salvo e o exibe com DiagnosticView.
"use strict";

(() => {
  const box = document.getElementById("diagnostic");
  const id = box.dataset.id;

  async function load() {
    AutoScan.showState(box, "loading", "Carregando diagnóstico...");
    try {
      const d = await AutoScan.api.get(`/api/diagnostics/${encodeURIComponent(id)}`);
      DiagnosticView.render(box, d, { title: `Diagnóstico nº ${d.diagnostic_id}` });
    } catch (err) {
      if (err.status === 404) {
        AutoScan.showState(box, "error", "Diagnóstico não encontrado", {
          detail: "Confira o número do diagnóstico ou abra a tela sem número para ver o mais recente.",
        });
      } else {
        AutoScan.showState(box, "error", "Não foi possível carregar o diagnóstico", {
          detail: err.message, actionLabel: "Tentar novamente", onAction: load,
        });
      }
    }
  }

  load();
})();
