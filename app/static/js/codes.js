// Catálogo de códigos DTC: busca com atraso curto enquanto digita e painel de detalhe.
// Aceita ?codigo=P0301 na URL para abrir um código direto (link vindo do Scanner).
"use strict";

(() => {
  const input = document.getElementById("q");
  const listBox = document.getElementById("code-list");
  const countEl = document.getElementById("result-count");
  const detailBox = document.getElementById("code-detail");
  let selected = new URLSearchParams(location.search).get("codigo")?.toUpperCase() || null;
  let searchTimer = null;
  let searchSeq = 0;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderList(codes) {
    countEl.textContent = codes.length === 1 ? "1 código encontrado" : `${codes.length} códigos encontrados`;
    if (!codes.length) {
      AutoScan.showState(listBox, "empty", "Nenhum código encontrado", {
        detail: "Tente outro código ou outra palavra.",
      });
      return;
    }
    const ul = el("ul", "code-list");
    for (const c of codes) {
      const btn = el("button", "code-item");
      btn.type = "button";
      btn.dataset.code = c.code;
      btn.setAttribute("aria-current", String(c.code === selected));
      btn.append(el("strong", "code-item-code", c.code), el("span", "code-item-desc", c.description));
      const li = el("li");
      li.append(btn);
      ul.append(li);
    }
    listBox.replaceChildren(ul);
  }

  async function runSearch() {
    const seq = ++searchSeq; // ignora respostas de buscas antigas que chegarem atrasadas
    try {
      const data = await AutoScan.api.get(`/api/fault-codes?q=${encodeURIComponent(input.value.trim())}`);
      if (seq === searchSeq) renderList(data.fault_codes);
    } catch (err) {
      if (seq !== searchSeq) return;
      countEl.textContent = "";
      AutoScan.showState(listBox, "error", "Não foi possível buscar", {
        detail: err.message, actionLabel: "Tentar novamente", onAction: runSearch,
      });
    }
  }

  function section(title, items) {
    const wrap = el("div", "detail-section");
    wrap.append(el("h4", null, title));
    const ul = el("ul", "bullet-list");
    for (const item of items) ul.append(el("li", null, item));
    wrap.append(ul);
    return wrap;
  }

  async function showDetail(code) {
    selected = code;
    history.replaceState(null, "", `?codigo=${encodeURIComponent(code)}`);
    for (const btn of listBox.querySelectorAll(".code-item")) {
      btn.setAttribute("aria-current", String(btn.dataset.code === code));
    }
    AutoScan.showState(detailBox, "loading", "Carregando código...");
    try {
      const c = await AutoScan.api.get(`/api/fault-codes/${encodeURIComponent(code)}`);
      const header = el("div", "detail-header");
      header.append(el("h3", "detail-code", c.code), AutoScan.badge("info", c.system));
      const note = el("div", "notice notice--compact");
      note.setAttribute("role", "note");
      note.append(el("p", null, c.note));
      detailBox.replaceChildren(
        header,
        el("p", "detail-title", c.description),
        el("p", null, c.explanation),
        section("Possíveis causas", c.causes),
        section("Sintomas comuns", c.symptoms),
        section("Verificações recomendadas", c.checks),
        note,
      );
      if (window.matchMedia("(max-width: 1100px)").matches) {
        document.getElementById("detail-card").scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (err) {
      AutoScan.showState(detailBox, "error", err.status === 404 ? "Código não encontrado" : "Não foi possível abrir o código", {
        detail: err.message,
      });
    }
  }

  input.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(runSearch, 250);
  });
  listBox.addEventListener("click", (e) => {
    const btn = e.target.closest(".code-item");
    if (btn) showDetail(btn.dataset.code);
  });

  AutoScan.showState(listBox, "loading", "Carregando catálogo...");
  runSearch();
  if (selected) showDetail(selected);
})();
