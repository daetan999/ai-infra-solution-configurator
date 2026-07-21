"use strict";

const API_ROOT = "/api/scenarios";

const stageCopy = {
  1: ["Stage 1 of 5", "Define the customer intent", "Start with the workload and the operating mode the platform must support."],
  2: ["Stage 2 of 5", "Set measurable service targets", "Capture the demand, performance, resilience, and growth signals that shape capacity."],
  3: ["Stage 3 of 5", "Draw the placement boundaries", "Make data location, platform inheritance, and hybrid constraints explicit."],
  4: ["Stage 4 of 5", "Design for the operating reality", "Describe the security posture, telemetry maturity, and team that will run the solution."],
  5: ["Stage 5 of 5", "Commit the commercial constraints", "Review the discovery evidence before generating a deterministic solution hypothesis."],
};

const numericFields = new Set([
  "model_size_billion",
  "latency_target_ms",
  "throughput_target_rps",
  "data_volume_tb",
  "availability_target_pct",
  "recovery_objective_hours",
  "timeline_weeks",
  "annual_growth_pct",
]);

const summaryFields = [
  ["Workload", "workload_type"],
  ["Lifecycle", "lifecycle_mode"],
  ["Model scale", "model_size_billion", "B parameters"],
  ["Latency", "latency_target_ms", "ms p95"],
  ["Throughput", "throughput_target_rps", "requests/s"],
  ["Data", "data_volume_tb", "TB"],
  ["Placement", "cloud_preference"],
  ["Sensitivity", "data_sensitivity"],
  ["Availability", "availability_target_pct", "%"],
  ["Timeline", "timeline_weeks", "weeks"],
  ["Growth", "annual_growth_pct", "% / year"],
  ["Operating model", "team_operating_model"],
];

const state = {
  stage: 1,
  scenarios: [],
  activeScenarioId: null,
  activeScenario: null,
  activeRun: null,
  dirty: false,
  controllers: new Map(),
  toastTimer: null,
};

const elements = {
  form: document.querySelector("#configurator-form"),
  scenarioRail: document.querySelector("#scenario-rail"),
  scenarioCount: document.querySelector("#scenario-count"),
  previous: document.querySelector("#previous-stage"),
  next: document.querySelector("#next-stage"),
  generate: document.querySelector("#generate-solution"),
  saveState: document.querySelector("#save-state"),
  requirementSummary: document.querySelector("#requirement-summary"),
  requirementsView: document.querySelector("#requirements-view"),
  solutionView: document.querySelector("#solution-view"),
  requirementsTab: document.querySelector("#requirements-tab"),
  solutionTab: document.querySelector("#solution-tab"),
  solutionEmpty: document.querySelector("#solution-empty"),
  solutionContent: document.querySelector("#solution-content"),
  engineStatus: document.querySelector("#engine-status"),
  engineStatusLabel: document.querySelector("#engine-status-label"),
  toast: document.querySelector("#toast"),
};

function humanize(value) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function asText(value, fallback = "Not provided") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  if (Array.isArray(value)) {
    return value.map((item) => asText(item, "")).filter(Boolean).join(", ") || fallback;
  }
  if (typeof value === "object") {
    return asText(
      value.title
        || value.name
        || value.component_or_pattern
        || value.risk
        || value.consideration
        || value.required_validation
        || value.impact
        || value.objective,
      fallback,
    );
  }
  return String(value);
}

function create(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = asText(text, "");
  }
  return node;
}

function showToast(message, isError = false) {
  window.clearTimeout(state.toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.toggle("is-error", isError);
  elements.toast.hidden = false;
  state.toastTimer = window.setTimeout(() => {
    elements.toast.hidden = true;
  }, 4200);
}

function setSaveState(message, isError = false) {
  elements.saveState.textContent = message;
  elements.saveState.classList.toggle("is-error", isError);
}

function errorMessage(payload, fallback) {
  const error = payload && payload.error;
  if (typeof error === "string") {
    return error;
  }
  if (error && error.message) {
    return error.message;
  }
  return fallback;
}

async function apiFetch(path, options = {}, requestKey = path) {
  const existing = state.controllers.get(requestKey);
  if (existing) {
    existing.abort();
  }
  const controller = new AbortController();
  state.controllers.set(requestKey, controller);
  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok || !payload || payload.success === false) {
      throw new Error(errorMessage(payload, `Request failed (${response.status}).`));
    }
    return payload.data;
  } finally {
    if (state.controllers.get(requestKey) === controller) {
      state.controllers.delete(requestKey);
    }
  }
}

function setEngineStatus(online) {
  elements.engineStatus.classList.toggle("is-degraded", !online);
  elements.engineStatusLabel.textContent = online ? "Rules engine online" : "Rules engine unavailable";
}

async function checkHealth() {
  try {
    const health = await apiFetch("/api/health", {}, "health");
    setEngineStatus(health?.status === "ok");
  } catch (error) {
    if (error.name !== "AbortError") {
      setEngineStatus(false);
    }
  }
}

function scenarioCollection(data) {
  if (Array.isArray(data)) {
    return data;
  }
  return Array.isArray(data?.scenarios) ? data.scenarios : [];
}

function scenarioBundle(data) {
  if (!data) {
    return { scenario: null, run: null };
  }
  const scenario = data.scenario || data;
  const run = data.latest_run || data.run || scenario.latest_run || null;
  return { scenario, run };
}

function renderScenarioRail() {
  const fragment = document.createDocumentFragment();
  if (!state.scenarios.length) {
    fragment.append(create("div", "rail-placeholder", "No scenarios yet. Start a discovery session."));
  }
  state.scenarios.forEach((scenario) => {
    const button = create("button", "scenario-item");
    button.type = "button";
    button.dataset.scenarioId = String(scenario.id);
    button.classList.toggle("is-active", String(scenario.id) === String(state.activeScenarioId));
    button.setAttribute("aria-pressed", String(String(scenario.id) === String(state.activeScenarioId)));
    button.append(
      create("strong", "", scenario.name),
      create("small", "", `${humanize(scenario.workload_type)} · v${scenario.version || 1}`),
    );
    button.addEventListener("click", () => selectScenario(scenario.id));
    fragment.append(button);
  });
  elements.scenarioRail.replaceChildren(fragment);
  elements.scenarioCount.textContent = String(state.scenarios.length);
}

async function loadScenarios(selectFirst = true) {
  try {
    const data = await apiFetch(API_ROOT, {}, "scenario-list");
    state.scenarios = scenarioCollection(data);
    renderScenarioRail();
    if (selectFirst && state.scenarios.length && state.activeScenarioId === null) {
      await selectScenario(state.scenarios[0].id);
    }
  } catch (error) {
    if (error.name !== "AbortError") {
      elements.scenarioRail.replaceChildren(create("div", "rail-placeholder", "Scenarios could not be loaded."));
      showToast(error.message, true);
    }
  }
}

function setFormValues(scenario) {
  if (!scenario) {
    return;
  }
  Array.from(elements.form.elements).forEach((control) => {
    if (!control.name || control.id === "hypothesis-confirmation") {
      return;
    }
    if (control.name === "security_requirements") {
      control.checked = Array.isArray(scenario.security_requirements)
        && scenario.security_requirements.includes(control.value);
      return;
    }
    if (control.type === "checkbox") {
      control.checked = Boolean(scenario[control.name]);
      return;
    }
    if (Object.hasOwn(scenario, control.name) && scenario[control.name] !== null) {
      control.value = scenario[control.name];
    }
  });
  document.querySelector("#hypothesis-confirmation").checked = false;
  renderRequirementSummary();
}

async function selectScenario(id) {
  if (!canDiscardDraft()) {
    return;
  }
  setSaveState("Loading scenario…");
  try {
    const data = await apiFetch(`${API_ROOT}/${encodeURIComponent(id)}`, {}, "scenario-detail");
    const bundle = scenarioBundle(data);
    state.activeScenarioId = bundle.scenario.id;
    state.activeScenario = bundle.scenario;
    state.activeRun = bundle.run;
    state.dirty = false;
    renderScenarioRail();
    setFormValues(bundle.scenario);
    renderSolution(bundle.scenario, bundle.run);
    setSaveState(`Saved · version ${bundle.scenario.version || 1}`);
  } catch (error) {
    if (error.name !== "AbortError") {
      setSaveState("Could not load", true);
      showToast(error.message, true);
    }
  }
}

function setStage(nextStage, focusHeading = true) {
  const stage = Math.min(5, Math.max(1, nextStage));
  state.stage = stage;
  document.querySelectorAll("[data-stage-panel]").forEach((panel) => {
    panel.hidden = Number(panel.dataset.stagePanel) !== stage;
  });
  document.querySelectorAll(".stage-tab").forEach((tab) => {
    const current = Number(tab.dataset.stage) === stage;
    tab.classList.toggle("is-current", current);
    if (current) {
      tab.setAttribute("aria-current", "step");
    } else {
      tab.removeAttribute("aria-current");
    }
  });
  const copy = stageCopy[stage];
  document.querySelector("#stage-kicker").textContent = copy[0];
  document.querySelector("#stage-title").textContent = copy[1];
  document.querySelector("#stage-help").textContent = copy[2];
  elements.previous.disabled = stage === 1;
  elements.next.hidden = stage === 5;
  elements.generate.hidden = stage !== 5;
  if (stage === 5) {
    renderRequirementSummary();
  }
  if (focusHeading) {
    document.querySelector("#stage-title").setAttribute("tabindex", "-1");
    document.querySelector("#stage-title").focus({ preventScroll: true });
  }
}

function stageValidation(stage) {
  const panel = document.querySelector(`[data-stage-panel="${stage}"]`);
  const controls = Array.from(panel.querySelectorAll("input, select, textarea"));
  for (const control of controls) {
    if (!control.checkValidity()) {
      return { stage, control, message: null };
    }
  }
  if (stage === 4 && elements.form.querySelectorAll('input[name="security_requirements"]:checked').length === 0) {
    return {
      stage,
      control: elements.form.querySelector('input[name="security_requirements"]'),
      message: "Select at least one security requirement.",
    };
  }
  return null;
}

function revealValidation(validation) {
  setStage(validation.stage, false);
  window.requestAnimationFrame(() => {
    if (validation.message) {
      showToast(validation.message, true);
      validation.control.focus();
    } else {
      validation.control.reportValidity();
    }
  });
}

function findFirstInvalidStage(start = 1, end = 5) {
  for (let stage = start; stage <= end; stage += 1) {
    const validation = stageValidation(stage);
    if (validation) {
      return validation;
    }
  }
  return null;
}

function navigateToStage(targetStage) {
  const target = Math.min(5, Math.max(1, targetStage));
  if (target > state.stage) {
    const validation = findFirstInvalidStage(state.stage, target - 1);
    if (validation) {
      revealValidation(validation);
      return false;
    }
  }
  setStage(target);
  return true;
}

function payloadFromForm() {
  const values = new FormData(elements.form);
  const payload = {};
  values.forEach((value, name) => {
    if (name !== "security_requirements") {
      payload[name] = numericFields.has(name) ? Number(value) : String(value).trim();
    }
  });
  payload.security_requirements = values.getAll("security_requirements").map(String);
  payload.hybrid_requirement = elements.form.elements.hybrid_requirement.checked;
  payload.fictional = true;
  return payload;
}

function renderRequirementSummary() {
  const payload = payloadFromForm();
  const fragment = document.createDocumentFragment();
  summaryFields.forEach(([label, key, unit]) => {
    const group = create("div");
    const displayValue = numericFields.has(key) ? asText(payload[key]) : humanize(payload[key]);
    group.append(create("dt", "", label), create("dd", "", `${displayValue}${unit ? ` ${unit}` : ""}`));
    fragment.append(group);
  });
  elements.requirementSummary.replaceChildren(fragment);
}

function switchView(view) {
  const showSolution = view === "solution";
  elements.requirementsView.hidden = showSolution;
  elements.solutionView.hidden = !showSolution;
  elements.requirementsTab.classList.toggle("is-active", !showSolution);
  elements.solutionTab.classList.toggle("is-active", showSolution);
  elements.requirementsTab.setAttribute("aria-selected", String(!showSolution));
  elements.solutionTab.setAttribute("aria-selected", String(showSolution));
  elements.requirementsTab.tabIndex = showSolution ? -1 : 0;
  elements.solutionTab.tabIndex = showSolution && !elements.solutionTab.disabled ? 0 : -1;
  const heading = showSolution
    ? elements.solutionContent.querySelector("h3") || elements.solutionEmpty.querySelector("h3")
    : document.querySelector("#stage-title");
  heading.setAttribute("tabindex", "-1");
  heading.focus({ preventScroll: true });
}

function appendList(element, items, emptyText) {
  const values = Array.isArray(items) ? items : [];
  const fragment = document.createDocumentFragment();
  if (!values.length) {
    fragment.append(create("li", "", emptyText));
  } else {
    values.forEach((item) => fragment.append(create("li", "", item)));
  }
  element.replaceChildren(fragment);
}

function recommendationsFrom(assessment) {
  return Array.isArray(assessment?.recommendations) ? assessment.recommendations : [];
}

function renderTraces(assessment) {
  const recommendations = recommendationsFrom(assessment);
  const fragment = document.createDocumentFragment();
  recommendations.forEach((recommendation, index) => {
    const details = create("details", "trace-item");
    if (index === 0) {
      details.open = true;
    }
    const summary = create("summary");
    summary.append(
      create("span", "trace-rule", recommendation.rule_triggered || recommendation.rule_id || `RULE-${index + 1}`),
      create("span", "trace-component", recommendation.recommended_component_or_pattern || recommendation.recommendation),
      create("span", "trace-requirement", recommendation.customer_requirement),
    );
    const body = create("dl", "trace-body");
    [
      ["Reason", recommendation.reason],
      ["Alternative", recommendation.alternative],
      ["Risk", recommendation.risk],
      ["Required validation", recommendation.required_validation],
    ].forEach(([label, value]) => {
      const group = create("div");
      group.append(create("dt", "", label), create("dd", "", value));
      body.append(group);
    });
    details.append(summary, body);
    fragment.append(details);
  });
  if (!recommendations.length) {
    fragment.append(create("p", "rail-placeholder", "No recommendation traces were returned."));
  }
  document.querySelector("#recommendation-traces").replaceChildren(fragment);
  document.querySelector("#trace-count").textContent = `${recommendations.length} rules`;
}

function renderComponents(assessment) {
  const architecture = assessment?.architecture && typeof assessment.architecture === "object"
    ? assessment.architecture
    : {};
  const fragment = document.createDocumentFragment();
  Object.entries(architecture).forEach(([layer, recommendation]) => {
    const group = create("div");
    group.append(create("dt", "", humanize(layer)), create("dd", "", recommendation));
    fragment.append(group);
  });
  if (!Object.keys(architecture).length) {
    const group = create("div");
    group.append(create("dt", "", "Status"), create("dd", "", "No architecture layers were returned."));
    fragment.append(group);
  }
  document.querySelector("#component-recommendations").replaceChildren(fragment);
}

function unique(values) {
  return [...new Set(values.filter((value) => value !== null && value !== undefined && value !== ""))];
}

function renderCaveats(assessment) {
  const recommendations = recommendationsFrom(assessment);
  const risks = assessment?.primary_risks || recommendations.map((item) => item.risk);
  const alternatives = assessment?.alternatives || recommendations.map((item) => item.alternative);
  const assumptions = assessment?.assumptions
    || (assessment?.missing_evidence || []).map((item) => item.question || item.reason || item.field);
  appendList(document.querySelector("#solution-risks"), unique(risks || []), "No primary risks were returned.");
  appendList(document.querySelector("#solution-assumptions"), unique(assumptions || []), "No explicit assumptions were returned.");
  appendList(document.querySelector("#solution-alternatives"), unique(alternatives || []), "No alternatives were returned.");
}

function renderConfidence(assessment) {
  const confidence = assessment?.solution_confidence || assessment?.confidence || {};
  const rawScore = Number(confidence.score ?? 0);
  const percent = rawScore <= 1 ? Math.round(rawScore * 100) : Math.round(rawScore);
  const safePercent = Math.min(100, Math.max(0, percent));
  document.querySelector("#confidence-score").textContent = `${safePercent}%`;
  document.querySelector("#confidence-level").textContent = `${humanize(confidence.level || "unrated")} confidence`;
  document.querySelector("#confidence-reason").textContent = asText(confidence.reason || confidence.rationale, "Evidence completeness and rule certainty.");
  document.querySelector("#confidence-ring").style.setProperty("--confidence", `${safePercent}%`);
}

function renderWorkshopOutputs(assessment) {
  const poc = assessment?.recommended_poc || assessment?.poc || {};
  const workshop = assessment?.recommended_next_workshop || assessment?.next_workshop || {};
  document.querySelector("#poc-title").textContent = asText(poc.objective || poc.title, "No PoC recommendation returned");
  document.querySelector("#poc-detail").textContent = asText(poc.success_criteria || poc.scope || poc.description, "Capture missing evidence before selecting a validation scope.");
  document.querySelector("#workshop-title").textContent = asText(workshop.title, "No next workshop returned");
  document.querySelector("#workshop-detail").textContent = asText(workshop.agenda || workshop.objective || workshop.description, "Resolve the open qualification questions with the responsible stakeholders.");
  appendList(document.querySelector("#open-questions"), assessment?.open_questions, "No open questions were returned.");
}

function renderSolution(scenario, run) {
  const assessment = run?.assessment || scenario?.assessment || null;
  const hasSolution = Boolean(scenario && assessment);
  elements.solutionEmpty.hidden = hasSolution;
  elements.solutionContent.hidden = !hasSolution;
  elements.solutionTab.disabled = !hasSolution;
  elements.solutionTab.tabIndex = hasSolution
    && elements.solutionTab.getAttribute("aria-selected") === "true" ? 0 : -1;
  if (!hasSolution) {
    return;
  }
  document.querySelector("#solution-name").textContent = scenario.name;
  document.querySelector("#solution-summary").textContent = asText(
    scenario.description,
    "Generated from the captured discovery inputs.",
  );
  const diagram = document.querySelector("#architecture-diagram");
  diagram.src = `${API_ROOT}/${encodeURIComponent(scenario.id)}/diagram.svg`;
  diagram.alt = `Generated architecture for ${scenario.name}`;
  renderConfidence(assessment);
  renderTraces(assessment);
  renderComponents(assessment);
  renderCaveats(assessment);
  renderWorkshopOutputs(assessment);
}

async function saveScenario(event) {
  event.preventDefault();
  const validation = findFirstInvalidStage();
  if (validation) {
    switchView("requirements");
    revealValidation(validation);
    return;
  }
  const updating = state.activeScenarioId !== null;
  const path = updating ? `${API_ROOT}/${encodeURIComponent(state.activeScenarioId)}` : API_ROOT;
  setSaveState(updating ? "Updating…" : "Generating…");
  elements.generate.disabled = true;
  try {
    const data = await apiFetch(path, {
      method: updating ? "PUT" : "POST",
      body: JSON.stringify(payloadFromForm()),
    }, "scenario-save");
    const bundle = scenarioBundle(data);
    state.activeScenario = bundle.scenario;
    state.activeRun = bundle.run;
    state.activeScenarioId = bundle.scenario.id;
    state.dirty = false;
    renderSolution(bundle.scenario, bundle.run);
    await loadScenarios(false);
    setSaveState(`Saved · version ${bundle.scenario.version || 1}`);
    showToast(updating ? "Solution hypothesis updated." : "Solution hypothesis generated.");
    switchView("solution");
  } catch (error) {
    if (error.name !== "AbortError") {
      setSaveState("Could not save", true);
      showToast(error.message, true);
    }
  } finally {
    elements.generate.disabled = false;
  }
}

function canDiscardDraft() {
  return !state.dirty || window.confirm("Discard unsaved changes to this scenario?");
}

function startNewScenario() {
  if (!canDiscardDraft()) {
    return;
  }
  state.activeScenarioId = null;
  state.activeScenario = null;
  state.activeRun = null;
  state.dirty = false;
  elements.form.reset();
  elements.form.elements.model_size_billion.value = "13";
  elements.form.elements.latency_target_ms.value = "800";
  elements.form.elements.throughput_target_rps.value = "12";
  elements.form.elements.data_volume_tb.value = "8";
  elements.form.elements.annual_growth_pct.value = "30";
  elements.form.elements.availability_target_pct.value = "99.9";
  elements.form.elements.recovery_objective_hours.value = "4";
  elements.form.elements.timeline_weeks.value = "16";
  document.querySelector("#hypothesis-confirmation").checked = false;
  renderScenarioRail();
  renderSolution(null, null);
  setSaveState("Not saved");
  setStage(1, false);
  switchView("requirements");
  elements.form.elements.name.focus();
}

async function downloadExport(format) {
  if (state.activeScenarioId === null) {
    showToast("Select or generate a scenario before exporting.", true);
    return;
  }
  const path = `${API_ROOT}/${encodeURIComponent(state.activeScenarioId)}/export?format=${encodeURIComponent(format)}`;
  const controller = new AbortController();
  try {
    const response = await fetch(path, { signal: controller.signal });
    if (!response.ok) {
      throw new Error(`Export failed (${response.status}).`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const extension = format === "markdown" ? "md" : format;
    anchor.href = url;
    anchor.download = `solution-${state.activeScenarioId}.${extension}`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    showToast(`${humanize(format)} export downloaded.`);
  } catch (error) {
    if (error.name !== "AbortError") {
      showToast(error.message, true);
    }
  }
}

elements.previous.addEventListener("click", () => setStage(state.stage - 1));
elements.next.addEventListener("click", () => navigateToStage(state.stage + 1));
elements.form.addEventListener("submit", saveScenario);
elements.form.addEventListener("input", () => {
  state.dirty = true;
  setSaveState("Unsaved changes");
});
document.querySelector("#refresh-summary").addEventListener("click", renderRequirementSummary);
document.querySelector("#new-scenario").addEventListener("click", startNewScenario);
document.querySelector("#return-to-requirements").addEventListener("click", () => switchView("requirements"));
elements.requirementsTab.addEventListener("click", () => switchView("requirements"));
elements.solutionTab.addEventListener("click", () => switchView("solution"));

document.querySelectorAll(".stage-tab").forEach((tab) => {
  tab.addEventListener("click", () => navigateToStage(Number(tab.dataset.stage)));
});

document.querySelectorAll(".export-button").forEach((button) => {
  button.addEventListener("click", () => downloadExport(button.dataset.exportFormat));
});

function activateInsightTab(tab, focus = false) {
  document.querySelectorAll(".insight-tab").forEach((item) => {
    const active = item === tab;
    item.classList.toggle("is-active", active);
    item.setAttribute("aria-selected", String(active));
    item.tabIndex = active ? 0 : -1;
  });
  document.querySelectorAll(".insight-list").forEach((panel) => {
    panel.hidden = panel.id !== tab.dataset.insight;
  });
  if (focus) {
    tab.focus();
  }
}

function nextTabForKey(event, tabs) {
  const current = tabs.indexOf(event.currentTarget);
  let next = current;
  switch (event.key) {
    case "ArrowRight":
      next = (current + 1) % tabs.length;
      break;
    case "ArrowLeft":
      next = (current - 1 + tabs.length) % tabs.length;
      break;
    case "Home":
      next = 0;
      break;
    case "End":
      next = tabs.length - 1;
      break;
    default:
      return null;
  }
  event.preventDefault();
  return tabs[next];
}

const insightTabs = Array.from(document.querySelectorAll(".insight-tab"));
insightTabs.forEach((tab) => {
  tab.addEventListener("click", () => activateInsightTab(tab));
  tab.addEventListener("keydown", (event) => {
    const target = nextTabForKey(event, insightTabs);
    if (target) {
      activateInsightTab(target, true);
    }
  });
});

const modeTabs = [elements.requirementsTab, elements.solutionTab];
modeTabs.forEach((tab) => {
  tab.addEventListener("keydown", (event) => {
    const available = modeTabs.filter((item) => !item.disabled);
    const target = nextTabForKey(event, available);
    if (target) {
      switchView(target === elements.solutionTab ? "solution" : "requirements");
    }
  });
});

checkHealth();
loadScenarios();
