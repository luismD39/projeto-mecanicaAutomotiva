// Histórico: lista diagnósticos salvos com filtros por veículo e período.
// Os filtros ficam na URL (?vehicle_id=1&from=2026-11-01) para a página poder ser recarregada.
"use strict";

(() => {
  const form = document.getElementById("filters");
  const listBox = document.getElementById("history-list");
  const countEl = document.getElementById("history-count");
  const FIELDS = ["vehicle_id", "from", "to"];

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function showErrors(errors) {
    for (const name of FIELDS) {
      const msg = document.getElementById(`f-${name}-error`);
      msg.textContent = errors[name] || "";
      msg.hidden = !errors[name];
      form.elements[name].setAttribute("aria-invalid", String(Boolean(errors[name])));
    }
  }

  function currentParams() {
    const params = new URLSearchParams();
    for (const name of FIELDS) {
      const value = form.elements[name].value;
      if (value) params.set(name, value);
    }
    return params;
  }

  function link(text, href, className, ariaLabel) {
    const a = el("a", className, text);
    a.href = href;
    if (ariaLabel) a.setAttribute("aria-label", ariaLabel);
    return a;
  }

  function render(items, filtered) {
    countEl.textContent = items.length === 1 ? "1 diagnóstico encontrado" : `${items.length} diagnósticos encontrados`;
    if (!items.length) {
      AutoScan.showState(listBox, "empty",
        filtered ? "Nenhum diagnóstico com esses filtros" : "Nenhum diagnóstico salvo",
        filtered ? { detail: "Altere ou limpe os filtros." }
          : { detail: "Faça uma varredura no Scanner para começar o histórico." });
      return;
    }
    const table = el("table", "table");
    table.innerHTML = "<caption class='sr-only'>Diagnósticos salvos</caption><thead><tr>" +
      "<th scope='col'>Nº</th><th scope='col'>Data e hora</th><th scope='col'>Veículo</th>" +
      "<th scope='col'>DTCs</th><th scope='col'>Situação</th><th scope='col'>Ações</th></tr></thead>";
    const tbody = el("tbody");
    for (const d of items) {
      const vehicle = `${d.vehicle.make} ${d.vehicle.model} ${d.vehicle.year}`;
      const status = el("td", "cell-name");
      const summary = el("span", "muted history-summary", d.summary);
      status.append(AutoScan.badge(d.status, d.status_label), summary);
      const actions = el("div", "row-actions");
      actions.append(
        link("Abrir", `/diagnosticos?id=${d.diagnostic_id}`, "btn btn--secondary btn--sm", `Abrir diagnóstico nº ${d.diagnostic_id}`),
        link("PDF", `/api/reports/${d.diagnostic_id}/pdf`, "btn btn--secondary btn--sm", `Baixar PDF do diagnóstico nº ${d.diagnostic_id}`),
      );
      const tr = el("tr");
      const actionsCell = el("td");
      actionsCell.append(actions);
      tr.append(
        el("td", null, String(d.diagnostic_id)),
        el("td", null, new Date(d.completed_at).toLocaleString("pt-BR")),
        el("td", "cell-name", vehicle),
        el("td", null, String(d.dtc_count)),
        status,
        actionsCell,
      );
      tbody.append(tr);
    }
    table.append(tbody);
    const wrap = el("div", "table-wrap");
    wrap.append(table);
    listBox.replaceChildren(wrap);
  }

  async function load() {
    const params = currentParams();
    const f = form.elements;
    if (f.from.value && f.to.value && f.from.value > f.to.value) {
      showErrors({ to: "A data final deve ser igual ou posterior à data inicial." });
      return;
    }
    showErrors({});
    history.replaceState(null, "", params.size ? `?${params}` : location.pathname);
    AutoScan.showState(listBox, "loading", "Carregando histórico...");
    countEl.textContent = "";
    try {
      const data = await AutoScan.api.get(`/api/diagnostics?${params}`);
      render(data.diagnostics, params.size > 0);
    } catch (err) {
      if (err.fields) showErrors(err.fields);
      AutoScan.showState(listBox, "error", "Não foi possível carregar o histórico", {
        detail: err.message, actionLabel: "Tentar novamente", onAction: load,
      });
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    load();
  });
  document.getElementById("clear-filters").addEventListener("click", () => {
    form.reset();
    load();
  });

  // Filtros vindos da URL
  const fromUrl = new URLSearchParams(location.search);
  for (const name of FIELDS) {
    if (fromUrl.has(name)) form.elements[name].value = fromUrl.get(name);
  }
  load();
})();
