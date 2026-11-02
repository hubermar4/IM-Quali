const dashboardContext = {distance: "im", gender: "Male", ageGroup: "30-34"};
const qualificationAssumptions = {mode: "calibrated", extraPlaces: 0, legacyExtraPlaces: 0, fallback: false, rollDownFactor: 0};
let dashboardReturnView = null;
const cutoffLabels = {strict: "Strict allocation", matched: "Matched-slot cutoff", calibrated: "Rank-based roll-down factor", reported: "Reported last accepted", density: "Match-density boundary", scan: "15-absence gender-pool scan"};
const cutoffApproaches = [
  {mode: "strict", label: cutoffLabels.strict, color: "#006d77"},
  {mode: "matched", label: cutoffLabels.matched, color: "#d1495b"},
  {mode: "calibrated", label: cutoffLabels.calibrated, color: "#913d70"},
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
  const evidenceNote = `<p class="note">Matched-slot cutoff uses the Nth matched pool rank of the compatible same-cycle championship roster, where N is the performance-pool slot count. ${qualificationSystem === "current"
    ? "A ranks that roster under current rules, for original P1 races and for known R1-R4 race-years; in R1-R4 years those starters qualified through age-group slots."
    : "B uses the race-year's historical pool ranking and standard for original P1 races; for R1-R4 race-years it takes the Nth matched rank in the actual age-group ranking (N = age-group slots), counting a matched age-group winner."} Fewer than N matches or incompatible cycle, ranking, slots, or standard is unavailable, with no strict fallback. This boundary is not evidence of slot acceptance. Density and scan require an original P1 race; A re-ranks its compatible roster under current rules.</p>`;
  container.innerHTML = `<h2>Targets by approach · ${escapeHtml(divisionFor(gender, ageGroup))}</h2>
    <p class="note">Methods are evaluated independently for each selected race year. Scan labels identify each year's ranking scope and absence threshold. Missing or incompatible evidence stays explicit. Strict fallback means the strict allocation target is shown, not borrowed estimate evidence. Reported minute values and density estimates are approximate. Championship matches are not proof of slot acceptance.</p>
    ${evidenceNote}
    <p class="note">The exploratory match-density boundary compares observed Kona-starter match rates by ranking position with a constant-rate model, then fits a two-rate breakpoint. It requires at least 3 matches before the breakpoint and positive BIC improvement after the penalty; it reports the best breakpoint and weighted 5%-95% rank/time support, with sensitivity to single-race matches. This is unverified matching density, not evidence of actual acceptance or declines. Race targets never place this boundary faster than strict allocation.</p>
    <div class="table-wrap"><table><thead><tr><th>Race year</th>${approaches.map(({label}) => `<th>${escapeHtml(label)}</th>`).join("")}</tr></thead><tbody>${years.map(year => `<tr><td>${yearCell(eventId, year)}</td>${approaches.map(({mode}) => `<td>${approachCell(standards[year][mode], mode)}</td>`).join("")}</tr>`).join("") || '<tr><td colspan="6" class="empty">No race years are visible.</td></tr>'}</tbody></table></div>
    ${approachSummaryTable(eventId, years, approaches, standards)}`;
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
  section.querySelector(".note").textContent = `${division} · objective A, current rules on past results. Matched-slot cutoff uses the Nth same-cycle matched pool rank (N = performance-pool slots), re-ranked under current rules; for R1-R4 race-years those starters qualified through age-group slots. Insufficient or incompatible evidence is unavailable and matches do not prove slot acceptance. Chance uses the existing day-to-day variation model; the rank factor is not calibrated or backtested. Strict fallbacks are labelled in the table and excluded from the chart; reported evidence is never replaced. Modified courses are excluded.`;
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

const evidenceStyles = {strict: ["#006d77", ""], matched: ["#d1495b", "10 3"], density: ["#b08900", "2 3"], scan: ["#277da1", "9 3 2 3"], calibrated: ["#913d70", "12 4"], reported: ["#495057", "4 4"]};
const evidenceColors = {matched: "#00796b", unmatched: "#8d9994", winner: "#d4a017", density: "#e9b949", scan: "#277da1"};
const evidenceWinnerRecords = new Map();

function evidenceWinnerDot(cx, cy) {
  return `<circle class="evidence-winner" cx="${cx}" cy="${cy}" r="3" fill="${evidenceColors.winner}" pointer-events="none"/>`;
}

function evidenceSwatch(mode) {
  const [color, dash] = evidenceStyles[mode];
  return `<svg class="evidence-swatch" viewBox="0 0 24 8" aria-hidden="true"><line x1="0" y1="4" x2="24" y2="4" stroke="${color}" stroke-width="2.5" stroke-dasharray="${dash}"/></svg>`;
}

// Name of an age-group winner from the race results; null unless the fastest finisher matches the winner time.
function ageGroupWinnerName(eventId, year, division, time) {
  if (!evidenceWinnerRecords.has(eventId)) {
    const fastest = new Map();
    (DATASETS[eventId]?.records || []).forEach(row => {
      const key = `${row.year}|${row.division}`;
      if (!fastest.has(key) || row.overall < fastest.get(key).overall) fastest.set(key, row);
    });
    evidenceWinnerRecords.set(eventId, fastest);
  }
  const row = evidenceWinnerRecords.get(eventId).get(`${year}|${division}`);
  return row && Number.isFinite(time) && Math.abs(row.overall - time) <= 1 ? row.name : null;
}

function rankedFasterCount(ranking, ageGraded) {
  let low = 0, high = ranking.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (ranking[middle][1] < ageGraded) low = middle + 1;
    else high = middle;
  }
  return low;
}

// Age-group panels scale to their own slots and boundaries instead of a shared pool axis.
function ageGroupAxisMaximum(ranks, fieldSize) {
  const span = 1.25 * Math.max(10, ...ranks.filter(Number.isFinite));
  const rounded = span <= 20 ? 5 * Math.ceil(span / 5) : span <= 100 ? 10 * Math.ceil(span / 10) : 50 * Math.ceil(span / 50);
  return Math.max(1, Math.min(fieldSize, rounded));
}

function targetEvidenceEntries(eventId, years) {
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
    const matchedWinners = new Map();
    if (plotCompatible) winnerStarters.forEach(starter => {
      if (starter.gender !== dashboardContext.gender) return;
      (starter.matches || []).forEach(match => {
        if (match.event_id !== eventId || match.year !== year) return;
        const winner = plotScope === "age group"
          ? match.division === standard.division && match.initial_slot === "Strict age-group slot" && match.pool_rank === 1
          : match.initial_slot === "Automatic winner";
        if (winner) matchedWinners.set(match.division, {name: starter.name, finishTime: match.finish_time});
      });
    });
    // P1 winners (matched or not) come from the objective's own allocation; they never hold a pool rank.
    const winnerTimes = new Map(Object.entries((qualificationSystem === "historical"
      ? data.historical_qualification?.pools : data.qualification?.pools)?.[year]?.winners || {})
      .filter(([division]) => division.startsWith(dashboardContext.gender === "Male" ? "M" : "F")));
    matchedWinners.forEach((winner, division) => { if (!winnerTimes.has(division)) winnerTimes.set(division, winner.finishTime); });
    const plotWinners = plotCompatible && plotScope === "gender" ? [...winnerTimes].map(([division, finishTime]) => {
      const winnerRatio = qualificationSystem === "historical"
        ? historicalRows.find(row => row.division === division)?.ratio : data.qualification?.ratios?.[division];
      const matched = matchedWinners.get(division);
      return {division, finishTime, matched: Boolean(matched),
        name: matched?.name || ageGroupWinnerName(eventId, year, division, finishTime),
        ageGraded: Number.isFinite(finishTime) && winnerRatio > 0 ? finishTime * winnerRatio : null};
    }).sort((first, second) => first.division.localeCompare(second.division)) : [];
    const leaderRow = plotCompatible && plotScope === "age group" ? plotRanking[0] : null;
    const leader = leaderRow ? {matched: leaderRow[3] === true || leaderRow[2] > 0,
      name: matchedWinners.get(standard.division)?.name || ageGroupWinnerName(eventId, year, standard.division, leaderRow[0])} : null;
    return {year, standard, standards, pool, sourceCycle, matchEligible, compatible: hasMatches,
      ranking: hasMatches ? pool.ranking_evidence : rawRanking, expectedSlots,
      plotPool, plotCompatible, plotRanking, plotWinners, leader,
      plotOnlyLegacy: qualificationSystem === "historical" && source?.method === "legacy" && plotCompatible,
      plotUnavailableReason};
  });
  const methodsFor = entry => {
    const {standard, standards, pool, compatible, ranking, expectedSlots} = entry;
    const reason = DATASETS[eventId]?.group === "703" ? "No 70.3 World Championship starter list"
      : "No compatible ranked starter evidence for this race-year and cycle";
    const info = (mode, rank, basis = "", noRank = "No rank available") => {
      const result = standards[mode];
      const fallback = result?.cutoffSource?.startsWith("Strict fallback");
      const method = {mode, label: cutoffLabels[mode], rank: null, basis, target: null};
      if (!result) return {...method, status: "No compatible target"};
      if (!result.available || fallback) return {...method, status: fallback ? result.cutoffSource : result.unavailableReason || result.cutoffSource || "Unavailable"};
      const target = assumptionTime(result);
      if (!ranking.length) return {...method, target, status: reason};
      if (!Number.isFinite(rank) || rank < 1 || rank > ranking.length) return {...method, target,
        status: Number.isFinite(rank) ? `rank ${rank}: no ranked finisher` : noRank};
      const [finish, graded] = ranking[rank - 1];
      return {...method, rank, target, finish, graded};
    };
    const ordinal = value => `${value}${[11, 12, 13].includes(value % 100) ? "th" : ["th", "st", "nd", "rd"][value % 10] || "th"}`;
    const density = pool?.cutoff_estimate || {};
    const scan = pool?.cutoff_scan || {};
    const factor = standards.calibrated;
    const factorValue = factor?.rollDownFactor ?? qualificationAssumptions.rollDownFactor ?? 0;
    const factorDetail = Number.isFinite(expectedSlots)
      ? `scenario f = ${factorValue}; extra = floor(${expectedSlots} × f + 0.5) = ${Math.floor(expectedSlots * factorValue + 0.5)}` : "scenario";
    const matched = standards.matched;
    const matchedDetail = !matched?.available ? "" : standard?.scope === "age group"
      ? `${ordinal(expectedSlots)} of ${matched.matchedPoolStarters} matched age-group ranks, a matched age-group winner counts (N = ${expectedSlots} age-group slots)`
      : `${ordinal(expectedSlots)} of ${matched.matchedPoolStarters} matched pool ranks (N = ${expectedSlots} pool slots)`;
    const densityDetail = Number.isFinite(density.low_rank) && Number.isFinite(density.high_rank)
      ? `exploratory; support ranks ${density.low_rank}-${density.high_rank}; ${density.matched_pool_starters ?? "unknown"} matched ranks${density.sensitive ? "; sensitive to single-race matches" : ""}`
      : density.reason || "";
    const scanDetail = scan.criterion_met
      ? `stopping gap ${scan.gap_start_rank}-${scan.gap_end_rank}${Number.isFinite(scan.modeled_roll_down_percent) ? `; model-derived roll-down ${scan.modeled_roll_down_percent}%` : ""}`
      : scan.reason || "";
    const reported = standards.reported;
    const reportRank = compatible && reported?.available && pool?.reported_cutoff_precision === "second"
      ? evidenceRankAtOrBelow(ranking, pool.reported_cutoff, standard.scope) : {rank: null, reason: "reported precision does not establish an exact rank"};
    const reportDetail = pool?.reported_cutoff_source
      ? `${pool.reported_cutoff_source}; reported cutoff ${duration(pool.reported_cutoff)}; ${pool.reported_cutoff_precision || "unknown"} precision` : "";
    const methods = [
      info("strict", expectedSlots, standard?.scope === "gender" ? "initial pool boundary; AG winners use the separate automatic route" : "allocated age-group boundary"),
      info("matched", matched?.matchedCutoffRank, matchedDetail),
      info("density", density.rank, densityDetail),
      info("scan", scan.criterion_met ? scan.rank : null, scanDetail, scan.criterion_met ? "no post-allocation match" : "scan incomplete"),
      info("calibrated", factor?.factorRank, factorDetail),
      info("reported", reportRank.rank, reportDetail, reportRank.reason),
    ];
    const reportedRow = methods.at(-1);
    if (!reportedRow.rank && reportedRow.target && standard?.scope === "gender" && Number.isFinite(pool?.reported_cutoff)) {
      reportedRow.gradedText = pool.reported_cutoff_precision === "second"
        ? qualificationDuration(pool.reported_cutoff) : `~${duration(pool.reported_cutoff).slice(0, 5)}`;
    }
    return entry.matchEligible ? methods : methods.filter(method => (entry.sourceCycle
      ? ["strict", "matched", "calibrated"] : ["strict", "calibrated"]).includes(method.mode));
  };
  // B R1-R4 descriptive markers: never a qualification method, target or metric.
  const legacyRowsFor = ({plotPool, plotRanking}) => {
    const density = plotPool.cutoff_estimate || {};
    const scan = plotPool.cutoff_scan || {};
    const row = (mode, label, rank, basis, missing) => {
      const ranked = Number.isFinite(rank) && rank >= 1 && rank <= plotRanking.length ? plotRanking[rank - 1] : null;
      return {mode, label, plotOnly: true, rank: ranked ? rank : null, finish: ranked?.[0], graded: ranked?.[1],
        target: "not a target", basis: ranked ? basis : "", status: ranked ? null : missing};
    };
    return [
      row("density", "Legacy density boundary", density.rank,
        `descriptive${Number.isFinite(density.low_rank) && Number.isFinite(density.high_rank) ? `; support ranks ${density.low_rank}-${density.high_rank}` : ""}; age-group rank 1 excluded`,
        `unavailable: ${density.reason || "insufficient evidence"}`),
      row("scan", "Five-unmatched scan", scan.criterion_met === true && scan.consecutive_absences === 5 ? scan.rank : null,
        `descriptive; stopping gap ${scan.gap_start_rank}-${scan.gap_end_rank}; age-group rank 1 excluded`,
        `unavailable: ${scan.reason || "incomplete scan"}`),
    ];
  };
  entries.forEach(entry => {
    entry.methods = methodsFor(entry);
    entry.legacyRows = entry.plotOnlyLegacy ? legacyRowsFor(entry) : [];
  });
  return entries;
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
  const entries = targetEvidenceEntries(eventId, years);
  const expanded = document.getElementById("targetEvidenceExpand").checked;
  const ageGroupPanel = entry => entry.plotCompatible && entry.plotPool?.slot_scope === "age group";
  const poolMaximum = expanded ? Math.max(100, ...entries.filter(entry => !ageGroupPanel(entry)).flatMap(({pool, methods}) => [
    ...methods.map(method => method.rank || 0), methods.find(method => method.mode === "scan")?.rank ? pool?.cutoff_scan?.gap_end_rank || 0 : 0,
    methods.find(method => method.mode === "density")?.rank ? pool?.cutoff_estimate?.high_rank || 0 : 0,
  ])) : 100;
  const panelMaximum = entry => {
    if (!ageGroupPanel(entry)) return poolMaximum;
    if (expanded) return entry.plotRanking.length;
    const scan = entry.plotPool.cutoff_scan || {};
    // The density support band may run past the axis; it is clipped rather than stretching the scale.
    return ageGroupAxisMaximum([entry.expectedSlots, ...entry.methods.map(method => method.rank), ...entry.legacyRows.map(row => row.rank),
      ...(entry.plotOnlyLegacy && scan.criterion_met === true && scan.consecutive_absences === 5 ? [scan.gap_end_rank] : [])], entry.plotRanking.length);
  };
  const plot = {left: 130, right: 940, top: 12, matched: 38, unmatched: 84, bottom: 110};
  const axis = maximum => {
    const step = (plot.right - plot.left) / maximum;
    const x = rank => Math.round((plot.left + (rank - 0.5) * step) * 10) / 10;
    const tickStep = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500].find(value => maximum / value <= 10) || 1000;
    const ticks = [...new Set([1, ...Array.from({length: Math.floor(maximum / tickStep)}, (_, index) => (index + 1) * tickStep)])];
    if (maximum - ticks.at(-1) >= tickStep * 0.4) ticks.push(maximum);
    const band = (low, high, color, opacity, title) => low <= maximum
      ? `<rect x="${x(low) - step / 2}" y="${plot.top}" width="${(Math.min(high, maximum) - low + 1) * step}" height="${plot.bottom - plot.top}" fill="${color}" opacity="${opacity}"><title>${escapeHtml(title)}</title></rect>` : "";
    const boundary = (rank, mode, title) => rank <= maximum
      ? `<line x1="${x(rank)}" x2="${x(rank)}" y1="${plot.top}" y2="${plot.bottom}" stroke="${evidenceStyles[mode][0]}" stroke-width="2" stroke-dasharray="${evidenceStyles[mode][1]}"><title>${escapeHtml(title)}</title></line>` : "";
    return {maximum, step, x, ticks, band, boundary};
  };
  const methodTitle = method => `${method.label}: rank ${method.rank}; finisher ${Number.isFinite(method.finish) ? duration(method.finish) : "unavailable"}${Number.isFinite(method.graded) ? `; age-graded ${qualificationDuration(method.graded)}` : ""}${method.basis ? `; ${method.basis}` : ""}`;
  const hit = (cx, cy, width, height, detail, focusable) => `<rect class="evidence-point" x="${Math.round((cx - width / 2) * 10) / 10}" y="${cy - height / 2}" width="${Math.round(width * 10) / 10}" height="${height}" fill="transparent" tabindex="${focusable ? 0 : -1}" role="button" aria-label="${escapeHtml(detail)}" aria-keyshortcuts="ArrowLeft ArrowRight" aria-describedby="targetEvidenceTooltip" data-x="${cx}" data-evidence-detail="${escapeHtml(detail)}"/>`;
  const methodTable = ({methods, legacyRows, expectedSlots, standard, matchEligible, sourceCycle}) => {
    const graded = standard?.scope !== "age group";
    const beyond = rank => !Number.isFinite(rank) || !Number.isFinite(expectedSlots) ? "—"
      : rank > expectedSlots ? `+${rank - expectedSlots}` : String(rank - expectedSlots);
    const rows = [...methods, ...legacyRows].map(method => `<tr${method.plotOnly ? ' class="plot-only"' : ""}>`
      + `<td>${evidenceSwatch(method.mode)}${escapeHtml(method.label)}${method.plotOnly ? " <small>(plot only)</small>" : ""}</td>`
      + `<td class="num">${method.rank ?? "—"}</td><td class="num">${beyond(method.rank)}</td>`
      + `<td>${Number.isFinite(method.finish) ? duration(method.finish) : "—"}</td>`
      + (graded ? `<td>${Number.isFinite(method.graded) ? qualificationDuration(method.graded) : escapeHtml(method.gradedText || "—")}</td>` : "")
      + `<td>${escapeHtml(method.target || "—")}</td>`
      + `<td class="basis">${escapeHtml([method.status, method.basis].filter(Boolean).join("; "))}</td></tr>`).join("");
    const missing = matchEligible ? "" : qualificationSystem === "current" && sourceCycle
      ? `<p class="note">Match-density boundary, 15-absence scan and reported last accepted are not applicable: the original race used age-group allocation (R1-R4), and these pool methods need an original P1 race. The matched-slot cutoff re-ranks this cycle's matched starters under current rules, although they qualified through age-group slots.</p>`
      : sourceCycle
      ? `<p class="note">Match-density boundary, 15-absence scan and reported last accepted are not applicable: the original race used age-group allocation (R1-R4), and these pool methods need an original P1 race. The matched-slot cutoff takes the Nth matched rank in the actual age-group ranking (N = age-group slots); a matched age-group winner counts.</p>`
      : `<p class="note">Matched-slot cutoff, match-density boundary, 15-absence scan and reported last accepted are not applicable: the original qualifying cycle is unknown, and these methods need a known qualifying cycle.</p>`;
    return `<table class="evidence-methods"><thead><tr><th>Method</th><th class="num">Rank</th><th class="num" title="Ranks past the initial allocation: a model or scenario depth, not a count of declines">Beyond allocation</th><th>Finish time</th>${graded ? "<th>Age-graded</th>" : ""}<th>Target ${escapeHtml(standard?.division || "")}</th><th>Basis</th></tr></thead><tbody>${rows}</tbody></table>${missing}`;
  };
  panels.innerHTML = entries.map(entry => {
    const {year, methods, expectedSlots, plotPool, plotCompatible, plotRanking, plotWinners, leader, plotOnlyLegacy, plotUnavailableReason} = entry;
    const table = methodTable(entry);
    if (!plotCompatible || !plotRanking.length) {
      const reason = plotCompatible ? "No ranked qualifying finishers are available for this World Championship match list." : plotUnavailableReason;
      return `<div class="evidence-year" data-evidence-year="${escapeHtml(year)}"><div class="evidence-year-head"><h3>${escapeHtml(year)}</h3><span>Ranked evidence unavailable</span></div><p class="note">${escapeHtml(reason)}</p>${table}</div>`;
    }
    const ageGroupScope = plotPool.slot_scope === "age group";
    const {maximum, step, x, ticks, band, boundary} = axis(panelMaximum(entry));
    const scope = ageGroupScope ? `Age group ${dashboardContext.ageGroup} rank` : `${dashboardContext.gender} performance pool rank`;
    const scan = plotPool.cutoff_scan || {};
    const density = plotPool.cutoff_estimate || {};
    const selected = mode => methods.some(method => method.mode === mode && method.rank);
    let markup = ticks.map(rank => `<line class="grid" x1="${x(rank)}" x2="${x(rank)}" y1="${plot.top}" y2="${plot.bottom}"/>`).join("")
      + `<text x="${plot.left - 12}" y="${plot.matched + 4}" text-anchor="end">Matched</text><text x="${plot.left - 12}" y="${plot.unmatched + 4}" text-anchor="end">Not matched</text>`;
    if (selected("density") && Number.isFinite(density.low_rank) && Number.isFinite(density.high_rank)) {
      markup += band(density.low_rank, density.high_rank, evidenceColors.density, 0.22, `Density support: ranks ${density.low_rank} to ${density.high_rank}`);
    }
    if (selected("scan") && scan.criterion_met && Number.isFinite(scan.gap_start_rank) && Number.isFinite(scan.gap_end_rank)) {
      markup += band(scan.gap_start_rank, scan.gap_end_rank, evidenceColors.scan, 0.15, `Stopping gap: ranks ${scan.gap_start_rank} to ${scan.gap_end_rank}`);
    }
    if (plotOnlyLegacy && Number.isFinite(density.rank)) {
      if (Number.isFinite(density.low_rank) && Number.isFinite(density.high_rank)) {
        markup += band(density.low_rank, density.high_rank, evidenceColors.density, 0.22, `Historical age-group density support, plot only: ranks ${density.low_rank} to ${density.high_rank}`);
      }
      markup += boundary(density.rank, "density", `Historical age-group density boundary, plot only: rank ${density.rank}; ${density.reason || "exploratory"}`);
    }
    if (plotOnlyLegacy && scan.criterion_met === true && scan.consecutive_absences === 5
      && Number.isFinite(scan.gap_start_rank) && Number.isFinite(scan.gap_end_rank)) {
      markup += band(scan.gap_start_rank, scan.gap_end_rank, evidenceColors.scan, 0.15, `Historical five-unmatched age-group scan, plot only: ranks ${scan.gap_start_rank} to ${scan.gap_end_rank}`);
      if (Number.isFinite(scan.rank)) markup += boundary(scan.rank, "scan", `Last matched age-group finisher before five consecutive unmatched ranks: rank ${scan.rank}`);
    }
    markup += methods.filter(method => method.rank).map(method => boundary(method.rank, method.mode, methodTitle(method))).join("");
    let glyphs = "", hits = "", winnerHits = "";
    plotRanking.slice(0, maximum).forEach((row, index) => {
      const [raw, graded, matches] = row;
      const rank = index + 1;
      const isLeader = ageGroupScope && rank === 1;
      const matched = isLeader ? leader.matched : matches > 0;
      const status = isLeader
        ? `${matched ? "matched" : "not matched"} age-group rank 1${leader.name ? ` (${leader.name})` : ""}; age-group winner, not a P1 automatic-slot winner; excluded from legacy plot density/scan inputs and counts`
        : matched ? `matched${matches > 1 ? `, ${matches} candidate races` : ""}` : "not matched";
      const detail = `Race year ${year}; ${scope}: ${rank}; Finishing time: ${Number.isFinite(raw) ? duration(raw) : "unavailable"}${Number.isFinite(graded) ? `; age-graded time: ${qualificationDuration(graded)}` : ""}; Match status: ${status}`;
      const cy = matched ? plot.matched : plot.unmatched;
      glyphs += isLeader ? evidenceWinnerDot(x(rank), cy)
        : `<circle cx="${x(rank)}" cy="${cy}" r="3" fill="${matched ? evidenceColors.matched : evidenceColors.unmatched}" pointer-events="none"/>`;
      hits += hit(x(rank), cy, step, 36, detail, index === 0);
    });
    // P1 winners sit where their age-graded time falls but never take a pool rank.
    const overflow = {matched: 0, unmatched: 0};
    plotWinners.forEach(winner => {
      const faster = Number.isFinite(winner.ageGraded) ? rankedFasterCount(plotRanking, winner.ageGraded) : null;
      const inside = faster !== null && faster < maximum;
      const lane = winner.matched ? "matched" : "unmatched";
      const cx = inside ? Math.round((plot.left + faster * step) * 10) / 10 : plot.right + 20 + 7 * Math.min(4, overflow[lane]++);
      const position = faster === null ? "no age-graded standard, so no position"
        : faster === 0 ? "faster than every ranked pool finisher by age-graded time"
        : faster >= plotRanking.length ? "slower than every ranked pool finisher by age-graded time"
        : `between pool ranks ${faster} and ${faster + 1} by age-graded time`;
      const detail = `Race year ${year}; AG winner ${winner.division}; ${winner.name || "name unavailable"}; finishing time ${Number.isFinite(winner.finishTime) ? duration(winner.finishTime) : "unavailable"}; separate automatic-slot route; no performance-pool rank; ${winner.matched ? "matched" : "not matched"} on the World Championship start list${Number.isFinite(winner.ageGraded) ? `; age-graded ${qualificationDuration(winner.ageGraded)}` : ""}; ${position}${inside ? "" : `; drawn right of displayed rank ${maximum}`}`;
      glyphs += evidenceWinnerDot(cx, plot[lane]);
      winnerHits += hit(cx, plot[lane], 10, 16, detail, false);
    });
    if (overflow.matched || overflow.unmatched) {
      markup += `<line class="grid" x1="${plot.right + 8}" x2="${plot.right + 8}" y1="${plot.top}" y2="${plot.bottom}" stroke-dasharray="3 3"/><text x="${plot.right + 34}" y="${plot.bottom + 17}" text-anchor="middle">&gt;${maximum}</text>`;
    }
    markup += `<line class="axis" x1="${plot.left}" y1="${plot.bottom}" x2="${plot.right}" y2="${plot.bottom}"/>`
      + ticks.map(rank => `<line class="axis" x1="${x(rank)}" x2="${x(rank)}" y1="${plot.bottom}" y2="${plot.bottom + 4}"/><text x="${x(rank)}" y="${plot.bottom + 17}" text-anchor="middle">${rank}</text>`).join("")
      + `<text x="${(plot.left + plot.right) / 2}" y="${plot.bottom + 36}" text-anchor="middle">${escapeHtml(scope)}</text>`
      + glyphs + hits + winnerHits;
    const winnerSummary = ageGroupScope
      ? `age-group rank 1 ${leader?.matched ? "matched" : "not matched"}`
      : `${plotWinners.length} AG winners, ${plotWinners.filter(winner => winner.matched).length} matched`;
    const facts = [scope, `WC ${plotPool.kona_cycle} start list`, `ranked under ${plotPool.ranking_cycle} rules`,
      `${expectedSlots} initial ${ageGroupScope ? "age-group" : "pool"} slots`,
      `${plotRanking.filter(row => row[2] > 0).length} matched ranks${ageGroupScope ? " besides rank 1" : ""}`, winnerSummary,
      `showing ranks 1-${maximum} of ${plotRanking.length}`];
    return `<div class="evidence-year" data-evidence-year="${escapeHtml(year)}"><div class="evidence-year-head"><h3>${escapeHtml(year)}</h3><span>${facts.map(escapeHtml).join(" · ")}</span></div>`
      + `<svg class="chart evidence-chart" viewBox="0 0 1000 ${plot.bottom + 44}" role="group" aria-label="${escapeHtml(year)} ${escapeHtml(scope)}. Use left and right arrow keys to inspect ranks and age-group winners.">${markup}</svg>${table}</div>`;
  }).join("");
  const hasAgeGroupPanels = entries.some(ageGroupPanel);
  const axisNote = [hasAgeGroupPanels && entries.every(entry => ageGroupPanel(entry) || !entry.plotCompatible) ? ""
    : `Pool panels show ranks 1-${poolMaximum}${expanded ? " through the available boundaries" : " (expand to see later boundaries and gaps)"}.`,
  hasAgeGroupPanels ? `Age-group panels are scaled to their own slots and boundaries${expanded ? " and show the whole age-group field" : " (expand to see the whole age-group field)"}.` : ""].filter(Boolean).join(" ");
  note.textContent = `${qualificationSystem === "current" ? "A: current rules on historical results" : "B: historically correct rules"}. ${axisNote} Dots are the race-year's ranked finishers: teal if found on the same-cycle World Championship start list, grey if not. Gold dots are age-group winners, matched or not. In a performance-pool ranking they take the separate automatic-slot route: they are placed by age-graded time but hold no pool rank and are excluded from pool ranks, matched-slot counts, density and scan. ${qualificationSystem === "current"
    ? "Races that originally used age-group allocation (R1-R4) show strict, matched-slot and rank-factor boundaries; their matched starters qualified through age-group slots and are re-ranked under current rules."
    : "In a historical age-group ranking the winner is age-group rank 1. The matched-slot cutoff takes the Nth matched age-group rank (N = age-group slots) and counts a matched winner; the legacy density and five-unmatched scan markers are plot-only, exclude that winner and never affect targets, Finder chances or model metrics."} Beyond allocation counts ranks past the initial slots: a model or scenario depth, not a count of declines. A match does not prove acceptance; no match does not prove absence or decline.`;
}

// Same per-year method rows as the evidence tables, so both views report identical ranks and targets.
function renderTargetMethodCharts() {
  const title = document.getElementById("qualificationChartTitle");
  const note = document.getElementById("qualificationChartNote");
  if (!title || !note || !document.getElementById("qualificationRollDownChart")) return;
  const eventId = eventSelect.value;
  if (!isQualifyingEvent(eventId)) return;
  const historical = qualificationSystem === "historical";
  const division = divisionFor(dashboardContext.gender, dashboardContext.ageGroup);
  const years = allRaceYears(eventId);
  const entries = targetEvidenceEntries(eventId, years);
  title.textContent = `${historical ? "Historical" : "Current-rules"} time needed and roll-down · ${division}`;
  const series = value => cutoffApproaches.map(({mode, label, color}) => ({mode, label, color,
    values: entries.map(entry => entry.methods.some(method => method.mode === mode) ? value(entry, mode) : null)}));
  lineChart("qualificationChart", years, series((entry, mode) => {
    const standard = entry.standards[mode];
    return standard?.available && !standard.cutoffSource?.startsWith("Strict fallback") && Number.isFinite(standard.needed) ? standard.needed : null;
  }));
  const signedRanks = value => {
    const rounded = Math.abs(value) >= 5 ? Math.round(value) : Math.round(value * 10) / 10;
    return `${rounded > 0 ? "+" : ""}${rounded}`;
  };
  const rollDownSeries = series((entry, mode) => {
    const rank = entry.methods.find(method => method.mode === mode)?.rank;
    return Number.isFinite(rank) && Number.isFinite(entry.expectedSlots) ? rank - entry.expectedSlots : null;
  });
  lineChart("qualificationRollDownChart", years, rollDownSeries, signedRanks,
    {zeroBaseline: rollDownSeries.every(item => item.values.every(value => value === null || value >= 0))});
  note.textContent = `${historical ? "B: historically correct rules" : "A: current rules on historical results"}. Top: raw ${division} finish time needed per race-year for every applicable method (pool years: slower of the age-group winner and the pool equivalent). Bottom: each method's boundary rank minus the initial slots, from the same ranking as the evidence tables above. Strict allocation is the no-roll-down baseline (0); the rank factor is a scenario; matched-slot, density and scan are model estimates from matched World Championship starters; reported last accepted counts only with an exact rank. ${historical
    ? "R1-R4 years use age-group ranks and offer strict, matched-slot (Nth matched age-group rank, a matched winner counts) and rank factor; P1 years use gender-pool ranks."
    : "All years use the current gender pool; matched-slot cutoffs of R1-R4 race-years re-rank starters who qualified through age-group slots."} Strict fallbacks and plot-only legacy markers are excluded. Roll-down depth is not a count of declines or proof of acceptance.`;
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
    const points = [...point.closest("svg").querySelectorAll(".evidence-point")]
      .sort((first, second) => Number(first.dataset.x) - Number(second.dataset.x));
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
  renderTargetMethodCharts();
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
    .qualification-approach {flex:0 0 auto; border:0; padding:0; margin:0; min-width:min(100%,520px)}
    .qualification-approach legend {float:left; width:100%; padding:0; margin:0 0 6px; color:var(--muted); font-size:11px; font-weight:700; text-transform:uppercase; line-height:20px}
    .segmented-control {clear:both; display:flex; border:1px solid var(--line-strong); border-radius:3px; overflow:hidden; min-height:39px}
    .segmented-control label {display:flex; align-items:center; gap:7px; padding:0 12px; background:#f4f7f5; cursor:pointer; flex:1 0 auto; white-space:nowrap}
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
    .assumption-fields {align-items:flex-start; gap:12px 24px; margin-top:12px; border-top:1px solid var(--line); padding-top:12px}
    .assumption-fields > label {line-height:20px}
    .assumption-fields .binary-label {display:flex; align-items:center; gap:7px; height:39px; color:var(--ink); font-size:13px; font-weight:600; text-transform:none}
    .field-head {display:flex; align-items:center; gap:6px; height:20px; margin-bottom:6px; color:var(--muted); font-size:11px; font-weight:700; text-transform:uppercase}
    .field-head label {display:inline; line-height:20px}
    .context-tip {position:relative; min-width:110px}
    .factor-input-row {display:flex; align-items:center; gap:6px}
    .factor-input-row input {max-width:110px}
    .factor-status {display:block; max-width:300px; margin-top:4px; color:var(--muted); font-size:12px; line-height:1.35}
    #finderObjective {align-self:center; font-size:12px; font-weight:700}
    #cutoffHelp {flex:1 1 100%; color:var(--muted); font-size:12px}
    #cutoffHelp summary {cursor:pointer; color:var(--ink); font-weight:700}
    #cutoffHelp p {max-width:960px; margin:6px 0 0}
    .context-help {flex:0 0 auto; width:20px; height:20px; min-height:0; padding:0; color:var(--ink); background:#e5ece8; border:1px solid var(--line); border-radius:50%; font-size:11px; font-weight:700; line-height:1}
    .context-tip [role=tooltip] {display:none; position:absolute; z-index:20; top:calc(100% + 4px); left:0; box-sizing:border-box; width:260px; max-width:calc(100vw - 48px); padding:9px; color:#fff; background:#15231e; border-radius:3px; font-size:12px; font-weight:400; text-transform:none; line-height:1.4; overflow-wrap:anywhere}
    .context-tip:focus-within:has(input:focus-visible) [role=tooltip], .context-help:focus-visible + [role=tooltip], .context-help[aria-expanded=true] + [role=tooltip] {display:block}
    @media (hover:hover) {.context-tip:hover [role=tooltip] {display:block}}
    .assumption-fields input[type=checkbox] {width:auto}
    #selectedQualificationSummary {border-bottom:1px solid var(--line); padding-bottom:16px; margin-bottom:18px}
    #contextYearCount {font-size:12px; color:var(--muted)}
    .chart-panel {border:0; border-top:1px solid var(--line); border-radius:0; box-shadow:none; padding:16px 0; background:transparent}
    #comparePanel .chart-grid:empty {display:none}
    h1 {font-size:32px} .metric strong {font-size:22px; overflow-wrap:anywhere}
    @media(max-width:700px) {.context-fields {display:grid; grid-template-columns:repeat(2,minmax(0,1fr))} .context-fields label {min-width:0} .context-fields select {width:100%} .qualification-approach, .assumption-fields > label {grid-column:1 / -1; min-width:0} .segmented-control input {flex:0 0 auto} .segmented-control label {flex:1 1 0; padding:7px 10px; white-space:normal} .segmented-control span {min-width:0; overflow-wrap:anywhere} .context-tip {grid-column:1 / -1; min-width:0} .context-tip [role=tooltip] {left:0; right:auto} h1 {font-size:27px}}
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
      <div class="context-tip"><div class="field-head"><label for="contextRollDownFactor">Additional hypothetical declines per slot</label><button type="button" class="context-help" aria-label="Help: roll-down factor" aria-controls="rollDownFactorHelp" aria-expanded="false">?</button><span role="tooltip" id="rollDownFactorHelp">A hypothetical ratio of additional declines per initial slot, not observed declines, a probability, or a percentage of time. Extra positions are slots × factor rounded to the nearest integer, with halves rounded upward. With 30 slots, factors 0, 1 and 2 target ranks 30, 60 and 90. Automatic winner slots are separate.</span></div><div class="factor-input-row"><input id="contextRollDownFactor" type="number" min="0" step="any" inputmode="decimal" aria-describedby="rollDownFactorHelp contextRollDownStatus"><button type="button" class="context-action" id="resetRollDownFactor">Reset to 0</button></div><output id="contextRollDownStatus" class="factor-status" aria-live="polite"></output></div>
      <div class="context-tip"><div class="field-head"><span>Missing evidence</span><button type="button" class="context-help" aria-label="Help: strict fallback" aria-controls="fallbackHelp" aria-expanded="false">?</button><span role="tooltip" id="fallbackHelp">Use the strict allocation target only when the selected method has no compatible evidence. It remains labelled as a fallback.</span></div><label class="binary-label"><input type="checkbox" id="contextFallback" aria-describedby="fallbackHelp">Use strict fallback when evidence is unavailable</label></div>
      <details id="cutoffHelp"><summary>Method and fallback information</summary><p>The rank factor is a hypothetical scenario. Matched-slot cutoff takes the Nth matched starter in the compatible same-cycle championship ranking, where N is the gender-pool slot count. A uses current rules and standard for original P1 races and known R1-R4 race-years; B uses the historical ranking and standard for original P1 races and, for R1-R4 race-years, the Nth matched rank in the actual age-group ranking (N = age-group slots, a matched age-group winner counts). Fewer than N matches or incompatible evidence is unavailable, with no strict fallback; matches do not prove acceptance. Density and scan require an original P1 race and compatible same-cycle matches. Strict fallback applies only to density and scan for P1 races when checked and is labelled.</p></details>
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
  const methodTimeChart = allocation.querySelector("#qualificationChart");
  methodTimeChart.insertAdjacentHTML("beforebegin", '<h3 class="chart-subtitle">Time needed by method</h3>');
  methodTimeChart.insertAdjacentHTML("afterend", '<h3 class="chart-subtitle">Roll-down depth: ranks beyond the initial allocation</h3><svg id="qualificationRollDownChart" class="chart" viewBox="0 0 1000 330"></svg><p id="qualificationChartNote" class="note"></p>');
  const overview = document.createElement("section");
  overview.id = "targetOverview";
  const raceSelector = document.createElement("div");
  raceSelector.id = "targetRaceSelector";
  const targetEvidence = document.createElement("section");
  targetEvidence.id = "targetEvidencePlot";
  const keyDot = color => `<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="3.5" fill="${color}"/></svg>`;
  targetEvidence.innerHTML = `<div class="chart-heading"><h2>Ranked championship evidence</h2><label class="binary-label"><input type="checkbox" id="targetEvidenceExpand">Show later boundaries and stopping gaps</label></div><p id="targetEvidenceNote" class="note"></p>
    <ul class="evidence-key" aria-label="Plot key"><li>${keyDot(evidenceColors.matched)}Matched WC starter</li><li>${keyDot(evidenceColors.unmatched)}Not matched</li><li>${keyDot(evidenceColors.winner)}Age-group winner</li><li><span class="evidence-band" style="--band:${evidenceColors.density}"></span>Density support</li><li><span class="evidence-band" style="--band:${evidenceColors.scan}"></span>Scan stopping gap</li>${["strict", "matched", "density", "scan", "calibrated", "reported"].map(mode => `<li>${evidenceSwatch(mode)}${escapeHtml(cutoffLabels[mode])}</li>`).join("")}</ul>
    <div class="evidence-scroll"><div id="targetEvidenceChart"></div></div><div id="targetEvidenceTooltip" role="tooltip" hidden></div>`;
  const konaPanel = embedPanel(document.getElementById("konaPanel"));
  const evidence = stepSection("World Championship start-list evidence (Kona + Nice): who qualified where, and how far slots rolled down", konaPanel);
  evidence.id = "wcEvidence";
  document.getElementById("qualificationNote").before(raceSelector);
  content.append(overview, targetEvidence, stepSection("Compare cutoff approaches by year", selectedSummary), allocation, evidence);
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