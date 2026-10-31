// Dashboard: cartão de status do sistema (consulta /api/health).
"use strict";

(() => {
  const box = document.getElementById("system-status");

  function row(label, value) {
    const div = document.createElement("div");
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    if (value instanceof Node) dd.append(value);
    else dd.textContent = value;
    div.append(dt, dd);
    return div;
  }

  async function load() {
    AutoScan.showState(box, "loading", "Verificando o sistema...");
    try {
      const data = await AutoScan.api.get("/api/health");
      const dl = document.createElement("dl");
      dl.className = "data-list";
      dl.append(
        row("Servidor", AutoScan.badge("ok", "Funcionando")),
        row("Banco de dados", AutoScan.badge("ok", "Conectado")),
        row("Origem dos dados", "Simulação"),
        row("Versão", data.version),
      );
      box.replaceChildren(dl);
    } catch (err) {
      AutoScan.showState(box, "error", "Não foi possível verificar o sistema", {
        detail: err.message,
        actionLabel: "Tentar novamente",
        onAction: load,
      });
    }
  }

  load();
})();
