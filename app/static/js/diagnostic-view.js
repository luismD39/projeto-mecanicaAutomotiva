// Exibição de um diagnóstico salvo. Usada pelo Scanner (logo após a varredura) e pela tela Diagnósticos.
// Separa: códigos armazenados (DTC), condições observadas e hipóteses geradas por regras.
"use strict";

const DiagnosticView = (() => {
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function section(title, ...children) {
    const s = el("section", "card result-section");
    s.append(el("h3", null, title), ...children);
    return s;
  }

  function bulletList(items) {
    const ul = el("ul", "bullet-list");
    for (const item of items) ul.append(el("li", null, item));
    return ul;
  }

  function faultsSection(d) {
    let content;
    if (d.faults.length) {
      content = el("ul", "fault-list");
      for (const f of d.faults) {
        const li = el("li", "fault-item");
        const link = el("a", "fault-code", f.code);
        link.href = `/codigos-dtc?codigo=${encodeURIComponent(f.code)}`;
        link.setAttribute("aria-label", `${f.code}: ver no catálogo de códigos`);
        const text = el("div");
        text.append(el("strong", null, f.description), el("span", "muted", `${f.system} · ${f.evidence}`));
        li.append(link, text);
        content.append(li);
      }
    } else {
      content = el("p", "muted", "Nenhum código de falha armazenado na ECU simulada.");
    }
    return section("Códigos de falha armazenados (DTC)", content, el("p", "hint", d.dtc_note));
  }

  function conditionsSection(d) {
    let content;
    if (d.conditions.length) {
      content = el("ul", "alert-list");
      for (const c of d.conditions) {
        const li = el("li");
        li.append(AutoScan.statusBadge(c.status, c.status_label), el("span", null, c.message));
        content.append(li);
      }
    } else {
      content = el("p", "muted", "Todos os parâmetros dentro dos limites didáticos.");
    }
    return section("Condições observadas", content, el("p", "hint", d.thresholds_notice));
  }

  function findingCard(f) {
    const card = el("article", "finding");
    card.dataset.level = f.level;
    const head = el("div", "finding-head");
    head.append(AutoScan.badge(f.level, f.level_label), el("h4", null, f.title));
    card.append(head, el("p", "finding-rule", `Regra ${f.rule_id}`));
    for (const [title, items] of [["Evidências observadas", f.evidence], ["Hipóteses possíveis", f.hypotheses],
      ["Verificações recomendadas", f.checks]]) {
      const block = el("div", "detail-section");
      block.append(el("h5", null, title), bulletList(items));
      card.append(block);
    }
    return card;
  }

  function findingsSection(d) {
    const intro = el("p", "hint",
      "Cada resultado vem de uma regra explícita. As hipóteses indicam o que investigar; não confirmam defeito.");
    if (!d.findings.length) {
      return section("Análise por regras (hipóteses)", intro,
        el("p", "muted", "Nenhuma regra disparada: não há indícios de anormalidade nesta leitura."));
    }
    const grid = el("div", "grid grid--2 findings-grid");
    d.findings.forEach((f) => grid.append(findingCard(f)));
    return section("Análise por regras (hipóteses)", intro, grid, el("p", "hint", d.findings[0].disclaimer));
  }

  function readingsSection(d) {
    const table = el("table", "table");
    table.innerHTML = "<caption class='sr-only'>Parâmetros lidos na varredura</caption>" +
      "<thead><tr><th scope='col'>Parâmetro</th><th scope='col'>Valor</th><th scope='col'>Situação</th></tr></thead>";
    const tbody = el("tbody");
    for (const r of d.readings) {
      const status = el("td");
      if (r.status) status.append(AutoScan.statusBadge(r.status, r.status_label));
      const tr = el("tr");
      tr.append(
        el("td", "cell-name", r.display_name),
        el("td", null, r.value === null ? "Sem leitura" : `${AutoScan.formatReading(r)} ${r.unit}`),
        status,
      );
      tbody.append(tr);
    }
    table.append(tbody);
    const wrap = el("div", "table-wrap");
    wrap.append(table);
    return section("Parâmetros lidos", wrap);
  }

  // Desenha o diagnóstico `d` (resposta de /api/diagnostics/<id>) dentro de `container`.
  // Devolve o cabeçalho, para quem chamou poder rolar até ele.
  function render(container, d, { title = "Resultado da varredura" } = {}) {
    const when = new Date(d.completed_at).toLocaleString("pt-BR");
    const header = el("section", "card result-header");
    const top = el("div", "result-top");
    top.append(AutoScan.badge(d.status, d.status_label), el("h2", null, title));
    header.append(
      top,
      el("p", "result-summary", d.summary),
      el("p", "hint", `Diagnóstico nº ${d.diagnostic_id} · ${when} · ${d.vehicle.make} ${d.vehicle.model} ${d.vehicle.year} · ${d.notice}`),
    );

    const grid = el("div", "grid grid--2 result-grid");
    grid.append(faultsSection(d), conditionsSection(d));
    container.replaceChildren(header, grid, findingsSection(d), readingsSection(d));
    return header;
  }

  return { render };
})();
