const dashboardContext = {distance: "im", gender: "Male", ageGroup: "30-34"};
const qualificationAssumptions = {mode: "strict", extraPlaces: 0, legacyExtraPlaces: 0, fallback: false};
let dashboardReturnView = null;
const cutoffLabels = {strict: "Strict allocation", places: "Manual extra places", reported: "Reported last accepted", density: "Density estimate", scan: "15-absence scan"};
const dashboardWorkspaces = {
  explorer: {label: "Race Explorer", views: ["statistics", "overall", "splits"]},
  compare: {label: "Compare Races", views: ["compare"]},
  qualification: {label: "Qualification", views: ["qualification", "easiest", "odds", "kona"]},
  course: {label: "Course Analysis", views: ["experimental"]},
};
const dashboardViewLabels = {
  statistics: "Participation", overall: "Finish Times", splits: "Athletes & Splits",
  compare: "Race Comparison", qualification: "Race Targets", easiest: "Race Finder",
  odds: "Historical Target Hits", kona: "Kona Evidence", experimental: "Course & Conditions",
};
const contextControlIds = {
  distance: ["oddsDistance", "easiestDistance", "experimentalDistance", "compareSplitDistance", "compareStatisticsDistance", "compareScatterDistance", "compareFieldDistance", "compareSlotDistance"],
  gender: ["qualificationGender", "oddsGender", "easiestGender", "experimentalGender", "compareImGender", "compare703Gender", "compareScatterGender", "konaGender", "compareFieldGender"],
  ageGroup: ["qualificationAgeGroup", "oddsAgeGroup", "easiestAgeGroup", "experimentalAgeGroup", "compareImAgeGroup", "compare703AgeGroup", "compareScatterAgeGroup", "compareFieldAgeGroup", "konaAgeGroup"],
};
let activeWorkspace = "explorer";
const workspaceLastView = {explorer: "splits", compare: "compare", qualification: "qualification", course: "experimental"};

function renderContextYears() {
  const container = document.getElementById("contextYears");
  if (!container) return;
  container.innerHTML = compareYears.map(year => `<button type="button" class="year-toggle" data-year="${year}" aria-pressed="${compareYearVisible(year)}" style="--year-color:${compareYearColor(year)}">${year}</button>`).join("");
  const count = compareYears.filter(compareYearVisible).length;
  document.getElementById("contextYearCount").textContent = `${count} / ${compareYears.length} race years`;
}

function renderWorkspaceNavigation() {
  document.getElementById("workspaceTabs").innerHTML = Object.entries(dashboardWorkspaces).map(([key, workspace]) => `<button type="button" role="tab" tabindex="${key === activeWorkspace ? 0 : -1}" class="tab-button ${key === activeWorkspace ? "active" : ""}" aria-selected="${key === activeWorkspace}" data-workspace="${key}">${workspace.label}</button>`).join("");
  document.getElementById("viewTabs").innerHTML = dashboardWorkspaces[activeWorkspace].views.map(view => `<button type="button" role="tab" id="view-${view}" tabindex="${view === activeTab ? 0 : -1}" class="tab-button ${view === activeTab ? "active" : ""}" aria-controls="${view}Panel" aria-selected="${view === activeTab}" data-view="${view}">${dashboardViewLabels[view]}</button>`).join("");
}

function activateDashboardView(view) {
  const entry = Object.entries(dashboardWorkspaces).find(([, workspace]) => workspace.views.includes(view));
  activeWorkspace = entry[0];
  workspaceLastView[activeWorkspace] = view;
  document.querySelector(`.legacy-tabs [data-tab="${view}"]`).click();
  renderWorkspaceNavigation();
  updateDashboardScope();
  decorateDashboard();
}

function updateDashboardScope() {
  const allAthletes = ["splits", "overall", "statistics"].includes(activeTab);
  const cycle = selectedKonaTrace()?.year || "2026";
  document.querySelector(".assumption-fields").hidden = allAthletes || ["kona", "compare"].includes(activeTab);
  for (const [id, distance] of [["compareImDistribution", "im"], ["compare703Distribution", "703"], ["compareImQualification", "im"], ["compare703Qualification", "703"]]) {
    document.getElementById(id).closest(".chart-panel").hidden = dashboardContext.distance !== distance;
  }
  document.getElementById("eventTitle").textContent = allAthletes || activeTab === "qualification"
    ? `${dataset().name} / ${dashboardViewLabels[activeTab]}` : dashboardViewLabels[activeTab];
  document.getElementById("contextScope").textContent = allAthletes
    ? "All athletes. Gender and age group apply to qualification analyses only."
    : activeTab === "kona"
      ? `Kona ${cycle} cycle. Race-year filters affect displayed candidate editions, not matching or estimator evidence. Starter counts cover the full championship field.`
      : activeTab === "experimental"
        ? "Selected race years displayed. Published course/season factors and athlete calibration retain their full training scope."
        : "Selected race years. Course models and personal-result calibration retain their full source scope.";
  document.getElementById("eventSubtitle").textContent = allAthletes || activeTab === "qualification"
    ? dataset().subtitle
    : `${dashboardWorkspaces[activeWorkspace].label} / ${dashboardViewLabels[activeTab]}`;
}

function syncDashboardContext(key, value) {
  dashboardContext[key] = value;
  if (key === "distance") {
    if (["10:30:00", "05:00:00"].includes(easiestTypedTime)) easiestTypedTime = value === "703" ? "05:00:00" : "10:30:00";
    const eventIds = raceGroups()[value] || [];
    if (!eventIds.includes(eventSelect.value) && eventIds.length) eventSelect.value = eventIds[0];
  }
  for (const [field, ids] of Object.entries(contextControlIds)) {
    for (const id of ids) {
      const control = document.getElementById(id);
      if (field === "ageGroup" && ![...control.options].some(option => option.value === dashboardContext[field])) {
        control.add(new Option(dashboardContext[field], dashboardContext[field]));
      }
      control.value = dashboardContext[field];
    }
    document.getElementById(`context${field[0].toUpperCase()}${field.slice(1)}`).value = dashboardContext[field];
  }
  renderSharedViews();
  updateDashboardScope();
}

function syncQualificationAssumptions() {
  qualificationSystem = document.getElementById("contextRules").value;
  qualificationAssumptions.mode = document.getElementById("contextCutoff").value;
  qualificationAssumptions.extraPlaces = Math.max(0, Math.round(Number(document.getElementById("contextExtraPlaces").value) || 0));
  qualificationAssumptions.legacyExtraPlaces = Math.max(0, Math.round(Number(document.getElementById("contextLegacyPlaces").value) || 0));
  qualificationAssumptions.fallback = document.getElementById("contextFallback").checked;
  document.querySelectorAll(".qualification-system").forEach(control => control.value = qualificationSystem);
  easiestCutoffMode.value = qualificationAssumptions.mode;
  [qualificationDeclines, oddsDeclines, easiestDeclines].forEach(control => {
    control.value = qualificationAssumptions.extraPlaces;
  });
  document.getElementById("contextExtraPlaces").disabled = qualificationAssumptions.mode !== "places";
  document.getElementById("contextLegacyPlaces").disabled = qualificationAssumptions.mode !== "places";
  qualificationLegacyDeclines.value = qualificationAssumptions.legacyExtraPlaces;
  oddsDeclines.disabled = easiestDeclines.disabled = qualificationAssumptions.mode !== "places";
  renderSharedViews();
}

function assumptionTime(standard, baseline = false) {
  const value = baseline ? standard?.strictNeeded : standard?.needed;
  if (!baseline && standard && !standard.available) return "No estimate";
  if (!baseline && Number.isFinite(value) && ["minute", "estimate"].includes(standard?.precision)) {
    return `~${duration(Math.round(value / 60) * 60).slice(0, 5)}`;
  }
  return neededText(value);
}

function qualificationEvidenceLink(standard) {
  if (!standard) return "Unavailable";
  const pool = standard.cutoffPool;
  const label = escapeHtml(standard.cutoffSource);
  if (!pool) return label;
  const reported = standard.mode === "reported" && pool.reported_cutoff_url
    ? `<br><a href="${escapeHtml(pool.reported_cutoff_url)}" target="_blank" rel="noreferrer">${escapeHtml(pool.reported_cutoff_source || "Reported source")}</a>` : "";
  return `${label}${reported}<br><button type="button" class="context-action" data-evidence-race="${escapeHtml(standard.eventId)}" data-evidence-year="${escapeHtml(standard.year)}" data-evidence-cycle="${escapeHtml(standard.cutoffCycle || "2026")}">Kona evidence</button>`;
}

function renderSelectedQualification() {
  const container = document.getElementById("selectedQualificationSummary");
  if (!container) return;
  const eventId = eventSelect.value;
  const gender = dashboardContext.gender;
  const ageGroup = dashboardContext.ageGroup;
  container.innerHTML = `<h2>Selected Target / Strict Baseline</h2><p class="note">${escapeHtml(cutoffLabels[qualificationAssumptions.mode])} · ${escapeHtml(divisionFor(gender, ageGroup))}. Raw finish times; reported minute values and density estimates remain approximate. Matching evidence is not slot acceptance. ${qualificationAssumptions.fallback ? "Strict fallback enabled for unavailable editions." : "Unavailable editions are excluded from target rankings."}</p>
    <div class="table-wrap"><table><thead><tr><th>Race Year</th><th>Strict Baseline</th><th>Selected Target</th><th>Cutoff Evidence / Cycle</th></tr></thead><tbody>${qualificationYears(eventId, qualificationSystem).map(year => {
      const standard = easiestQualificationStandard(eventId, year, gender, ageGroup, qualificationSystem, qualificationAssumptions.mode, qualificationAssumptions.extraPlaces);
      return `<tr><td>${yearCell(eventId, year)}</td><td>${assumptionTime(standard, true)}</td><td><strong>${assumptionTime(standard)}</strong></td><td>${qualificationEvidenceLink(standard)}</td></tr>`;
    }).join("") || '<tr><td colspan="4" class="empty">No data for selected race years.</td></tr>'}</tbody></table></div>`;
}

function decorateQualificationRankings() {
  for (const prefix of ["easiest", "odds"]) {
    const body = document.getElementById(`${prefix}RankingBody`);
    body.querySelectorAll("tr").forEach(row => {
      const cell = row.cells[0];
      const entry = Object.entries(DATASETS).find(([, ds]) => cell?.textContent.endsWith(ds.name));
      if (entry && !cell.querySelector("button")) {
        cell.innerHTML = `<button type="button" class="race-link" data-target-race="${entry[0]}">${escapeHtml(cell.textContent)}</button>`;
      }
    });
  }
  const inferred = !["strict", "places"].includes(qualificationAssumptions.mode);
  for (const eventId of oddsEventIds()) {
    const body = document.getElementById("oddsRankingBody");
    if (![...body.rows].some(row => row.cells[0]?.textContent === DATASETS[eventId].name)) {
      const row = body.insertRow();
      row.innerHTML = `<td><button type="button" class="race-link" data-target-race="${eventId}">${escapeHtml(DATASETS[eventId].name)}</button></td><td colspan="9">No compatible target for selected race years. Not ranked.</td>`;
    }
  }
  document.getElementById("easiestRankingNote").textContent = `Modelled chance averages selected, compatible race years, not a historical acceptance probability. ${cutoffLabels[qualificationAssumptions.mode]} replaces manual extra places. ${inferred ? qualificationAssumptions.fallback ? "Unavailable editions use explicitly enabled strict fallback." : "Uncovered or incompatible editions are excluded; races with no compatible target stay visible and unranked." : "Strict allocation counts remain separate from hypothetical roll-down."} Published course factors and your saved results retain their full calibration scope. Few race years give uncertain estimates.`;
  const oddsNote = document.getElementById("oddsRankingNote");
  oddsNote.textContent = oddsNote.textContent.split(" Selected cutoff:")[0].replace("Strict entitlement model: declines and ceremony attendance are not observed in the results.", "") + ` Selected cutoff: ${cutoffLabels[qualificationAssumptions.mode]}. Target hits are historical comparisons, not modelled future chance or verified acceptance. Unavailable editions are excluded unless strict fallback is enabled.`;
  const oddsHeader = document.getElementById("oddsRankingHead").querySelectorAll("th")[2];
  if (oddsHeader) oddsHeader.textContent = "Historical Target Hits";
  const coverageHeader = document.getElementById("easiestRankingHead").querySelectorAll("th")[4];
  if (coverageHeader) coverageHeader.title = "Only compatible selected editions are included; unavailable editions use strict targets only when fallback is explicitly enabled.";
  document.querySelectorAll("#easiestRankingBody tr").forEach(row => {
    if (row.cells.length === 13 && qualificationAssumptions.mode === "strict") row.cells[4].textContent = "Strict allocation";
    if (row.cells.length === 13 && ["reported", "density"].includes(qualificationAssumptions.mode)) {
      const value = parseTime(row.cells[7].textContent);
      if (Number.isFinite(value)) row.cells[7].textContent = `~${duration(Math.round(value / 60) * 60).slice(0, 5)}`;
    }
  });
}

function decorateDashboard() {
  updateDashboardScope();
  renderSelectedQualification();
  decorateQualificationRankings();
  document.getElementById("ageGroupTargetChartTitle").textContent = `Selected target by age group / ${cutoffLabels[qualificationAssumptions.mode]}`;
  document.querySelectorAll(".tab-panel tbody").forEach(body => {
    if (!body.children.length) {
      const columns = body.closest("table").querySelectorAll("thead th").length;
      body.innerHTML = `<tr><td colspan="${Math.max(1, columns)}" class="empty">No data for the selected race years.</td></tr>`;
    }
  });
}

function initializeDashboardUI() {
  const style = document.createElement("style");
  style.textContent = `
    .legacy-tabs {display:none} .workspace-tabs {margin-bottom:0}
    .view-tabs {padding-top:0; margin-bottom:18px; background:#e5ebe7}
    .context-bar {padding:14px 16px; background:#fff; border-bottom:1px solid var(--line); margin-bottom:4px}
    .context-fields {display:flex; flex-wrap:wrap; gap:12px; align-items:end}
    .context-fields[hidden], .context-years[hidden], .chart-panel[hidden] {display:none}
    .context-fields label {min-width:110px} .context-bar .note {margin:10px 0 0}
    .context-fields input[type=number] {width:100%; min-width:0; box-sizing:border-box}
    .context-years {display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin-top:12px}
    .year-toggle {min-height:30px; padding:4px 9px; background:#f4f7f5; color:var(--ink); border:1px solid var(--line); border-bottom:3px solid var(--year-color); font-variant-numeric:tabular-nums}
    .year-toggle:hover {background:#e5ece8} .year-toggle[aria-pressed=false] {opacity:.4}
    .context-action {min-height:30px; padding:4px 9px; background:#e5ece8; color:var(--ink)}
    .race-link {padding:0; border:0; background:none; color:var(--accent); text-align:left; text-decoration:underline}
    .local-context-control {display:none !important}
    .personal-profile {padding:16px 0; border-block:1px solid var(--line); margin-top:24px}
    .personal-profile > summary {cursor:pointer; font-family:Georgia,"Times New Roman",serif; font-size:19px}
    .controls {border:0; border-bottom:1px solid var(--line); border-radius:0; background:transparent; padding:12px 0}
    .assumption-fields {margin-top:12px; border-top:1px solid var(--line); padding-top:12px}
    .assumption-fields .binary-label {display:flex; align-items:center; gap:6px; min-height:32px}
    .assumption-fields input[type=checkbox] {width:auto}
    #selectedQualificationSummary {border-bottom:1px solid var(--line); padding-bottom:16px; margin-bottom:18px}
    #contextYearCount {font-size:12px; color:var(--muted)}
    .chart-panel {border:0; border-top:1px solid var(--line); border-radius:0; box-shadow:none; padding:16px 0; background:transparent}
    #comparePanel .chart-grid:empty {display:none}
    h1 {font-size:32px} .metric strong {font-size:22px; overflow-wrap:anywhere}
    @media(max-width:700px) {.context-fields {display:grid; grid-template-columns:repeat(2,minmax(0,1fr))} .context-fields label {min-width:0} .context-fields select {width:100%} h1 {font-size:27px}}
  `;
  document.head.append(style);
  document.querySelector("nav.tabs").classList.add("legacy-tabs");
  const nav = document.createElement("div");
  nav.innerHTML = `<nav id="workspaceTabs" class="tabs workspace-tabs" role="tablist" aria-label="Workspaces"></nav>
    <div class="context-bar"><div class="context-fields" hidden>
      <label>Distance<select id="contextDistance"><option value="im">IRONMAN 140.6</option><option value="703">IRONMAN 70.3</option></select></label>
      <label>Gender<select id="contextGender"><option value="Male">Men</option><option value="Female">Women</option></select></label>
      <label>Age group<select id="contextAgeGroup"></select></label>
    </div><div class="context-fields assumption-fields">
      <label>Rules & allocation<select id="contextRules"><option value="current">Current scenario</option><option value="historical">Actual historical</option></select></label>
      <label>Cutoff<select id="contextCutoff">${Object.entries(cutoffLabels).map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}</select></label>
      <label>Pool extra places<input id="contextExtraPlaces" type="number" min="0" step="1" value="0" disabled></label>
      <label>Legacy AG extra places<input id="contextLegacyPlaces" type="number" min="0" step="1" value="0" disabled></label>
      <label class="binary-label"><input type="checkbox" id="contextFallback">Use strict fallback</label>
    </div><div class="context-years"><button type="button" id="contextReturn" class="context-action" hidden>Back to ranking</button><span id="contextYearCount"></span>
      <button type="button" class="context-action" data-years-action="all">All</button>
      <button type="button" class="context-action" data-years-action="none">None</button>
      <button type="button" class="context-action" data-years-action="reset">Reset</button>
      <div id="contextYears" class="context-years" style="margin:0"></div></div><p class="note" id="contextScope"></p></div>
    <nav id="viewTabs" class="tabs view-tabs" role="tablist" aria-label="Workspace views"></nav>`;
  document.querySelector(".legacy-tabs").before(nav);
  document.querySelectorAll(".tab-panel").forEach(panel => {
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", `view-${panel.id.replace("Panel", "")}`);
  });
  const selectedSummary = document.createElement("section");
  selectedSummary.id = "selectedQualificationSummary";
  document.getElementById("qualificationContent").prepend(selectedSummary);
  const comparisons = document.createElement("section");
  comparisons.id = "qualificationComparisons";
  comparisons.innerHTML = '<h2>Cross-race qualification</h2><div class="chart-grid"></div>';
  document.getElementById("qualificationPanel").append(comparisons);
  const comparisonGrid = comparisons.querySelector(".chart-grid");
  for (const id of ["compareImQualification", "compare703Qualification", "compareMeanQualification", "compareQualificationResidual", "compareSlotPressure", "compareCutoffPercentile", "compareQualificationUncertainty"]) {
    comparisonGrid.append(document.getElementById(id).closest(".chart-panel"));
  }
  const slots = document.getElementById("compareTotalSlots");
  const participation = slots.closest(".chart-panel");
  const slotsPanel = document.createElement("div");
  slotsPanel.className = "chart-panel wide";
  slotsPanel.append(slots.previousElementSibling, slots);
  const slotControls = document.createElement("div");
  slotControls.className = "chart-controls";
  const slotDistance = document.getElementById("compareStatisticsDistance").closest("label").cloneNode(true);
  slotDistance.querySelector("select").id = "compareSlotDistance";
  slotControls.append(slotDistance);
  slotsPanel.firstElementChild.after(slotControls);
  comparisonGrid.prepend(slotsPanel);
  participation.querySelector("h2").textContent = "Participation by race";
  participation.querySelector(".note").textContent = "Finishers include professionals. DNS rates use registered athletes; DNF rates use starters.";
  document.querySelector("#comparePanel > .note").textContent = "Races are compared at the selected distance. Shortened or modified editions are excluded from cross-race time comparisons.";
  const fieldPanel = document.getElementById("compareAgeGroupDepth").closest(".chart-panel");
  const fieldControls = document.createElement("div");
  fieldControls.className = "chart-controls";
  for (const [sourceId, id] of [["compareScatterDistance", "compareFieldDistance"], ["compareScatterGender", "compareFieldGender"], ["compareScatterAgeGroup", "compareFieldAgeGroup"]]) {
    const label = document.getElementById(sourceId).closest("label").cloneNode(true);
    label.querySelector("select").id = id;
    fieldControls.append(label);
  }
  fieldPanel.querySelector("h2").after(fieldControls);
  document.querySelectorAll(".qualification-system").forEach(control => control.closest("label")?.classList.add("local-context-control"));
  [easiestCutoffMode, easiestDeclines, oddsDeclines].forEach(control => control.closest("label")?.classList.add("local-context-control"));
  document.getElementById("years").parentElement.classList.add("local-context-control");
  document.getElementById("compareYears").closest("fieldset").classList.add("local-context-control");
  const finder = document.getElementById("easiestPanel");
  const personal = finder.querySelector(":scope > section");
  const strength = document.getElementById("easiestProfileTitle").closest("section");
  const ranking = document.getElementById("easiestRankingTitle").closest("section");
  personal.before(finder.querySelector(":scope > .metrics"), ranking);
  const profile = document.createElement("details");
  profile.className = "personal-profile";
  profile.innerHTML = "<summary>Past results & strength profile</summary>";
  personal.before(profile);
  profile.append(personal, strength);
  profile.open = myResults.length > 0;
  const allGroups = compareAgeGroups(Object.keys(DATASETS).filter(isQualifyingEvent));
  document.getElementById("contextAgeGroup").innerHTML = allGroups.map(value => `<option value="${value}">${value}</option>`).join("");
  document.getElementById("contextAgeGroup").value = dashboardContext.ageGroup;
  for (const [key, ids] of Object.entries(contextControlIds)) {
    const shared = document.getElementById(`context${key[0].toUpperCase()}${key.slice(1)}`);
    shared.addEventListener("change", () => syncDashboardContext(key, shared.value));
    ids.forEach(id => document.getElementById(id).addEventListener("change", event => syncDashboardContext(key, event.target.value)));
  }
  eventSelect.addEventListener("change", () => syncDashboardContext("distance", dataset().group));
  ["contextRules", "contextCutoff", "contextFallback"].forEach(id => document.getElementById(id).addEventListener("change", syncQualificationAssumptions));
  document.getElementById("contextExtraPlaces").addEventListener("input", syncQualificationAssumptions);
  document.getElementById("contextLegacyPlaces").addEventListener("input", syncQualificationAssumptions);
  qualificationLegacyDeclines.addEventListener("input", () => {
    document.getElementById("contextLegacyPlaces").value = qualificationLegacyDeclines.value;
    syncQualificationAssumptions();
  }, true);
  document.querySelectorAll(".qualification-system").forEach(control => control.addEventListener("change", () => {
    document.getElementById("contextRules").value = control.value;
    syncQualificationAssumptions();
  }));
  easiestCutoffMode.addEventListener("change", () => {
    document.getElementById("contextCutoff").value = easiestCutoffMode.value;
    syncQualificationAssumptions();
  }, true);
  [qualificationDeclines, oddsDeclines, easiestDeclines].forEach(control => control.addEventListener("input", () => {
    document.getElementById("contextExtraPlaces").value = control.value;
    if (control !== qualificationDeclines) document.getElementById("contextCutoff").value = "places";
    syncQualificationAssumptions();
  }, true));
  document.addEventListener("click", event => {
    const targetRace = event.target.closest("[data-target-race]");
    const evidence = event.target.closest("[data-evidence-race]");
    if (targetRace || evidence) {
      if (!dashboardReturnView) dashboardReturnView = activeTab;
      document.getElementById("contextReturn").hidden = false;
      if (targetRace) {
        eventSelect.value = targetRace.dataset.targetRace;
        syncDashboardContext("distance", dataset().group);
        activateDashboardView("qualification");
      } else {
        document.getElementById("konaCycle").value = evidence.dataset.evidenceCycle || "2026";
        initializeKonaTrace();
        document.getElementById("konaRace").value = `${evidence.dataset.evidenceRace}|${evidence.dataset.evidenceYear}`;
        activateDashboardView("kona");
        renderKonaTrace();
      }
      return;
    }
    if (event.target.closest("#contextReturn")) {
      activateDashboardView(dashboardReturnView || "easiest");
      dashboardReturnView = null;
      document.getElementById("contextReturn").hidden = true;
      return;
    }
    const year = event.target.closest("button[data-year]");
    if (year) {toggleCompareYear(year.dataset.year); return;}
    const action = event.target.closest("[data-years-action]");
    if (action) {
      hiddenCompareYears.clear();
      if (action.dataset.yearsAction === "none") compareYears.forEach(value => hiddenCompareYears.add(value));
      renderSharedViews();
      return;
    }
    const workspace = event.target.closest("[data-workspace]");
    const view = event.target.closest("[data-view]");
    if (workspace) activateDashboardView(workspaceLastView[workspace.dataset.workspace]);
    if (view) activateDashboardView(view.dataset.view);
  });
  document.querySelectorAll("#workspaceTabs, #viewTabs").forEach(tabs => tabs.addEventListener("keydown", event => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    const buttons = [...tabs.querySelectorAll("button")];
    const index = buttons.indexOf(document.activeElement);
    const next = event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + buttons.length) % buttons.length;
    event.preventDefault();
    const key = buttons[next].dataset.workspace || buttons[next].dataset.view;
    buttons[next].click();
    tabs.querySelector(`[data-workspace="${key}"], [data-view="${key}"]`).focus();
  }));
  document.getElementById("contextRules").value = qualificationSystem;
  syncDashboardContext("distance", dataset().group);
  syncQualificationAssumptions();
  renderWorkspaceNavigation();
  renderContextYears();
  decorateDashboard();
}