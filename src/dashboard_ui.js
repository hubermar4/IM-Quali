const dashboardContext = {distance: "im", gender: "Male", ageGroup: "30-34"};
const qualificationAssumptions = {mode: "strict", extraPlaces: 0, legacyExtraPlaces: 0, fallback: false};
let dashboardReturnView = null;
const cutoffLabels = {strict: "Strict allocation", places: "Manual extra places", reported: "Reported last accepted", density: "Match-density boundary", scan: "15-absence scan"};
const cutoffApproaches = [
  {mode: "strict", label: cutoffLabels.strict, color: "#006d77"},
  {mode: "places", label: cutoffLabels.places, color: "#e76f51"},
  {mode: "reported", label: cutoffLabels.reported, color: "#495057"},
  {mode: "density", label: cutoffLabels.density, color: "#b08900"},
  {mode: "scan", label: cutoffLabels.scan, color: "#277da1"},
];
const dashboardWorkspaces = {
  explorer: {label: "Race Explorer", views: ["statistics", "overall", "splits"]},
  compare: {label: "Compare Races", views: ["compare"]},
  qualification: {label: "Qualification", views: ["qualification", "easiest", "odds", "kona", "crossrace"]},
  course: {label: "Course Analysis", views: ["experimental"]},
};
const dashboardViewLabels = {
  statistics: "Participation", overall: "Finish Times", splits: "Athletes & Splits",
  compare: "Race Comparison", qualification: "Race Targets", easiest: "Race Finder",
  odds: "Historical Target Hits", kona: "Kona Evidence", crossrace: "Cross-race Analysis",
  experimental: "Course & Conditions",
};
const contextControlIds = {
  distance: ["oddsDistance", "easiestDistance", "experimentalDistance", "compareSplitDistance", "compareStatisticsDistance", "compareScatterDistance", "compareFieldDistance", "compareSlotDistance"],
  gender: ["qualificationGender", "oddsGender", "easiestGender", "compareImGender", "compare703Gender", "compareScatterGender", "konaGender", "compareFieldGender"],
  ageGroup: ["qualificationAgeGroup", "oddsAgeGroup", "easiestAgeGroup", "compareImAgeGroup", "compare703AgeGroup", "compareScatterAgeGroup", "compareFieldAgeGroup", "konaAgeGroup"],
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
  const legacyButton = document.querySelector(`.legacy-tabs [data-tab="${view}"]`);
  if (legacyButton) legacyButton.click();
  else {
    activeTab = view;
    document.querySelectorAll(".tab-panel").forEach(panel => panel.classList.toggle("active", panel.id === `${view}Panel`));
  }
  renderWorkspaceNavigation();
  updateDashboardScope();
  decorateDashboard();
}

function clearDashboardReturn() {
  dashboardReturnView = null;
  document.getElementById("contextReturn").hidden = true;
}

function updateExtraPlacesControls() {
  const konaView = activeTab === "kona";
  const qualificationView = ["qualification", "easiest", "odds", "crossrace"].includes(activeTab);
  const trace = konaView ? selectedKonaTrace() : null;
  const poolAvailable = dashboardContext.distance === "im" && (konaView
    ? trace?.slot_scope === "gender" : qualificationView && qualificationSystem === "current");
  const legacyAvailable = dashboardContext.distance === "im" && (konaView
    ? trace?.slot_scope === "age group" : qualificationView && qualificationSystem === "historical");
  for (const [id, available] of [["contextExtraPlaces", poolAvailable], ["contextLegacyPlaces", legacyAvailable]]) {
    const control = document.getElementById(id);
    control.closest("label").hidden = !available;
    control.disabled = !available;
  }
}

function updateDashboardScope() {
  const allAthletes = ["splits", "overall", "statistics"].includes(activeTab);
  const qualificationView = ["qualification", "easiest", "odds", "crossrace"].includes(activeTab);
  const cycle = selectedKonaTrace()?.year || "2026";
  const konaView = activeTab === "kona";
  const trace = selectedKonaTrace();
  document.querySelector(".assumption-fields").hidden = !qualificationView && !konaView;
  document.querySelector(".qualification-approach").hidden = !qualificationView;
  document.getElementById("contextFallback").closest("label").hidden = konaView;
  updateExtraPlacesControls();
  document.querySelector("#contextGender").closest("label").hidden = activeTab === "experimental";
  document.querySelector("#contextAgeGroup").closest("label").hidden = activeTab === "experimental";
  document.querySelector(".context-fields:not(.assumption-fields)").hidden = allAthletes || ["kona", "compare"].includes(activeTab);
  for (const [id, distance] of [["compareImDistribution", "im"], ["compare703Distribution", "703"], ["compareImQualification", "im"], ["compare703Qualification", "703"]]) {
    document.getElementById(id).closest(".chart-panel").hidden = dashboardContext.distance !== distance;
  }
  document.getElementById("eventTitle").textContent = allAthletes || ["qualification", "crossrace"].includes(activeTab)
    ? `${dataset().name} / ${dashboardViewLabels[activeTab]}` : dashboardViewLabels[activeTab];
  document.getElementById("contextScope").textContent = allAthletes
    ? "All athletes. Gender and age group apply to qualification analyses only."
    : activeTab === "kona"
      ? `Kona ${cycle} cycle. Race-year filters affect displayed candidate editions, not matching or estimator evidence. Starter counts cover the full championship field.`
      : activeTab === "experimental"
        ? "Selected race years displayed. Published course/season factors and athlete calibration retain their full training scope."
        : "Selected race years. Course models and personal-result calibration retain their full source scope.";
  document.getElementById("eventSubtitle").textContent = allAthletes || ["qualification", "crossrace"].includes(activeTab)
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
  qualificationSystem = document.querySelector('input[name="contextRules"]:checked').value;
  qualificationAssumptions.extraPlaces = Math.max(0, Math.round(Number(document.getElementById("contextExtraPlaces").value) || 0));
  qualificationAssumptions.legacyExtraPlaces = Math.max(0, Math.round(Number(document.getElementById("contextLegacyPlaces").value) || 0));
  qualificationAssumptions.fallback = document.getElementById("contextFallback").checked;
  [qualificationDeclines, oddsDeclines, easiestDeclines].forEach(control => {
    control.value = qualificationAssumptions.extraPlaces;
  });
  updateExtraPlacesControls();
  qualificationLegacyDeclines.value = qualificationAssumptions.legacyExtraPlaces;
  oddsDeclines.disabled = easiestDeclines.disabled = dashboardContext.distance !== "im";
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
  const years = Object.keys(DATASETS[eventId].overall).sort().filter(compareYearVisible);
  const approaches = scopedCutoffApproaches();
  const standards = Object.fromEntries(years.map(year => [year, Object.fromEntries(approaches.map(({mode}) => [
    mode, approachStandard(eventId, year, gender, ageGroup, qualificationSystem, mode),
  ]))]));
  container.innerHTML = `<h2>Targets by approach · ${escapeHtml(divisionFor(gender, ageGroup))}</h2>
    <p class="note">All five approaches are evaluated independently for each race year. Scan labels identify each year's ranking scope and absence threshold. Missing or incompatible evidence stays explicit. Strict fallback means the strict allocation target is shown, not borrowed estimate evidence. Reported minute values and density estimates are approximate. Kona matches are not proof of slot acceptance.</p>
    <p class="note">The exploratory match-density boundary compares observed Kona-starter match rates by ranking position with a constant-rate model, then fits a two-rate breakpoint. It requires at least 3 matches before the breakpoint and positive BIC improvement after the penalty; it reports the best breakpoint and weighted 5%-95% rank/time support, with sensitivity to single-race matches. This is unverified matching density, not evidence of actual acceptance or declines. Race targets never place this boundary faster than strict allocation.</p>
    <div class="table-wrap"><table><thead><tr><th>Race year</th>${approaches.map(({label}) => `<th>${escapeHtml(label)}</th>`).join("")}</tr></thead><tbody>${years.map(year => `<tr><td>${yearCell(eventId, year)}</td>${approaches.map(({mode}) => `<td>${approachCell(standards[year][mode], mode)}</td>`).join("")}</tr>`).join("") || '<tr><td colspan="6" class="empty">No race years are visible.</td></tr>'}</tbody></table></div>`;
  lineChart("qualificationChart", years, approaches.map(({mode, label, color}) => ({
    label, color,
    values: years.map(year => {
      const standard = standards[year][mode];
      return standard?.available && Number.isFinite(standard.needed) ? standard.needed : null;
    }),
  })));
}

function approachStandard(eventId, year, gender, ageGroup, system, mode) {
  const strict = strictQualificationStandard(eventId, year, gender, ageGroup, system, {extraPlaces: 0});
  if (!strict) return null;
  const extraPlaces = strict.scope === "age group"
    ? qualificationAssumptions.legacyExtraPlaces : qualificationAssumptions.extraPlaces;
  return easiestQualificationStandard(eventId, year, gender, ageGroup, system, mode, extraPlaces);
}

function scopedCutoffApproaches() {
  return cutoffApproaches.map(approach => approach.mode !== "scan" ? approach : {
    ...approach,
    label: qualificationSystem === "current" ? "15-absence scan" : "Absence scan by scope",
  });
}

function scanScopeLabel(standard) {
  const pool = standard?.cutoffPool;
  const scan = pool?.cutoff_scan;
  const scope = standard?.scope === "age group" ? "age-group" : "gender-pool";
  const absences = scan?.consecutive_absences ?? (scope === "age-group" ? 3 : 15);
  return `${absences}-absence ${scope} scan`;
}

function approachCell(standard, mode) {
  const scanLabel = mode === "scan" ? `<small>${escapeHtml(scanScopeLabel(standard))}</small><br>` : "";
  if (!standard) return `${scanLabel}<span title="No qualification target for this system and race year">No compatible target</span>`;
  if (!standard.available) {
    const reason = standard.unavailableReason || standard.cutoffSource || "Evidence unavailable";
    return `${scanLabel}<span title="${escapeHtml(reason)}">No estimate</span><br><small>${escapeHtml(reason)}</small>`;
  }
  const value = assumptionTime(standard);
  const fallback = standard.cutoffSource?.startsWith("Strict fallback");
  const source = fallback ? "Strict fallback" : standard.cutoffSource;
  return `${scanLabel}<strong>${fallback ? "Strict fallback · " : ""}${escapeHtml(value)}</strong><br><small>${escapeHtml(source || "")}</small>`;
}

function allRaceYears(eventId) {
  return Object.keys(DATASETS[eventId]?.overall || {}).sort().filter(compareYearVisible);
}

function ensureApproachPanel(id, title, chartId, chartTitle) {
  let panel = document.getElementById(id);
  if (panel) return panel;
  panel = document.createElement("section");
  panel.id = id;
  panel.innerHTML = `<h2>${title}</h2><p class="note">Each method uses only compatible evidence for that race year. Missing years are marked, not filled from another edition.</p><div class="table-wrap"><table><thead></thead><tbody></tbody></table></div><div class="chart-panel wide"><h3>${chartTitle}</h3><svg id="${chartId}" class="chart" viewBox="0 0 1000 400"></svg></div>`;
  return panel;
}

function renderOddsApproaches() {
  const group = oddsDistance.value;
  const gender = oddsGender.value;
  const ageGroup = oddsAgeGroup.value;
  const entered = parseTime(oddsTime.value);
  const averageBasis = oddsTimeBasis.value === "average";
  const division = divisionFor(gender, ageGroup);
  const eventIds = oddsEventIds();
  const approaches = scopedCutoffApproaches();
  const byRace = eventIds.map(eventId => {
    const rows = allRaceYears(eventId).map(year => {
      const standards = Object.fromEntries(approaches.map(({mode}) => [mode,
        approachStandard(eventId, year, gender, ageGroup, qualificationSystem, mode),
      ]));
      const factor = courseFactor(eventId, year);
      const modified = isModifiedCourse(eventId, year);
      const expected = Number.isFinite(entered) && (!averageBasis || Number.isFinite(factor))
        ? entered * (averageBasis ? factor : 1) : null;
      return {year, standards, expected, factor, modified};
    });
    return {eventId, rows};
  });
  const section = document.getElementById("oddsApproachComparison");
  const table = section.querySelector("table");
  table.querySelector("thead").innerHTML = `<tr><th>Race</th><th>Year</th>${approaches.map(({label}) => `<th>${escapeHtml(label)}<br><small>target · result</small></th>`).join("")}</tr>`;
  table.querySelector("tbody").innerHTML = byRace.flatMap(({eventId, rows}) => rows.map(row => `<tr><td>${escapeHtml(DATASETS[eventId].name)}</td><td>${yearCell(eventId, row.year)}</td>${approaches.map(({mode}) => {
    const standard = row.standards[mode];
    if (row.modified) return `<td>${mode === "scan" ? `<small>${escapeHtml(scanScopeLabel(standard))}</small><br>` : ""}Excluded: modified course</td>`;
    if (!standard?.available) {
      const reason = standard?.unavailableReason || standard?.cutoffSource || "No target for this race year";
      return `<td>${approachCell(standard, mode)}<br><small>${escapeHtml(reason)}</small></td>`;
    }
    if (!Number.isFinite(row.expected)) return `<td>${approachCell(standard, mode)}<br><small>Enter a target time to evaluate</small></td>`;
    const hit = row.expected <= standard.needed;
    return `<td>${approachCell(standard, mode)}<br><small>${hit ? "Hit" : "Not hit"} · ${escapeHtml(duration(row.expected))} expected</small></td>`;
  }).join("")}</tr>`)).join("") || '<tr><td colspan="7" class="empty">No race years are visible.</td></tr>';
  const series = byRace.flatMap(({eventId, rows}) => approaches.map(({mode, label, color}) => ({
    label: `${DATASETS[eventId].name} · ${label}`,
    color,
    thresholds: rows.flatMap(row => {
      const standard = row.standards[mode];
      const factor = averageBasis ? row.factor : 1;
      return !row.modified && standard?.available && Number.isFinite(standard.needed) && Number.isFinite(factor)
        ? [standard.needed / factor] : [];
    }),
  })));
  stepShareChart("oddsApproachChart", series, entered);
  section.querySelector(".note").textContent = `${division} · ${group === "im" ? "IRONMAN 140.6" : "IRONMAN 70.3"}. Each race-year row shows its target and whether your entered time meets it for every approach; the chart summarizes compatible years. Modified courses are excluded. Strict fallback means the strict target stands in for an unavailable estimate and is identified explicitly.`;
}

function renderFinderApproaches() {
  const group = easiestDistance.value;
  const gender = easiestGender.value;
  const ageGroup = easiestAgeGroup.value;
  const division = divisionFor(gender, ageGroup);
  const eventIds = (raceGroups()[group] || []).filter(isQualifyingEvent);
  const profile = easiestProfile(group, division);
  const averageTransitions = typicalTransitions(group);
  const averageTime = profile.used
    ? SWIM_BIKE_RUN.reduce((sum, split) => sum + profile.splits[split], 0) + profile.transitionRatio * averageTransitions
    : parseTime(easiestTypedTime);
  const model = groupModel(group);
  const sigma = (model.fit?.overall?.residual_sd ?? 0.036) * (profile.used ? Math.sqrt(1 + 1 / profile.used) : 1);
  const approaches = scopedCutoffApproaches();
  const raceRows = eventIds.map(eventId => ({eventId, rows: allRaceYears(eventId).map(year => {
    const standards = Object.fromEntries(approaches.map(({mode}) => [mode,
      approachStandard(eventId, year, gender, ageGroup, qualificationSystem, mode),
    ]));
    const modified = isModifiedCourse(eventId, year);
    const expected = modified || !Number.isFinite(averageTime) ? null
      : predictRaceYear(eventId, year, profile.used ? profile.splits : null, profile.transitionRatio, averageTime);
    return {year, standards, expected, modified};
  })}));
  const section = document.getElementById("finderApproachComparison");
  const table = section.querySelector("table");
  table.querySelector("thead").innerHTML = `<tr><th>Race</th><th>Year</th>${approaches.map(({label}) => `<th>${escapeHtml(label)}<br><small>target · margin · chance</small></th>`).join("")}</tr>`;
  table.querySelector("tbody").innerHTML = raceRows.flatMap(({eventId, rows}) => rows.map(row => `<tr><td>${escapeHtml(DATASETS[eventId].name)}</td><td>${yearCell(eventId, row.year)}</td>${approaches.map(({mode}) => {
    const standard = row.standards[mode];
    const scanLabel = mode === "scan" ? `<small>${escapeHtml(scanScopeLabel(standard))}</small><br>` : "";
    if (row.modified) return `<td>${scanLabel}Excluded: modified course</td>`;
    if (!standard?.available) return `<td>${approachCell(standard, mode)}</td>`;
    if (!row.expected) return `<td>${scanLabel}No expected time or course factor</td>`;
    const margin = standard.needed - row.expected.total;
    const chance = standard.needed === Infinity ? 1 : standard.needed === -Infinity ? 0 : normalCdf(Math.log(standard.needed / row.expected.total) / sigma);
    return `<td>${scanLabel}<strong>${assumptionTime(standard)}</strong><br>${signedDuration(margin)} · ${Math.round(100 * chance)}%</td>`;
  }).join("")}</tr>`)).join("") || '<tr><td colspan="7" class="empty">No race years are visible.</td></tr>';
  const chartSeries = approaches.map(({mode, label, color}) => ({
    label, color,
    values: raceRows.map(({rows}) => rows.flatMap(row => {
      const standard = row.standards[mode];
      if (row.modified || !row.expected || !standard?.available || !Number.isFinite(standard.needed)) return [];
      return [{year: row.year, value: standard.needed - row.expected.total,
        detail: `${neededText(standard.needed)} target · ${duration(row.expected.total)} expected · ${label}`}];
    })),
  }));
  categoryPointChart("finderApproachChart", raceRows.map(({eventId}) => DATASETS[eventId].name), chartSeries,
    {includeZero: true, formatValue: signedDuration, formatTick: signedDurationShort, yAxisLabel: "Target minus expected time"});
  section.querySelector(".note").textContent = `${division} · all five approaches are shown per race year. Chance uses the existing day-to-day variation model; it is not a historical acceptance probability. Missing/incompatible evidence and modified courses are not silently replaced.`;
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
  for (const eventId of oddsEventIds()) {
    const body = document.getElementById("oddsRankingBody");
    if (![...body.rows].some(row => row.cells[0]?.textContent === DATASETS[eventId].name)) {
      const row = body.insertRow();
      row.innerHTML = `<td><button type="button" class="race-link" data-target-race="${eventId}">${escapeHtml(DATASETS[eventId].name)}</button></td><td colspan="9">No compatible target for selected race years. Not ranked.</td>`;
    }
  }
  document.getElementById("easiestRankingNote").textContent = `This ranking is the strict-allocation baseline. The comparison below evaluates strict, manual extra places, reported last accepted, density estimate, and the ${qualificationSystem === "current" ? "15-absence scan" : "scope-specific absence scan"}. Incompatible or unavailable evidence is marked per race year; strict fallback is identified explicitly. Chance is modelled, not historical acceptance probability.`;
  const oddsNote = document.getElementById("oddsRankingNote");
  oddsNote.textContent = `${oddsNote.textContent.split(" Selected cutoff:")[0]} All five cutoff approaches are compared below. Historical target hits are not verified slot acceptance; incompatible race years are marked unavailable rather than borrowing another edition's evidence.`;
  const oddsHeader = document.getElementById("oddsRankingHead").querySelectorAll("th")[2];
  if (oddsHeader) oddsHeader.textContent = "Historical Target Hits";
  const coverageHeader = document.getElementById("easiestRankingHead").querySelectorAll("th")[4];
  if (coverageHeader) coverageHeader.title = "The main ranking uses strict allocation; the comparison below shows all five approaches per race year.";
}

function decorateDashboard() {
  updateDashboardScope();
  renderSelectedQualification();
  renderOddsApproaches();
  renderFinderApproaches();
  decorateQualificationRankings();
  document.getElementById("ageGroupTargetChartTitle").textContent = "Strict allocation context by age group";
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
    .qualification-approach {border:0; padding:0; margin:0; min-width:min(100%,520px)}
    .qualification-approach legend {font-size:12px; color:var(--muted); margin-bottom:5px}
    .segmented-control {display:flex; border:1px solid var(--line); border-radius:4px; overflow:hidden; min-height:38px}
    .segmented-control label {display:flex; align-items:center; gap:7px; padding:7px 10px; background:#f4f7f5; cursor:pointer; flex:1}
    .segmented-control label + label {border-left:1px solid var(--line)}
    .segmented-control label:has(input:checked) {background:#dcebe8; color:var(--ink); font-weight:700}
    .segmented-control input {margin:0; accent-color:var(--accent)}
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
      <label class="context-gender">Gender<select id="contextGender"><option value="Male">Men</option><option value="Female">Women</option></select></label>
      <label class="context-age-group">Age group<select id="contextAgeGroup"></select></label>
    </div><div class="context-fields assumption-fields">
      <fieldset class="qualification-approach"><legend>Qualification approach</legend><div class="segmented-control" role="radiogroup" aria-label="Qualification approach">
        <label><input type="radio" name="contextRules" value="historical"><span>Historically correct rules</span></label>
        <label><input type="radio" name="contextRules" value="current" checked><span>Current performance pool on historical results</span></label>
      </div></fieldset>
      <label>Pool extra places<input id="contextExtraPlaces" type="number" min="0" step="1" value="0"></label>
      <label>Legacy AG extra places<input id="contextLegacyPlaces" type="number" min="0" step="1" value="0" disabled></label>
      <label class="binary-label"><input type="checkbox" id="contextFallback">Use strict fallback when evidence is unavailable</label>
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
  const oddsApproaches = ensureApproachPanel("oddsApproachComparison", "Historical target hits by cutoff approach", "oddsApproachChart", "Share of race years meeting your time");
  document.getElementById("oddsPanel").append(oddsApproaches);
  const finderApproaches = ensureApproachPanel("finderApproachComparison", "Race Finder by cutoff approach", "finderApproachChart", "Target margin by race and year");
  document.getElementById("easiestPanel").append(finderApproaches);
  const crossRacePanel = document.createElement("div");
  crossRacePanel.id = "crossracePanel";
  crossRacePanel.className = "tab-panel";
  crossRacePanel.setAttribute("role", "tabpanel");
  crossRacePanel.setAttribute("aria-labelledby", "view-crossrace");
  crossRacePanel.innerHTML = '<p class="note">Strict allocation, qualification cutoffs, slot pressure and uncertainty compared across qualifying races. The selected qualification approach applies to all charts here.</p><section id="qualificationComparisons"><h2>Cross-race qualification</h2><div class="chart-grid"></div></section>';
  document.getElementById("oddsPanel").before(crossRacePanel);
  const comparisons = document.getElementById("qualificationComparisons");
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
  [easiestDeclines, oddsDeclines].forEach(control => control.closest("label")?.classList.add("local-context-control"));
  [qualificationGender, qualificationAgeGroup, qualificationDeclines, qualificationLegacyDeclines].forEach(control => control.closest("label")?.classList.add("local-context-control"));
  experimentalDistance.closest("label").classList.add("local-context-control");
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
  document.querySelectorAll('input[name="contextRules"]').forEach(control => control.addEventListener("change", syncQualificationAssumptions));
  document.getElementById("contextFallback").addEventListener("change", syncQualificationAssumptions);
  document.getElementById("contextExtraPlaces").addEventListener("input", syncQualificationAssumptions);
  document.getElementById("contextLegacyPlaces").addEventListener("input", syncQualificationAssumptions);
  qualificationLegacyDeclines.addEventListener("input", () => {
    document.getElementById("contextLegacyPlaces").value = qualificationLegacyDeclines.value;
    syncQualificationAssumptions();
  }, true);
  [qualificationDeclines, oddsDeclines, easiestDeclines].forEach(control => control.addEventListener("input", () => {
    document.getElementById("contextExtraPlaces").value = control.value;
    syncQualificationAssumptions();
  }, true));
  [qualificationAgeGroup, qualificationGender].forEach(control => control.addEventListener("change", renderSelectedQualification));
  [oddsDistance, oddsGender, oddsAgeGroup, oddsTimeBasis].forEach(control => control.addEventListener("change", renderOddsApproaches));
  oddsTime.addEventListener("input", renderOddsApproaches);
  [easiestDistance, easiestGender, easiestAgeGroup].forEach(control => control.addEventListener("change", renderFinderApproaches));
  easiestTime.addEventListener("input", renderFinderApproaches);
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
      clearDashboardReturn();
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
    if (workspace || view) clearDashboardReturn();
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
  document.querySelector(`input[name="contextRules"][value="${qualificationSystem}"]`).checked = true;
  syncDashboardContext("distance", dataset().group);
  syncQualificationAssumptions();
  renderWorkspaceNavigation();
  renderContextYears();
  decorateDashboard();
}