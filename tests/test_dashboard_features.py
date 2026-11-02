import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import build_dashboard
import kona_trace


class DashboardUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = build_dashboard.build_html({})

    def test_shared_cutoff_method_selector_and_comparison_evidence_are_present(self):
        self.assertIn('id="contextCutoff"', self.html)
        self.assertIn('<option value="matched">Matched-slot cutoff</option>', self.html)
        self.assertNotIn("easiestCutoffMode", self.html)
        ui = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text(encoding="utf-8")
        self.assertIn('{mode: "matched", label: cutoffLabels.matched', ui)
        self.assertIn('info("matched", matched?.matchedCutoffRank, matchedDetail)', ui)
        for function_name in ("renderSelectedQualification", "renderOddsApproaches", "renderFinderApproaches"):
            start = ui.index(f"function {function_name}(")
            end = ui.find("\nfunction ", start + 1)
            self.assertIn("scopedCutoffApproaches", ui[start:end if end >= 0 else None])
        finder_start = ui.index("function renderFinderApproaches(")
        finder_end = ui.find("\nfunction ", finder_start + 1)
        self.assertIn('scopedCutoffApproaches("current")', ui[finder_start:finder_end])
        for label in (
            "Strict allocation", "Matched-slot cutoff", "Rank-based roll-down factor", "Reported last accepted",
            "Match-density boundary", "15-absence gender-pool scan",
        ):
            self.assertIn(label, self.html)
        self.assertNotIn('id="contextExtraPlaces"', self.html)
        self.assertNotIn('id="contextLegacyPlaces"', self.html)
        self.assertIn("No compatible target", self.html)
        self.assertIn("No estimate", self.html)
        self.assertIn("Match-density boundary", self.html)
        self.assertIn("positive BIC improvement after the penalty", self.html)
        self.assertIn("not evidence of actual acceptance or declines", self.html)
        self.assertIn("Strict fallback", self.html)
        self.assertIn("Historically correct rules", self.html)
        self.assertIn("Current performance pool on historical results", self.html)
        self.assertIn("historical-rule age-group targets, published or reconstructed allocations", self.html)
        self.assertIn("not verified slot acceptance", self.html)
        self.assertNotIn("official age-group cut-off of each race-year", self.html)
        self.assertIn(".evidence-scroll { overflow-x: auto; container-type: inline-size; }", self.html)
        self.assertIn("width: min(100%, 100cqi)", self.html)
        for input_id, help_id in (
            ("contextFallback", "fallbackHelp"),
            ("contextRollDownFactor", "rollDownFactorHelp"),
        ):
            input_tag = re.search(rf'<input\b(?=[^>]*\bid="{input_id}")[^>]*>', self.html)
            self.assertIsNotNone(input_tag, input_id)
            description = re.search(r'\baria-describedby="([^"]+)"', input_tag.group(0))
            self.assertIsNotNone(description, input_id)
            description_ids = description.group(1).split()
            self.assertIn(help_id, description_ids)
            if input_id == "contextRollDownFactor":
                self.assertIn("contextRollDownStatus", description_ids)
                self.assertIn('id="contextRollDownStatus"', self.html)
            self.assertIn(f'role="tooltip" id="{help_id}"', self.html)
            self.assertIn(f'aria-controls="{help_id}"', self.html)
        self.assertIn(".context-tip:focus-within", self.html)
        self.assertIn(".context-tip {grid-column:1 / -1; min-width:0}", self.html)
        self.assertIn(".context-tip [role=tooltip] {left:0; right:auto}", self.html)
        self.assertIn(
            ".factor-input-row {display:flex; align-items:center; gap:6px}",
            self.html,
        )

    def test_mobile_qualification_controls_use_available_width(self):
        self.assertIn(
            ".qualification-approach, .assumption-fields > label {grid-column:1 / -1; min-width:0}",
            self.html,
        )
        self.assertIn(".segmented-control span {min-width:0; overflow-wrap:anywhere}", self.html)
        self.assertIn(
            "@media(max-width:360px) {.segmented-control {flex-direction:column}", self.html
        )
        self.assertIn(".segmented-control label {min-height:44px}", self.html)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_matched_slot_cutoff_uses_nth_matched_rank_and_compatible_objective_pool(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_app.js").read_text(encoding="utf-8")
        helper = source[source.index("    function calibratedStandard("):source.index("    function easiestPoolEstimateCell(")]
        fixture = r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {fallback:true,rollDownFactor:1};
const isModifiedCourse = () => false;
const duration = value => String(value);
const qualificationDuration = value => String(value);
const currentStandard = {scope:"gender",division:"M50-54",performanceSlots:30,ratio:0.8,needed:35000,winner:34000};
const historicalStandard = {scope:"gender",division:"M50-54",performanceSlots:30,ratio:0.9,needed:34500,winner:31000};
let ageGroupStrict = null;
const strictQualificationStandard = (event,year,gender,ageGroup,system) => system === "historical" && ageGroupStrict
    ? {...ageGroupStrict,year} : ({
    ...(system === "current" ? currentStandard : historicalStandard),year,automaticSlots:4,slots:2,
});
const makePool = (rankingCycle,matchedRanks) => {
    const matches = new Set(matchedRanks);
    return {event_id:"race",year:"2025",gender:"Male",slot_scope:"gender",division:null,pool_slots:30,
        kona_cycle:"2026",ranking_cycle:rankingCycle,
        ranking_evidence:Array.from({length:60},(_,index)=>[36000+index,30000+index,matches.has(index+1)?1:0]),
        cutoff_estimate:{time:32000,rank:40},cutoff_scan:{time:32500,rank:42,criterion_met:true,consecutive_absences:15}};
};
const matchedRanks = [...Array.from({length:29},(_,index)=>index+1),31];
const currentPool = makePool("2027",matchedRanks);
const historicalPool = makePool("2026",[...Array.from({length:29},(_,index)=>index+1),35]);
const trace = {year:"2026",standard_cycle:"2026",standards:{"M50-54":0.9},
    counterfactual_standard_cycle:"2027",counterfactual_standards:{"M50-54":0.8},venues:{Male:["Kona"]},
    summaries:{all:[historicalPool]},counterfactual_summaries:[currentPool],starters:[],counterfactual_winners:[]};
const targets = [{year:"2025",gender:"Male",division:"M50-54",slot_scope:"gender",standard_cycle:"2026",
    source:{method:"performance",cycles:["2026"]}}];
const poolTimes = Array.from({length:60},(_,index)=>({division:"M50-54",age_graded:30000+index}));
const DATASETS = {race:{group:"im",qualification:{standard_cycle:"2027",pools:{2025:{male:poolTimes}}},
    historical_qualification:{targets,pools:{2025:{male:poolTimes}}}},
    im_kona:{kona_traces:{2026:trace}}};
const get = (system,mode="matched") => easiestQualificationStandard("race","2025","Male","50-54",system,mode,0);
"""
        assertions = r"""
const current = get("current");
assert.equal(current.available,true);
assert.equal(current.matchedCutoffRank,31);
assert.equal(current.matchedPoolStarters,30);
assert.equal(current.matchedTime,36030);
assert.equal(current.ageGraded,30030);
assert.equal(current.cutoffCycle,"2027");
assert.equal(current.cutoffRoster,"2026");
assert.match(current.cutoffSource,/Matched-slot cutoff.*rank 31.*30 matched.*30 slots/);
assert.equal(current.needed,Math.max(currentStandard.winner,30030/0.8));
assert.equal(current.needed,Math.max(currentStandard.winner,30030/0.8));
const originalWinnerTime=currentStandard.winner;
currentStandard.winner=40000;
assert.equal(get("current").needed,40000);
currentStandard.winner=originalWinnerTime;
const historical = get("historical");
assert.equal(historical.available,true);
assert.equal(historical.matchedCutoffRank,35);
assert.equal(historical.matchedPoolStarters,30);
assert.equal(historical.matchedTime,36034);
assert.equal(historical.ageGraded,30034);
assert.equal(historical.needed,Math.max(historicalStandard.winner,30034/0.9));

const winner = {gender:"Male",matches:[{event_id:"race",year:"2025",pool_rank:null,initial_slot:"Automatic winner"}]};
trace.counterfactual_winners=[winner]; trace.starters=[winner];
currentPool.ranking_evidence[30][2]=0;
const only29 = get("current");
assert.equal(only29.available,false);
assert.equal(only29.needed,null);
assert.match(only29.unavailableReason,/29 matched pool ranks.*30 performance-pool slots/);
assert.match(only29.cutoffSource,/No estimate/);
currentPool.ranking_evidence[30][2]=1;

for (const [system,pool] of [["current",currentPool],["historical",historicalPool]]) {
    const originalCycle=pool.kona_cycle;
    pool.kona_cycle="2019";
    assert.match(get(system).unavailableReason,/different qualifying cycle/);
    pool.kona_cycle=originalCycle;
    const originalRanking=pool.ranking_cycle;
    pool.ranking_cycle="2019";
    assert.match(get(system).unavailableReason,/different ranking cycle/);
    pool.ranking_cycle=originalRanking;
    const originalSlots=pool.pool_slots;
    pool.pool_slots=29;
    assert.match(get(system).unavailableReason,/changed allocation or standard/);
    pool.pool_slots=originalSlots;
}
const originalVenues=trace.venues;
trace.venues={Male:[]};
for (const system of ["current","historical"]) {
    assert.match(get(system).unavailableReason,/no World Championship start list for qualifying cycle 2026/);
}
trace.venues=originalVenues;
const originalCurrentRatio=trace.counterfactual_standards["M50-54"];
trace.counterfactual_standards["M50-54"]=0.7;
assert.match(get("current").unavailableReason,/changed allocation or standard/);
trace.counterfactual_standards["M50-54"]=originalCurrentRatio;
const originalCounterfactualCycle=trace.counterfactual_standard_cycle;
trace.counterfactual_standard_cycle="2019";
assert.match(get("current").unavailableReason,/different ranking cycle/);
trace.counterfactual_standard_cycle=originalCounterfactualCycle;
const originalHistoricalCycle=trace.standard_cycle;
trace.standard_cycle="2019";
assert.match(get("historical").unavailableReason,/different ranking cycle/);
trace.standard_cycle=originalHistoricalCycle;

const otherCycle = {...trace,year:"2025",counterfactual_summaries:[currentPool],summaries:{all:[historicalPool]}};
DATASETS.im_kona.kona_traces[2025]=otherCycle;
trace.counterfactual_summaries=[]; trace.summaries.all=[];
assert.match(get("current").unavailableReason,/different qualifying cycle/);
trace.counterfactual_summaries=[currentPool]; trace.summaries.all=[historicalPool];

targets[0]={year:"2025",gender:"Male",division:"M50-54",slot_scope:"age group",
    source:{method:"legacy",cycles:["2026"]}};
const historicalLegacy=get("historical");
assert.equal(historicalLegacy.available,false);
assert.equal(historicalLegacy.needed,null);
assert.match(historicalLegacy.unavailableReason,/age-group allocation.*unsupported/);
const currentLegacy=get("current");
assert.equal(currentLegacy.available,true);
assert.equal(currentLegacy.matchedCutoffRank,31);
assert.equal(currentLegacy.needed,Math.max(currentStandard.winner,30030/0.8));
assert.match(currentLegacy.cutoffSource,/original R1-R4 race: these starters qualified through age-group slots/);
for (const mode of ["density","scan"]) {
    assert.equal(get("current",mode).available,false);
    assert.match(get("current",mode).unavailableReason,/age-group allocation.*unsupported/);
}
// B R1-R4: Nth matched rank in the actual age-group ranking; a matched age-group winner counts.
ageGroupStrict = {scope:"age group",division:"M50-54",slots:3,needed:36002,winner:null};
const ageGroupPool = {event_id:"race",year:"2025",gender:"Male",slot_scope:"age group",division:"M50-54",pool_slots:3,
    kona_cycle:"2026",ranking_cycle:"2026",pool_size:12,
    ranking_evidence:Array.from({length:12},(_,index)=>[36000+index,null,[2,4].includes(index)?1:0,index === 0])};
trace.summaries.all=[ageGroupPool];
const historicalAgeGroup=get("historical");
assert.equal(historicalAgeGroup.available,true);
assert.equal(historicalAgeGroup.matchedCutoffRank,5);
assert.equal(historicalAgeGroup.matchedPoolStarters,3);
assert.equal(historicalAgeGroup.needed,36004);
assert.equal(historicalAgeGroup.ageGraded,null);
assert.match(historicalAgeGroup.cutoffSource,/rank 5 is matched age-group finisher 3 of 3 for 3 age-group slots \(a matched age-group winner counts\)/);
assert.equal(get("current").matchedCutoffRank,31);
for (const mode of ["density","scan"]) assert.match(get("historical",mode).unavailableReason,/age-group allocation.*unsupported/);
ageGroupPool.ranking_evidence[0][3]=false;
const withoutWinner=get("historical");
assert.equal(withoutWinner.available,false);
assert.equal(withoutWinner.needed,null);
assert.match(withoutWinner.unavailableReason,/only 2 matched age-group ranks for 3 age-group slots/);
ageGroupPool.ranking_evidence[0][3]=true;
ageGroupPool.pool_slots=4;
assert.match(get("historical").unavailableReason,/changed age-group allocation/);
ageGroupPool.pool_slots=3;
ageGroupPool.kona_cycle="2019";
assert.match(get("historical").unavailableReason,/different qualifying cycle/);
ageGroupPool.kona_cycle="2026";
trace.summaries.all=[historicalPool];
ageGroupStrict=null;
targets[0]={year:"2025",gender:"Male",division:"M50-54",slot_scope:"age group",
    source:{method:"legacy",cycles:["2019"]}};
assert.match(get("current").unavailableReason,/no World Championship start list for qualifying cycle 2019/);
assert.match(get("historical").unavailableReason,/age-group allocation.*unsupported/);
targets[0]={year:"2025",gender:"Male",division:"M50-54",slot_scope:"gender",standard_cycle:"2026",
    source:{method:"performance",cycles:["2026"]}};

const densityBefore=get("current","density");
const scanBefore=get("current","scan");
const factorBefore=get("current","calibrated");
currentPool.ranking_evidence.forEach(row=>{row[2]=0;});
assert.equal(get("current","density").needed,densityBefore.needed);
assert.equal(get("current","scan").needed,scanBefore.needed);
assert.equal(get("current","calibrated").factorRank,60);
assert.equal(factorBefore.factorRank,60);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_finder_fallback_is_labelled_and_excluded_from_method_chart(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text(encoding="utf-8")
        helpers = source[source.index("function scanScopeLabel("):source.index("function allRaceYears(")]
        renderer = source[source.index("function renderFinderApproaches()"):source.index("function decorateQualificationRankings()")]
        fixture = r"""
const assert = require("node:assert/strict");
const escapeHtml = value => String(value ?? "");
const assumptionTime = value => `T${value.needed}`;
const easiestDistance = {value:"703"}, easiestGender = {value:"Male"}, easiestAgeGroup = {value:"50-54"};
const easiestTypedTime = "T", DATASETS = {race:{name:"Race"}};
const divisionFor = () => "M50-54", raceGroups = () => ({"703":["race"]}), isQualifyingEvent = () => true;
const easiestProfile = () => ({used:0}), typicalTransitions = () => 0, parseTime = () => 40000;
const requestedSystems = [], evaluatedSystems = [];
const groupModel = () => ({}), scopedCutoffApproaches = system => {
    requestedSystems.push(system);
    return [{mode:"matched",label:"Matched-slot cutoff"},{mode:"reported",label:"Reported"},{mode:"scan",label:"Scan"}];
};
const allRaceYears = () => ["2025"], approachStandard = (event,year,gender,ageGroup,system,mode) => mode === "reported"
    ? {available:false,unavailableReason:"no documented matching reported cutoff"}
    : mode === "matched" ? (evaluatedSystems.push(system), {available:false,unavailableReason:"only 29 matched ranks for 30 slots"})
    : (evaluatedSystems.push(system), {available:true,needed:42000,scope:"gender",cutoffSource:"Strict fallback: no 70.3 World Championship start list"});
const isModifiedCourse = () => false, predictRaceYear = () => ({total:40000}), normalCdf = () => 0.75;
const yearCell = (id,year) => year, signedDuration = value => String(value), signedDurationShort = value => String(value);
const neededText = value => String(value), duration = value => String(value);
const head = {}, body = {}, note = {}, table = {querySelector: selector => selector === "thead" ? head : body};
const section = {querySelector: selector => selector === "table" ? table : note};
const document = {getElementById: () => section};
let chartSeries;
const categoryPointChart = (id,categories,series) => {chartSeries = series};
"""
        assertions = r"""
renderFinderApproaches();
assert.deepEqual(requestedSystems,["current"]);
assert.ok(evaluatedSystems.length > 0 && evaluatedSystems.every(system=>system === "current"));
assert.match(head.innerHTML,/Matched-slot cutoff/);
assert.match(body.innerHTML,/only 29 matched ranks for 30 slots/);
assert.match(body.innerHTML,/no documented matching reported cutoff/);
assert.match(body.innerHTML,/Strict fallback.*T42000/);
assert.match(body.innerHTML,/no 70\.3 World Championship start list/);
assert.ok(chartSeries.every(series => series.values[0].length === 0));
assert.match(note.textContent,/excluded from the chart/);
"""
        result = subprocess.run(["node"], input=fixture + helpers + renderer + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_reported_evidence_never_uses_strict_fallback_in_either_objective(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_app.js").read_text(encoding="utf-8")
        helper = source[source.index("    function easiestQualificationStandard"):source.index("    function easiestPoolEstimateCell")]
        fixture = r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {fallback:true};
const isModifiedCourse = () => false;
const strictQualificationStandard = () => ({scope:"gender",division:"M50-54",performanceSlots:20,ratio:0.8,needed:35000,winner:30000});
const DATASETS = {race:{group:"703",qualification:{standard_cycle:"2027"},historical_qualification:{targets:[
    {year:"2025",division:"M50-54",slot_scope:"gender",standard_cycle:"2026",source:{method:"performance",cycles:["2026"]}}]}},im_kona:{}};
"""
        assertions = r"""
for (const system of ["current","historical"]) {
    const get = mode => easiestQualificationStandard("race","2025","Male","50-54",system,mode,0);
    assert.equal(get("reported").available,false);
    assert.equal(get("reported").needed,null);
    assert.match(get("reported").unavailableReason,system === "current" ? /historical evidence only/ : /70\.3/);
    for (const mode of ["scan","density"]) {
        const standard = get(mode);
        assert.equal(standard.available,true);
        assert.equal(standard.needed,35000);
        assert.equal(standard.cutoffPool,null);
        assert.match(standard.cutoffSource,/Strict fallback: .+/);
    }
}
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_historical_targets_require_a_known_compatible_cycle(self):
        event = {"group": "im", "qualifying": True, "years": {"2030": ["unused"]}}
        frame = pd.DataFrame({"Division": ["M30-34"], "finish_status": ["FIN"]})
        for source in ({"method": "performance", "cycles": ["2030"]},
                       {"method": "legacy", "cycles": []}):
            with self.subTest(source=source), patch.object(build_dashboard, "read_results", return_value=frame), \
                    patch.object(build_dashboard, "prepare_eligible_age_group_rows", return_value=frame), \
                    patch.object(build_dashboard, "HISTORICAL_SLOT_SOURCES", {("im_austria", "2030"): source}):
                result = build_dashboard.load_historical_qualification_data("im_austria", event)
            self.assertEqual(result["targets"], [])
            self.assertEqual(result["unavailable_years"], ["2030"])

    def test_qualification_workspace_is_a_five_step_flow_with_embedded_evidence(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text(encoding="utf-8")
        self.assertNotIn('class="qualification-system"', self.html)
        self.assertEqual(source.count('name="contextRules" value='), 2)
        self.assertIn('const qualificationSteps = ["qyou", "qtime", "qdifficulty", "qualification", "easiest"];', source)
        self.assertIn('qualification: {label: "Qualification", views: qualificationSteps}', source)
        self.assertIn('[easiestOpenFilter, easiestFinishRisk].forEach(control => finderFilters.append(control.closest("label")))', source)
        self.assertIn('finder.prepend(finderFilters)', source)
        for label in ("1 · You", "2 · Your time", "3 · Race difficulty", "4 · Qualification targets", "5 · Where to qualify"):
            self.assertIn(label, source)
        for view in ("qualification", "easiest", "odds"):
            start = source.index(f"function {'renderSelectedQualification' if view == 'qualification' else 'renderFinderApproaches' if view == 'easiest' else 'renderOddsApproaches'}()")
            end = source.find("\nfunction ", start + 1)
            self.assertIn('"current"' if view == "easiest" else "qualificationSystem", source[start:end])
        panel_match = re.search(
            r'for \(const id of \[(.*?)\]\) \{\s+comparisonGrid\.append\(document\.getElementById\(id\)\.closest\("\.chart-panel"\)\);',
            source, re.S,
        )
        self.assertIsNotNone(panel_match)
        moved_panels = re.findall(r'"([^"]+)"', panel_match.group(1))
        self.assertEqual(set(moved_panels), {
            "compareImQualification", "compare703Qualification", "compareMeanQualification",
            "compareQualificationResidual", "compareSlotPressure", "compareCutoffPercentile",
            "compareQualificationUncertainty",
        })
        self.assertEqual(source.count('crossRacePanel.id = "crossracePanel"'), 1)
        # Former Kona Evidence, Target Hits and Cross-race tabs live inside steps 3 and 4.
        self.assertIn('embedPanel(document.getElementById("konaPanel"))', source)
        self.assertIn('embedPanel(document.getElementById("oddsPanel"))', source)
        self.assertIn('evidence.id = "wcEvidence";', source)
        self.assertIn('stepSection("Cross-race comparison charts", crossRacePanel)', source)
        self.assertIn('document.querySelector(`.legacy-tabs [data-tab="${view}"]`)', source)
        self.assertIn("if (legacyButton) legacyButton.click();", source)
        self.assertIn('activeTab = view;', source)
        self.assertIn('dashboardReturnView = activeTab;', source)
        self.assertRegex(source, r"if \(workspace \|\| view\) clearDashboardReturn\(\);")
        self.assertIn('data-evidence-race="${escapeHtml(standard.eventId)}"', source)
        self.assertIn('document.getElementById("contextReturn")', source)
        self.assertIn("function currentAbility(", self.html)
        self.assertIn('["qtime", "easiest"].includes(activeTab)', self.html)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_roll_down_counts_only_for_rule_compatible_scan_evidence(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text(encoding="utf-8")
        start = source.index("function rollDownEvidence")
        helper = source[start:source.index("\nfunction renderTargetOverview", start)]
        fixture = r"""
const assert = require("node:assert/strict");
const escapeHtml = value => String(value ?? "");
const assumptionTime = standard => `T${standard.needed}`;
"""
        assertions = r"""
const pool = (extra) => ({pool_slots: 14, slot_scope: "gender", kona_cycle: "2026", ranking_cycle: "2027",
    cutoff_scan: {rank: 51}, cutoff_estimate: {rank: 400}, ...extra});
const standard = (mode, extra = {}) => ({available: true, estimatedCutoffUsed: true, needed: 32000, mode, cutoffPool: pool(extra)});
assert.equal(rollDownEvidence(standard("scan"), "scan").passed, 37);
assert.equal(rollDownEvidence(standard("density"), "density").passed, null);
const legacyRoster = rollDownEvidence(standard("scan", {kona_cycle: "2017"}), "scan");
assert.equal(legacyRoster.passed, null);
assert.match(rollDownCell(legacyRoster), /no decline count/);
assert.equal(rollDownEvidence(standard("scan", {kona_cycle: "2017", ranking_cycle: "2017", slot_scope: "age group", pool_slots: 3, cutoff_scan: {rank: 7}}), "scan"), null);
assert.equal(rollDownEvidence(standard("density", {kona_cycle: "2017", ranking_cycle: "2017", slot_scope: "age group"}), "density"), null);
assert.equal(rollDownEvidence({...standard("scan"), available: false}, "scan"), null);
assert.match(rollDownCell(rollDownEvidence(standard("scan"), "scan")), /37 ranks beyond 14 allocated pool slots/);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_manual_navigation_clears_return_navigation_state(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text()
        start = source.index("function clearDashboardReturn")
        helper = source[start:source.index("\nfunction ", start + 1)]
        fixture = r"""
let dashboardReturnView = "easiest";
const returnButton = {hidden:false};
const document = {getElementById: id => id === "contextReturn" ? returnButton : null};
"""
        assertions = r"""
const assert = require("node:assert/strict");
clearDashboardReturn();
assert.equal(dashboardReturnView, null);
assert.equal(returnButton.hidden, true);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_cutoff_scope_and_cycle_are_required_before_legacy_report_is_shown(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        helper = script[script.index("    function easiestQualificationStandard"):script.index("    function easiestPoolEstimateCell")]
        fixture = r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {fallback:false};
const isModifiedCourse = () => false;
const standard = {scope:"age group",division:"M50-54",slots:2,needed:33000,winner:30000};
const pool = {event_id:"race",year:"2019",gender:"Male",slot_scope:"age group",division:"M50-54",pool_slots:2,kona_cycle:"2019",ranking_cycle:"2019",
    cutoff_estimate:{time:35000},cutoff_scan:{time:36000,consecutive_absences:5},reported_cutoff:31000};
const DATASETS = {race:{group:"im",qualification:{standard_cycle:"2026"},
    historical_qualification:{targets:[{year:"2019",division:"M50-54",slot_scope:"age group",standard_cycle:"2019",source:{method:"legacy",cycles:["2019"]}}]}},
    im_kona:{kona_traces:{2019:{year:"2019",standard_cycle:"2019",venues:{Male:["Kona"]},standards:{},summaries:{all:[pool]}},
        2026:{year:"2026",standards:{"M50-54":0.8},summaries:{all:[]},counterfactual_summaries:[{
            ...pool,slot_scope:"gender",division:null,pool_slots:20,reported_cutoff:null,
        }]}}}};
const strictQualificationStandard = () => standard;
"""
        assertions = r"""
const get = (system, mode) => easiestQualificationStandard("race","2019","Male","50-54",system,mode,0);
assert.equal(get("historical","reported").available,false);
assert.match(get("historical","reported").unavailableReason,/documented/);
pool.reported_cutoff_source = "Reviewed race report";
pool.reported_cutoff_precision = "minute";
assert.equal(get("historical","reported").needed,31000);
assert.equal(get("historical","reported").precision,"minute");
assert.equal(get("current","reported").available,false);
DATASETS.race.historical_qualification.targets[0].standard_cycle = "2018";
DATASETS.race.historical_qualification.targets[0].source.cycles = ["2018"];
assert.equal(get("historical","density").available,false);
assert.equal(get("historical","density").needed,null);
assert.equal(get("historical","density").strictNeeded,33000);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_counterfactual_calendar_keeps_cycle_race_years_with_current_slots(self):
        events = {
            "race": {"group": "im", "qualifying": True, "qualification_slots": 50,
                     "years": {"2017": ["old.csv"], "2025": ["recent.csv"]}},
            "half": {"group": "703", "qualifying": True, "qualification_slots": 30,
                     "years": {"2017": ["half.csv"]}},
            "nonqualifying": {"group": "im", "qualifying": False, "qualification_slots": 40,
                              "years": {"2017": ["other.csv"]}},
        }
        names = {"race": "Race", "half": "Half", "nonqualifying": "Other"}
        cycle_calendar = [
            {"qualification_cycle": "2017", "race_name": name, "event_year": "2017",
             "total_qualifiers": 40, "race_date": "2017-07-02"}
            for name in ("Race", "Half", "Other", "Unknown")
        ]
        calendar = build_dashboard.current_pool_counterfactual_calendar(cycle_calendar, events, names)
        # Only the cycle's own race-years: Austria 2017 is compared with the Kona 2017 start list.
        self.assertEqual(calendar, [
            {"qualification_cycle": "2017", "race_name": "Race", "event_year": "2017",
             "total_qualifiers": 50, "race_date": "2017-07-02"},
        ])
        self.assertEqual(build_dashboard.current_pool_counterfactual_calendar(cycle_calendar, events, {}), [])

    def test_course_analysis_controls_are_local_and_include_race_year_details(self):
        for selector in (
            "experimentalSplit", "experimentalGender", "experimentalAgeGroup",
            "experimentalBreakdownRace", "experimentalRaceA", "experimentalRaceB",
            "experimentalAthleteSearch",
        ):
            self.assertNotIn(selector, self.html)
        self.assertIn("experimentalPercentile", self.html)
        self.assertIn('id="experimentalFactorSplit"', self.html)
        for split in ("overall", "swim", "t1", "bike", "t2", "run"):
            self.assertIn(f'<option value="{split}">', self.html)
        field_heading = self.html.index('<h2 id="experimentalFieldTitle">')
        field_input = self.html.index('<input id="experimentalPercentile"')
        field_chart = self.html.index('<svg id="experimentalFieldChart"')
        self.assertLess(field_heading, field_input)
        self.assertLess(field_input, field_chart)
        self.assertIn("course-race-toggle", self.html)
        self.assertIn("standard-course-row", self.html)
        self.assertIn("Standard course (factor 1.000 reference)", self.html)
        self.assertIn("standardSplitMedians", self.html)
        self.assertIn("(% / min)", self.html)
        self.assertIn('id="contextDistance"', self.html)

    def test_scan_rate_is_explicitly_model_derived_not_observed(self):
        self.assertIn("modeled_roll_down_percent", self.html)
        self.assertIn("model-derived assumption", self.html)
        self.assertIn("not observed declines", self.html)
        self.assertIn("manualKonaCutoff", self.html)

    def test_historical_target_hits_show_each_race_year_and_cutoff_approach(self):
        self.assertIn("target · result", self.html)
        self.assertIn('yearCell(eventId, row.year)', self.html)
        self.assertIn("strict allocation target is shown", self.html)

    def test_pages_index_redirects_to_existing_dashboard_entry(self):
        index = build_dashboard.build_index_html()
        self.assertIn('url=dashboard.html', index)
        self.assertIn('href="dashboard.html"', index)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_extra_places_are_not_a_cutoff_method(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text()
        helper = source[source.index("function updateExtraPlacesControls()"):
                source.index("function updateRollDownFactorControl(")]
        fixture = r"""
const assert = require("node:assert/strict");
const dashboardContext = {distance: "im"};
let qualificationSystem = "historical";
let activeTab = "qualification";
const qualificationAssumptions = {mode:"places"};
const controls = Object.fromEntries(["contextExtraPlaces", "contextLegacyPlaces"].map(id => [id, {
    value: id === "contextLegacyPlaces" ? "3" : "2", disabled: false,
    label: {hidden: false}, closest() { return this.label; },
}]));
const document = {getElementById(id) { return controls[id]; }};
const selectedKonaTrace = () => null;
"""
        assertions = r"""
updateExtraPlacesControls();
assert.equal(controls.contextLegacyPlaces.value, "3");
dashboardContext.distance = "703";
updateExtraPlacesControls();
qualificationSystem = "current";
updateExtraPlacesControls();
assert.equal(controls.contextExtraPlaces.value, "2");
assert.equal(controls.contextLegacyPlaces.value, "3");
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_roll_down_factor_control_validates_and_resets_to_current_gender(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text()
        helper = source[source.index("function updateRollDownFactorControl("):source.index("function updateDashboardScope()")]
        fixture = r"""
const assert = require("node:assert/strict");
const dashboardContext = {gender:"Male",distance:"im"};
const qualificationAssumptions = {rollDownFactor:0};
let activeTab = "qualification", qualificationSystem = "current", renders = 0;
const DATASETS = {im_kona:{rolldown_calibration:{genders:{male:{factor:1.05,n:8},female:{factor:1.12,n:5}}}}};
const input = {value:"",attributes:{},setAttribute(key,value){this.attributes[key]=value},getAttribute(key){return this.attributes[key]}};
const output = {};
const document = {getElementById:id=>id === "contextRollDownFactor" ? input : output};
const renderSharedViews = () => renders++;
"""
        assertions = r"""
updateRollDownFactorControl();
assert.equal(input.value,"0");
assert.match(output.textContent,/not observed or calibrated/);
dashboardContext.gender="Female";
updateRollDownFactorControl();
assert.equal(input.value,"0");
input.value="2.5"; changeRollDownFactor();
assert.equal(qualificationAssumptions.rollDownFactor,2.5);
assert.match(output.textContent,/Hypothetical/);
dashboardContext.gender="Male"; updateRollDownFactorControl();
assert.equal(input.value,"2.5");
for (const value of ["", "-0.01", "Infinity"]) {
    input.value=value; changeRollDownFactor();
    assert.equal(qualificationAssumptions.rollDownFactor,2.5);
    assert.equal(input.attributes["aria-invalid"],"true");
    updateRollDownFactorControl(false);
    assert.match(output.textContent,/last valid setting/);
}
resetRollDownFactor();
assert.equal(input.value,"0");
assert.equal(qualificationAssumptions.rollDownFactor,0);
assert.equal(input.attributes["aria-invalid"],"false");
assert.equal(renders,2);
qualificationSystem="historical"; updateRollDownFactorControl();
assert.match(output.textContent,/not observed or calibrated/);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_rank_evidence_plot_keeps_scopes_and_full_stopping_gap(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text(encoding="utf-8")
        helper = source[source.index("const cutoffLabels ="):source.index("const cutoffApproaches =")]
        helper += source[source.index("function evidenceRankAtOrBelow("):source.index("function decorateDashboard()")]
        app = (Path(__file__).resolve().parents[1] / "src" / "dashboard_app.js").read_text(encoding="utf-8")
        helper += app[app.index("    function duration("):app.index("    function pace(")]
        helper += app[app.index("    function manualKonaCutoff("):app.index("    function championshipVenues(")]
        helper += app[app.index("    function calibratedStandard("):app.index("    function easiestQualificationStandard(")]
        fixture = r"""
const assert = require("node:assert/strict");
const dashboardContext = {gender:"Male",ageGroup:"50-54"};
const qualificationAssumptions = {extraPlaces:5,legacyExtraPlaces:2,rollDownFactor:15};
const cutoffApproaches = ["strict","matched","density","scan","calibrated","reported"].map(mode=>({mode}));
let qualificationSystem = "historical";
const eventSelect = {value:"race"};
const makePool = (year,rank,slots) => ({event_id:"race",year,gender:"Male",slot_scope:"age group",division:"M50-54",pool_slots:slots,
    kona_cycle:year,ranking_cycle:year,cutoff_estimate:{rank:rank-1,low_rank:rank-3,high_rank:rank},
    cutoff_scan:{rank,criterion_met:true,gap_start_rank:rank+1,gap_end_rank:rank+5,consecutive_absences:5},
    ranking_evidence:Array.from({length:140},(_,index)=>[33000+index,null,index === rank-1 ? 2 : 0,index === 0])});
const pools = {2017:makePool("2017",110,3),2025:makePool("2025",120,7)};
const historicalPools = {2017:{...pools[2017]},2025:{...pools[2025]}};
const makeCounterfactualPool = (year,rank,slots,konaCycle=year) => ({...makePool(year,rank,slots),slot_scope:"gender",division:null,
    kona_cycle:konaCycle,ranking_cycle:"2026",cutoff_scan:{rank:115,criterion_met:true,gap_start_rank:116,gap_end_rank:130,consecutive_absences:15},
    ranking_evidence:Array.from({length:145},(_,index)=>[35000+index,30000+index,index === rank-1 ? 2 : 0])});
const makeWinnerStarter = (year,automatic=false) => [{name:"Matched Winner",gender:"Male",matches:[{
    event_id:"race",year,division:"M50-54",finish_time:32100,pool_rank:automatic ? null : 1,
    initial_slot:automatic ? "Automatic winner" : "Strict age-group slot"}]}];
const makeTrace = (year,historical,current,raceYear=year,automatic=false) => ({year,standard_cycle:year,venues:{Male:["Kona"]},
    standards:{"M50-54":0.8,"M45-49":0.8},counterfactual_standard_cycle:"2026",counterfactual_standards:{"M50-54":0.8,"M45-49":0.8},
    summaries:{all:[historical]},counterfactual_summaries:[current],starters:makeWinnerStarter(raceYear,automatic),
    counterfactual_winners:makeWinnerStarter(raceYear,true)});
const currentPools = {2017:makeCounterfactualPool("2017",110,3),2025:makeCounterfactualPool("2025",120,7)};
const historicalP1 = makeCounterfactualPool("2025",120,7,"2026");
const currentP1 = makeCounterfactualPool("2025",120,7,"2026");
const target = year => ({year,division:"M50-54",slot_scope:"age group",source:{method:"legacy",cycles:[year]},
    times:Array.from({length:140},(_,index)=>index ? 33000+index : null)});
const DATASETS = {race:{group:"im",historical_qualification:{targets:[target("2017"),target("2025")]},
    qualification:{standard_cycle:"2026",ratios:{"M50-54":0.8,"M45-49":0.8},pools:Object.fromEntries(["2017","2025"].map(year=>[year,
        {male:Array.from({length:145},(_,index)=>({division:"M50-54",age_graded:30000+index})),winners:{"M45-49":40000,"F50-54":33000}}]))}},other:{group:"im"},im_kona:{kona_traces:{
    2017:makeTrace("2017",historicalPools[2017],currentPools[2017]),
    2025:makeTrace("2025",historicalPools[2025],currentPools[2025]),
    2026:makeTrace("2026",historicalP1,currentP1,"2025",true)}}};
const elements = {targetEvidencePlot:{},targetEvidenceExpand:{checked:false},targetEvidenceNote:{},targetEvidenceChart:{},targetEvidenceTooltip:{},
    qualificationChartTitle:{},qualificationChartNote:{},qualificationRollDownChart:{}};
const charts = {};
const lineChart = (id,labels,series,format,options) => { charts[id] = {labels,series,format,options}; };
const isQualifyingEvent = () => true;
const divisionFor = (gender,ageGroup) => `${gender === "Male" ? "M" : "F"}${ageGroup}`;
const document = {getElementById:id=>elements[id]};
DATASETS.im_kona.kona_traces[2017].summaries.all.push({...historicalPools[2017],division:"M45-49"});
let visible = ["2017","2025"];
const allRaceYears = ()=>visible;
const approachStandard = (event,year,gender,ageGroup,system,mode)=> {
    if (event !== "race") return null;
    const standard = system === "historical" && DATASETS.race.historical_qualification.targets.find(row=>row.year === year).source.method === "legacy"
        ? {scope:"age group",division:`${gender === "Male" ? "M" : "F"}${ageGroup}`,slots:pools[year].pool_slots,cutoffPool:pools[year]}
        : {scope:"gender",division:`${gender === "Male" ? "M" : "F"}${ageGroup}`,performanceSlots:pools[year].pool_slots,ratio:0.8,cutoffPool:pools[year]};
    if (mode === "matched") return {...standard,available:true,needed:50000,cutoffSource:"Matched-slot cutoff",
        matchedCutoffRank:system === "historical" ? 31 : 30,matchedPoolStarters:30,matchedTime:36030};
    if (mode === "reported" && !pools[year].reported_cutoff || system === "historical" && ["density","scan"].includes(mode))
        return {...standard,available:false,unavailableReason:mode === "reported" ? "no documented report" : "original age-group rules"};
    if (mode === "density" && qualificationAssumptions.densityFallback)
        return {...standard,available:true,needed:50000,cutoffSource:"Strict fallback: insufficient evidence"};
    const slots = standard.scope === "age group" ? standard.slots : standard.performanceSlots;
    const factorRank = slots + Math.floor(slots * qualificationAssumptions.rollDownFactor + 0.5);
    if (mode === "calibrated" && qualificationAssumptions.realFactor)
        return {...calibratedStandard({...standard,year,winner:0,needed:50000},event,gender,system),cutoffPool:pools[year]};
    if (mode === "calibrated" && factorRank > pools[year].ranking_evidence.length)
        return {...standard,available:false,factorRank,unavailableReason:"no ranked finisher at the factor rank"};
    return {...standard,available:true,needed:50000,cutoffSource:"scenario",factorRank,rollDownFactor:qualificationAssumptions.rollDownFactor};
};
const escapeHtml = value=>String(value ?? "");
const assumptionTime = value=>String(value.needed);
"""
        assertions = r"""
renderTargetEvidence();
let chart = elements.targetEvidenceChart.innerHTML;
assert.match(chart,/data-evidence-year="2017"/);
assert.match(chart,/data-evidence-year="2025"/);
assert.match(chart,/Age group 50-54 rank/);
assert.match(chart,/Race year 2017; Age group 50-54 rank: 1; Finishing time: 09:10:00/);
assert.doesNotMatch(chart,/Matched AG winners|evidence-winner-list|evidence-legend/);
assert.match(chart,/class="evidence-methods"/);
assert.match(chart,/Beyond allocation/);
assert.match(chart,/showing ranks 1-140 of 140/);
assert.match(elements.targetEvidenceNote.textContent,/Age-group panels are scaled to their own slots and boundaries \(expand to see the whole age-group field\)/);
assert.doesNotMatch(elements.targetEvidenceNote.textContent,/Pool panels/);
assert.equal(ageGroupAxisMaximum([3,3,7,14,12],180),20);
assert.equal(ageGroupAxisMaximum([15,15,68,80,37],180),100);
assert.equal(ageGroupAxisMaximum([3],8),8);
assert.equal(ageGroupAxisMaximum([3,null,undefined],180),15);
elements.targetEvidenceExpand.checked=true;
renderTargetEvidence();
chart = elements.targetEvidenceChart.innerHTML;
let panels = chart.split('<div class="evidence-year"').slice(1);
assert.match(panels[0],/Strict allocation: rank 3/);
assert.match(panels[0],/Rank-based roll-down factor: rank 48/);
assert.doesNotMatch(panels[0],/Match-density boundary: rank|15-absence gender-pool scan: rank|manual extra/i);
assert.match(panels[0],/Historical age-group density boundary, plot only: rank 109/);
assert.match(panels[0],/Historical five-unmatched age-group scan, plot only: ranks 111 to 115/);
assert.match(panels[0],/Race year 2017; Age group 50-54 rank: 110; Finishing time: 09:11:49/);
assert.match(panels[0],/Match status: matched age-group rank 1 \(Matched Winner\); age-group winner, not a P1 automatic-slot winner; excluded from legacy plot density\/scan inputs and counts/);
assert.match(panels[0],/<circle class="evidence-winner"[^>]+fill="#d4a017"/);
assert.match(panels[0],/age-group rank 1 matched/);
assert.match(panels[0],/2 candidate races/);
assert.match(panels[0],/<td>[^<]*<svg class="evidence-swatch"[\s\S]*?Legacy density boundary <small>\(plot only\)<\/small><\/td><td class="num">109<\/td><td class="num">\+106<\/td>/);
assert.match(panels[0],/<td class="num">3<\/td><td class="num">0<\/td>/);
assert.match(panels[1],/Strict allocation: rank 7/);
assert.match(panels[1],/Rank-based roll-down factor: rank 112/);
assert.doesNotMatch(panels[1],/Match-density boundary: rank|15-absence gender-pool scan: rank|manual extra/i);
assert.match(panels[1],/Legacy density boundary <small>\(plot only\)<\/small>/);
assert.match(panels[1],/not applicable: the original race used age-group allocation \(R1-R4\)/);
assert.doesNotMatch(chart,/Kona Standard time/);
assert.match(elements.targetEvidenceNote.textContent,/and show the whole age-group field/);
dashboardContext.ageGroup="45-49";
renderTargetEvidence();
assert.match(elements.targetEvidenceChart.innerHTML,/Age group 45-49 rank/);
dashboardContext.ageGroup="50-54";
renderTargetEvidence();
qualificationSystem = "current";
for (const mode of ["density","scan"]) {
    qualificationAssumptions.mode = mode;
    qualificationAssumptions.densityFallback = true;
    renderTargetEvidence();
    assert.doesNotMatch(elements.targetEvidenceChart.innerHTML,/Match-density boundary: rank|15-absence gender-pool scan: rank|Reported last accepted: rank|Strict fallback:/i);
}
qualificationAssumptions.densityFallback = false;
for (const pool of Object.values(pools)) Object.assign(pool,{slot_scope:"gender",division:null,ranking_cycle:"2026",
    cutoff_scan:{rank:115,criterion_met:true,gap_start_rank:116,gap_end_rank:130,consecutive_absences:15},
    ranking_evidence:Array.from({length:145},(_,index)=>[35000+index,30000+index,0])});
pools[2025].kona_cycle="2026";
Object.assign(DATASETS.race.historical_qualification.targets[1],{slot_scope:"gender",standard_cycle:"2026",source:{method:"performance",cycles:["2026"]}});
currentP1.ranking_evidence = pools[2025].ranking_evidence;
historicalP1.ranking_evidence = pools[2025].ranking_evidence;
qualificationSystem = "historical";
renderTargetEvidence();
panels = elements.targetEvidenceChart.innerHTML.split('<div class="evidence-year"').slice(1);
assert.match(panels[0],/Legacy density boundary <small>\(plot only\)<\/small>/);
assert.doesNotMatch(panels[0],/Match-density boundary: rank|15-absence gender-pool scan: rank|Reported last accepted: rank/i);
assert.match(panels[1],/15-absence gender-pool scan/);
assert.match(panels[1],/Matched-slot cutoff: rank 31/);
qualificationSystem = "current";
renderTargetEvidence();
chart = elements.targetEvidenceChart.innerHTML;
assert.equal((chart.match(/Stopping gap: ranks 116 to 130/g) || []).length,1);
assert.match(chart,/Race year 2025; Male performance pool rank: 1; Finishing time: 09:43:20; age-graded time: 08:20:00/);
assert.match(chart,/stopping gap 116-130/);
assert.match(chart,/separate automatic-slot route; no performance-pool rank/);
assert.match(chart,/Matched Winner/);
assert.match(chart,/class="evidence-winner"/);
assert.match(chart,/M50-54; Matched Winner; finishing time 08:55:00; separate automatic-slot route; no performance-pool rank; matched/);
assert.match(chart,/AG winner M45-49; name unavailable; finishing time 11:06:40; separate automatic-slot route; no performance-pool rank; not matched on the World Championship start list; age-graded 08:53:20; slower than every ranked pool finisher by age-graded time; drawn right of displayed rank 130/);
assert.match(chart,/AG winner M50-54; Matched Winner[^"]*faster than every ranked pool finisher by age-graded time/);
assert.match(chart,/2 AG winners, 1 matched/);
assert.doesNotMatch(chart,/F50-54/);
panels = chart.split('<div class="evidence-year"').slice(1);
assert.ok(panels[1].indexOf("AG winner M45-49") > panels[1].lastIndexOf("Male performance pool rank: 130;"));
assert.doesNotMatch(panels[1],/Male performance pool rank: [0-9]+; Finishing time: 08:55:00/);
assert.equal(DATASETS.im_kona.kona_traces[2026].counterfactual_winners[0].matches[0].pool_rank,null);
assert.match(chart,/Rank-based roll-down factor: rank 112/);
assert.match(chart,/Matched-slot cutoff: rank 30/);
assert.doesNotMatch(chart,/auto median/);
renderTargetMethodCharts();
const chartValues = id => Object.fromEntries(charts[id].series.map(item=>[item.mode,item.values]));
assert.equal(elements.qualificationChartTitle.textContent,"Current-rules time needed and roll-down · M50-54");
assert.deepEqual(charts.qualificationChart.labels,["2017","2025"]);
let methodTimes = chartValues("qualificationChart");
assert.deepEqual(methodTimes.strict,[50000,50000]);
assert.deepEqual(methodTimes.matched,[50000,50000]);
assert.deepEqual(methodTimes.density,[null,50000]);
assert.deepEqual(methodTimes.reported,[null,null]);
let depths = chartValues("qualificationRollDownChart");
assert.deepEqual(depths.strict,[0,0]);
assert.deepEqual(depths.matched,[27,23]);
assert.deepEqual(depths.calibrated,[45,105]);
assert.deepEqual(depths.density,[null,112]);
assert.deepEqual(depths.scan,[null,108]);
assert.equal(charts.qualificationRollDownChart.options.zeroBaseline,true);
assert.equal(charts.qualificationRollDownChart.format(12),"+12");
assert.match(elements.qualificationChartNote.textContent,/^A: current rules on historical results/);
assert.match(elements.qualificationChartNote.textContent,/re-rank starters who qualified through age-group slots/);
qualificationSystem = "historical";
renderTargetMethodCharts();
assert.equal(elements.qualificationChartTitle.textContent,"Historical time needed and roll-down · M50-54");
methodTimes = chartValues("qualificationChart");
depths = chartValues("qualificationRollDownChart");
assert.deepEqual(methodTimes.matched,[50000,50000]);
assert.deepEqual(methodTimes.density,[null,null]);
assert.deepEqual(depths.matched,[28,24]);
assert.match(elements.qualificationChartNote.textContent,/^B: historically correct rules/);
qualificationSystem = "current";
qualificationAssumptions.rollDownFactor = 1.1;
renderTargetEvidence();
chart = elements.targetEvidenceChart.innerHTML;
assert.match(chart,/Rank-based roll-down factor: rank 15/);
qualificationAssumptions.extraPlaces=9;
renderTargetEvidence();
chart = elements.targetEvidenceChart.innerHTML;
assert.doesNotMatch(chart,/Manual extra-place scenario/);
assert.match(chart,/Strict allocation: rank 3/);
assert.match(chart,/Rank-based roll-down factor: rank 15/);
qualificationAssumptions.rollDownFactor = 100;
renderTargetEvidence();
assert.match(elements.targetEvidenceChart.innerHTML,/no ranked finisher at the factor rank/);
qualificationAssumptions.rollDownFactor = 0;
pools[2025].reported_cutoff=30024;
pools[2025].reported_cutoff_source="External source";
pools[2025].reported_cutoff_precision="second";
renderTargetEvidence();
assert.match(elements.targetEvidenceChart.innerHTML,/Reported last accepted: rank 25/);
pools[2025].reported_cutoff_precision="minute";
renderTargetEvidence();
assert.match(elements.targetEvidenceChart.innerHTML,/reported precision does not establish an exact rank/);
assert.match(elements.targetEvidenceChart.innerHTML,/reported cutoff 08:20:24; minute precision/);
qualificationAssumptions.densityFallback=true;
renderTargetEvidence();
assert.match(elements.targetEvidenceChart.innerHTML,/Strict fallback: insufficient evidence/);
assert.doesNotMatch(elements.targetEvidenceChart.innerHTML,/Match-density boundary: rank/);
qualificationAssumptions.densityFallback=false;
visible=["2025"];
renderTargetEvidence();
assert.doesNotMatch(elements.targetEvidenceChart.innerHTML,/data-evidence-year="2017"/);
assert.match(elements.targetEvidenceChart.innerHTML,/data-evidence-year="2025"/);
pools[2025].ranking_cycle="2019";
currentP1.ranking_cycle="2019";
renderTargetEvidence();
assert.match(elements.targetEvidenceChart.innerHTML,/World Championship ranking is incompatible/s);
pools[2025].ranking_cycle="2026";
currentP1.ranking_cycle="2026";
dashboardContext.gender="Female";
renderTargetEvidence();
assert.match(elements.targetEvidenceChart.innerHTML,/World Championship roster unavailable for cycle 2026 \(Female\)/);
dashboardContext.gender="Male"; dashboardContext.ageGroup="45-49";
renderTargetEvidence();
assert.match(elements.targetEvidenceChart.innerHTML,/Male performance pool rank/);
dashboardContext.ageGroup="50-54"; eventSelect.value="other";
renderTargetEvidence();
assert.match(elements.targetEvidenceChart.innerHTML,/Qualifying cycle unknown; corresponding World Championship evidence unavailable/);
eventSelect.value="race"; DATASETS.race.group="703";
renderTargetEvidence();
assert.match(elements.targetEvidenceChart.innerHTML,/No compatible 70.3 World Championship ranking evidence/);
DATASETS.race.group="im";
pools[2025].pool_slots=30;
currentP1.pool_slots=30;
historicalP1.pool_slots=30;
for (let index=0; index<145; index++) {
    const ageGraded=index<29 ? 30577+index : index===29 ? 30605.8956 : 30606+index-30;
    pools[2025].ranking_evidence[index][1]=ageGraded;
    DATASETS.race.qualification.pools[2025].male[index].age_graded=ageGraded;
}
pools[2025].ranking_evidence[29]=[32556,30605.8956,0];
pools[2025].ranking_evidence[30]=[32557.6,30606,0];
DATASETS.race.historical_qualification.pools=DATASETS.race.qualification.pools;
qualificationAssumptions.realFactor=true;
for (const system of ["current","historical"]) {
    qualificationSystem=system;
    for (const [factor,rank,cutoff,raw] of [[0,30,"08:30:05","09:02:36"],[1/30,31,"08:30:06","09:02:38"]]) {
        qualificationAssumptions.rollDownFactor=factor;
        const standard=approachStandard("race","2025","Male","50-54",system,"calibrated");
        assert.equal(standard.factorRank,rank);
        assert.equal(qualificationDuration(standard.ageGraded),cutoff);
        assert.equal(standard.needed,standard.ageGraded/0.8);
        const cutoffCell=manualKonaCutoff({pool_slots:30,manual_pool_times:DATASETS.race.qualification.pools[2025].male.map(row=>row.age_graded)},{slot_scope:"gender"});
        assert.ok(cutoffCell.includes(`<strong>${cutoff}</strong>`));
        assert.ok(cutoffCell.includes(`gender-pool rank ${rank}`));
        renderTargetEvidence();
        chart=elements.targetEvidenceChart.innerHTML;
        assert.ok(chart.includes(`Male performance pool rank: ${rank}; Finishing time: ${raw}; age-graded time: ${cutoff}`));
        assert.ok(chart.includes(`Rank-based roll-down factor: rank ${rank}; finisher ${raw}; age-graded ${cutoff}`));
    }
}
visible=[];
renderTargetEvidence();
assert.match(elements.targetEvidenceNote.textContent,/Select at least one race year/);
assert.equal(elements.targetEvidenceChart.innerHTML,"");
const times = [[1,100,0],[2,100.25,0],[3,100.25,0],[4,101,0]];
assert.equal(evidenceRankAtOrBelow(times,100.24,"gender").rank,1);
assert.equal(evidenceRankAtOrBelow(times,100.25,"gender").rank,3);
assert.equal(evidenceRankAtOrBelow(times,101,"gender").rank,4);
assert.match(evidenceRankAtOrBelow(times,101.001,"gender").reason,/beyond all ranked finishers/);
assert.match(evidenceRankAtOrBelow(times,99,"gender").reason,/no ranked finisher/);
assert.equal(evidenceRankAtOrBelow(times,2,"age group").rank,2);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_rank_evidence_tooltip_supports_hover_touch_and_keyboard(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text()
        helper = source[source.index("function attachEvidenceTooltips("):source.index("function decorateDashboard()")]
        fixture = r"""
const assert = require("node:assert/strict");
const handlers = {}, section = {addEventListener:(name,handler)=>handlers[name]=handler,
    contains:()=>true,querySelector:()=>({getBoundingClientRect:()=>({left:0,right:390})})};
const tooltip = {hidden:true,style:{},getBoundingClientRect:()=>({width:320,height:60})};
const document = {activeElement:null,getElementById:()=>tooltip,addEventListener:(name,handler)=>handlers[`document:${name}`]=handler};
const window = {innerWidth:390,innerHeight:844};
const svg = {getBoundingClientRect:()=>({top:100,bottom:400}),querySelectorAll:()=>points};
const makePoint = detail => ({dataset:{evidenceDetail:detail},tabindex:"0",
    matches:selector=>selector === ".evidence-point",
    closest:selector=>selector === "svg" ? svg : selector === ".evidence-point" ? point : null,
    getBoundingClientRect:()=>({left:4,top:120,width:5,height:48}),
    setAttribute:(name,value)=>point.tabindex=value,
    focus:()=>{document.activeElement=point;handlers.focusin({target:point});}});
let point = makePoint("Age-group rank: 1");
const first = point;
point = makePoint("Age-group rank: 2");
const second = point;
const points = [first,second];
first.closest = selector=>selector === "svg" ? svg : selector === ".evidence-point" ? first : null;
first.setAttribute = (name,value)=>first.tabindex=value;
first.focus = ()=>{document.activeElement=first;handlers.focusin({target:first});};
"""
        assertions = r"""
attachEvidenceTooltips(section);
handlers.pointerover({target:first,clientX:5,clientY:120,pointerType:"mouse"});
assert.equal(tooltip.textContent,"Age-group rank: 1");
assert.equal(tooltip.hidden,false);
assert.equal(tooltip.style.left,"4px");
assert.ok(parseFloat(tooltip.style.top) >= 0);
handlers.pointerout({target:first,pointerType:"mouse"});
assert.equal(tooltip.hidden,true);
handlers.pointerdown({target:first,clientX:5,clientY:120,pointerType:"touch"});
handlers.pointerout({target:first,pointerType:"touch"});
assert.equal(tooltip.hidden,false);
handlers["document:pointerdown"]({target:{closest:()=>null}});
assert.equal(tooltip.hidden,true);
first.focus();
let prevented = false;
handlers.keydown({target:first,key:"ArrowRight",preventDefault:()=>{prevented=true;}});
assert.equal(document.activeElement,second);
assert.equal(tooltip.textContent,"Age-group rank: 2");
assert.equal(first.tabindex,"-1");
assert.equal(second.tabindex,"0");
assert.equal(prevented,true);
handlers.scroll();
assert.equal(tooltip.hidden,false);
assert.equal(tooltip.textContent,"Age-group rank: 2");
handlers.keydown({target:second,key:"Escape"});
assert.equal(tooltip.hidden,true);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_finder_field_summary_uses_matching_denominators_and_selected_years(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_app.js").read_text()
        helper = source[source.index("    function finderFieldSummary("):source.index("    function fillManualForm(")]
        fixture = r"""
const assert = require("node:assert/strict");
const DATASETS = {race:{qualification_slots:{male:25,female:25},statistics:[{year:"2022",starters:1000},{year:"2023",starters:2000}],
    division_stats:{"2022":{"M50-54":{starters:100,finishers:80,top_20_percent:36000},"M45-49":{starters:200},"F30-34":{starters:600}},
                    "2023":{"M50-54":{starters:200,finishers:160,top_20_percent:40000},"M45-49":{starters:400},"F30-34":{starters:1200}}},
    qualification:{summaries:[{year:"2022",male_auto:5,male_perf:20},{year:"2023",male_auto:5,male_perf:20}]}}};
const slotAllocations = {};
const divisionFor = ()=>"M50-54";
let visible = ["2022"];
const qualificationYears = ()=>visible;
const isModifiedCourse = ()=>false;
const courseFactor = (id,year)=>year === "2022" ? 1.2 : 1;
const lowerMedian = values=>values.sort((a,b)=>a-b)[Math.floor((values.length-1)/2)] ?? null;
"""
        assertions = r"""
let result = finderFieldSummary("race","Male","50-54");
assert.equal(result.participantsPerSlot,18);
assert.equal(result.genderRatio,12);
assert.equal(result.ageGroupStarters,100);
assert.equal(result.strength,30000);
assert.equal(result.strengthFinishers,80);
visible=["2023"];
result=finderFieldSummary("race","Male","50-54");
assert.equal(result.participantsPerSlot,36);
assert.equal(result.genderRatio,24);
assert.equal(result.strength,40000);
assert.equal(result.strengthFinishers,160);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_finder_explains_each_missing_year(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_app.js").read_text()
        helper = source[source.index("    function finderMissingReasons("):source.index("    function finderFieldSummary(")]
        fixture = r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {mode:"scan",extraPlaces:7};
const easiestQualificationStandard = (event,year,gender,ageGroup,system,mode,places) => {
    assert.equal(system,"current"); assert.equal(mode,"scan"); assert.equal(places,7);
    return year === "2022" ? {unavailableReason:"no compatible roster"} : null;
};
"""
        assertions = r"""
assert.deepEqual(finderMissingReasons("race",["2021","2022","2023"],[{year:"2021"}],"Male","50-54"),
    [{year:"2022",reason:"no compatible roster"},{year:"2023",reason:"no compatible target"}]);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class KonaTraceTests(unittest.TestCase):
    def test_nice_is_a_non_qualifying_championship_merged_into_the_start_list(self):
        self.assertIn("im_nice_wc", build_dashboard.NON_QUALIFYING_EVENTS)
        if "im_nice_wc" in build_dashboard.EVENTS:
            self.assertFalse(build_dashboard.EVENTS["im_nice_wc"]["qualifying"])
        with tempfile.TemporaryDirectory() as folder:
            kona_file, nice_file = Path(folder, "kona2023.csv"), Path(folder, "nice2023.csv")
            row = {"Bib": 1, "Name": "A", "Country": "AUT", "Division": "F30-34", "Gender": "Female",
                   "Finish": "FIN", "Overall Time": "10:00:00"}
            pd.DataFrame([row]).to_csv(kona_file, index=False)
            pd.DataFrame([{**row, "Name": "B", "Division": "M30-34", "Gender": "Male"}]).to_csv(nice_file, index=False)
            field = build_dashboard.championship_start_list([kona_file], [nice_file])
            self.assertEqual(field["Venue"].tolist(), ["Kona", "Nice"])
            trace = kona_trace.build_kona_trace(field, [], {}, build_dashboard.read_results, {}, year="2023")
            self.assertEqual(trace["venues"], {"Male": ["Nice"], "Female": ["Kona"]})
            self.assertEqual(build_dashboard.championship_start_list([kona_file], [])["Venue"].tolist(), ["Kona"])

    def test_legacy_trace_uses_actual_age_group_slots_and_raw_times(self):
        names = ["Winner Person", "Early Person", "Later Person"]
        race = pd.DataFrame([
            {"Bib": rank, "Name": name, "Country": "Austria", "Gender": "Male",
             "Division": "M50-54", "Finish": "FIN", "Overall Time": f"09:{rank * 10:02d}:00"}
            for rank, name in enumerate(names, 1)
        ])
        events = {"race": {"name": "Race", "group": "im", "years": {"2019": ["race"]}}}
        calendar = [{"qualification_cycle": "2019", "race_name": "Race", "event_year": "2019", "total_qualifiers": 40}]
        target = {"slot_scope": "age group", "division": "M50-54", "gender": "Male", "slots": 2,
                  "method": "Official age-group allocation (results)", "source": {"total": 40, "cycles": ["2019"]}}
        trace = kona_trace.build_kona_trace(race.iloc[[0, 2]], calendar, events, lambda files: race.copy(),
                                           {"race": "Race"}, year="2019", historical_targets={("race", "2019"): [target]})
        self.assertEqual(trace["standards"], {})
        self.assertEqual(trace["slot_scope"], "age group")
        row = trace["summaries"]["all"][0]
        self.assertEqual(row["cutoff_scan"]["consecutive_absences"], 5)
        self.assertEqual(row["slot_scope"], "age group")
        self.assertEqual(row["division"], "M50-54")
        self.assertEqual(row["pool_slots"], 2)
        self.assertEqual(row["strict_cutoff"], 9 * 3600 + 20 * 60)
        self.assertEqual(row["candidate_deepest_rank"], 3)
        self.assertEqual(row["candidate_cutoff"], 9 * 3600 + 30 * 60)
        self.assertEqual(row["ranking_evidence"], [[33000.0, None, 0, True], [33600.0, None, 0, False], [34200.0, None, 1, False]])
        self.assertEqual(row["matched_pool_starters"], 1)
        self.assertEqual(trace["starters"][0]["matches"][0]["initial_slot"], "Strict age-group slot")
        target["source"]["cycles"] = ["2018"]
        incompatible = kona_trace.build_kona_trace(race, calendar, events, lambda files: race.copy(),
                                                 {"race": "Race"}, year="2019", historical_targets={("race", "2019"): [target]})
        self.assertEqual(incompatible["covered_races"], [])
        self.assertIn("cycle-compatible", incompatible["missing_races"][0]["reason"])

    def test_legacy_rank_one_match_is_gold_metadata_not_a_density_or_scan_metric(self):
        race = pd.DataFrame([
            {"Bib": rank, "Name": name, "Country": "Austria", "Gender": "Male",
             "Division": "M50-54", "Finish": "FIN", "Overall Time": f"09:{rank * 10:02d}:00"}
            for rank, name in enumerate(("Winner Person", "Early Person", "Later Person"), 1)
        ])
        events = {"race": {"name": "Race", "group": "im", "years": {"2019": ["race"]}}}
        calendar = [{"qualification_cycle": "2019", "race_name": "Race", "event_year": "2019", "total_qualifiers": 40}]
        target = {"slot_scope": "age group", "division": "M50-54", "gender": "Male", "slots": 2,
                  "method": "Official age-group allocation (results)", "source": {"total": 40, "cycles": ["2019"]}}

        def summarize(kona_indices):
            trace = kona_trace.build_kona_trace(race.iloc[kona_indices], calendar, events, lambda files: race.copy(),
                                                {"race": "Race"}, year="2019",
                                                historical_targets={("race", "2019"): [target]})
            return trace["summaries"]["all"][0]

        with_rank_one = summarize([0, 2])
        without_rank_one = summarize([2])
        self.assertEqual(with_rank_one["cutoff_estimate"], without_rank_one["cutoff_estimate"])
        self.assertEqual(with_rank_one["cutoff_scan"], without_rank_one["cutoff_scan"])
        self.assertEqual(with_rank_one["matched_pool_starters"], without_rank_one["matched_pool_starters"])
        self.assertEqual(with_rank_one["ranking_evidence"][0], [33000.0, None, 0, True])
        self.assertEqual(without_rank_one["ranking_evidence"][0], [33000.0, None, 0, False])
        self.assertEqual(with_rank_one["ranking_evidence"][2][2], 1)

    def test_legacy_trace_requires_five_unmatched_ranks_and_resets_at_matches(self):
        race = pd.DataFrame([
            {"Bib": rank, "Name": f"Athlete {chr(64 + rank)}", "Country": "Austria", "Gender": "Male",
             "Division": "M50-54", "Finish": "FIN", "Overall Time": f"09:{rank:02d}:00"}
            for rank in range(1, 21)
        ])
        events = {"race": {"name": "Race", "group": "im", "years": {"2019": ["race"]}}}
        calendar = [{"qualification_cycle": "2019", "race_name": "Race", "event_year": "2019", "total_qualifiers": 40}]
        target = {"slot_scope": "age group", "division": "M50-54", "gender": "Male", "slots": 2,
                  "method": "Official age-group allocation (results)", "source": {"total": 40, "cycles": ["2019"]}}
        trace = kona_trace.build_kona_trace(race.iloc[[2, 6, 11]], calendar, events, lambda files: race.copy(),
                                           {"race": "Race"}, year="2019", historical_targets={("race", "2019"): [target]})
        scan = trace["summaries"]["all"][0]["cutoff_scan"]
        self.assertEqual((scan["rank"], scan["gap_start_rank"], scan["gap_end_rank"]), (12, 13, 17))
        times = list(range(20))
        three = kona_trace.scan_pool_cutoff(times, [3, 7, 12], 2, consecutive_absences=3)
        five = kona_trace.scan_pool_cutoff(times, [3, 7, 12], 2, consecutive_absences=5)
        self.assertEqual((three["rank"], five["rank"]), (3, 12))
        incomplete = kona_trace.scan_pool_cutoff(times[:16], [3, 7, 12], 2, consecutive_absences=5)
        self.assertFalse(incomplete["criterion_met"])
        self.assertIsNone(incomplete["time"])

    def build_trace(self, extra_race=False, edit_kona=None, edit_race=None, race_id="race", race_year="2025"):
        def athlete(name, rank, time, status="FIN", division="M30-34"):
            return {"Bib": rank, "Name": name, "Country": "Austria", "Gender": "Male",
                    "Division": division, "Age Group Rank": rank, "Overall Time": time, "Finish": status}

        race = pd.DataFrame([
            athlete("Winner Person", 1, "08:00:00"),
            athlete("Early Person", 2, "08:10:00"),
            athlete("Middle Person", 3, "08:20:00"),
            athlete("Late Person", 4, "08:30:00"),
        ])
        kona = pd.DataFrame([
            athlete("Person Early", 1, "09:00:00", status="DNF"),
            athlete("Middle Person", 2, "09:10:00", status="DNS"),
            athlete("Late Person", 3, "09:20:00"),
            athlete("Other Person", 4, "09:30:00"),
        ])
        if edit_kona:
            kona = edit_kona(kona)
        if edit_race:
            race = edit_race(race)
        events = {race_id: {"name": "Race", "group": "im", "years": {race_year: ["race"]}}}
        calendar = [
            {"qualification_cycle": "2026", "race_name": "Race", "event_year": race_year, "total_qualifiers": 3},
            {"qualification_cycle": "2026", "race_name": "Missing Race", "event_year": "2026", "total_qualifiers": 3},
            {"qualification_cycle": "2027", "race_name": "Race", "event_year": "2025", "total_qualifiers": 3},
        ]
        names = {race_id: "Race"}
        frames = {"race": race}
        if extra_race:
            events["second"] = {"name": "Second", "group": "im", "years": {"2026": ["second"]}}
            calendar.append({"qualification_cycle": "2026", "race_name": "Second", "event_year": "2026", "total_qualifiers": 3})
            names["second"] = "Second"
            frames["second"] = race.replace({"Early Person": "Someone Else", "Middle Person": "Another Person"})
        return kona_trace.build_kona_trace(kona, calendar, events, lambda files: frames[files[0]].copy(), names)

    def test_reported_cutoff_is_specific_to_austria_2026_men(self):
        trace = self.build_trace(race_id="im_austria", race_year="2026")
        self.assertEqual(trace["standards"]["M50-54"], 0.9002)
        self.assertEqual(trace["standards"]["F50-54"], 0.9051)
        for summaries in trace["summaries"].values():
            male = next(row for row in summaries if row["gender"] == "Male")
            female = next(row for row in summaries if row["gender"] == "Female")
            self.assertEqual(male["reported_cutoff"], 32280)
            self.assertEqual(male["reported_cutoff_precision"], "minute")
            self.assertIn("User report", male["reported_cutoff_source"])
            self.assertIsNone(male["observed_cutoff"])
            self.assertIsNone(male["deepest_rank"])
            self.assertIsNone(male["estimated_skipped_slots"])
            self.assertIsNone(female["reported_cutoff"])
        for trace in (self.build_trace(race_id="im_austria"), self.build_trace(race_year="2026")):
            self.assertTrue(all(row["reported_cutoff"] is None for row in trace["summaries"]["all"]))

    def test_reported_hamburg_cutoffs_preserve_seconds_and_source(self):
        trace = self.build_trace(race_id="im_hamburg", race_year="2026")
        expected = {"Male": (32624, "Dusan Milosevic"), "Female": (39872, "Janine Schulschek")}
        for summaries in trace["summaries"].values():
            for row in summaries:
                seconds, athlete = expected[row["gender"]]
                self.assertEqual(row["reported_cutoff"], seconds)
                self.assertEqual(row["reported_cutoff_precision"], "second")
                self.assertEqual(row["reported_cutoff_athlete"], athlete)
                self.assertEqual(row["reported_cutoff_url"], "https://tri-mag.de/szene/von-hamburg-nach-hawaii-so-schnell-musste-man-fuer-die-kona-quali-sein/")
                self.assertIn("9 June 2026", row["reported_cutoff_source"])
                self.assertIsNone(row["deepest_rank"])
                self.assertIsNone(row["observed_cutoff"])
                self.assertIsNone(row["estimated_skipped_slots"])
        trace = self.build_trace(race_id="im_hamburg")
        self.assertTrue(all(row["reported_cutoff"] is None for row in trace["summaries"]["all"]))

    def test_matches_starters_including_dnf_but_not_dns(self):
        trace = self.build_trace()
        self.assertEqual(len(trace["starters"]), 3)
        self.assertEqual(trace["matched_starters"], 2)
        early = next(row for row in trace["starters"] if row["name"] == "Person Early")
        self.assertEqual(early["matches"][0]["pool_rank"], 1)
        male = next(row for row in trace["summaries"]["single"] if row["gender"] == "Male")
        self.assertEqual(male["pool_slots"], 2)
        self.assertEqual(male["candidate_deepest_rank"], 3)
        self.assertEqual(male["candidate_cutoff"], 8.5 * 3600)
        self.assertEqual(male["candidate_skipped_slots"], 1)
        self.assertIsNone(male["deepest_rank"])
        self.assertIsNone(male["observed_cutoff"])
        self.assertIsNone(male["estimated_skipped_slots"])

    def test_gender_ranking_evidence_preserves_age_graded_fractional_seconds(self):
        trace = self.build_trace(edit_race=lambda frame: frame.assign(Division="M50-54"))
        male = next(row for row in trace["summaries"]["all"] if row["gender"] == "Male")
        expected = round((8 * 3600 + 10 * 60) * trace["standards"]["M50-54"], 4)
        self.assertEqual(male["ranking_evidence"][0][1], expected)
        self.assertNotEqual(expected, int(expected))

    def test_multiple_possible_qualifying_races_are_not_assigned_arbitrarily(self):
        trace = self.build_trace(extra_race=True)
        self.assertEqual(trace["multiple_candidates"], 1)
        single = next(row for row in trace["summaries"]["single"] if row["event_id"] == "race" and row["gender"] == "Male")
        all_matches = next(row for row in trace["summaries"]["all"] if row["event_id"] == "race" and row["gender"] == "Male")
        self.assertEqual(single["candidate_deepest_rank"], 1)
        self.assertEqual(single["candidate_skipped_slots"], 0)
        self.assertEqual(all_matches["candidate_deepest_rank"], 3)
        self.assertTrue(all(row["observed_cutoff"] is None for row in trace["summaries"]["all"]))

    def test_age_intervals_allow_ageing_up_but_reject_incompatible_ages(self):
        self.assertTrue(kona_trace.compatible_age("M30-34", "2025", "M35-39", "2026"))
        self.assertTrue(kona_trace.compatible_age("M18-24", "2025", "M25-29", "2026"))
        self.assertFalse(kona_trace.compatible_age("M30-34", "2025", "M45-49", "2026"))

    def test_normalized_identity_requires_name_and_country(self):
        first = {"Name": "Ren\u00e9 Example", "Gender": "Male", "Country": "Austria"}
        second = {"Name": "EXAMPLE Rene", "Gender": "Male", "Country": " AUSTRIA "}
        self.assertEqual(kona_trace.athlete_key(first), kona_trace.athlete_key(second))
        self.assertIsNone(kona_trace.athlete_key({**first, "Country": None}))
        self.assertIsNone(kona_trace.athlete_key({**first, "Name": None}))

    def test_ambiguous_names_are_not_matched(self):
        def duplicate_last(frame):
            return pd.concat([frame, frame.iloc[[-1]]], ignore_index=True)

        trace = self.build_trace(edit_race=duplicate_last)
        self.assertEqual(trace["matched_starters"], 1)
        self.assertEqual(trace["ambiguous_identities"], 1)
        trace = self.build_trace(edit_kona=lambda frame: pd.concat([frame, frame.iloc[[2]]], ignore_index=True))
        self.assertEqual(trace["matched_starters"], 1)
        self.assertEqual(trace["ambiguous_identities"], 1)

    def test_nonfinishers_at_qualifying_races_are_not_candidates(self):
        def mark_late_dnf(frame):
            frame.loc[frame["Name"].eq("Late Person"), "Finish"] = "DNF"
            return frame

        self.assertEqual(self.build_trace(edit_race=mark_late_dnf)["matched_starters"], 1)

    def test_coverage_uses_the_qualifying_cycle_not_the_calendar_year(self):
        trace = self.build_trace()
        self.assertEqual(len(trace["covered_races"]), 1)
        self.assertEqual(trace["covered_races"][0]["year"], "2025")
        self.assertEqual([row["name"] for row in trace["missing_races"]], ["Missing Race"])

    def test_density_estimate_ignores_isolated_deep_matches(self):
        times = [30000 + rank * 30 for rank in range(200)]
        ranks = list(range(5, 51, 5)) + [120, 190]
        estimate = kona_trace.estimate_pool_cutoff(times, ranks, 20)
        self.assertEqual(estimate["rank"], 50)
        self.assertEqual(estimate["time"], times[49])
        self.assertGreater(estimate["bic_gain"], 0)
        self.assertLessEqual(estimate["low_rank"], 50)
        self.assertGreaterEqual(estimate["high_rank"], 50)
        self.assertLess(estimate["high_rank"], 120)
        self.assertEqual(kona_trace.scan_pool_cutoff(times, ranks, 20)["rank"], 50)

    def test_density_rejects_uniform_matches_without_hiding_scan(self):
        times = list(range(30000, 30200))
        for ranks, slots in (([1, 180], 20), (list(range(10, 201, 10)), 20), ([1, 2, 3], 0)):
            with self.subTest(ranks=ranks, slots=slots):
                estimate = kona_trace.estimate_pool_cutoff(times, ranks, slots)
                self.assertIsNone(estimate["time"])
                self.assertIsNone(estimate["rank"])
                self.assertIsNotNone(estimate["reason"])
        scan = kona_trace.scan_pool_cutoff(times, [1, 180], 20)
        self.assertIsNone(scan["rank"])
        self.assertIsNone(scan["time"])
        self.assertIsNotNone(scan["reason"])

    def test_cutoff_scan_stops_at_first_fifteen_absences(self):
        times = [30000 + rank * 30 for rank in range(200)]
        ranks = [5, 10, 20, 25, 39, 60, 190]
        estimate = kona_trace.scan_pool_cutoff(times, ranks, 20)
        self.assertEqual(estimate["rank"], 39)
        self.assertEqual(estimate["time"], times[38])
        self.assertTrue(estimate["criterion_met"])
        self.assertEqual(estimate["gap_start_rank"], 40)
        self.assertEqual(estimate["gap_end_rank"], 54)
        self.assertEqual(estimate["modeled_roll_down_percent"], 48.72)

    def test_cutoff_scan_resets_after_fourteen_absences(self):
        times = list(range(30000, 30200))
        estimate = kona_trace.scan_pool_cutoff(times, [20, 35, 50], 20)
        self.assertEqual(estimate["rank"], 50)
        self.assertEqual(estimate["gap_end_rank"], 65)
        estimate = kona_trace.scan_pool_cutoff(times, [20, 36], 20)
        self.assertIsNone(estimate["rank"])
        self.assertIsNone(estimate["time"])
        self.assertIsNotNone(estimate["reason"])
        self.assertEqual(estimate["gap_end_rank"], 35)

    def test_cutoff_scan_without_post_allocation_match_is_unavailable(self):
        times = list(range(30000, 30200))
        for absence_limit in (5, 15):
            with self.subTest(absence_limit=absence_limit):
                estimate = kona_trace.scan_pool_cutoff(
                    times, [10, 20], 20, consecutive_absences=absence_limit)
                self.assertTrue(estimate["criterion_met"])
                self.assertEqual(estimate["gap_start_rank"], 21)
                self.assertEqual(estimate["gap_end_rank"], 20 + absence_limit)
                self.assertIsNone(estimate["rank"])
                self.assertIsNone(estimate["time"])
                self.assertIsNone(estimate["athlete"])
                self.assertIsNone(estimate["modeled_roll_down_percent"])
                self.assertIn("Strict allocation was the last supported boundary", estimate["reason"])

    def test_positive_roll_down_scan_is_later_and_not_faster_than_strict(self):
        times = list(range(30000, 30200))
        initial_slots = 20
        estimate = kona_trace.scan_pool_cutoff(
            times, [initial_slots, 25], initial_slots, consecutive_absences=5)
        self.assertEqual(estimate["rank"], 25)
        self.assertGreater(estimate["rank"], initial_slots)
        self.assertEqual(estimate["time"], times[24])
        self.assertGreaterEqual(estimate["time"], times[initial_slots - 1])
        self.assertEqual(estimate["gap_start_rank"], 26)
        self.assertEqual(estimate["gap_end_rank"], 30)

    def test_cutoff_scan_requires_full_gap_and_preceding_match(self):
        times = list(range(30000, 30200))
        for ranks, slots in (([], 20), (list(range(10, 201, 10)), 20), ([1, 2, 3], 0)):
            with self.subTest(ranks=ranks, slots=slots):
                estimate = kona_trace.scan_pool_cutoff(times, ranks, slots)
                self.assertIsNone(estimate["time"])
                self.assertIsNone(estimate["rank"])
                self.assertIsNone(estimate["modeled_roll_down_percent"])
                self.assertIsNotNone(estimate["reason"])
        estimate = kona_trace.scan_pool_cutoff(times[:34], [20], 20)
        self.assertFalse(estimate["criterion_met"])
        self.assertIsNone(estimate["time"])
        estimate = kona_trace.scan_pool_cutoff(times, [20, 25], 20, consecutive_absences=5)
        self.assertEqual(estimate["rank"], 25)
        self.assertEqual(estimate["gap_end_rank"], 30)
        for invalid in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                kona_trace.scan_pool_cutoff(times, [20], 20, consecutive_absences=invalid)

    def test_cutoff_estimates_do_not_become_observed_acceptances(self):
        trace = self.build_trace()
        row = next(row for row in trace["summaries"]["all"] if row["gender"] == "Male")
        self.assertEqual(row["slot_scope"], "gender")
        self.assertEqual(row["cutoff_scan"]["consecutive_absences"], 15)
        self.assertIn("cutoff_estimate", row)
        self.assertIn("cutoff_scan", row)
        self.assertIn("manual_pool_times", row)
        self.assertEqual(row["manual_pool_times"], sorted(row["manual_pool_times"]))
        self.assertIsNone(row["observed_cutoff"])
        self.assertIsNone(row["estimated_skipped_slots"])

    def test_cutoff_estimate_is_independent_of_summary_evidence(self):
        trace = self.build_trace(extra_race=True)
        for all_row, single_row in zip(trace["summaries"]["all"], trace["summaries"]["single"]):
            self.assertEqual(all_row["cutoff_estimate"], single_row["cutoff_estimate"])
            self.assertIn("single_match_time", all_row["cutoff_estimate"])
            self.assertEqual(all_row["cutoff_scan"], single_row["cutoff_scan"])
            self.assertEqual(all_row["cutoff_scan"]["consecutive_absences"], 15)

    def test_scan_reports_last_athlete_even_with_multiple_race_candidates(self):
        def extend_race(frame):
            padding = pd.DataFrame([
                {"Bib": rank, "Name": "Padding " + chr(65 + rank // 26) + chr(65 + rank % 26),
                 "Country": "Austria", "Gender": "Male", "Division": "M30-34",
                 "Age Group Rank": rank, "Overall Time": "09:00:00", "Finish": "FIN"}
                for rank in range(5, 55)
            ])
            return pd.concat([frame, padding], ignore_index=True)

        trace = self.build_trace(extra_race=True, edit_race=extend_race)
        for mode in ("all", "single"):
            row = next(row for row in trace["summaries"][mode]
                       if row["event_id"] == "race" and row["gender"] == "Male")
            self.assertEqual(row["cutoff_scan"]["athlete"], "Late Person")
            self.assertEqual(row["cutoff_scan"]["rank"], 3)
            self.assertEqual(row["cutoff_scan"]["time"], 30600)
            self.assertEqual(row["cutoff_scan"]["gap_start_rank"], 4)
            self.assertEqual(row["cutoff_scan"]["gap_end_rank"], 18)
            self.assertIsNone(row["cutoff_estimate"]["time"])
            self.assertIsNone(row["observed_cutoff"])


@unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard chart tests")
class DashboardComparisonTests(unittest.TestCase):
    def test_absence_labels_follow_the_rank_scope(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        helpers = script[script.index("    function scannedKonaCutoffCell"):script.index("    function manualKonaCutoff")]
        pool_helper = script[script.index("    function easiestPoolEstimateCell"):script.index("    function renderEasiest()")]
        fixture = r"""
const assert = require("node:assert/strict");
const escapeHtml = value => String(value ?? "");
const qualificationDuration = value => `T${value}`;
const duration = value => `T${value}`;
const DATASETS = {im_kona:{kona_trace:{year:"2026"}}};
"""
        assertions = r"""
const legacy = {year:"2019",slot_scope:"age group",pool_slots:2,cutoff_scan:{time:30000,rank:3,
    athlete:"Athlete",consecutive_absences:5,gap_start_rank:4,gap_end_rank:8}};
const current = {...legacy,slot_scope:"gender",cutoff_scan:{...legacy.cutoff_scan,consecutive_absences:15}};
assert.match(scannedKonaCutoffCell(legacy),/age-group rank 3/);
assert.match(scannedKonaCutoffCell(legacy),/5 unmatched ranks/);
assert.match(scannedKonaCutoffCell(current),/gender-pool rank 3/);
assert.match(easiestPoolEstimateCell(legacy),/5-absence age-group scan/);
assert.match(easiestPoolEstimateCell(current),/15-absence gender-pool scan/);
"""
        result = subprocess.run(["node"], input=fixture + helpers + pool_helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_counterfactual_and_historical_estimates_use_distinct_scopes(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        helper = script[script.index("    function easiestQualificationStandard"):script.index("    function easiestPoolEstimateCell")]
        fixture = r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {fallback:false};
const isModifiedCourse = () => false;
const historicalStandard = {scope:"gender",division:"M50-54",performanceSlots:20,ratio:0.9,needed:33000,winner:30000};
const currentStandard = {scope:"gender",division:"M50-54",slots:2,performanceSlots:20,ratio:0.8,needed:35000,winner:30000};
const strictQualificationStandard = (id, year, gender, ageGroup, system) => system === "historical" ? historicalStandard : currentStandard;
const oldPool = {event_id:"race",year:"2025",gender:"Male",slot_scope:"gender",pool_slots:20,kona_cycle:"2026",ranking_cycle:"2026",
    cutoff_estimate:{time:31500},cutoff_scan:{time:32400,criterion_met:true,consecutive_absences:15}};
const counterfactualPool = {event_id:"race",year:"2025",gender:"Male",slot_scope:"gender",pool_slots:20,kona_cycle:"2026",ranking_cycle:"2027",
    cutoff_estimate:{time:32000},cutoff_scan:{time:32400,criterion_met:true,consecutive_absences:15}};
const target = {year:"2025",division:"M50-54",slot_scope:"gender",standard_cycle:"2026",source:{method:"performance",cycles:["2026"]}};
const DATASETS = {race:{group:"im",qualification:{standard_cycle:"2027"},historical_qualification:{targets:[target]}},
    im_kona:{kona_traces:{2026:{year:"2026",standard_cycle:"2026",venues:{Male:["Kona"]},standards:{"M50-54":0.9},summaries:{all:[oldPool]},counterfactual_standard_cycle:"2027",
            counterfactual_standards:{"M50-54":0.8},counterfactual_summaries:[counterfactualPool]}}}};
const get = (system, mode) => easiestQualificationStandard("race","2025","Male","50-54",system,mode,0);
const actual = get("historical","scan");
assert.equal(actual.needed,36000);
assert.equal(actual.cutoffPool,oldPool);
assert.match(actual.cutoffSource,/15-absence gender-pool scan/);
assert.equal(get("historical","reported").available,false);
const current = get("current","scan");
assert.equal(current.needed,40500);
assert.equal(current.cutoffPool,counterfactualPool);
assert.equal(current.cutoffCycle,"2027");
assert.equal(current.cutoffRoster,"2026");
assert.match(current.cutoffSource,/15-absence gender-pool scan/);
assert.equal(get("current","reported").available,false);
assert.equal(get("current","density").needed,40000);
oldPool.cutoff_estimate.time = 27000;
assert.equal(get("historical","density").needed,33000);
assert.match(get("historical","density").cutoffSource,/Match-density boundary.*bounded by strict allocation/);
counterfactualPool.cutoff_estimate.time = 24000;
assert.equal(get("current","density").needed,35000);
assert.match(get("current","density").cutoffSource,/Match-density boundary.*bounded by strict allocation/);
for (const [system, pool, expectedRanking] of [["current", counterfactualPool, "2027"], ["historical", oldPool, "2026"]]) {
    for (const [field, expected, reason] of [["ranking_cycle", expectedRanking, /ranking cycle/], ["kona_cycle", "2026", /qualifying cycle/]]) {
        pool[field] = "1999";
        for (const mode of ["scan", "density"]) {
            qualificationAssumptions.fallback = false;
            const unavailable = get(system, mode);
            assert.equal(unavailable.available, false);
            assert.equal(unavailable.needed, null);
            assert.match(unavailable.unavailableReason, reason);
            qualificationAssumptions.fallback = true;
            const fallback = get(system, mode);
            assert.equal(fallback.needed, system === "current" ? 35000 : 33000);
            assert.equal(fallback.cutoffPool, null);
            assert.match(fallback.cutoffSource, /Strict fallback/);
        }
        pool[field] = expected;
    }
    qualificationAssumptions.fallback = false;
    assert.equal(get(system, "scan").estimatedCutoffUsed, true);
    for (const [field, invalid, reason] of [["slot_scope", "unknown", /scope/], ["pool_slots", 21, /allocation/]]) {
        const original = pool[field];
        pool[field] = invalid;
        for (const mode of ["scan", "density"]) {
            assert.equal(get(system, mode).available, false);
            assert.match(get(system, mode).unavailableReason, reason);
            qualificationAssumptions.fallback = true;
            assert.match(get(system, mode).cutoffSource, /Strict fallback/);
            qualificationAssumptions.fallback = false;
        }
        pool[field] = original;
    }
    const trace = DATASETS.im_kona.kona_traces[2026];
    const standards = system === "current" ? trace.counterfactual_standards : trace.standards;
    const originalRatio = standards["M50-54"];
    standards["M50-54"] = 0.5;
    assert.match(get(system, "scan").unavailableReason, /allocation or standard/);
    qualificationAssumptions.fallback = true;
    assert.match(get(system, "density").cutoffSource, /Strict fallback/);
    qualificationAssumptions.fallback = false;
    standards["M50-54"] = originalRatio;
    const venues = trace.venues;
    trace.venues = {Male:[]};
    for (const mode of ["scan", "density"]) {
        assert.match(get(system, mode).unavailableReason, /no World Championship start list for qualifying cycle 2026/);
        qualificationAssumptions.fallback = true;
        assert.match(get(system, mode).cutoffSource, /Strict fallback/);
        qualificationAssumptions.fallback = false;
    }
    trace.venues = venues;
    const cycleField = system === "current" ? "counterfactual_standard_cycle" : "standard_cycle";
    const originalCycle = trace[cycleField];
    trace[cycleField] = "1999";
    assert.match(get(system, "scan").unavailableReason, /ranking cycle/);
    trace[cycleField] = originalCycle;
}
target.source.cycles = ["2027"];
target.standard_cycle = "2027";
for (const system of ["current", "historical"]) {
    for (const mode of ["scan", "density"]) {
        qualificationAssumptions.fallback = false;
        assert.equal(get(system, mode).available, false);
        assert.match(get(system, mode).unavailableReason, /no World Championship start list for qualifying cycle 2027/);
        qualificationAssumptions.fallback = true;
        assert.equal(get(system, mode).needed, system === "current" ? 35000 : 33000);
        assert.match(get(system, mode).cutoffSource, /Strict fallback.*no World Championship start list for qualifying cycle 2027/);
    }
}
"""
        result = subprocess.run(["node"], input=fixture + helper, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_counterfactual_uses_the_race_years_own_kona_cycle(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        helper = script[script.index("    function easiestQualificationStandard"):script.index("    function easiestPoolEstimateCell")]
        fixture = r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {fallback:false};
const isModifiedCourse = () => false;
const strictQualificationStandard = () => ({scope:"gender",division:"M50-54",performanceSlots:20,ratio:0.8,needed:35000,winner:30000});
const pool = (year, scan, roster) => ({event_id:"race",year,gender:"Male",slot_scope:"gender",division:null,pool_slots:20,kona_cycle:roster,ranking_cycle:"2027",
    cutoff_estimate:{time:null},cutoff_scan:{time:scan,criterion_met:true,consecutive_absences:15}});
const trace = (year, pools) => ({year,standard_cycle:year,venues:{Male:["Kona"]},standards:{},summaries:{all:[]},counterfactual_standard_cycle:"2027",
    counterfactual_standards:{"M50-54":0.8},counterfactual_summaries:pools});
const DATASETS = {race:{group:"im",qualification:{standard_cycle:"2027"},
    historical_qualification:{targets:[
        {year:"2017",division:"M50-54",slot_scope:"age group",source:{method:"legacy",cycles:["2017"]}},
        ...["2025","2026"].map(year=>({year,division:"M50-54",slot_scope:"gender",standard_cycle:"2026",source:{method:"performance",cycles:["2026"]}}))]}},
    im_kona:{kona_trace:null,kona_traces:{
        2017:trace("2017",[pool("2017",32000,"2017")]),
        2025:trace("2025",[pool("2025",33000,"2025")]),
        2026:trace("2026",[pool("2025",34000,"2026"),pool("2026",32400,"2026")])}}};
DATASETS.im_kona.kona_trace = DATASETS.im_kona.kona_traces[2026];
const get = year => easiestQualificationStandard("race",year,"Male","50-54","current","scan",0);
const old = get("2017");
assert.equal(old.available,false);
assert.match(old.unavailableReason,/age-group allocation/);
qualificationAssumptions.fallback=true;
assert.equal(get("2017").available,false);
qualificationAssumptions.fallback=false;
assert.equal(get("2026").needed,40500);
assert.equal(get("2026").cutoffRoster,"2026");
const missing = get("2019");
assert.equal(missing.available,false);
assert.match(missing.unavailableReason,/unknown or ambiguous/);
assert.equal(get("2025").needed,42500);
assert.equal(get("2025").cutoffRoster,"2026");
DATASETS.race.historical_qualification.targets = [];
assert.match(get("2025").unavailableReason,/ambiguous/);
"""
        result = subprocess.run(["node"], input=fixture + helper, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_historical_age_group_estimate_is_not_age_graded_or_reused_for_current_rules(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        helper = script[script.index("    function calibratedStandard"):script.index("    function easiestPoolEstimateCell")]
        fixture = r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {fallback:true,rollDownFactor:0.5};
const isModifiedCourse = () => false;
const standard = {year:"2019",scope:"age group",division:"M50-54",slots:2,needed:33000,winner:30000};
const strictQualificationStandard = () => standard;
const pool = {event_id:"race",year:"2019",gender:"Male",slot_scope:"age group",division:"M50-54",pool_slots:2,
    cutoff_estimate:{time:35000},cutoff_scan:{time:36000}};
const DATASETS = {race:{group:"im",historical_qualification:{targets:[{year:"2019",division:"M50-54",slot_scope:"age group",times:[32000,33000,35000],source:{method:"legacy",cycles:["2019"]}}]}},
 im_kona:{kona_traces:{2019:{year:"2019",standards:{},summaries:{all:[pool]}}}}};
const get = (system="historical",mode="calibrated") => easiestQualificationStandard("race","2019","Male","50-54",system,mode,10);
assert.equal(get().factorRank,3);
assert.equal(get().needed,35000);
assert.equal(get().strictNeeded,33000);
assert.equal(get().ageGraded,null);
assert.equal(get("historical","scan").available,false);
assert.equal(get("historical","density").available,false);
assert.equal(get("current","density").available,false);
assert.equal(get("historical","reported").available,false);
qualificationAssumptions.rollDownFactor=1;
assert.equal(get().available,false);
assert.equal(get().needed,null);
pool.pool_slots=3;
assert.equal(get("historical","strict").cutoffPool,null);
"""
        result = subprocess.run(["node"], input=fixture + helper, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard UI tests")
    def test_historical_legacy_estimates_require_confirmed_cycle(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        helper = script[script.index("    function easiestQualificationStandard"):script.index("    function easiestPoolEstimateCell")]
        fixture = r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {fallback:false, legacyExtraPlaces:0};
const isModifiedCourse = () => false;
const standard = {scope:"age group",division:"M50-54",slots:2,needed:33000,winner:30000};
const pool = {event_id:"race",year:"2019",gender:"Male",slot_scope:"age group",division:"M50-54",pool_slots:2,
    cutoff_estimate:{time:35000},cutoff_scan:{time:36000,consecutive_absences:5},
    reported_cutoff:31000,reported_cutoff_source:"Reviewed race report"};
const DATASETS = {race:{group:"im",historical_qualification:{targets:[{year:"2019",division:"M50-54",times:[32000,33000]}]}},
    im_kona:{kona_traces:{2019:{year:"2019",standards:{},summaries:{all:[pool]}}}}};
const strictQualificationStandard = (id, year, gender, ageGroup, system, options={}) =>
    ({...standard, needed:standard.needed + (options.extraPlaces || 0) * 100});
"""
        assertions = r"""
const get = mode => easiestQualificationStandard("race","2019","Male","50-54","historical",mode,0);
for (const mode of ["reported","density","scan"]) {
    const result = get(mode);
    assert.equal(result.available,false);
    assert.equal(result.needed,null);
    assert.match(result.unavailableReason,/unknown or ambiguous/);
    assert.equal(result.cutoffPool,null);
    assert.equal(result.cutoffCycle,null);
}
assert.equal(get("strict").available,true);
qualificationAssumptions.fallback=true;
assert.equal(get("scan").available,false);
assert.equal(get("places").available,false);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_qualification_wrapper_preserves_baseline_and_overrides(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        core = script[script.index("    function divisionFor"):script.index("    function neededText")]
        wrapper = script[script.index("    function qualificationStandard"):script.index("    function easiestPoolEstimateCell")]
        fixture = r"""
    const assert = require("node:assert/strict");
    const slotAllocations = {};
    const qualificationAssumptions = {mode: "strict", extraPlaces: 1, legacyExtraPlaces: 0, fallback: false, rollDownFactor: 1};
    const isModifiedCourse = (id, year) => year === "2024";
    const pool = {male: [{division:"M30-34", age_graded:30000}, {division:"M30-34", age_graded:31000}], winners:{"M30-34":29000}, automatic:{male:["M30-34"]}};
    const ds = {group:"im", division_stats:{"2026":{"M30-34":{starters:10,finishers:9,median:40000}}}, qualification:{standard_cycle:"2026",ratios:{"M30-34":1},pools:{"2026":pool},summaries:[{year:"2026",male_perf:1,male_auto:1}]},historical_qualification:{targets:[{year:"2026",division:"M30-34",slot_scope:"gender",source:{method:"performance",cycles:["2026"]}}]}};
    const DATASETS = {race:ds, im_kona:{kona_trace:{year:"2026",venues:{Male:["Kona"]},standards:{"M30-34":1},summaries:{all:[]},counterfactual_standard_cycle:"2026",counterfactual_standards:{"M30-34":1},counterfactual_summaries:[{event_id:"race",year:"2026",gender:"Male",slot_scope:"gender",kona_cycle:"2026",ranking_cycle:"2026",pool_slots:1,cutoff_scan:{time:32000,criterion_met:true,consecutive_absences:15}}]}}};
    """
        assertions = r"""
    const get = () => qualificationStandard("race","2026","Male","30-34","current");
    assert.equal(get().needed,30000);
    qualificationAssumptions.mode="calibrated";
    assert.equal(get().needed,31000);
    assert.equal(get().strictNeeded,30000);
    assert.equal(get().factorRank,2);
    qualificationAssumptions.mode="places";
    assert.equal(get(),null);
    qualificationAssumptions.mode="scan";
    assert.equal(get().needed,32000);
    assert.equal(get().strictNeeded,30000);
    slotAllocations.race={male:2};
    assert.equal(get(),null);
    qualificationAssumptions.fallback=true;
    assert.equal(get().needed,31000);
    assert.match(get().cutoffSource,/changed allocation/);
    qualificationAssumptions.mode="strict";
    assert.equal(get().performanceSlots,2);
    assert.equal(get().qualifiers,3);
    """
        result = subprocess.run(["node"], input=fixture + core + wrapper + assertions,
                    text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_where_cutoffs_replace_extra_places_and_convert_age_grading(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        helper = script[script.index("    function easiestQualificationStandard"):script.index("    function renderEasiest()")]
        fixture = r"""
const assert = require("node:assert/strict");
let appliedPlaces;
let standard = {division: "M50-54", scope: "gender", ratio: 0.8, winner: 34000,
    needed: 35000, ageGraded: 31500, qualifiers: 2, performanceSlots: 20};
const pool = {event_id: "race", year: "2026", gender: "Male", kona_cycle:"2026", ranking_cycle:"2026",
    slot_scope: "gender", pool_slots: 20, cutoff_estimate: {time: 32000}, cutoff_scan: {time: 32400,criterion_met:true,consecutive_absences:15}};
const target = {year:"2026",division:"M50-54",slot_scope:"gender",standard_cycle:"2026",source:{method:"performance",cycles:["2026"]}};
const DATASETS = {race: {group: "im", qualification: {standard_cycle: "2026", pools:{"2026":{male:Array(30).fill({})}}},historical_qualification:{targets:[target]}}, half: {group: "703"},
    im_kona: {kona_trace: {year: "2026", standard_cycle:"2026", venues:{Male:["Kona"],Female:["Kona"]}, standards: {"M50-54": 0.8}, summaries: {all: [pool]},
        counterfactual_standard_cycle: "2026", counterfactual_standards: {"M50-54": 0.8}, counterfactual_summaries: [pool]}}};
const qualificationAssumptions = {fallback: true};
const isModifiedCourse = () => false;
const strictQualificationStandard = (id, year, gender, ageGroup, system, options) => {
    appliedPlaces = options.extraPlaces;
    return standard && {...standard, needed: standard.needed + options.extraPlaces * 100};
};
"""
        assertions = r"""
const get = (mode, year = "2026", gender = "Male", event = "race") =>
    easiestQualificationStandard(event, year, gender, "50-54", "current", mode, 10);
assert.equal(get("places").available, false);
assert.equal(appliedPlaces, 0);
let result = get("density");
assert.equal(appliedPlaces, 0);
assert.equal(result.needed, 40000);
assert.equal(result.ageGraded, 32000);
assert.equal(result.ratio, 0.8);
assert.equal(result.estimatedCutoffUsed, true);
assert.match(result.cutoffSource, /density.*2026.*exploratory/);
assert.equal(get("scan").needed, 40500);
assert.equal(get("scan").qualifiers, 2);
let historic = easiestQualificationStandard("race", "2026", "Male", "50-54", "historical", "scan", 10);
assert.equal(historic.needed, 40500);
target.standard_cycle = "2027";
historic = easiestQualificationStandard("race", "2026", "Male", "50-54", "historical", "scan", 10);
assert.equal(historic.needed, 35000);
assert.match(historic.cutoffSource, /different qualifying cycle/);
target.standard_cycle = "2026";
for (const args of [["scan", "2025"], ["scan", "2026", "Male", "half"]]) {
    result = get(...args);
    assert.equal(result.available, false);
    assert.equal(result.needed, null);
    assert.equal(result.estimatedCutoffUsed, false);
    assert.match(result.cutoffSource, /No estimate/);
}
result = get("scan", "2026", "Female");
assert.equal(result.needed,35000);
assert.match(result.cutoffSource,/Strict fallback/);
pool.cutoff_scan.time = null;
assert.equal(get("scan").needed, 35000);
pool.cutoff_scan.time = 32400;
standard.winner = 41000;
assert.equal(get("scan").needed, 41000);
standard.winner = null;
assert.equal(get("density").needed, Infinity);
standard.scope = "age group";
assert.match(get("density").cutoffSource, /legacy/);
assert.equal(get("density").needed, 35000);
standard.scope = "gender";
qualificationAssumptions.fallback = false;
assert.equal(get("scan", "2025").available, false);
assert.equal(get("scan", "2025").needed, null);
assert.equal(get("scan", "2025").strictNeeded, 35000);
standard.winner = 34000;
standard.performanceSlots = 21;
assert.match(get("scan").cutoffSource, /changed allocation/);
assert.equal(get("scan").available, false);
standard.performanceSlots = 20;
standard.ratio = 0.9;
assert.equal(get("density").available, false);
standard.ratio = 0.8;
pool.reported_cutoff = 32280;
pool.reported_cutoff_precision = "minute";
assert.equal(get("reported").available, false);
pool.reported_cutoff_source = "Documented race report";
assert.equal(get("reported").available, false);
historic = easiestQualificationStandard("race", "2026", "Male", "50-54", "historical", "reported", 10);
assert.equal(historic.needed, 40350);
assert.equal(historic.precision, "minute");
assert.equal(get("strict").needed, 35000);
assert.equal(get("strict").strictNeeded, 35000);
standard = null;
assert.equal(get("scan"), null);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        syntax = subprocess.run(["node", "--check"], input=script,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)

    def test_reviewed_sources_exclude_unknown_other_race_and_special_entries(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        review_script = script[script.index("    const konaReviewStorageKey"):script.index("    function renderKonaTrace")]
        fixture = 'const assert = require("node:assert/strict"); const localStorage = {getItem() { return null; }};'
        assertions = r"""
const pool = {event_id: "race", year: "2026", pool_slots: 20};
const first = {bib: "1", name: "Early Person", country: "Austria", gender: "Male", matches: [
  {event_id: "race", year: "2026", pool_rank: 40, age_graded: 8 * 3600 + 58 * 60},
  {event_id: "second", year: "2026", pool_rank: 3, age_graded: 8 * 3600},
]};
const late = {bib: "2", name: "Late Person", country: "Austria", gender: "Male", matches: [
  {event_id: "race", year: "2026", pool_rank: 400, age_graded: 12 * 3600},
]};
const winner = {bib: "3", name: "Winner Person", country: "Austria", gender: "Male", matches: [
  {event_id: "race", year: "2026", pool_rank: null, age_graded: null},
]};
const starters = [first, late, winner];
assert.equal(reviewedKonaSummary(pool, starters).observed_cutoff, null);
assert.equal(reviewedKonaSummary(pool, starters).estimated_skipped_slots, null);
konaReviews[konaReviewKey(first)] = "race|2026";
let summary = reviewedKonaSummary(pool, starters);
assert.equal(summary.observed_cutoff, 8 * 3600 + 58 * 60);
assert.equal(summary.deepest_rank, 40);
assert.equal(summary.attributed_starters, 1);
assert.equal(summary.estimated_skipped_slots, 20);
konaReviews[konaReviewKey(late)] = "other";
assert.equal(reviewedKonaSummary(pool, starters).observed_cutoff, summary.observed_cutoff);
konaReviews[konaReviewKey(first)] = "second|2026";
assert.equal(reviewedKonaSummary(pool, starters).observed_cutoff, null);
konaReviews[konaReviewKey(first)] = "race|2025";
assert.equal(reviewedKonaSummary(pool, starters).observed_cutoff, null);
konaReviews[konaReviewKey(winner)] = "race|2026";
summary = reviewedKonaSummary(pool, starters);
assert.equal(summary.attributed_starters, 1);
assert.equal(summary.observed_cutoff, null);
assert.equal(summary.deepest_rank, null);
konaReviews[konaReviewKey(first)] = "race|2026";
assert.equal(reviewedKonaSummary({...pool, pool_slots: 0}, [first]).estimated_skipped_slots, null);
"""
        result = subprocess.run(["node"], input=fixture + review_script + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def run_chart_assertions(self, assertions):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        chart_script = script[script.index("    const compareColors"):script.index("    function renderKonaTrace")]
        fixture = r"""
const assert = require("node:assert/strict");
const DATASETS = {race: {name: "Race", overall: {2024: [], 2025: []},
  statistics: [
    {year: "2024", registered: 100, starters: 80, finishers: 60, dns: 20, dnf: 16},
    {year: "2025", registered: 0, starters: 0, finishers: 0, dns: 0, dnf: 0},
    {year: "2026", registered: 100, starters: 100, finishers: 100, dns: 0, dnf: 0},
  ], historical_qualification: {targets: [
    {year: "2024", source: {total: 60}}, {year: "2024", source: {total: 60}},
  ]},
}};
DATASETS.modified = DATASETS.race;
DATASETS.championship = DATASETS.race;
const isModifiedCourse = (id, year) => id === "modified" && year === "2024";
const isQualifyingEvent = id => id !== "championship";
const attachPointTooltips = () => {};
let renders = 0;
const renderSharedViews = () => { renders++; };
const svg = {comparison: true, viewBox: {baseVal: {width: 1000, height: 360}},
  closest() { return this.comparison; }, querySelectorAll() { return []; }, innerHTML: ""};
const document = {getElementById() { return svg; }};
const chartOptions = {zeroBasedNice: true, formatValue: String, formatTick: String};
"""
        result = subprocess.run(["node"], input=fixture + chart_script + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ratios_and_historical_slots(self):
        self.run_chart_assertions(r"""
assert.equal(raceComparisonStatistic("race", "2024", "finishers").value, 60);
assert.equal(raceComparisonStatistic("race", "2024", "dns").value, 20);
assert.equal(raceComparisonStatistic("race", "2024", "dnf").value, 20);
assert.equal(raceComparisonStatistic("race", "2024", "slots").value, 60);
assert.equal(raceComparisonStatistic("race", "2025", "slots"), null);
assert.equal(raceComparisonStatistic("championship", "2024", "slots"), null);
for (const metric of ["dns", "dnf"]) {
  assert.equal(raceComparisonStatistic("race", "2025", metric), null);
  assert.equal(raceComparisonStatistic("race", "2026", metric).value, 0);
}
for (const metric of ["finishers", "dns", "dnf", "slots"]) {
  assert.equal(raceComparisonStatistic("modified", "2024", metric), null);
}
assert.deepEqual(yearSeries(["race"], () => null).map(item => item.label), ["2024", "2025", "2026"]);
""")

    def test_year_visibility_and_empty_chart_controls(self):
        self.run_chart_assertions(r"""
const series = yearSeries(["race"], (id, year) => raceComparisonStatistic(id, year, "finishers"));
categoryPointChart("chart", ["Race"], series, chartOptions);
assert.equal((svg.innerHTML.match(/class="data-point"/g) || []).length, 3);
toggleCompareYear("2024");
assert.equal(renders, 1);
categoryPointChart("chart", ["Race"], series, chartOptions);
assert.doesNotMatch(svg.innerHTML, /data-year="2024"/);
assert.doesNotMatch(svg.innerHTML, /data-compare-year=|role="button"/);
assert.equal(series[0].values[0].length, 1);
svg.comparison = false;
categoryPointChart("chart", ["Race"], series, chartOptions);
assert.doesNotMatch(svg.innerHTML, /data-year="2024"/);
assert.doesNotMatch(svg.innerHTML, /data-compare-year=|role="button"/);
svg.comparison = true;
toggleCompareYear("2025");
toggleCompareYear("2026");
categoryPointChart("chart", ["Race"], series, chartOptions);
assert.doesNotMatch(svg.innerHTML, /class="data-point"|NaN|Infinity/);
assert.match(svg.innerHTML, /No data for visible years/);
assert.equal((svg.innerHTML.match(/data-compare-year=/g) || []).length, 0);
toggleCompareYear("2024");
categoryPointChart("chart", ["Race"], series, chartOptions);
assert.match(svg.innerHTML, /data-year="2024"/);
""")


    def test_reported_cutoff_cell_preserves_precision_and_links_source(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        helper = script[script.index("    function reportedKonaCutoffCell"):script.index("    function renderKonaTrace")]
        statements = (
            'const assert = require("node:assert/strict");',
            'const escapeHtml = value => String(value ?? "").replaceAll("<", "&lt;").replaceAll(">", "&gt;");',
            'const qualificationDuration = seconds => new Date(seconds * 1000).toISOString().slice(11, 19);',
            helper,
            'const row = {reported_cutoff: 32624, reported_cutoff_precision: "second", reported_cutoff_source: "tri-mag.de, 9 June 2026", reported_cutoff_url: "https://tri-mag.de/article/"};',
            'assert.match(reportedKonaCutoffCell(row), /09:03:44/);',
            r'assert.match(reportedKonaCutoffCell(row), /href="https:\/\/tri-mag.de\/article\/"/);',
            'assert.match(reportedKonaCutoffCell(row), /9 June 2026/);',
            'assert.match(reportedKonaCutoffCell({...row, reported_cutoff: 39872}), /11:04:32/);',
            'const minute = reportedKonaCutoffCell({...row, reported_cutoff: 32280, reported_cutoff_precision: "minute", reported_cutoff_url: null});',
            'assert.match(minute, />08:58</); assert.doesNotMatch(minute, /08:58:00|href=/);',
            'assert.equal(reportedKonaCutoffCell({reported_cutoff: null}), "\u2014");',
            'assert.match(reportedKonaCutoffCell({...row, reported_cutoff_source: "<unsafe>"}), /&lt;unsafe&gt;/);',
            'const modeled = {reported_cutoff: null, cutoff_estimate: {time: 32263, rank: 40, low_time: 32166, high_time: 32358, single_match_time: 32166, matched_pool_starters: 26, bic_gain: 105, sensitive: true}};',
            'assert.match(estimatedKonaCutoffCell(modeled), /~08:58/);',
            'assert.match(estimatedKonaCutoffCell(modeled), /Range 08:56 to 09:00/);',
            'assert.match(estimatedKonaCutoffCell(modeled), /Sensitive to match selection/);',
            'assert.match(estimatedKonaCutoffCell({...modeled, reported_cutoff: 32280}), /~08:58/);',
            'assert.match(estimatedKonaCutoffCell({cutoff_estimate: {time: null, reason: "Insufficient pool matches"}}), /Insufficient pool matches/);',
            'const scanned = {pool_slots: 20, reported_cutoff: 32280, cutoff_scan: {time: 32263, rank: 40, athlete: "<Person>", gap_start_rank: 41, gap_end_rank: 55, consecutive_absences: 15}};',
            'assert.match(scannedKonaCutoffCell(scanned), /08:57:43/);',
            'assert.match(scannedKonaCutoffCell(scanned), /gender-pool rank 40/);',
            'assert.match(scannedKonaCutoffCell(scanned), /15 unmatched ranks: 41 to 55/);',
            'assert.match(scannedKonaCutoffCell(scanned), /&lt;Person&gt;/);',
            'assert.doesNotMatch(scannedKonaCutoffCell(scanned), /Range|BIC|Reported/);',
            'assert.match(scannedKonaCutoffCell({cutoff_scan: {time: null, reason: "Pool ends before the absence criterion is met"}}), /Pool ends before the absence criterion is met/);',
        )
        result = subprocess.run(["node"], input="\n".join(statements),
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()