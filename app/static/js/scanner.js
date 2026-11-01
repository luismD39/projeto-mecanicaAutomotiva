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

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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
      DiagnosticView.render(resultBox, result).scrollIntoView({ behavior: "smooth", block: "start" });
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
