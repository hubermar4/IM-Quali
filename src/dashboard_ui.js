const dashboardContext = {distance: "im", gender: "Male", ageGroup: "30-34"};
const qualificationAssumptions = {mode: "calibrated", extraPlaces: 0, legacyExtraPlaces: 0, fallback: false, rollDownFactor: 0};
let dashboardReturnView = null;
const cutoffLabels = {strict: "Strict allocation", matched: "Matched-slot cutoff", calibrated: "Rank-based roll-down factor", reported: "Reported last accepted", density: "Match-density boundary", scan: "15-absence gender-pool scan"};
const cutoffApproaches = [
  {mode: "strict", label: cutoffLabels.strict, color: "#006d77"},
  {mode: "matched", label: cutoffLabels.matched, color: "#d1495b"},
  {mode: "calibrated", label: cutoffLabels.calibrated, color: "#2a9d8f"},
  {mode: "reported", label: cutoffLabels.reported, color: "#495057"},
  {mode: "density", label: cutoffLabels.density, color: "#b08900"},
  {mode: "scan", label: cutoffLabels.scan, color: "#277da1"},
];
const qualificationSteps = ["qyou", "qtime", "qdifficulty", "qualification", "easiest"];
const dashboardWorkspaces = {
  explorer: {label: "Race Explorer", views: ["statistics", "overall", "splits"]},
  compare: {label: "Compare Races", views: ["compare"]},
  qualification: {label: "Qualification", views: qualificationSteps},
  course: {label: "Course Analysis", views: ["experimental", "backtest"]},
};
const dashboardViewLabels = {
  statistics: "Participation", overall: "Finish Times", splits: "Athletes & Splits",
  compare: "Race Comparison", qyou: "1 · You", qtime: "2 · Your time", qdifficulty: "3 · Race difficulty",
  qualification: "4 · Qualification targets", easiest: "5 · Where to qualify",
  experimental: "Course & Conditions", backtest: "Backtest",
};
const qualificationStepIntro = {
  qyou: "Choose your distance, gender and age group for your next race.",
  qtime: "Your finish time on a standard course, entered or derived from past results.",
  qdifficulty: "Race-year course and conditions factors and your expected time.",
  qualification: "Compare qualification targets and compatible World Championship evidence for a selected race.",
  easiest: "Recommendations use current rules on past results, independently of the historical analysis in Targets.",
};
const qualificationStepNext = {qyou: "qtime", qtime: "qdifficulty", qdifficulty: "qualification", qualification: "easiest"};
const contextControlIds = {
  distance: ["oddsDistance", "easiestDistance", "experimentalDistance", "compareSplitDistance", "compareStatisticsDistance", "compareScatterDistance", "compareFieldDistance", "compareSlotDistance"],
  gender: ["qualificationGender", "oddsGender", "easiestGender", "compareImGender", "compare703Gender", "compareScatterGender", "konaGender", "compareFieldGender"],
  ageGroup: ["qualificationAgeGroup", "oddsAgeGroup", "easiestAgeGroup", "compareImAgeGroup", "compare703AgeGroup", "compareScatterAgeGroup", "compareFieldAgeGroup", "konaAgeGroup"],
};
let activeWorkspace = "explorer";
const workspaceLastView = {explorer: "splits", compare: "compare", qualification: "qyou", course: "experimental"};

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
  if (view === "easiest") { renderCompare(); renderOdds(); }
  renderWorkspaceNavigation();
  updateDashboardScope();
  decorateDashboard();
}

function clearDashboardReturn() {
  dashboardReturnView = null;
  document.getElementById("contextReturn").hidden = true;
}

function updateExtraPlacesControls() {
  return;
}

function updateRollDownFactorControl(updateValue = true) {
  const input = document.getElementById("contextRollDownFactor");
  const status = document.getElementById("contextRollDownStatus");
  if (updateValue) {
    input.value = String(qualificationAssumptions.rollDownFactor);
    input.setAttribute("aria-invalid", "false");
  }
  if (input.getAttribute("aria-invalid") === "true") {
    status.textContent = "Enter a nonnegative factor. The last valid setting remains active.";
    return;
  }
  status.textContent = "Hypothetical additional declines per allocated slot; not observed or calibrated.";
}

function changeRollDownFactor() {
  const input = document.getElementById("contextRollDownFactor");
  const value = input.value === "" ? NaN : Number(input.value);
  if (!Number.isFinite(value) || value < 0) {
    input.setAttribute("aria-invalid", "true");
    document.getElementById("contextRollDownStatus").textContent = "Enter a nonnegative factor. The last valid setting remains active.";
    return;
  }
  input.setAttribute("aria-invalid", "false");
  qualificationAssumptions.rollDownFactor = value;
  updateRollDownFactorControl(false);
  renderSharedViews();
}

function resetRollDownFactor() {
  qualificationAssumptions.rollDownFactor = 0;
  updateRollDownFactorControl();
  renderSharedViews();
}

function updateDashboardScope() {
  const allAthletes = ["splits", "overall", "statistics"].includes(activeTab);
  const targetView = ["qualification", "easiest"].includes(activeTab);
  const isQualification = activeWorkspace === "qualification";
  const identityFields = document.querySelector(".context-fields:not(.assumption-fields)");
  const identityHome = document.getElementById("identityHome");
  (isQualification && activeTab === "qyou" ? document.getElementById("qyouFields") : identityHome).append(identityFields);
  document.getElementById("contextIdentitySummary").hidden = !isQualification || activeTab === "qyou";
  document.getElementById("contextIdentityText").textContent = `${dashboardContext.distance === "im" ? "IRONMAN" : "IRONMAN 70.3"} · ${dashboardContext.gender === "Male" ? "Men" : "Women"} · ${dashboardContext.ageGroup}`;
  const eventControl = document.querySelector(".event-control");
  (activeTab === "qualification" ? document.getElementById("targetRaceSelector") : document.getElementById("eventControlHome")).append(eventControl);
  document.querySelector(".assumption-fields").hidden = !targetView;
  document.querySelector(".qualification-approach").hidden = activeTab !== "qualification";
  document.getElementById("contextFallback").closest(".context-tip").hidden = !targetView || !["density", "scan"].includes(qualificationAssumptions.mode);
  document.getElementById("finderObjective").hidden = activeTab !== "easiest";
  updateExtraPlacesControls();
  updateRollDownFactorControl(false);
  document.querySelector("#contextGender").closest("label").hidden = ["experimental", "backtest"].includes(activeTab);
  document.querySelector("#contextAgeGroup").closest("label").hidden = ["experimental", "backtest"].includes(activeTab);
  identityFields.hidden = isQualification ? activeTab !== "qyou" : allAthletes || activeTab === "compare";
  for (const [id, distance] of [["compareImDistribution", "im"], ["compare703Distribution", "703"], ["compareImQualification", "im"], ["compare703Qualification", "703"]]) {
    document.getElementById(id).closest(".chart-panel").hidden = dashboardContext.distance !== distance;
  }
  const perRace = allAthletes || activeTab === "qualification";
  document.getElementById("eventTitle").textContent = perRace
    ? `${dataset().name} / ${dashboardViewLabels[activeTab]}` : dashboardViewLabels[activeTab];
  document.getElementById("contextScope").textContent = allAthletes
    ? "All athletes. Gender and age group apply to qualification analyses only."
    : activeTab === "backtest"
      ? "Leave-one-out backtest on all repeat athletes; gender, age group and year selections do not apply."
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
  if (key === "gender") updateRollDownFactorControl();
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
  qualificationAssumptions.mode = document.getElementById("contextCutoff").value;
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
  const evidenceNote = `<p class="note">Matched-slot cutoff requires an original P1 race and compatible same-cycle championship matches. ${qualificationSystem === "current"
    ? "A ranks that roster under current rules."
    : "B uses the race-year's historical pool ranking and standard."} It uses the Nth matched pool rank, where N is the performance-pool slot count; fewer than N matches or incompatible cycle, ranking, slots, or standard is unavailable, with no strict fallback. This boundary is not evidence of slot acceptance. Density and scan also require an original P1 race; A re-ranks its compatible roster under current rules.</p>`;
  container.innerHTML = `<h2>Targets by approach · ${escapeHtml(divisionFor(gender, ageGroup))}</h2>
    <p class="note">Methods are evaluated independently for each selected race year. Scan labels identify each year's ranking scope and absence threshold. Missing or incompatible evidence stays explicit. Strict fallback means the strict allocation target is shown, not borrowed estimate evidence. Reported minute values and density estimates are approximate. Championship matches are not proof of slot acceptance.</p>
    ${evidenceNote}
    <p class="note">The exploratory match-density boundary compares observed Kona-starter match rates by ranking position with a constant-rate model, then fits a two-rate breakpoint. It requires at least 3 matches before the breakpoint and positive BIC improvement after the penalty; it reports the best breakpoint and weighted 5%-95% rank/time support, with sensitivity to single-race matches. This is unverified matching density, not evidence of actual acceptance or declines. Race targets never place this boundary faster than strict allocation.</p>
    <div class="table-wrap"><table><thead><tr><th>Race year</th>${approaches.map(({label}) => `<th>${escapeHtml(label)}</th>`).join("")}</tr></thead><tbody>${years.map(year => `<tr><td>${yearCell(eventId, year)}</td>${approaches.map(({mode}) => `<td>${approachCell(standards[year][mode], mode)}</td>`).join("")}</tr>`).join("") || '<tr><td colspan="6" class="empty">No race years are visible.</td></tr>'}</tbody></table></div>
    ${approachSummaryTable(eventId, years, approaches, standards)}`;
  lineChart("qualificationChart", years, approaches.map(({mode, label, color}) => ({
    label, color,
    values: years.map(year => {
      const standard = standards[year][mode];
      return standard?.available && !standard.cutoffSource?.startsWith("Strict fallback") && Number.isFinite(standard.needed) ? standard.needed : null;
    }),
  })));
}

// Cross-year summary of each approach's raw target; modified courses are excluded.
function approachSummaryTable(eventId, years, approaches, standards) {
  const comparable = years.filter(year => !isModifiedCourse(eventId, year));
  const rows = approaches.map(({mode, label}) => {
    const points = comparable
      .map(year => ({year, standard: standards[year][mode]}))
      .filter(({standard}) => standard?.available && !standard.cutoffSource?.startsWith("Strict fallback") && Number.isFinite(standard.needed));
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
    <p class="note">Finite targets only ("any finish" years and strict fallbacks are not counted in summaries or method charts). Trend is the least-squares slope over race years with at least three values; negative means the target got faster, i.e. harder.</p>
    <div class="table-wrap"><table><thead><tr><th>Approach</th><th>Years with target</th><th>Median</th><th>Fastest – slowest</th><th>Trend</th><th>Latest</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function approachStandard(eventId, year, gender, ageGroup, system, mode) {
  const strict = strictQualificationStandard(eventId, year, gender, ageGroup, system, {extraPlaces: 0});
  if (!strict) return null;
  const extraPlaces = strict.scope === "age group"
    ? qualificationAssumptions.legacyExtraPlaces : qualificationAssumptions.extraPlaces;
  return easiestQualificationStandard(eventId, year, gender, ageGroup, system, mode, extraPlaces);
}

function scopedCutoffApproaches(system = qualificationSystem) {
  return cutoffApproaches.map(approach => approach.mode !== "scan" ? approach : {
    ...approach,
    label: "15-absence gender-pool scan",
  });
}

function scanScopeLabel(standard) {
  const pool = standard?.cutoffPool;
  const scan = pool?.cutoff_scan;
  const absences = scan?.consecutive_absences ?? 15;
  return `${absences}-absence gender-pool scan`;
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
  return `${scanLabel}<strong>${fallback ? "Strict fallback · " : ""}${escapeHtml(value)}</strong><br><small>${escapeHtml(standard.cutoffSource || "")}</small>`;
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
  const system = activeTab === "easiest" ? "current" : qualificationSystem;
  const approaches = scopedCutoffApproaches(system);
  const byRace = eventIds.map(eventId => {
    const rows = allRaceYears(eventId).map(year => {
      const standards = Object.fromEntries(approaches.map(({mode}) => [mode,
        approachStandard(eventId, year, gender, ageGroup, system, mode),
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
      return !row.modified && standard?.available && !standard.cutoffSource?.startsWith("Strict fallback") && Number.isFinite(standard.needed) && Number.isFinite(factor)
        ? [standard.needed / factor] : [];
    })),
  }));
  stepShareChart("oddsApproachChart", series, entered);
  section.querySelector(".note").textContent = `${division} · ${group === "im" ? "IRONMAN 140.6" : "IRONMAN 70.3"}. Each race-year row shows its target and whether your entered time meets it for every approach; the chart pools the compatible race-years of all listed races per approach. Modified courses and strict fallbacks are excluded from the chart. Strict fallback means the strict target stands in for an unavailable estimate and is identified explicitly.`;
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
  const approaches = scopedCutoffApproaches("current");
  const raceRows = eventIds.map(eventId => ({eventId, rows: allRaceYears(eventId).map(year => {
    const standards = Object.fromEntries(approaches.map(({mode}) => [mode,
      approachStandard(eventId, year, gender, ageGroup, "current", mode),
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
    if (!row.expected) return `<td>${approachCell(standard, mode)}<br><small>No expected time or course factor</small></td>`;
    const margin = standard.needed - row.expected.total;
    const chance = standard.needed === Infinity ? 1 : standard.needed === -Infinity ? 0 : normalCdf(Math.log(standard.needed / row.expected.total) / sigma);
    return `<td>${approachCell(standard, mode)}<br>${signedDuration(margin)} · ${Math.round(100 * chance)}%</td>`;
  }).join("")}</tr>`)).join("") || '<tr><td colspan="7" class="empty">No race years are visible.</td></tr>';
  const chartSeries = approaches.map(({mode, label, color}) => ({
    label, color,
    values: raceRows.map(({rows}) => rows.flatMap(row => {
      const standard = row.standards[mode];
      if (row.modified || !row.expected || !standard?.available || standard.cutoffSource?.startsWith("Strict fallback") || !Number.isFinite(standard.needed)) return [];
      return [{year: row.year, value: standard.needed - row.expected.total,
        detail: `${neededText(standard.needed)} target · ${duration(row.expected.total)} expected · ${label}`}];
    })),
  }));
  categoryPointChart("finderApproachChart", raceRows.map(({eventId}) => DATASETS[eventId].name), chartSeries,
    {includeZero: true, formatValue: signedDuration, formatTick: signedDurationShort, yAxisLabel: "Target minus expected time"});
  section.querySelector(".note").textContent = `${division} · objective A, current rules on past results. Matched-slot cutoff uses the Nth same-cycle matched P1 pool rank (N = performance-pool slots), re-ranked under current rules; insufficient or incompatible evidence is unavailable and matches do not prove slot acceptance. Chance uses the existing day-to-day variation model; the rank factor is not calibrated or backtested. Strict fallbacks are labelled in the table and excluded from the chart; reported evidence is never replaced. Modified courses are excluded.`;
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
  const oddsSuffix = " Cutoff methods and reported evidence are compared below. Target hits are not verified slot acceptance; incompatible race years are marked unavailable rather than borrowing another edition's evidence.";
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

function rollDownEvidence(standard, mode) {
  if (!standard?.available || !standard.estimatedCutoffUsed) return null;
  const pool = standard.cutoffPool;
  if (pool?.slot_scope === "age group" && ["scan", "density"].includes(mode)) return null;
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
    ? `<br><small>≈ ${evidence.passed} ranks beyond ${evidence.slots} allocated ${evidence.scope === "age group" ? "AG" : "pool"} slots (not a decline count)</small>`
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
    const selected = get(qualificationAssumptions.mode);
    const scan = rollDownEvidence(get("scan"), "scan");
    const density = rollDownEvidence(get("density"), "density");
    const reported = rollDownEvidence(get("reported"), "reported");
    const factor = courseFactor(eventId, year);
    const modified = isModifiedCourse(eventId, year);
    const predicted = !modified && Number.isFinite(averageTime)
      ? predictRaceYear(eventId, year, profile.used ? profile.splits : null, profile.transitionRatio, averageTime)?.total ?? null : null;
    return {year, strict, selected, scan, density, reported, factor, modified, predicted,
      breakdown: genderSlotBreakdown(eventId, year, qualificationSystem),
      standardTarget: selected?.available && Number.isFinite(selected.needed) && factor ? selected.needed / factor : null,
      unavailable: get("scan")?.unavailableReason};
  });
  const finite = values => values.filter(Number.isFinite);
  const passedValues = finite(rows.map(row => row.scan?.passed));
  const margins = finite(rows.map(row => row.selected?.available && Number.isFinite(row.predicted) && Number.isFinite(row.selected.needed) ? row.selected.needed - row.predicted : null));
  const isFallback = row => row.selected?.available && row.selected.cutoffSource?.startsWith("Strict fallback");
  const standardFallbacks = rows.filter(row => isFallback(row) && Number.isFinite(row.standardTarget)).length;
  const marginFallbacks = rows.filter(row => isFallback(row) && Number.isFinite(row.predicted) && Number.isFinite(row.selected.needed)).length;
  const body = rows.map(row => {
    if (!row.strict) return `<tr><td>${yearCell(eventId, row.year)}</td><td colspan="10">No slot data for these rules</td></tr>`;
    const strict = row.strict;
    const ageGroupSlots = strict.scope === "age group"
      ? `${strict.slots} ${escapeHtml(division)} slot${strict.slots === 1 ? "" : "s"}` : `${strict.qualifiers} projected ${escapeHtml(division)} qualifiers`;
    const margin = row.selected?.available && Number.isFinite(row.predicted) ? row.selected.needed - row.predicted : null;
    return `<tr><td>${yearCell(eventId, row.year)}</td><td><small>${escapeHtml(strict.method || "")}</small></td><td>${slotBreakdownText(row.breakdown)}</td>`
      + `<td>${ageGroupSlots}<br><small>of ${strict.finishers} finishers</small></td>`
      + `<td><strong>${neededText(strict.needed)}</strong><br><small>${targetRouteText(strict)}</small></td>`
      + `<td>${approachCell(row.selected, qualificationAssumptions.mode)}</td><td>${row.modified ? "Modified course" : neededText(row.standardTarget)}${!row.modified && row.selected?.cutoffSource?.startsWith("Strict fallback") ? `<br><small>${escapeHtml(row.selected.cutoffSource)}</small>` : ""}</td>`
      + `<td>${rollDownCell(row.reported, "No documented report")}</td><td>${rollDownCell(row.scan, row.unavailable)}</td><td>${rollDownCell(row.density, row.unavailable)}</td>`
      + `<td>${duration(row.predicted)}</td><td>${margin === null ? "—" : `${signedDuration(margin)}${margin >= 0 ? " ✓" : ""}`}</td></tr>`;
  }).join("");
  container.innerHTML = `<h2>Slots, roll-down and targets · ${escapeHtml(division)}</h2>
    ${stepMetrics([
      ["Median strict target (as raced)", neededText(lowerMedian(finite(rows.map(row => row.strict?.needed))))],
      [`Selected method on a standard course (${standardFallbacks} strict fallback)`, neededText(lowerMedian(finite(rows.map(row => row.standardTarget))))],
      ["Median scan depth beyond allocation", passedValues.length ? `≈ ${lowerMedian(passedValues)} ranks in ${passedValues.length} yr` : "No evidence"],
      [`Your median margin vs. selected target (${marginFallbacks} strict fallback)`, margins.length ? signedDuration(lowerMedian(margins)) : "—"],
    ])}
    <div class="table-wrap" style="max-height:none"><table><thead><tr><th>Year</th><th>Rules</th><th title="Gender-pool years: automatic age-group winner slots + performance-pool slots. Legacy years: age-group slots per gender.">Slots (M · F)</th><th>${escapeHtml(division)} allocation / projection</th><th>Strict target</th><th>Selected method · ${escapeHtml(cutoffLabels[qualificationAssumptions.mode])}</th><th>Selected target on a standard course</th><th>Reported last accepted</th><th>Absence-scan estimate</th><th>Density estimate</th><th>Your predicted time</th><th>Your margin vs. selected target</th></tr></thead><tbody>${body || '<tr><td colspan="12" class="empty">No race years are visible.</td></tr>'}</tbody></table></div>
    <p class="note">Scan rank beyond allocation is a model-derived assumption, not a count of declines. Unmatched athletes may be missing or unrecognized; a match does not prove acceptance at this race. P1 targets include the separate age-group winner route.</p>`;
}

function evidenceRankAtOrBelow(ranking, threshold, scope) {
  const index = scope === "age group" ? 0 : 1;
  const times = ranking.map(row => row[index]);
  if (!Number.isFinite(threshold) || !times.length || times.some(time => !Number.isFinite(time))) {
    return {rank: null, reason: "ranked times or threshold unavailable"};
  }
  if (threshold > times.at(-1)) return {rank: null, reason: "threshold beyond all ranked finishers; no extrapolated rank"};
  let low = 0, high = times.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (times[middle] <= threshold) low = middle + 1;
    else high = middle;
  }
  return low ? {rank: low, reason: null} : {rank: null, reason: "no ranked finisher at or below threshold"};
}

function renderTargetEvidence() {
  const section = document.getElementById("targetEvidencePlot");
  if (!section) return;
  const eventId = eventSelect.value;
  const years = allRaceYears(eventId);
  const note = document.getElementById("targetEvidenceNote");
  const panels = document.getElementById("targetEvidenceChart");
  document.getElementById("targetEvidenceTooltip").hidden = true;
  if (!years.length) {
    note.textContent = "Select at least one race year.";
    panels.innerHTML = "";
    return;
  }
  const entries = years.map(year => {
    const standards = Object.fromEntries(cutoffApproaches.map(({mode}) => [mode,
      approachStandard(eventId, year, dashboardContext.gender, dashboardContext.ageGroup, qualificationSystem, mode)]));
    const standard = standards.strict;
    const pool = standard?.cutoffPool;
    const trace = pool && DATASETS.im_kona?.kona_traces?.[pool.kona_cycle];
    const data = DATASETS[eventId];
    const historicalRows = data.historical_qualification?.targets?.filter(row => row.year === year) || [];
    const target = historicalRows.find(row => row.division === standard?.division);
    const original = target || historicalRows[0];
    const source = original?.source;
    const sourceCycle = source?.cycles?.length === 1 && !source.other_cycles?.length ? String(source.cycles[0]) : null;
    const matchEligible = Boolean(sourceCycle && source?.method === "performance" && original?.slot_scope === "gender");
    const expectedSlots = standard?.scope === "age group" ? standard.slots : standard?.performanceSlots;
    const expectedCycle = qualificationSystem === "current" ? data.qualification?.standard_cycle : sourceCycle;
    const ratio = qualificationSystem === "current" ? trace?.counterfactual_standards?.[standard?.division] : trace?.standards?.[standard?.division];
    const compatible = matchEligible && DATASETS[eventId]?.group !== "703" && pool && trace && String(trace.year) === sourceCycle
      && String(pool.kona_cycle) === sourceCycle && expectedCycle
      && String(qualificationSystem === "current" ? trace.counterfactual_standard_cycle : trace.standard_cycle) === String(expectedCycle)
      && String(pool.ranking_cycle) === String(expectedCycle) && Array.isArray(trace.venues?.[dashboardContext.gender]) && trace.venues[dashboardContext.gender].length
      && pool.slot_scope === standard.scope && Number.isFinite(expectedSlots) && expectedSlots > 0 && pool.pool_slots === expectedSlots
      && (!pool.division || pool.division === standard.division)
      && (qualificationSystem !== "historical" || target?.division === standard.division && String(target.standard_cycle) === sourceCycle)
      && Number.isFinite(standard.ratio) && Number.isFinite(ratio) && ratio > 0 && Math.abs(standard.ratio - ratio) <= 0.000001;
    const rawRanking = !standard ? [] : standard.scope === "age group" ? (target?.times || []).map(time => [time, null, null])
      : ((qualificationSystem === "historical" ? data.historical_qualification?.pools : data.qualification?.pools)?.[year]?.[dashboardContext.gender.toLowerCase()] || []).map(row => {
        const ratio = qualificationSystem === "historical"
          ? data.historical_qualification?.targets?.find(item => item.year === year && item.division === row.division)?.ratio
          : data.qualification?.ratios?.[row.division];
        return [ratio > 0 ? row.age_graded / ratio : null, row.age_graded, null];
      });
    const hasMatches = Boolean(compatible && pool.ranking_evidence?.length);
    const evidenceTrace = sourceCycle ? DATASETS.im_kona?.kona_traces?.[sourceCycle] : null;
    const plotScope = qualificationSystem === "current" ? "gender" : standard?.scope;
    const plotRows = qualificationSystem === "current"
      ? evidenceTrace?.counterfactual_summaries || []
      : evidenceTrace?.summaries?.all || [];
    const plotCandidates = plotRows.filter(row => row.event_id === eventId && row.year === year
      && row.gender === dashboardContext.gender && row.slot_scope === plotScope
      && (plotScope !== "age group" || row.division === standard?.division));
    const plotPool = plotCandidates.length === 1 ? plotCandidates[0] : null;
    const plotRankingCycle = qualificationSystem === "current" ? data.qualification?.standard_cycle : sourceCycle;
    const plotTraceCycle = qualificationSystem === "current"
      ? evidenceTrace?.counterfactual_standard_cycle : evidenceTrace?.standard_cycle;
    const plotRatio = qualificationSystem === "current"
      ? evidenceTrace?.counterfactual_standards?.[standard?.division]
      : evidenceTrace?.standards?.[standard?.division];
    const plotRosterAvailable = Boolean(evidenceTrace && String(evidenceTrace.year) === sourceCycle
      && Array.isArray(evidenceTrace.venues?.[dashboardContext.gender])
      && evidenceTrace.venues[dashboardContext.gender].length);
    const plotAllocationMatches = plotScope === "age group"
      ? plotPool?.pool_slots === standard?.slots
      : plotPool?.pool_slots === expectedSlots && Number.isFinite(standard?.ratio)
        && Number.isFinite(plotRatio) && Math.abs(standard.ratio - plotRatio) <= 0.000001;
    const plotCompatible = Boolean(data.group === "im" && sourceCycle && plotRosterAvailable
      && plotPool && plotPool.ranking_evidence && String(plotPool.kona_cycle) === sourceCycle
      && String(plotPool.ranking_cycle) === String(plotRankingCycle)
      && String(plotTraceCycle) === String(plotRankingCycle)
      && plotAllocationMatches
      && (qualificationSystem !== "historical" || plotScope !== "gender"
        || target?.division === standard?.division && String(target?.standard_cycle) === sourceCycle));
    const plotUnavailableReason = data.group !== "im" ? "No compatible 70.3 World Championship ranking evidence."
      : !sourceCycle ? "Qualifying cycle unknown; corresponding World Championship evidence unavailable."
      : !plotRosterAvailable ? `World Championship roster unavailable for cycle ${sourceCycle} (${dashboardContext.gender}).`
      : plotCandidates.length !== 1 ? "No unique compatible ranked starter evidence for this race-year and cycle."
      : "World Championship ranking is incompatible with the selected cycle, scope, standard, or allocation.";
    const plotRanking = plotCompatible ? plotPool.ranking_evidence : [];
    const winnerStarters = qualificationSystem === "current"
      ? evidenceTrace?.counterfactual_winners || [] : evidenceTrace?.starters || [];
    const plotWinners = plotCompatible ? winnerStarters.flatMap(starter => {
      if (starter.gender !== dashboardContext.gender) return [];
      return (starter.matches || []).filter(match => match.event_id === eventId && match.year === year
        && (plotScope !== "age group" || match.division === standard.division)
        && (plotScope === "age group"
          ? match.initial_slot === "Strict age-group slot" && match.pool_rank === 1
          : match.age_group_winner === true || match.initial_slot === "Automatic winner"))
        .map(match => ({name: starter.name, division: match.division, finishTime: match.finish_time}));
    }).sort((first, second) => first.division.localeCompare(second.division)) : [];
    return {year, standard, standards, pool, matchEligible, compatible: hasMatches,
      ranking: hasMatches ? pool.ranking_evidence : rawRanking, expectedSlots,
      plotPool, plotCompatible, plotRanking, plotWinners,
      plotOnlyLegacy: qualificationSystem === "historical" && source?.method === "legacy" && plotCompatible,
      plotUnavailableReason};
  });
  const methodsFor = entry => {
    const {standard, standards, pool, compatible, ranking, expectedSlots} = entry;
    const reason = DATASETS[eventId]?.group === "703" ? "No 70.3 World Championship starter list"
      : "No compatible ranked starter evidence for this race-year and cycle";
    const info = (mode, rank, detail = "") => {
      const result = standards[mode];
      const fallback = result?.cutoffSource?.startsWith("Strict fallback");
      if (!result) return {mode, rank: null, detail: "No compatible target"};
      if (!result.available || fallback) return {mode, rank: null, detail: fallback ? result.cutoffSource : result.unavailableReason || result.cutoffSource || "Unavailable"};
      if (!ranking.length) return {mode, rank: null, rankUnavailable: true, detail: `${reason}. Target: ${assumptionTime(result)}${detail ? `; ${detail}` : ""}`};
      if (!Number.isFinite(rank) || rank < 1 || rank > ranking.length) return {mode, rank: null, rankUnavailable: true,
        detail: `${Number.isFinite(rank) ? `rank ${rank}: no ranked finisher` : "No rank available"}${detail ? `; ${detail}` : ""}`};
      const row = ranking[rank - 1];
      const times = `finisher ${Number.isFinite(row[0]) ? duration(row[0]) : "unavailable"}${Number.isFinite(row[1]) ? `; age-graded ${qualificationDuration(row[1])}` : ""}`;
      return {mode, rank, detail: `${times}${detail ? `; ${detail}` : ""}`};
    };
    const density = pool?.cutoff_estimate || {};
    const scan = pool?.cutoff_scan || {};
    const factor = standards.calibrated;
    const factorDetail = factor?.available ? `factor ${factor.rollDownFactor}; initial slots ${expectedSlots}; target ${assumptionTime(factor)}` : "";
    const matched = standards.matched;
    const matchedDetail = matched?.available
      ? `${matched.matchedPoolStarters} matched pool ranks; N=${expectedSlots}; mapped target ${assumptionTime(matched)}` : "";
    const reported = standards.reported;
    const reportRank = compatible && reported?.available && pool?.reported_cutoff_precision === "second"
      ? evidenceRankAtOrBelow(ranking, pool.reported_cutoff, standard.scope) : {rank: null, reason: "reported precision does not establish an exact rank"};
    const reportDetail = `${pool?.reported_cutoff_source || "External report"}; reported cutoff ${duration(pool?.reported_cutoff)}; ${pool?.reported_cutoff_precision || "unknown"} precision${reportRank.reason ? `; ${reportRank.reason}` : ""}`;
    const methods = [
      info("strict", expectedSlots, standard?.scope === "gender" ? "pool boundary; AG winner route is separate" : "allocated age-group boundary"),
      info("matched", matched?.matchedCutoffRank, matchedDetail),
      info("density", density.rank, Number.isFinite(density.low_rank) && Number.isFinite(density.high_rank) ? `exploratory support ranks ${density.low_rank}-${density.high_rank}` : "exploratory density support unavailable"),
      info("scan", scan.criterion_met ? scan.rank : null, scan.criterion_met ? `${scan.consecutive_absences}-absence stopping gap ${scan.gap_start_rank}-${scan.gap_end_rank}` : `scan incomplete: ${scan.reason || "no full stopping gap"}`),
      info("calibrated", factor?.factorRank, factorDetail),
      info("reported", reportRank.rank, reportDetail),
    ];
    return entry.matchEligible ? methods : methods.filter(method => ["strict", "calibrated"].includes(method.mode));
  };
  entries.forEach(entry => { entry.methods = methodsFor(entry); });
  const expanded = document.getElementById("targetEvidenceExpand").checked;
  const legacyPlotRanks = entries.flatMap(({plotOnlyLegacy, plotPool}) => plotOnlyLegacy ? [
    plotPool?.cutoff_estimate?.rank, plotPool?.cutoff_estimate?.high_rank,
    plotPool?.cutoff_scan?.rank, plotPool?.cutoff_scan?.gap_end_rank,
  ] : []).filter(Number.isFinite);
  const maximum = expanded ? Math.max(100, ...entries.flatMap(({pool, methods}) => [
    ...methods.map(method => method.rank || 0), methods.find(method => method.mode === "scan")?.rank ? pool?.cutoff_scan?.gap_end_rank || 0 : 0,
    methods.find(method => method.mode === "density")?.rank ? pool?.cutoff_estimate?.high_rank || 0 : 0,
  ]), ...legacyPlotRanks) : Math.max(100, ...legacyPlotRanks);
  const x = rank => 130 + (rank - 1) * 820 / Math.max(1, maximum - 1);
  const styles = {strict: ["#006d77", ""], matched: ["#d1495b", "10 3"], density: ["#b08900", "2 3"], scan: ["#277da1", "9 3 2 3"], calibrated: ["#913d70", "12 4"], reported: ["#495057", "4 4"]};
  const label = {strict: "Strict allocation", matched: "Matched-slot cutoff", density: "Exploratory density breakpoint", scan: "15-absence scan", calibrated: "Rank-based roll-down factor", reported: "Reported last accepted"};
  const marker = method => method.rank && method.rank <= maximum
    ? `<line x1="${x(method.rank)}" x2="${x(method.rank)}" y1="35" y2="195" stroke="${styles[method.mode][0]}" stroke-width="2" stroke-dasharray="${styles[method.mode][1]}"><title>${escapeHtml(label[method.mode])}: rank ${method.rank}; ${escapeHtml(method.detail)}</title></line>` : "";
  panels.innerHTML = entries.map(({year, standard, pool, compatible, ranking, methods,
    plotPool, plotCompatible, plotRanking, plotWinners, plotOnlyLegacy, plotUnavailableReason}) => {
    const legend = `<ul class="evidence-legend" aria-label="${escapeHtml(year)} approach boundaries">${methods.map(method => `<li><span class="evidence-swatch" style="--marker-color:${styles[method.mode][0]}"></span><strong>${escapeHtml(label[method.mode])}</strong>: ${method.rank ? `rank ${method.rank}${method.rank > maximum ? " (outside displayed axis; expand)" : ""}; ` : method.rankUnavailable ? "Rank unavailable: " : "Unavailable: "}${escapeHtml(method.detail)}</li>`).join("")}</ul>`;
    const plotScopeLabel = plotCompatible ? plotPool.slot_scope : standard?.scope;
    const winnerRole = plotScopeLabel === "gender"
      ? "separate automatic-slot route; no performance-pool rank"
      : "age-group rank 1; not a P1 automatic-slot winner";
    const winnerDescription = winner => `${winner.division}; ${winner.name}; finishing time ${Number.isFinite(winner.finishTime) ? duration(winner.finishTime) : "unavailable"}; ${winnerRole}`;
    const winnerList = `<p class="note"><strong>Matched AG winners (gold)</strong>: ${winnerRole}.</p>${plotWinners.length
      ? `<ul class="evidence-winner-list" aria-label="Matched age-group first-place finishers">${plotWinners.map(winner => `<li aria-label="${escapeHtml(winnerDescription(winner))}"><span class="evidence-winner-swatch" aria-hidden="true"></span><strong>${escapeHtml(winner.division)}</strong> · ${escapeHtml(winner.name)} · ${Number.isFinite(winner.finishTime) ? duration(winner.finishTime) : "finish time unavailable"}<small class="evidence-winner-role">${escapeHtml(winnerRole)}</small></li>`).join("")}</ul>`
      : `<p class="note">${plotCompatible ? "No matched age-group first-place finisher in the available evidence." : "Unavailable: compatible World Championship winner-match evidence is missing."}</p>`}`;
    if (!plotCompatible || !plotRanking.length) {
      const reason = plotCompatible ? "No ranked qualifying finishers are available for this World Championship match list." : plotUnavailableReason;
      return `<div class="evidence-year" data-evidence-year="${escapeHtml(year)}"><h3>${escapeHtml(year)}</h3><p class="note">${escapeHtml(reason)}</p>${winnerList}${legend}</div>`;
    }
    const scan = plotPool?.cutoff_scan || {};
    const density = plotPool?.cutoff_estimate || {};
    const scope = plotPool.slot_scope === "age group" ? `Age group ${dashboardContext.ageGroup} rank` : `${dashboardContext.gender} performance pool rank`;
    const winnerLane = plotPool.slot_scope === "gender" && plotWinners.length
      ? `<text x="115" y="24" text-anchor="end">Matched AG winners</text><line x1="130" y1="20" x2="950" y2="20" stroke="#d4a017" opacity=".35"/>${plotWinners.map((winner, index) => {
        const laneX = 130 + (index + 1) * 820 / (plotWinners.length + 1);
        const description = winnerDescription(winner);
        return `<g class="evidence-winner-marker" role="img" tabindex="0" focusable="true" aria-label="${escapeHtml(description)}"><title>${escapeHtml(description)}</title><circle cx="${laneX}" cy="20" r="5" fill="#d4a017" stroke="#fff" stroke-width="1.5"/></g>`;
      }).join("")}` : "";
    let markup = `${winnerLane}<text x="115" y="78" text-anchor="end">Matched</text><text x="115" y="158" text-anchor="end">Not matched</text>`;
    if (methods.find(method => method.mode === "density")?.rank && Number.isFinite(density.low_rank) && Number.isFinite(density.high_rank) && density.low_rank <= maximum) {
      markup += `<rect x="${x(density.low_rank)}" y="35" width="${Math.max(1, x(Math.min(density.high_rank, maximum)) - x(density.low_rank))}" height="160" fill="#e9b949" opacity=".18"><title>Density support: ranks ${density.low_rank} to ${density.high_rank}</title></rect>`;
    }
    if (methods.find(method => method.mode === "scan")?.rank && scan.criterion_met && Number.isFinite(scan.gap_start_rank) && Number.isFinite(scan.gap_end_rank) && scan.gap_start_rank <= maximum) {
      markup += `<rect x="${x(scan.gap_start_rank)}" y="35" width="${Math.max(3, x(Math.min(scan.gap_end_rank, maximum)) - x(scan.gap_start_rank))}" height="160" fill="#277da1" opacity=".15"><title>Stopping gap: ranks ${scan.gap_start_rank} to ${scan.gap_end_rank}</title></rect>`;
    }
    if (plotOnlyLegacy && Number.isFinite(density.rank) && density.rank <= maximum) {
      if (Number.isFinite(density.low_rank) && Number.isFinite(density.high_rank) && density.low_rank <= maximum) {
        markup += `<rect x="${x(density.low_rank)}" y="35" width="${Math.max(1, x(Math.min(density.high_rank, maximum)) - x(density.low_rank))}" height="160" fill="#e9b949" opacity=".18"><title>Historical age-group density support, plot only: ranks ${density.low_rank} to ${density.high_rank}</title></rect>`;
      }
      markup += `<line x1="${x(density.rank)}" x2="${x(density.rank)}" y1="35" y2="195" stroke="${styles.density[0]}" stroke-width="2" stroke-dasharray="2 3"><title>Historical age-group density boundary, plot only: rank ${density.rank}; ${escapeHtml(density.reason || "exploratory")}</title></line>`;
    }
    if (plotOnlyLegacy && scan.criterion_met === true && scan.consecutive_absences === 5
      && Number.isFinite(scan.gap_start_rank) && Number.isFinite(scan.gap_end_rank) && scan.gap_start_rank <= maximum) {
      markup += `<rect x="${x(scan.gap_start_rank)}" y="35" width="${Math.max(3, x(Math.min(scan.gap_end_rank, maximum)) - x(scan.gap_start_rank))}" height="160" fill="#277da1" opacity=".15"><title>Historical five-unmatched age-group scan, plot only: ranks ${scan.gap_start_rank} to ${scan.gap_end_rank}</title></rect>`;
      if (Number.isFinite(scan.rank) && scan.rank <= maximum) {
        markup += `<line x1="${x(scan.rank)}" x2="${x(scan.rank)}" y1="35" y2="195" stroke="${styles.scan[0]}" stroke-width="2" stroke-dasharray="9 3 2 3"><title>Last matched age-group finisher before five consecutive unmatched ranks: rank ${scan.rank}</title></line>`;
      }
    }
    markup += methods.map(marker).join("");
    const width = 820 / Math.max(1, maximum - 1);
    plotRanking.slice(0, maximum).forEach((row, index) => {
      const [raw, graded, matches] = row;
      const rank = index + 1;
      const ageGroupWinner = plotPool.slot_scope === "age group" && rank === 1 && (row[3] === true || matches > 0);
      const matched = matches > 0 || ageGroupWinner;
      const matchStatus = ageGroupWinner ? "matched age-group rank 1; excluded from legacy plot density/scan inputs and counts"
        : matched ? `matched${matches > 1 ? `, ${matches} candidate races` : ""}` : "not matched";
      const detail = `Race year ${year}; ${scope}: ${rank}; Finishing time: ${Number.isFinite(raw) ? duration(raw) : "unavailable"}${Number.isFinite(graded) ? `; age-graded time: ${qualificationDuration(graded)}` : ""}; Match status: ${plotCompatible ? matchStatus : "unavailable"}`;
      const center = matched ? 74 : 154;
      markup += `<circle cx="${x(rank)}" cy="${center}" r="3" fill="${ageGroupWinner ? "#d4a017" : matches ? "#00796b" : "#8d9994"}" pointer-events="none"/>`;
      markup += `<rect class="evidence-point" x="${x(rank) - width / 2}" y="${center - 24}" width="${width}" height="48" fill="transparent" tabindex="${index ? -1 : 0}" role="button" aria-label="${escapeHtml(detail)}" aria-keyshortcuts="ArrowLeft ArrowRight" aria-describedby="targetEvidenceTooltip" data-evidence-detail="${escapeHtml(detail)}"/>`;
    });
    markup += `<line class="axis" x1="130" y1="195" x2="950" y2="195"/><text x="130" y="215">1</text><text x="950" y="215" text-anchor="end">${maximum}</text><text x="540" y="240" text-anchor="middle">${scope}</text>`;
    const scanNote = !methods.some(method => method.mode === "scan") ? ""
      : scan.criterion_met ? ` Scan gap ${scan.gap_start_rank}-${scan.gap_end_rank} (${scan.consecutive_absences} consecutive unmatched).`
      : ` Scan incomplete: ${scan.reason || "no full stopping gap"}.`;
    const plotOnlyNote = plotOnlyLegacy ? `<p class="note">B legacy plot only: ${Number.isFinite(density.rank)
      ? `density boundary at age-group rank ${density.rank}${Number.isFinite(density.low_rank) && Number.isFinite(density.high_rank) ? ` (support ${density.low_rank}-${density.high_rank})` : ""}`
      : `density boundary unavailable (${escapeHtml(density.reason || "insufficient evidence")})`}; ${scan.criterion_met === true && scan.consecutive_absences === 5
        ? `five-unmatched scan gap ${scan.gap_start_rank}-${scan.gap_end_rank}`
        : `five-unmatched scan unavailable (${escapeHtml(scan.reason || "incomplete scan")})`}. These descriptive markers are not qualification methods or results and do not affect targets, rank factors, Finder chances, calibration, or model metrics. A matched age-group rank-1 finisher is shown gold and excluded from plot density/scan inputs and counts.</p>` : "";
    return `<div class="evidence-year" data-evidence-year="${escapeHtml(year)}"><h3>${escapeHtml(year)} · ${scope}</h3><p class="note">WC ${escapeHtml(plotPool.kona_cycle)}; ranking cycle ${escapeHtml(plotPool.ranking_cycle)}.${escapeHtml(scanNote)}${standard.scope === "gender" ? " Matched age-group winners are listed separately in gold, without performance-pool ranks." : ""}</p>${winnerList}${plotOnlyNote}<svg class="chart evidence-chart" viewBox="0 0 1000 260" role="group" aria-label="${escapeHtml(year)} ${escapeHtml(scope)}. Use left and right arrow keys to inspect ranks.">${markup}</svg>${legend}</div>`;
  }).join("");
  note.textContent = `${qualificationSystem === "current" ? "A: current rules" : "B: historical rules"}. All panels show ranks 1-${maximum}${expanded ? " through the available boundaries" : " (expand to see later boundaries and gaps)"}. Rank axes identify the selected age group or gender performance pool. Matched P1 winners appear in a separate gold lane with no pool rank; they are excluded from pool density and scan metrics. B legacy density and five-unmatched scan markers are plot-only, not selected methods or qualification results, and do not affect targets, Finder chances, or model metrics. A match does not prove acceptance; not matched does not prove absence or decline.`;
}

function attachEvidenceTooltips(section) {
  const tooltip = document.getElementById("targetEvidenceTooltip");
  const show = (point, clientX, clientY) => {
    tooltip.textContent = point.dataset.evidenceDetail;
    tooltip.hidden = false;
    const plot = point.closest("svg").getBoundingClientRect();
    const box = tooltip.getBoundingClientRect();
    const left = Math.max(4, Math.min(clientX - box.width / 2, window.innerWidth - box.width - 4));
    let top = clientY - box.height - 12;
    if (top < Math.max(4, plot.top)) top = clientY + 12;
    top = Math.max(4, Math.min(top, plot.bottom - box.height - 4, window.innerHeight - box.height - 4));
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  };
  const pointFor = event => event.target.closest(".evidence-point");
  section.addEventListener("pointerover", event => {
    const point = pointFor(event);
    if (point) show(point, event.clientX, event.clientY);
  });
  section.addEventListener("pointermove", event => {
    const point = pointFor(event);
    if (point && event.pointerType !== "touch") show(point, event.clientX, event.clientY);
  });
  section.addEventListener("pointerout", event => {
    const point = pointFor(event);
    if (point && event.pointerType !== "touch" && document.activeElement !== point) tooltip.hidden = true;
  });
  section.addEventListener("pointerdown", event => {
    const point = pointFor(event);
    if (point) show(point, event.clientX, event.clientY);
  });
  document.addEventListener("pointerdown", event => { if (!pointFor(event)) tooltip.hidden = true; });
  section.addEventListener("focusin", event => {
    const point = pointFor(event);
    if (!point) return;
    const box = point.getBoundingClientRect();
    show(point, box.left + box.width / 2, box.top + box.height / 2);
  });
  section.addEventListener("focusout", event => { if (pointFor(event)) tooltip.hidden = true; });
  section.addEventListener("keydown", event => {
    const point = pointFor(event);
    if (event.key === "Escape") { tooltip.hidden = true; return; }
    if (point && ["Enter", " "].includes(event.key)) {
      const box = point.getBoundingClientRect();
      show(point, box.left + box.width / 2, box.top + box.height / 2);
      event.preventDefault();
      return;
    }
    if (!point || !["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    const points = [...point.closest("svg").querySelectorAll(".evidence-point")];
    const index = points.indexOf(point);
    const next = points[Math.max(0, Math.min(points.length - 1, index + (event.key === "ArrowRight" ? 1 : -1)))];
    point.setAttribute("tabindex", "-1");
    next.setAttribute("tabindex", "0");
    next.focus();
    event.preventDefault();
  });
  section.addEventListener("scroll", () => {
    const point = document.activeElement;
    if (!point?.matches?.(".evidence-point") || !section.contains(point)) { tooltip.hidden = true; return; }
    const box = point.getBoundingClientRect();
    const viewport = section.querySelector(".evidence-scroll").getBoundingClientRect();
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    if (x < viewport.left || x > viewport.right || y < 0 || y > window.innerHeight) tooltip.hidden = true;
    else show(point, x, y);
  }, true);
}

function decorateDashboard() {
  updateDashboardScope();
  renderYourTimeSummary();
  renderRaceDifficulty();
  renderTargetOverview();
  renderTargetEvidence();
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
    .finder-why div {white-space:normal; min-width:260px; max-width:420px; padding:8px 0}
    details.step-section {margin-top:24px; border-top:1px solid var(--line); padding-top:12px}
    details.step-section > summary {cursor:pointer; font-family:Georgia,"Times New Roman",serif; font-size:19px; padding:4px 0}
    details.step-section[open] > summary {margin-bottom:12px}
    #targetOverview .metrics, #qtimeSummary .metrics {grid-template-columns:repeat(auto-fit, minmax(180px, 1fr))}
    .controls {border:0; border-bottom:1px solid var(--line); border-radius:0; background:transparent; padding:12px 0}
    .assumption-fields {margin-top:12px; border-top:1px solid var(--line); padding-top:12px}
    .assumption-fields .binary-label {display:flex; align-items:center; gap:6px; min-height:32px}
    .context-tip {position:relative; min-width:110px}
    .context-tip > label {padding-right:36px}
    .factor-input-row {display:flex; align-items:center; gap:6px; padding-right:38px}
    .factor-input-row input {max-width:110px}
    .factor-status {display:block; max-width:280px; margin-top:4px; color:var(--muted); font-size:12px; line-height:1.35}
    .context-help {position:absolute; top:0; right:0; width:32px; height:32px; padding:0; color:var(--ink); background:#e5ece8; border:1px solid var(--line); border-radius:50%; font-weight:700}
    .context-tip [role=tooltip] {display:none; position:absolute; z-index:20; top:100%; right:0; box-sizing:border-box; width:240px; max-width:calc(100vw - 48px); padding:9px; color:#fff; background:#15231e; border-radius:3px; font-size:12px; font-weight:400; text-transform:none; line-height:1.4; overflow-wrap:anywhere}
    .context-tip:focus-within:has(input:focus-visible) [role=tooltip], .context-help:focus-visible + [role=tooltip], .context-help[aria-expanded=true] + [role=tooltip] {display:block}
    @media (hover:hover) {.context-tip:hover [role=tooltip] {display:block}}
    .assumption-fields input[type=checkbox] {width:auto}
    #selectedQualificationSummary {border-bottom:1px solid var(--line); padding-bottom:16px; margin-bottom:18px}
    #contextYearCount {font-size:12px; color:var(--muted)}
    .chart-panel {border:0; border-top:1px solid var(--line); border-radius:0; box-shadow:none; padding:16px 0; background:transparent}
    #comparePanel .chart-grid:empty {display:none}
    h1 {font-size:32px} .metric strong {font-size:22px; overflow-wrap:anywhere}
    @media(max-width:700px) {.context-fields {display:grid; grid-template-columns:repeat(2,minmax(0,1fr))} .context-fields label {min-width:0} .context-fields select {width:100%} .qualification-approach, .assumption-fields > label {grid-column:1 / -1; min-width:0} .segmented-control input {flex:0 0 auto} .segmented-control span {min-width:0; overflow-wrap:anywhere} .context-tip {grid-column:1 / -1; min-width:0} .context-tip [role=tooltip] {left:0; right:auto} h1 {font-size:27px}}
    @media(max-width:360px) {.segmented-control {flex-direction:column} .segmented-control label {min-height:44px} .segmented-control label + label {border-left:0; border-top:1px solid var(--line)}}
  `;
  document.head.append(style);
  document.querySelector("nav.tabs").classList.add("legacy-tabs");
  const nav = document.createElement("div");
  nav.innerHTML = `<nav id="workspaceTabs" class="tabs workspace-tabs" role="tablist" aria-label="Workspaces"></nav>
    <div class="context-bar"><div id="identityHome"><div class="context-fields" hidden>
      <label>Distance<select id="contextDistance"><option value="im">IRONMAN 140.6</option><option value="703">IRONMAN 70.3</option></select></label>
      <label class="context-gender">Gender<select id="contextGender"><option value="Male">Men</option><option value="Female">Women</option></select></label>
      <label class="context-age-group">Age group<select id="contextAgeGroup"></select></label>
    </div></div><div id="contextIdentitySummary" hidden><span id="contextIdentityText"></span> <button type="button" class="context-action" data-view="qyou">Edit</button></div><div class="context-fields assumption-fields">
      <fieldset class="qualification-approach"><legend>Qualification approach</legend><div class="segmented-control" role="radiogroup" aria-label="Qualification approach">
        <label><input type="radio" name="contextRules" value="historical"><span>Historically correct rules</span></label>
        <label><input type="radio" name="contextRules" value="current" checked><span>Current performance pool on historical results</span></label>
      </div></fieldset>
      <span id="finderObjective">Recommendations: A · current rules on past results</span>
      <label>Cutoff method<select id="contextCutoff" aria-describedby="cutoffHelp"><option value="calibrated">Rank-based roll-down factor</option><option value="strict">Strict allocation</option><option value="matched">Matched-slot cutoff</option><option value="density">Match-density boundary</option><option value="scan">15-absence gender-pool scan</option></select></label>
      <div class="context-tip"><label for="contextRollDownFactor">Additional hypothetical declines per slot</label><div class="factor-input-row"><input id="contextRollDownFactor" type="number" min="0" step="any" inputmode="decimal" aria-describedby="rollDownFactorHelp contextRollDownStatus"><button type="button" class="context-action" id="resetRollDownFactor">Reset to 0</button></div><button type="button" class="context-help" aria-label="Help: roll-down factor" aria-controls="rollDownFactorHelp" aria-expanded="false">?</button><span role="tooltip" id="rollDownFactorHelp">A hypothetical ratio of additional declines per initial slot, not observed declines, a probability, or a percentage of time. Extra positions are slots × factor rounded to the nearest integer, with halves rounded upward. With 30 slots, factors 0, 1 and 2 target ranks 30, 60 and 90. Automatic winner slots are separate.</span><output id="contextRollDownStatus" class="factor-status" aria-live="polite"></output></div>
      <div class="context-tip"><label class="binary-label"><input type="checkbox" id="contextFallback" aria-describedby="fallbackHelp">Use strict fallback when evidence is unavailable</label><button type="button" class="context-help" aria-label="Help: strict fallback" aria-controls="fallbackHelp" aria-expanded="false">?</button><span role="tooltip" id="fallbackHelp">Use the strict allocation target only when the selected method has no compatible evidence. It remains labelled as a fallback.</span></div>
      <details id="cutoffHelp"><summary>Method and fallback information</summary><p>The rank factor is a hypothetical scenario. Matched-slot cutoff applies only to original P1 races: it takes the Nth matched starter in the compatible same-cycle championship ranking, where N is the gender-pool slot count. A uses current rules and standard; B uses the historical ranking and standard. Fewer than N matches or incompatible evidence is unavailable, with no strict fallback; matches do not prove acceptance. Density and scan also require an original P1 race and compatible same-cycle matches. Strict fallback applies only to density and scan for P1 races when checked and is labelled.</p></details>
    </div><div class="context-years"><button type="button" id="contextReturn" class="context-action" hidden>Back to ranking</button><span id="contextYearCount"></span>
      <button type="button" class="context-action" data-years-action="all">All</button>
      <button type="button" class="context-action" data-years-action="none">None</button>
      <button type="button" class="context-action" data-years-action="reset">Reset</button>
      <div id="contextYears" class="context-years" style="margin:0"></div></div><p class="note" id="contextScope"></p></div>
    <nav id="viewTabs" class="tabs view-tabs" role="tablist" aria-label="Workspace views"></nav>`;
  document.querySelector(".legacy-tabs").before(nav);
  const eventHome = document.createElement("div");
  eventHome.id = "eventControlHome";
  document.querySelector(".event-control").before(eventHome);
  eventHome.append(document.querySelector(".event-control"));
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
  createStepPanel("qyou").innerHTML = '<section><h2>You</h2><div id="qyouFields"></div></section>';
  // Step 1: your standard-course time from a typed time or past results.
  const timePanel = createStepPanel("qtime");
  timePanel.innerHTML = '<section id="qtimeSummary"></section>';
  const finderControls = finder.querySelector(":scope > .controls");
  [easiestDistance, easiestGender, easiestAgeGroup].forEach(control => control.closest("label").classList.add("local-context-control"));
  const finderFilters = document.createElement("div");
  finderFilters.className = "controls";
  [easiestOpenFilter, easiestFinishRisk].forEach(control => finderFilters.append(control.closest("label")));
  finder.prepend(finderFilters);
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
  const raceSelector = document.createElement("div");
  raceSelector.id = "targetRaceSelector";
  const targetEvidence = document.createElement("section");
  targetEvidence.id = "targetEvidencePlot";
  targetEvidence.innerHTML = '<div class="chart-heading"><h2>Ranked championship evidence</h2><label class="binary-label"><input type="checkbox" id="targetEvidenceExpand">Show later boundaries and stopping gaps</label></div><p id="targetEvidenceNote" class="note"></p><div class="evidence-scroll"><div id="targetEvidenceChart"></div></div><div id="targetEvidenceTooltip" role="tooltip" hidden></div>';
  const konaPanel = embedPanel(document.getElementById("konaPanel"));
  const evidence = stepSection("World Championship start-list evidence (Kona + Nice): who qualified where, and how far slots rolled down", konaPanel);
  evidence.id = "wcEvidence";
  content.append(raceSelector, overview, targetEvidence, stepSection("Compare cutoff approaches by year", selectedSummary), allocation, evidence);
  document.getElementById("targetEvidenceExpand").addEventListener("change", renderTargetEvidence);
  attachEvidenceTooltips(targetEvidence);
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
    stepSection("Compare cutoff methods and reported evidence per race-year", finderApproaches),
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
  document.getElementById("contextCutoff").addEventListener("change", syncQualificationAssumptions);
  document.getElementById("contextFallback").addEventListener("change", syncQualificationAssumptions);
  document.getElementById("contextRollDownFactor").addEventListener("input", changeRollDownFactor);
  document.getElementById("resetRollDownFactor").addEventListener("click", resetRollDownFactor);
  const helpButtons = [...nav.querySelectorAll(".context-help")];
  const closeHelp = () => helpButtons.forEach(button => button.setAttribute("aria-expanded", "false"));
  helpButtons.forEach(button => button.addEventListener("click", () => {
    const open = button.getAttribute("aria-expanded") !== "true";
    closeHelp();
    button.setAttribute("aria-expanded", String(open));
  }));
  document.addEventListener("pointerdown", event => {
    if (!event.target.closest(".context-tip")) closeHelp();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") closeHelp();
  });
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
  updateRollDownFactorControl();
  syncDashboardContext("distance", dataset().group);
  syncQualificationAssumptions();
  renderWorkspaceNavigation();
  renderContextYears();
  decorateDashboard();
}