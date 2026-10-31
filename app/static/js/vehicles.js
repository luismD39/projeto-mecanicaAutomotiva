// Tela Veículos: cadastro, edição, ativação e exclusão.
"use strict";

(() => {
  const form = document.getElementById("vehicle-form");
  const formTitle = document.getElementById("form-title");
  const submitBtn = document.getElementById("submit-btn");
  const cancelBtn = document.getElementById("cancel-edit");
  const listBox = document.getElementById("vehicle-list");
  const dialog = document.getElementById("delete-dialog");
  const FIELDS = ["make", "model", "year", "mileage_km", "engine", "fuel_type"];

  let vehicles = [];
  let editingId = null;
  let deletingId = null;

  const vehicleName = (v) => `${v.make} ${v.model} ${v.year}`;
  const formatKm = (km) => `${Math.round(km).toLocaleString("pt-BR")} km`;

  // ---------- Formulário ----------

  function readForm() {
    const f = form.elements;
    return {
      make: f.make.value.trim(),
      model: f.model.value.trim(),
      year: f.year.value === "" ? null : Number(f.year.value),
      mileage_km: f.mileage_km.value === "" ? 0 : Number(f.mileage_km.value),
      engine: f.engine.value.trim() || null,
      fuel_type: f.fuel_type.value,
    };
  }

  // Mesmas regras do backend (app/services/vehicles.py); o backend valida de novo.
  function validate(data) {
    const f = form.elements;
    const yearMin = Number(f.year.min);
    const yearMax = Number(f.year.max);
    const errors = {};
    if (!data.make) errors.make = "Informe o fabricante/marca.";
    if (!data.model) errors.model = "Informe o modelo.";
    if (!Number.isInteger(data.year) || data.year < yearMin || data.year > yearMax) {
      errors.year = `Informe um ano entre ${yearMin} e ${yearMax}.`;
    }
    if (!Number.isFinite(data.mileage_km) || data.mileage_km < 0 || data.mileage_km > Number(f.mileage_km.max)) {
      errors.mileage_km = "Informe uma quilometragem entre 0 e 2.000.000 km.";
    }
    if (!data.fuel_type) errors.fuel_type = "Escolha um tipo de combustível da lista.";
    return errors;
  }

  function showErrors(errors) {
    let first = null;
    for (const name of FIELDS) {
      const input = form.elements[name];
      const msg = document.getElementById(`f-${name}-error`);
      const text = errors[name] || "";
      msg.textContent = text;
      msg.hidden = !text;
      input.setAttribute("aria-invalid", String(Boolean(text)));
      if (text && !first) first = input;
    }
    first?.focus();
  }

  function resetForm() {
    form.reset();
    showErrors({});
    editingId = null;
    formTitle.textContent = "Cadastrar veículo";
    submitBtn.textContent = "Cadastrar veículo";
    cancelBtn.hidden = true;
  }

  function startEdit(vehicle) {
    resetForm();
    editingId = vehicle.id;
    const f = form.elements;
    f.make.value = vehicle.make;
    f.model.value = vehicle.model;
    f.year.value = vehicle.year;
    f.mileage_km.value = Math.round(vehicle.mileage_km);
    f.engine.value = vehicle.engine || "";
    f.fuel_type.value = vehicle.fuel_type;
    formTitle.textContent = `Editar ${vehicleName(vehicle)}`;
    submitBtn.textContent = "Salvar alterações";
    cancelBtn.hidden = false;
    form.scrollIntoView({ behavior: "smooth", block: "start" });
    f.make.focus({ preventScroll: true });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = readForm();
    const errors = validate(data);
    showErrors(errors);
    if (Object.keys(errors).length) return;

    submitBtn.disabled = true;
    try {
      if (editingId) {
        await AutoScan.api.put(`/api/vehicles/${editingId}`, data);
        AutoScan.notify("Alterações salvas.", "ok");
      } else {
        const created = await AutoScan.api.post("/api/vehicles", data);
        AutoScan.notify(
          created.is_active ? `${vehicleName(created)} cadastrado e definido como ativo.` : `${vehicleName(created)} cadastrado.`,
          "ok",
        );
      }
      resetForm();
      await loadList();
    } catch (err) {
      if (err.fields) showErrors(err.fields);
      AutoScan.notify(err.message, "crit");
    } finally {
      submitBtn.disabled = false;
    }
  });

  cancelBtn.addEventListener("click", resetForm);

  // ---------- Lista ----------

  function button(label, action, id, ariaLabel, kind = "secondary") {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `btn btn--${kind} btn--sm`;
    btn.textContent = label;
    btn.dataset.action = action;
    btn.dataset.id = id;
    btn.setAttribute("aria-label", ariaLabel);
    return btn;
  }

  function cell(content, className) {
    const td = document.createElement("td");
    if (className) td.className = className;
    td.append(content);
    return td;
  }

  function renderList() {
    if (!vehicles.length) {
      AutoScan.showState(listBox, "empty", "Nenhum veículo cadastrado", {
        detail: "Use o formulário para cadastrar o primeiro veículo fictício.",
      });
      return;
    }

    const table = document.createElement("table");
    table.className = "table";
    table.innerHTML =
      "<thead><tr><th scope='col'>Veículo</th><th scope='col'>Quilometragem</th>" +
      "<th scope='col'>Situação</th><th scope='col'>Ações</th></tr></thead>";
    const tbody = document.createElement("tbody");

    for (const v of vehicles) {
      const tr = document.createElement("tr");
      if (v.is_active) tr.className = "is-active";

      const name = document.createElement("div");
      const strong = document.createElement("strong");
      strong.textContent = `${v.make} ${v.model}`;
      const small = document.createElement("span");
      small.className = "muted";
      small.textContent = [v.year, v.engine || "motor não informado", v.fuel_label].join(" · ");
      name.append(strong, small);

      const status = v.is_active ? AutoScan.badge("ok", "Ativo") : document.createTextNode("Inativo");

      const actions = document.createElement("div");
      actions.className = "row-actions";
      if (!v.is_active) actions.append(button("Ativar", "activate", v.id, `Ativar ${vehicleName(v)}`, "primary"));
      actions.append(
        button("Editar", "edit", v.id, `Editar ${vehicleName(v)}`),
        button("Excluir", "delete", v.id, `Excluir ${vehicleName(v)}`, "danger-outline"),
      );

      tr.append(
        cell(name, "cell-name"),
        cell(formatKm(v.mileage_km)),
        cell(status),
        cell(actions),
      );
      tbody.append(tr);
    }
    table.append(tbody);

    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    wrap.append(table);
    listBox.replaceChildren(wrap);
  }

  async function loadList() {
    if (!vehicles.length) AutoScan.showState(listBox, "loading", "Carregando veículos...");
    try {
      vehicles = (await AutoScan.api.get("/api/vehicles")).vehicles;
      renderList();
      AutoScan.setActiveVehicleName(vehicles.find((v) => v.is_active));
    } catch (err) {
      AutoScan.showState(listBox, "error", "Não foi possível carregar os veículos", {
        detail: err.message,
        actionLabel: "Tentar novamente",
        onAction: loadList,
      });
    }
  }

  listBox.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    const vehicle = vehicles.find((v) => v.id === Number(btn.dataset.id));
    if (!vehicle) return;

    if (btn.dataset.action === "edit") startEdit(vehicle);

    if (btn.dataset.action === "activate") {
      btn.disabled = true;
      try {
        await AutoScan.api.post(`/api/vehicles/${vehicle.id}/activate`);
        AutoScan.notify(`${vehicleName(vehicle)} agora é o veículo ativo.`, "ok");
        await loadList();
      } catch (err) {
        AutoScan.notify(err.message, "crit");
        btn.disabled = false;
      }
    }

    if (btn.dataset.action === "delete") {
      deletingId = vehicle.id;
      document.getElementById("delete-text").textContent =
        `${vehicleName(vehicle)} será removido permanentemente. Esta ação não pode ser desfeita.`;
      dialog.showModal();
    }
  });

  // ---------- Exclusão ----------

  document.getElementById("delete-cancel").addEventListener("click", () => dialog.close());

  document.getElementById("delete-confirm").addEventListener("click", async (e) => {
    const confirmBtn = e.currentTarget;
    confirmBtn.disabled = true;
    try {
      await AutoScan.api.delete(`/api/vehicles/${deletingId}`);
      AutoScan.notify("Veículo excluído.", "ok");
      if (editingId === deletingId) resetForm();
      await loadList();
    } catch (err) {
      AutoScan.notify(err.message, "crit");
    } finally {
      confirmBtn.disabled = false;
      dialog.close();
    }
  });

  loadList();
})();
