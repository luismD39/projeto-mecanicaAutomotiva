// Scanner: anima as etapas enquanto o backend faz a varredura e depois mostra o resultado.
// A animação é só visual; o resultado vem inteiro do servidor.
"use strict";

(() => {
  const STEP_MS = 600;
  const button = document.getElementById("scan-btn");
  const stepsList = document.getElementById("scan-steps");
  const steps = [...stepsList.querySelectorAll(".scan-step")];
  const announcer = document.getElementById("scan-announcer");
  const resultBox = document.getElementById("scan-result");
  const STATE_TEXT = { pending: "Aguardando", active: "Em andamento", done: "Concluído", failed: "Falhou" };
  const BADGE = { ok: "ok", warn: "warn", crit: "crit" };

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function setStep(i, state) {
    steps[i].dataset.state = state;
    steps[i].querySelector(".scan-step-state").textContent = STATE_TEXT[state];
    if (state === "active") {
      announcer.textContent = `Etapa ${i + 1} de ${steps.length}: ${steps[i].querySelector(".scan-step-text").textContent}`;
    }
  }

  // Avança as etapas até a penúltima; a última só fecha quando o servidor responder.
  async function animate(abort) {
    for (let i = 0; i < steps.length - 1; i++) {
      if (abort.failed) return;
      setStep(i, "active");
      await sleep(STEP_MS);
      if (abort.failed) return;
      setStep(i, "done");
    }
    if (!abort.failed) setStep(steps.length - 1, "active");
  }

  function section(title, ...children) {
    const s = el("section", "card result-section");
    s.append(el("h3", null, title), ...children);
    return s;
  }

  function renderResult(d) {
    const when = new Date(d.completed_at).toLocaleString("pt-BR");

    const header = el("section", "card result-header");
    const top = el("div", "result-top");
    top.append(AutoScan.badge(BADGE[d.status] || "info", d.status_label), el("h2", null, "Resultado da varredura"));
    header.append(
      top,
      el("p", "result-summary", d.summary),
      el("p", "hint", `Diagnóstico nº ${d.diagnostic_id} · ${when} · ${d.vehicle.make} ${d.vehicle.model} ${d.vehicle.year} · ${d.notice}`),
    );

    // Códigos de falha armazenados
    let faultsContent;
    if (d.faults.length) {
      faultsContent = el("ul", "fault-list");
      for (const f of d.faults) {
        const li = el("li", "fault-item");
        const link = el("a", "fault-code", f.code);
        link.href = `/codigos-dtc?codigo=${encodeURIComponent(f.code)}`;
        link.setAttribute("aria-label", `${f.code}: ver no catálogo de códigos`);
        const text = el("div");
        text.append(el("strong", null, f.description), el("span", "muted", `${f.system} · ${f.evidence}`));
        li.append(link, text);
        faultsContent.append(li);
      }
    } else {
      faultsContent = el("p", "muted", "Nenhum código de falha armazenado na ECU simulada.");
    }
    const faultsNote = el("p", "hint", d.dtc_note);

    // Condições observadas nos sensores (não são códigos de falha)
    let condContent;
    if (d.conditions.length) {
      condContent = el("ul", "alert-list");
      for (const c of d.conditions) {
        const li = el("li");
        li.append(AutoScan.statusBadge(c.status, c.status_label), el("span", null, c.message));
        condContent.append(li);
      }
    } else {
      condContent = el("p", "muted", "Todos os parâmetros dentro dos limites didáticos.");
    }

    // Tabela de parâmetros lidos
    const table = el("table", "table");
    table.innerHTML = "<caption class='sr-only'>Parâmetros lidos na varredura</caption>" +
      "<thead><tr><th scope='col'>Parâmetro</th><th scope='col'>Valor</th><th scope='col'>Situação</th></tr></thead>";
    const tbody = el("tbody");
    for (const r of d.readings) {
      const tr = el("tr");
      const name = el("td", "cell-name", r.display_name);
      const value = el("td", null, r.value === null ? "Sem leitura" : `${AutoScan.formatReading(r)} ${r.unit}`);
      const status = el("td");
      if (r.status) status.append(AutoScan.statusBadge(r.status, r.status_label));
      tr.append(name, value, status);
      tbody.append(tr);
    }
    table.append(tbody);
    const wrap = el("div", "table-wrap");
    wrap.append(table);

    const grid = el("div", "grid grid--2 result-grid");
    grid.append(
      section("Códigos de falha armazenados (DTC)", faultsContent, faultsNote),
      section("Condições observadas", condContent, el("p", "hint", d.thresholds_notice)),
    );
    resultBox.replaceChildren(header, grid, section("Parâmetros lidos", wrap));
    header.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function scan() {
    button.disabled = true;
    resultBox.replaceChildren();
    stepsList.hidden = false;
    steps.forEach((_, i) => setStep(i, "pending"));
    const abort = { failed: false };

    try {
      const [result] = await Promise.all([AutoScan.api.post("/api/scanner/start"), animate(abort)]);
      setStep(steps.length - 1, "done");
      announcer.textContent = "Varredura concluída.";
      renderResult(result);
      AutoScan.setActiveVehicleName(result.vehicle);
    } catch (err) {
      abort.failed = true;
      const current = steps.findIndex((s) => s.dataset.state === "active");
      setStep(current === -1 ? 0 : current, "failed");
      announcer.textContent = "A varredura falhou.";
      AutoScan.showState(resultBox, "error", "A varredura não foi concluída", { detail: err.message });
    } finally {
      button.disabled = false;
      button.lastChild.textContent = "Nova varredura";
    }
  }

  button.addEventListener("click", scan);
})();
