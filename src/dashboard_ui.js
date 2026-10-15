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
const qualificationSteps = ["qtime", "qdifficulty", "qualification", "easiest"];
const dashboardWorkspaces = {
  explorer: {label: "Race Explorer", views: ["statistics", "overall", "splits"]},
  compare: {label: "Compare Races", views: ["compare"]},
  qualification: {label: "Qualification", views: qualificationSteps},
  course: {label: "Course Analysis", views: ["experimental"]},
};
const dashboardViewLabels = {
  statistics: "Participation", overall: "Finish Times", splits: "Athletes & Splits",
  compare: "Race Comparison", qtime: "1 · Your time", qdifficulty: "2 · Race difficulty",
  qualification: "3 · Qualification targets", easiest: "4 · Where to qualify",
  experimental: "Course & Conditions",
};
const qualificationStepIntro = {
  qtime: "Step 1 of 4 · Everything in this workspace starts from one number: your finish time on a standard course (an average qualifying race-year in average conditions). Type it, or add past results and it is derived split by split, corrected for each course, its race-day conditions and your age group. Gender and age group above are those of your next race.",
  qdifficulty: "Step 2 of 4 · How fast each qualifying race is, as raced and converted to a standard course, and the time you would be expected to finish there. +5% means the same athlete is 5% slower than on a standard course.",
  qualification: "Step 3 of 4 · Qualification targets for the race selected above: slots, the finish time needed with strict allocation (every slot accepted), how far the slots rolled down in practice (estimated from World Championship start lists in Kona and Nice), and the targets on a standard course.",
  easiest: "Step 4 of 4 · Combines your time (step 1), each race's difficulty (step 2) and its targets (step 3) into an estimated chance per race. Expand the sections below for how often your time would have qualified and for cross-race charts.",
};
const qualificationStepNext = {qtime: "qdifficulty", qdifficulty: "qualification", qualification: "easiest"};
const contextControlIds = {
  distance: ["oddsDistance", "easiestDistance", "experimentalDistance", "compareSplitDistance", "compareStatisticsDistance", "compareScatterDistance", "compareFieldDistance", "compareSlotDistance"],
  gender: ["qualificationGender", "oddsGender", "easiestGender", "compareImGender", "compare703Gender", "compareScatterGender", "konaGender", "compareFieldGender"],
  ageGroup: ["qualificationAgeGroup", "oddsAgeGroup", "easiestAgeGroup", "compareImAgeGroup", "compare703AgeGroup", "compareScatterAgeGroup", "compareFieldAgeGroup", "konaAgeGroup"],
};
let activeWorkspace = "explorer";
const workspaceLastView = {explorer: "splits", compare: "compare", qualification: "qtime", course: "experimental"};

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
    updateTitle();
  }
  if (view === "qtime") renderEasiestTab();
  if (view === "easiest") renderOdds();
  renderWorkspaceNavigation();
  updateDashboardScope();
  decorateDashboard();
}

function clearDashboardReturn() {
  dashboardReturnView = null;
  document.getElementById("contextReturn").hidden = true;
}

function updateExtraPlacesControls() {
  // Extra places only change targets (step 3) and the race ranking (step 4).
  const targetView = ["qualification", "easiest"].includes(activeTab);
  const poolAvailable = dashboardContext.distance === "im" && targetView && qualificationSystem === "current";
  const legacyAvailable = dashboardContext.distance === "im" && targetView && qualificationSystem === "historical";
  for (const [id, available] of [["contextExtraPlaces", poolAvailable], ["contextLegacyPlaces", legacyAvailable]]) {
    const control = document.getElementById(id);
    control.closest("label").hidden = !available;
    control.disabled = !available;
  }
}

function updateDashboardScope() {
  const allAthletes = ["splits", "overall", "statistics"].includes(activeTab);
  const targetView = ["qualification", "easiest"].includes(activeTab);
  document.querySelector(".assumption-fields").hidden = !targetView;
  document.querySelector(".qualification-approach").hidden = !targetView;
  document.getElementById("contextFallback").closest("label").hidden = !targetView;
  updateExtraPlacesControls();
  document.querySelector("#contextGender").closest("label").hidden = activeTab === "experimental";
  document.querySelector("#contextAgeGroup").closest("label").hidden = activeTab === "experimental";
  document.querySelector(".context-fields:not(.assumption-fields)").hidden = allAthletes || activeTab === "compare";
  for (const [id, distance] of [["compareImDistribution", "im"], ["compare703Distribution", "703"], ["compareImQualification", "im"], ["compare703Qualification", "703"]]) {
    document.getElementById(id).closest(".chart-panel").hidden = dashboardContext.distance !== distance;
  }
  const perRace = allAthletes || activeTab === "qualification";
  document.getElementById("eventTitle").textContent = perRace
    ? `${dataset().name} / ${dashboardViewLabels[activeTab]}` : dashboardViewLabels[activeTab];
  document.getElementById("contextScope").textContent = allAthletes
    ? "All athletes. Gender and age group apply to qualification analyses only."
    : activeTab === "experimental"
      ? "Selected race years displayed. Published course/season factors and athlete calibration retain their full training scope."
      : activeTab === "qtime"
        ? "Your results are converted with course factors fitted on all race years; the year selection does not change them."
        : "Selected race years. Course models and personal-result calibration retain their full source scope.";
  document.getElementById("eventSubtitle").textContent = perRace
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
  return `${label}${reported}<br><button type="button" class="context-action" data-evidence-race="${escapeHtml(standard.eventId)}" data-evidence-year="${escapeHtml(standard.year)}" data-evidence-cycle="${escapeHtml(standard.cutoffRoster || standard.cutoffCycle || "2026")}">WC start-list evidence</button>`;
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
  const evidenceNote = qualificationSystem === "current"
    ? `<p class="note">Current-rule density and scan targets for each race year use the start list of the World Championship that race year actually qualified for (e.g. Austria 2017 → Kona 2017 starters; in 2023–2025 Kona and Nice combined), re-ranked under the current rules and allocation. Race years without a local start list for their cycle (e.g. 2027-cycle races) show no estimate. Before the 2026 cycle those starters were selected by age-group rules, so their gender-pool boundary is only indicative.</p>`
    : "";
  container.innerHTML = `<h2>Targets by approach · ${escapeHtml(divisionFor(gender, ageGroup))}</h2>
    <p class="note">All five approaches are evaluated independently for each race year. Scan labels identify each year's ranking scope and absence threshold. Missing or incompatible evidence stays explicit. Strict fallback means the strict allocation target is shown, not borrowed estimate evidence. Reported minute values and density estimates are approximate. Kona matches are not proof of slot acceptance.</p>
    ${evidenceNote}
    <p class="note">The exploratory match-density boundary compares observed Kona-starter match rates by ranking position with a constant-rate model, then fits a two-rate breakpoint. It requires at least 3 matches before the breakpoint and positive BIC improvement after the penalty; it reports the best breakpoint and weighted 5%-95% rank/time support, with sensitivity to single-race matches. This is unverified matching density, not evidence of actual acceptance or declines. Race targets never place this boundary faster than strict allocation.</p>
    <div class="table-wrap"><table><thead><tr><th>Race year</th>${approaches.map(({label}) => `<th>${escapeHtml(label)}</th>`).join("")}</tr></thead><tbody>${years.map(year => `<tr><td>${yearCell(eventId, year)}</td>${approaches.map(({mode}) => `<td>${approachCell(standards[year][mode], mode)}</td>`).join("")}</tr>`).join("") || '<tr><td colspan="6" class="empty">No race years are visible.</td></tr>'}</tbody></table></div>
    ${approachSummaryTable(eventId, years, approaches, standards)}`;
  lineChart("qualificationChart", years, approaches.map(({mode, label, color}) => ({
    label, color,
    values: years.map(year => {
      const standard = standards[year][mode];
      return standard?.available && Number.isFinite(standard.needed) ? standard.needed : null;
    }),
  })));
}

// Cross-year summary of each approach's raw target; modified courses are excluded.
function approachSummaryTable(eventId, years, approaches, standards) {
  const comparable = years.filter(year => !isModifiedCourse(eventId, year));
  const rows = approaches.map(({mode, label}) => {
    const points = comparable
      .map(year => ({year, standard: standards[year][mode]}))
      .filter(({standard}) => standard?.available && Number.isFinite(standard.needed));
    const sorted = points.map(({standard}) => standard.needed).sort((left, right) => left - right);
    const fit = points.length >= 3 ? linearFit(points.map(({year, standard}) => ({x: Number(year), y: standard.needed}))) : null;
    const latest = points.at(-1);
    return `<tr><td>${escapeHtml(label)}</td><td>${points.length} / ${comparable.length}</td>`
      + `<td>${sorted.length ? neededText(quantile(sorted, 0.5)) : "—"}</td>`
      + `<td>${sorted.length ? `${neededText(sorted[0])} – ${neededText(sorted.at(-1))}` : "—"}</td>`
      + `<td>${fit ? `${signedDuration(fit.slope)} / year` : "—"}</td>`
      + `<td>${latest ? `${assumptionTime(latest.standard)} (${escapeHtml(latest.year)})` : "—"}</td></tr>`;
  }).join("");
  return `<h3>Summary across selected race years</h3>
    <p class="note">Finite targets only ("any finish" years are not counted). Trend is the least-squares slope over race years with at least three values; negative means the target got faster, i.e. harder.</p>
    <div class="table-wrap"><table><thead><tr><th>Approach</th><th>Years with target</th><th>Median</th><th>Fastest – slowest</th><th>Trend</th><th>Latest</th></tr></thead><tbody>${rows}</tbody></table></div>`;
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
  const series = approaches.map(({mode, label, color}) => ({
    label, color,
    thresholds: byRace.flatMap(({rows}) => rows.flatMap(row => {
      const standard = row.standards[mode];
      const factor = averageBasis ? row.factor : 1;
      return !row.modified && standard?.available && Number.isFinite(standard.needed) && Number.isFinite(factor)
        ? [standard.needed / factor] : [];
    })),
  }));
  stepShareChart("oddsApproachChart", series, entered);
  section.querySelector(".note").textContent = `${division} · ${group === "im" ? "IRONMAN 140.6" : "IRONMAN 70.3"}. Each race-year row shows its target and whether your entered time meets it for every approach; the chart pools the compatible race-years of all listed races per approach. Modified courses are excluded. Strict fallback means the strict target stands in for an unavailable estimate and is identified explicitly.`;
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
  const oddsNote = document.getElementById("oddsRankingNote");
  const oddsSuffix = " All five cutoff approaches are compared below. Historical target hits are not verified slot acceptance; incompatible race years are marked unavailable rather than borrowing another edition's evidence.";
  if (!oddsNote.textContent.endsWith(oddsSuffix)) oddsNote.textContent += oddsSuffix;
  const oddsHeader = document.getElementById("oddsRankingHead").querySelectorAll("th")[2];
  if (oddsHeader) oddsHeader.textContent = "Historical Target Hits";
}

function stepMetrics(items) {
  return `<div class="metrics">${items.map(([label, value]) => `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</div>`;
}

function renderYourTimeSummary() {
  const container = document.getElementById("qtimeSummary");
  if (!container) return;
  const ability = currentAbility();
  const {profile, averageTime, division, transitions} = ability;
  const basis = profile.used
    ? `${profile.used} past result${profile.used === 1 ? "" : "s"}, split by split`
    : "Typed finish time";
  const splits = profile.used
    ? `<div class="table-wrap" style="max-height:none"><table><thead><tr><th>On a standard course</th><th>Swim</th><th>Bike</th><th>Run</th><th>T1 + T2</th><th>Total</th></tr></thead><tbody><tr><td>${escapeHtml(division)}</td>${SWIM_BIKE_RUN.map(split => `<td>${duration(profile.splits[split])}</td>`).join("")}<td>${duration(profile.transitionRatio * transitions)}</td><td><strong>${duration(averageTime)}</strong></td></tr></tbody></table></div>`
    : `<p class="note">No usable past results for ${escapeHtml(division)} at this distance yet, so the typed time is used. Add results below to derive it from your swim, bike and run.</p>`;
  container.innerHTML = stepMetrics([
    ["Your finish time on a standard course", Number.isFinite(averageTime) ? duration(averageTime) : "Enter HH:MM:SS"],
    ["Based on", basis],
    ["Next race age group", division],
  ]) + splits;
}

function renderRaceDifficulty() {
  const container = document.getElementById("qdifficultyContent");
  if (!container || activeTab !== "qdifficulty") return;
  const group = dashboardContext.distance;
  const division = divisionFor(dashboardContext.gender, dashboardContext.ageGroup);
  const {profile, averageTime} = currentAbility(group, division);
  const splitAbility = profile.used ? profile.splits : null;
  const races = (raceGroups()[group] || []).filter(isQualifyingEvent).map(eventId => {
    const rows = allRaceYears(eventId).map(year => {
      const factor = courseFactor(eventId, year);
      const stats = DATASETS[eventId].division_stats?.[year]?.[division] || {};
      const modified = isModifiedCourse(eventId, year);
      const predicted = !modified && Number.isFinite(averageTime)
        ? predictRaceYear(eventId, year, splitAbility, profile.transitionRatio, averageTime)?.total ?? null : null;
      const standardTime = value => Number.isFinite(value) && factor ? value / factor : null;
      return {
        year, factor, modified, predicted, finishers: stats.finishers || 0,
        splits: Object.fromEntries(SWIM_BIKE_RUN.map(split => [split, courseFactor(eventId, year, split)])),
        conditions: conditionsFactor(eventId, year),
        median: stats.median ?? null, medianStandard: standardTime(stats.median),
        winner: stats.winner ?? null, winnerStandard: standardTime(stats.winner),
      };
    });
    const factors = rows.filter(row => !row.modified).map(row => row.factor).filter(Number.isFinite).sort((left, right) => left - right);
    return {
      eventId, rows,
      course: courseEffect(eventId, "overall"),
      splitEffects: Object.fromEntries(SWIM_BIKE_RUN.map(split => [split, courseEffect(eventId, split)])),
      factorRange: factors.length ? [factors[0], factors.at(-1)] : null,
      median: lowerMedian(rows.filter(row => !row.modified).map(row => row.median).filter(Number.isFinite)),
      medianStandard: lowerMedian(rows.map(row => row.medianStandard).filter(Number.isFinite)),
      predicted: lowerMedian(rows.map(row => row.predicted).filter(Number.isFinite)),
    };
  }).sort((left, right) => (left.course ?? Infinity) - (right.course ?? Infinity));
  const summaryRows = races.map(race => `<tr><td><button type="button" class="race-link" data-target-race="${race.eventId}">${escapeHtml(DATASETS[race.eventId].name)}</button></td>`
    + `<td>${race.rows.filter(row => !row.modified && Number.isFinite(row.factor)).length}</td>`
    + `<td><strong>${signedPercent(race.course)}</strong></td>${SWIM_BIKE_RUN.map(split => `<td>${signedPercent(race.splitEffects[split])}</td>`).join("")}`
    + `<td>${race.factorRange ? `${signedPercent(race.factorRange[0])} to ${signedPercent(race.factorRange[1])}` : "—"}</td>`
    + `<td>${duration(race.median)}</td><td>${duration(race.medianStandard)}</td><td><strong>${duration(race.predicted)}</strong></td></tr>`).join("");
  const yearRows = races.flatMap(race => race.rows.map(row => `<tr><td>${escapeHtml(DATASETS[race.eventId].name)}</td><td>${yearCell(race.eventId, row.year)}</td>`
    + `<td>${row.modified ? "Modified course" : signedPercent(row.factor)}</td>${SWIM_BIKE_RUN.map(split => `<td>${signedPercent(row.splits[split])}</td>`).join("")}`
    + `<td>${signedPercent(row.conditions)}</td><td>${row.finishers}</td><td>${duration(row.median)}</td><td>${duration(row.medianStandard)}</td>`
    + `<td>${duration(row.winner)}</td><td>${duration(row.winnerStandard)}</td><td>${duration(row.predicted)}</td></tr>`)).join("");
  container.innerHTML = `<h2>Course difficulty by race · ${escapeHtml(division)}</h2>
    <p class="note">Course effects are season-adjusted (equipment trend removed) and fitted on athletes who raced several race-years. "Race-year range" is the spread of course × season × conditions factors over the selected years. Medians are ${escapeHtml(division)} finishers; "standard course" divides each race-year's time by its factor. Your predicted time is the median over the selected race-years${profile.used ? ", built split by split from your results" : " of your standard-course time × each race-year factor"}. Sorted from fastest to slowest course.</p>
    <div class="table-wrap" style="max-height:none"><table><thead><tr><th>Race</th><th>Race-years</th><th>Course effect</th><th>Swim</th><th>Bike</th><th>Run</th><th>Race-year range</th><th>Median ${escapeHtml(division)} as raced</th><th>Median on a standard course</th><th>Your predicted time</th></tr></thead><tbody>${summaryRows || '<tr><td colspan="10" class="empty">No qualifying races at this distance.</td></tr>'}</tbody></table></div>
    <div class="chart-panel wide"><h3>Median ${escapeHtml(division)} finish: as raced vs. on a standard course, and your predicted time</h3><svg id="difficultyChart" class="chart" viewBox="0 0 1000 430"></svg></div>
    <details class="method"><summary>All race-years: factors, medians, winners and your predicted time</summary>
    <div class="table-wrap"><table><thead><tr><th>Race</th><th>Year</th><th>Race-year factor</th><th>Swim</th><th>Bike</th><th>Run</th><th title="Race-day conditions after removing course and season.">Conditions</th><th>${escapeHtml(division)} finishers</th><th>Median as raced</th><th>Median on standard course</th><th>Winner as raced</th><th>Winner on standard course</th><th>Your predicted time</th></tr></thead><tbody>${yearRows}</tbody></table></div></details>`;
  const point = (value, detail) => Number.isFinite(value) ? [{value, detail}] : [];
  const series = [
    {label: "Median as raced", color: "#9aa5a0", key: "median"},
    {label: "Median on a standard course", color: "#006d77", key: "medianStandard"},
    {label: "Your predicted time", color: "#e76f51", key: "predicted"},
  ].map(({label, color, key}) => ({label, color, values: races.map(race => race.rows.flatMap(row =>
    point(row[key], `${row.year} · ${label}: ${duration(row[key])}`).map(entry => ({...entry, year: row.year}))))}));
  categoryPointChart("difficultyChart", races.map(race => DATASETS[race.eventId].name), series,
    {formatValue: duration, formatTick: value => duration(value).slice(0, 5), yAxisLabel: "Finish time (HH:MM)"});
}

function genderSlotBreakdown(eventId, year, system) {
  const ds = DATASETS[eventId];
  if (system === "current") {
    const summary = ds.qualification.summaries.find(row => row.year === year);
    if (!summary) return null;
    const pool = key => slotAllocations[eventId]?.[key] ?? summary[`${key}_perf`];
    return {scope: "gender", Male: {auto: summary.male_auto, pool: pool("male")}, Female: {auto: summary.female_auto, pool: pool("female")}};
  }
  const rows = ds.historical_qualification.targets.filter(row => row.year === year);
  if (!rows.length) return null;
  if (rows[0].slot_scope === "age group") {
    const total = gender => rows.filter(row => row.gender === gender).reduce((sum, row) => sum + row.slots, 0);
    return {scope: "age group", Male: {total: total("Male")}, Female: {total: total("Female")}};
  }
  const pick = gender => {
    const row = rows.find(item => item.gender === gender);
    return row ? {auto: row.automatic_slots, pool: row.performance_slots} : {auto: 0, pool: 0};
  };
  return {scope: "gender", Male: pick("Male"), Female: pick("Female")};
}

function slotBreakdownText(breakdown) {
  if (!breakdown) return "—";
  if (breakdown.scope === "age group") {
    return `M ${breakdown.Male.total} · F ${breakdown.Female.total}<br><small>${breakdown.Male.total + breakdown.Female.total} age-group slots</small>`;
  }
  const total = ["Male", "Female"].reduce((sum, gender) => sum + breakdown[gender].auto + breakdown[gender].pool, 0);
  return `M ${breakdown.Male.auto} + ${breakdown.Male.pool} · F ${breakdown.Female.auto} + ${breakdown.Female.pool}<br><small>${total} slots: AG winners + gender pool</small>`;
}

// Roll-down implied by World Championship start lists: estimated last-accepted
// rank minus the allocated slots, i.e. slots declined or unclaimed.
function rollDownEvidence(standard, mode) {
  if (!standard?.available || !standard.estimatedCutoffUsed) return null;
  const pool = standard.cutoffPool;
  const rank = mode === "scan" ? pool?.cutoff_scan?.rank : null;
  // Starters of legacy cycles were selected per age group, so their depth in a
  // re-ranked gender pool is not a count of declined pool slots.
  const comparable = !(pool?.slot_scope === "gender" && pool?.ranking_cycle !== pool?.kona_cycle && Number(pool?.kona_cycle) < 2026);
  const passed = comparable && Number.isFinite(rank) && pool?.pool_slots > 0 ? Math.max(0, rank - pool.pool_slots) : null;
  return {standard, passed, comparable, slots: pool?.pool_slots, scope: pool?.slot_scope};
}

function rollDownCell(evidence, reason) {
  if (!evidence) return `<span title="${escapeHtml(reason || "No compatible evidence")}">—</span>`;
  const passed = Number.isFinite(evidence.passed)
    ? `<br><small>≈ ${evidence.passed} slot${evidence.passed === 1 ? "" : "s"} passed on (of ${evidence.slots} ${evidence.scope === "age group" ? "AG" : "pool"})</small>`
    : evidence.comparable || evidence.standard.mode !== "scan" ? "" : "<br><small>age-group-era starters: no decline count</small>";
  return `${escapeHtml(assumptionTime(evidence.standard))}${passed}`;
}

function renderTargetOverview() {
  const container = document.getElementById("targetOverview");
  if (!container) return;
  const eventId = eventSelect.value;
  if (!isQualifyingEvent(eventId)) {
    container.innerHTML = `<p class="note">${escapeHtml(DATASETS[eventId].name)} is a World Championship, not a qualifying race. Select a qualifying race in the event selector above.</p>`;
    return;
  }
  const gender = dashboardContext.gender;
  const ageGroup = dashboardContext.ageGroup;
  const division = divisionFor(gender, ageGroup);
  const {profile, averageTime} = currentAbility(DATASETS[eventId].group, division);
  const rows = allRaceYears(eventId).map(year => {
    const strict = approachStandard(eventId, year, gender, ageGroup, qualificationSystem, "strict");
    const get = mode => approachStandard(eventId, year, gender, ageGroup, qualificationSystem, mode);
    const scan = rollDownEvidence(get("scan"), "scan");
    const density = rollDownEvidence(get("density"), "density");
    const reported = rollDownEvidence(get("reported"), "reported");
    const factor = courseFactor(eventId, year);
    const modified = isModifiedCourse(eventId, year);
    const predicted = !modified && Number.isFinite(averageTime)
      ? predictRaceYear(eventId, year, profile.used ? profile.splits : null, profile.transitionRatio, averageTime)?.total ?? null : null;
    return {year, strict, scan, density, reported, factor, modified, predicted,
      breakdown: genderSlotBreakdown(eventId, year, qualificationSystem),
      standardTarget: Number.isFinite(strict?.needed) && factor ? strict.needed / factor : null,
      unavailable: get("scan")?.unavailableReason};
  });
  const finite = values => values.filter(Number.isFinite);
  const passedValues = finite(rows.map(row => row.scan?.passed));
  const margins = finite(rows.map(row => Number.isFinite(row.predicted) && Number.isFinite(row.strict?.needed) ? row.strict.needed - row.predicted : null));
  const body = rows.map(row => {
    if (!row.strict) return `<tr><td>${yearCell(eventId, row.year)}</td><td colspan="10">No slot data for these rules</td></tr>`;
    const strict = row.strict;
    const ageGroupSlots = strict.scope === "age group"
      ? `${strict.slots} ${escapeHtml(division)} slot${strict.slots === 1 ? "" : "s"}` : `${strict.qualifiers} strict qualifier${strict.qualifiers === 1 ? "" : "s"}`;
    const margin = Number.isFinite(row.predicted) ? strict.needed - row.predicted : null;
    return `<tr><td>${yearCell(eventId, row.year)}</td><td><small>${escapeHtml(strict.method || "")}</small></td><td>${slotBreakdownText(row.breakdown)}</td>`
      + `<td>${ageGroupSlots}<br><small>of ${strict.finishers} finishers</small></td>`
      + `<td><strong>${neededText(strict.needed)}</strong><br><small>${targetRouteText(strict)}</small></td>`
      + `<td>${row.modified ? "Modified course" : neededText(row.standardTarget)}</td>`
      + `<td>${rollDownCell(row.reported, "No documented report")}</td><td>${rollDownCell(row.scan, row.unavailable)}</td><td>${rollDownCell(row.density, row.unavailable)}</td>`
      + `<td>${duration(row.predicted)}</td><td>${margin === null ? "—" : `${signedDuration(margin)}${margin >= 0 ? " ✓" : ""}`}</td></tr>`;
  }).join("");
  container.innerHTML = `<h2>Slots, roll-down and targets · ${escapeHtml(division)}</h2>
    ${stepMetrics([
      ["Median strict target (as raced)", neededText(lowerMedian(finite(rows.map(row => row.strict?.needed))))],
      ["Median target on a standard course", neededText(lowerMedian(finite(rows.map(row => row.standardTarget))))],
      ["Median slots passed on (estimated)", passedValues.length ? `≈ ${lowerMedian(passedValues)} in ${passedValues.length} yr` : "No evidence"],
      ["Your median margin vs. strict target", margins.length ? signedDuration(lowerMedian(margins)) : "—"],
    ])}
    <div class="table-wrap" style="max-height:none"><table><thead><tr><th>Year</th><th>Rules</th><th title="Gender-pool years: automatic age-group winner slots + performance-pool slots. Legacy years: age-group slots per gender.">Slots (M · F)</th><th>${escapeHtml(division)} slots</th><th title="Finish time needed when every slot is accepted (no roll-down).">Strict target</th><th title="Strict target ÷ race-year course and conditions factor.">Strict target on a standard course</th><th>Reported last accepted</th><th title="Last World Championship starter before a run of unmatched athletes in the ranking.">Absence-scan estimate</th><th title="Rank where the density of World Championship starters drops.">Density estimate</th><th>Your predicted time</th><th>Your margin vs. strict</th></tr></thead><tbody>${body || '<tr><td colspan="11" class="empty">No race years are visible.</td></tr>'}</tbody></table></div>
    <p class="note">"Slots passed on" = absence-scan last-accepted rank − allocated slots: places declined or unclaimed (e.g. already qualified, absent at the roll-down) that rolled to the next athlete. It is inferred from where World Championship starters (Kona, and Nice in 2023–2025) stop appearing in the ranking, not an observed count, and is only given where those starters were selected under the same ranking rules (performance-pool cycles, or legacy age groups in historical mode). The density estimate is shown as a time only; its breakpoint is too unstable for a count. Estimates are never faster than the strict target. Positive margin = your predicted time beats the strict target.</p>`;
}

function decorateDashboard() {
  updateDashboardScope();
  renderYourTimeSummary();
  renderRaceDifficulty();
  renderTargetOverview();
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
    .step-intro {margin:0 0 18px !important; padding:11px 13px; color:#365048 !important; background:var(--accent-soft); border-left:3px solid var(--accent)}
    .step-next {display:flex; justify-content:flex-end; margin-top:28px}
    details.step-section {margin-top:24px; border-top:1px solid var(--line); padding-top:12px}
    details.step-section > summary {cursor:pointer; font-family:Georgia,"Times New Roman",serif; font-size:19px; padding:4px 0}
    details.step-section[open] > summary {margin-bottom:12px}
    #targetOverview .metrics, #qtimeSummary .metrics {grid-template-columns:repeat(auto-fit, minmax(180px, 1fr))}
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
  const stepSection = (summary, ...children) => {
    const section = document.createElement("details");
    section.className = "step-section";
    section.innerHTML = `<summary>${summary}</summary>`;
    section.append(...children);
    return section;
  };
  const embedPanel = panel => {
    panel.classList.remove("tab-panel", "active");
    panel.removeAttribute("role");
    panel.removeAttribute("aria-labelledby");
    return panel;
  };
  const createStepPanel = view => {
    const panel = document.createElement("div");
    panel.id = `${view}Panel`;
    panel.className = "tab-panel";
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", `view-${view}`);
    document.getElementById("qualificationPanel").before(panel);
    return panel;
  };
  const finder = document.getElementById("easiestPanel");
  finder.querySelector(":scope > p.note").remove();
  // Step 1: your standard-course time from a typed time or past results.
  const timePanel = createStepPanel("qtime");
  timePanel.innerHTML = '<section id="qtimeSummary"></section>';
  const finderControls = finder.querySelector(":scope > .controls");
  [easiestDistance, easiestGender, easiestAgeGroup].forEach(control => control.closest("label").classList.add("local-context-control"));
  easiestTime.closest("label").firstChild.textContent = "Finish time on a standard course (used without past results) ";
  const personal = finder.querySelector(":scope > section");
  personal.querySelector("h2").textContent = "Your past results (optional, recommended)";
  const strength = document.getElementById("easiestProfileTitle").closest("section");
  timePanel.append(finderControls, personal, strength);
  // Step 2: race difficulty as raced and on a standard course.
  createStepPanel("qdifficulty").innerHTML = '<section id="qdifficultyContent"></section>';
  // Step 3: targets of the selected race with roll-down evidence.
  const content = document.getElementById("qualificationContent");
  const allocation = stepSection("Slot allocation detail, what-if slot overrides and target charts", ...content.children);
  const overview = document.createElement("section");
  overview.id = "targetOverview";
  const konaPanel = embedPanel(document.getElementById("konaPanel"));
  const evidence = stepSection("World Championship start-list evidence (Kona + Nice): who qualified where, and how far slots rolled down", konaPanel);
  evidence.id = "wcEvidence";
  content.append(overview, stepSection("Compare all five cutoff approaches by year", selectedSummary), allocation, evidence);
  ["konaGender", "konaAgeGroup"].forEach(id => document.getElementById(id).closest("label").classList.add("local-context-control"));
  // Step 4: where to qualify, with target hits and cross-race charts on demand.
  const oddsPanel = embedPanel(document.getElementById("oddsPanel"));
  oddsPanel.querySelector(":scope > .controls").classList.add("local-context-control");
  oddsPanel.querySelector(":scope > p.note").textContent = "Uses your standard-course time from step 1, converted to each race-year with its course and conditions factor. A race-year counts as a hit when that time is at or below the time needed (age-group win or gender pool in performance-pool years; last allocated age-group slot in legacy years). Shortened race-years are excluded.";
  const oddsApproaches = ensureApproachPanel("oddsApproachComparison", "Historical target hits by cutoff approach", "oddsApproachChart", "Share of race years meeting your time");
  oddsPanel.append(oddsApproaches);
  const finderApproaches = ensureApproachPanel("finderApproachComparison", "Race Finder by cutoff approach", "finderApproachChart", "Target margin by race and year");
  const crossRacePanel = document.createElement("div");
  crossRacePanel.id = "crossracePanel";
  crossRacePanel.innerHTML = '<p class="note">Strict allocation, qualification cutoffs, slot pressure and uncertainty compared across qualifying races. The selected qualification approach applies to all charts here.</p><section id="qualificationComparisons"><h2>Cross-race qualification</h2><div class="chart-grid"></div></section>';
  finder.append(
    stepSection("Compare all five cutoff approaches per race-year", finderApproaches),
    stepSection("How often your time would have qualified (historical target hits)", oddsPanel),
    stepSection("Cross-race comparison charts", crossRacePanel),
  );
  for (const view of qualificationSteps) {
    const panel = document.getElementById(`${view}Panel`);
    const intro = document.createElement("p");
    intro.className = "note step-intro";
    intro.textContent = qualificationStepIntro[view];
    panel.prepend(intro);
    const next = qualificationStepNext[view];
    if (next) {
      const navigation = document.createElement("div");
      navigation.className = "step-next";
      navigation.innerHTML = `<button type="button" data-view="${next}">Next: ${dashboardViewLabels[next]} →</button>`;
      panel.append(navigation);
    }
  }
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
  const ranking = document.getElementById("easiestRankingTitle").closest("section");
  ranking.before(finder.querySelector(":scope > .metrics"));
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
  easiestTime.addEventListener("input", () => {
    renderFinderApproaches();
    renderYourTimeSummary();
  });
  document.addEventListener("click", event => {
    if (event.target.closest("#qtimePanel button")) setTimeout(renderYourTimeSummary);
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
        eventSelect.value = evidence.dataset.evidenceRace;
        syncDashboardContext("distance", dataset().group);
        document.getElementById("konaCycle").value = evidence.dataset.evidenceCycle || "2026";
        initializeKonaTrace();
        document.getElementById("konaRace").value = `${evidence.dataset.evidenceRace}|${evidence.dataset.evidenceYear}`;
        activateDashboardView("qualification");
        renderKonaTrace();
        const section = document.getElementById("wcEvidence");
        section.open = true;
        section.scrollIntoView({block: "start"});
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