// AutoScan Pro | funções compartilhadas por todas as páginas.
"use strict";

const AutoScan = (() => {
  class ApiError extends Error {
    constructor(message, code, status, fields = null) {
      super(message);
      this.code = code;
      this.status = status;
      this.fields = fields; // mensagens por campo de formulário, quando houver
    }
  }

  // Chama a API e devolve o JSON. Em caso de erro, lança ApiError com mensagem em português.
  async function request(path, options = {}) {
    let resp;
    try {
      resp = await fetch(path, {
        ...options,
        headers: { "Content-Type": "application/json", ...options.headers },
      });
    } catch {
      throw new ApiError(
        "Não foi possível conectar ao servidor. Verifique se o AutoScan Pro está em execução.",
        "NETWORK_ERROR",
        0,
      );
    }
    const data = await resp.json().catch(() => null);
    if (!resp.ok) {
      const err = data && data.error;
      throw new ApiError(
        err?.message || `Erro ${resp.status} no servidor.`,
        err?.code || "HTTP_ERROR",
        resp.status,
        err?.fields || null,
      );
    }
    return data;
  }

  const api = {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body: JSON.stringify(body ?? {}) }),
    put: (path, body) => request(path, { method: "PUT", body: JSON.stringify(body ?? {}) }),
    delete: (path) => request(path, { method: "DELETE" }),
  };

  // Mostra um estado (loading | empty | error) dentro de `container`,
  // usando os modelos <template> renderizados em base.html.
  function showState(container, kind, message, { detail, actionLabel, onAction } = {}) {
    const node = document.getElementById(`tpl-state-${kind}`).content.firstElementChild.cloneNode(true);
    node.querySelector(".state-message").textContent = message;
    const detailEl = node.querySelector(".state-detail");
    if (detail) {
      detailEl.textContent = detail;
      detailEl.hidden = false;
    }
    if (actionLabel && onAction) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn--secondary";
      btn.textContent = actionLabel;
      btn.addEventListener("click", onAction);
      node.append(btn);
    }
    container.replaceChildren(node);
  }

  // Cria um badge (ok | warn | crit | info) com ícone e texto.
  function badge(kind, text) {
    const node = document.getElementById(`tpl-badge-${kind}`).content.firstElementChild.cloneNode(true);
    node.querySelector(".badge-text").textContent = text;
    return node;
  }

  // Mensagem rápida no canto da tela (kind: ok | warn | crit | info). Some sozinha.
  function notify(message, kind = "ok") {
    const toast = document.createElement("div");
    toast.className = `toast toast--${kind}`;
    toast.append(document.getElementById(`tpl-badge-${kind}`).content.querySelector("svg").cloneNode(true));
    const text = document.createElement("p");
    text.textContent = message;
    toast.append(text);
    document.getElementById("toast-region").append(toast);
    setTimeout(() => toast.remove(), kind === "crit" ? 8000 : 4000);
  }

  // Atualiza o nome do veículo ativo no cabeçalho sem recarregar a página.
  function setActiveVehicleName(vehicle) {
    document.getElementById("topbar-vehicle-name").textContent = vehicle
      ? `${vehicle.make} ${vehicle.model} ${vehicle.year}`
      : "Nenhum veículo ativo";
  }

  // Executa `task` a cada `intervalMs`, sem sobrepor pedidos: o próximo só é agendado
  // depois que o anterior termina. Pausa com a aba escondida e para ao sair da página.
  function poll(task, intervalMs = 1000) {
    let timer = null;
    let running = false;
    let stopped = false;

    async function tick() {
      timer = null;
      if (stopped || document.hidden || running) return;
      running = true;
      try {
        await task();
      } finally {
        running = false;
      }
      if (!stopped && !document.hidden) timer = setTimeout(tick, intervalMs);
    }

    function runNow() {
      clearTimeout(timer);
      tick();
    }

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        clearTimeout(timer);
        timer = null;
      } else if (!running && timer === null) {
        tick();
      }
    });
    const stop = () => {
      stopped = true;
      clearTimeout(timer);
    };
    window.addEventListener("pagehide", stop);

    tick();
    return { runNow, stop };
  }

  // ---------- Leituras de sensores ----------

  const DECIMALS = { rpm: 0, "km/h": 0, V: 2 };
  const STATUS_BADGE = { normal: "ok", warn: "warn", crit: "crit", invalid: "warn" };

  function formatNumber(value, decimals = 1) {
    return value.toLocaleString("pt-BR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  function formatReading(reading) {
    if (reading.value === null) return "—";
    return formatNumber(reading.value, DECIMALS[reading.unit] ?? 1);
  }

  function statusBadge(status, label) {
    return badge(STATUS_BADGE[status] || "info", label);
  }

  // Preenche um cartão .kpi (ver _components.html: kpi_tile) com uma leitura.
  function renderTile(tile, reading) {
    tile.dataset.status = reading.status;
    tile.querySelector(".kpi-number").textContent = formatReading(reading);
    tile.querySelector(".kpi-status").replaceChildren(statusBadge(reading.status, reading.status_label));
    tile.querySelector(".kpi-note").textContent = reading.status_note || "";
  }

  function timeLabel(isoTimestamp) {
    return new Date(isoTimestamp).toLocaleTimeString("pt-BR");
  }

  // Menu lateral em telas pequenas.
  function setupMenu() {
    const toggle = document.querySelector(".menu-toggle");
    const sidebar = document.getElementById("sidebar");
    if (!toggle || !sidebar) return;

    const setOpen = (open) => {
      sidebar.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      toggle.querySelector(".sr-only").textContent = open ? "Fechar menu de navegação" : "Abrir menu de navegação";
      if (open) sidebar.querySelector(".nav-link")?.focus();
    };

    toggle.addEventListener("click", () => setOpen(!sidebar.classList.contains("is-open")));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && sidebar.classList.contains("is-open")) {
        setOpen(false);
        toggle.focus();
      }
    });
    document.addEventListener("click", (e) => {
      if (sidebar.classList.contains("is-open") && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
        setOpen(false);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", setupMenu);

  return {
    api, ApiError, showState, badge, notify, setActiveVehicleName,
    poll, formatNumber, formatReading, statusBadge, renderTile, timeLabel,
  };
})();
