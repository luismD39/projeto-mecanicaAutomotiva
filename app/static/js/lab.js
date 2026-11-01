// Laboratório de falhas: ativa/desativa cenários da ECU simulada e mostra o efeito ao vivo.
// O estado vem sempre do servidor (outra aba pode ter mudado os cenários).
"use strict";

(() => {
  const cards = [...document.querySelectorAll(".scenario")];
  const tiles = [...document.querySelectorAll(".kpi[data-sensor]")];
  const resetBtn = document.getElementById("reset-btn");
  const activeList = document.getElementById("active-list");
  const nameOf = Object.fromEntries(cards.map((c) => [c.dataset.scenario, c.querySelector("h3").textContent]));
  let lastActiveKey = null;
  let busy = false;

  // Atualiza cartões e resumo a partir da lista de cenários ativos.
  function renderActive(activeIds) {
    const key = [...activeIds].sort().join(",");
    if (key === lastActiveKey) return; // evita repetir anúncios no leitor de tela
    lastActiveKey = key;
    const active = new Set(activeIds);

    for (const card of cards) {
      const id = card.dataset.scenario;
      const isActive = active.has(id);
      const name = nameOf[id];
      const blockedBy = card.dataset.conflicts.split(",").filter((c) => c && active.has(c));
      const button = card.querySelector(".scenario-toggle");

      card.dataset.active = String(isActive);
      card.querySelector(".scenario-status").replaceChildren(
        isActive ? AutoScan.badge("warn", "Ativo") : Object.assign(document.createElement("span"), { className: "muted", textContent: "Inativo" }),
      );
      button.textContent = isActive ? "Desativar" : "Ativar";
      button.setAttribute("aria-label", `${isActive ? "Desativar" : "Ativar"} ${name}`);
      button.className = `btn ${isActive ? "btn--secondary" : "btn--primary"} scenario-toggle`;
      button.disabled = !isActive && blockedBy.length > 0;
      for (const note of card.querySelectorAll(".scenario-conflict")) {
        note.hidden = !(button.disabled && blockedBy.includes(note.dataset.conflictWith));
      }
    }
    activeList.textContent = activeIds.length
      ? activeIds.map((id) => nameOf[id]).join(", ")
      : "Nenhum: a ECU simulada está em condições normais.";
  }

  async function update() {
    try {
      const snap = await AutoScan.api.get("/api/sensors/live");
      for (const tile of tiles) AutoScan.renderTile(tile, snap.sensors[tile.dataset.sensor]);
      document.getElementById("fan-state").textContent = snap.fan.on ? "ligada" : "desligada";
      document.getElementById("mode-label").textContent = snap.mode_label;
      if (!busy) renderActive(snap.active_scenarios);
    } catch {
      document.getElementById("fan-state").textContent = "sem resposta do servidor";
    }
  }

  async function send(path, okMessage) {
    busy = true;
    try {
      const status = await AutoScan.api.post(path);
      renderActive(status.scenarios.filter((s) => s.active).map((s) => s.id));
      AutoScan.notify(okMessage, "ok");
      poller.runNow();
    } catch (err) {
      AutoScan.notify(err.message, err.status === 409 ? "warn" : "crit");
      lastActiveKey = null; // força redesenhar com o estado real na próxima leitura
      poller.runNow();
    } finally {
      busy = false;
    }
  }

  for (const card of cards) {
    const button = card.querySelector(".scenario-toggle");
    button.addEventListener("click", () => {
      const id = card.dataset.scenario;
      const activate = card.dataset.active !== "true";
      button.disabled = true;
      send(`/api/simulator/scenarios/${id}/${activate ? "activate" : "deactivate"}`,
        `${nameOf[id]} ${activate ? "ativado" : "desativado"}.`);
    });
  }

  resetBtn.addEventListener("click", () => send("/api/simulator/reset", "Condições normais restauradas."));

  // Estado inicial: o que o servidor desenhou (aplica também os bloqueios por conflito).
  renderActive(cards.filter((c) => c.dataset.active === "true").map((c) => c.dataset.scenario));
  const poller = AutoScan.poll(update, 1000);
})();
