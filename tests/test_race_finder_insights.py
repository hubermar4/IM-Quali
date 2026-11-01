import json
import math
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import backtest
import build_dashboard
import dashboard_insights
import reference_data


def trace_row(gender, strict, observed, cycle="2024", met=True, year="2023"):
    return {
        "event_id": "im_x", "year": year, "gender": gender, "slot_scope": "gender", "strict_cutoff": strict,
        "kona_cycle": cycle, "cutoff_scan": {"time": observed, "criterion_met": met}, "date": "2023-06-01",
    }


class InsightsTests(unittest.TestCase):
    def test_rolldown_calibration_is_median_ratio_per_gender(self):
        rows = [trace_row("Male", 1000, 1050 + i, year=str(2000 + i)) for i in range(6)]
        rows += [trace_row("Female", 1000, 1120, year=str(2000 + i)) for i in range(6)]
        rows.append(trace_row("Male", 1000, 2000, met=False, year="1999"))
        result = dashboard_insights.rolldown_calibration({"2024": {"counterfactual_summaries": rows}})
        self.assertEqual(result["genders"]["male"]["n"], 6)
        self.assertAlmostEqual(result["genders"]["male"]["factor"], 1.0525, places=3)
        self.assertEqual(result["genders"]["female"]["factor"], 1.12)

    def test_dnf_rate_is_shrunk_and_skips_modified_courses(self):
        stats = [{"year": "2023", "starters": 100, "dnf": 20, "dns": 0}, {"year": "2024", "starters": 500, "dnf": 500}]
        datasets = {
            "a": {"group": "im", "statistics": stats, "modified_courses": {"2024": "x"}},
            "b": {"group": "im", "statistics": [{"year": "2023", "starters": 900, "dnf": 90}], "modified_courses": {}},
        }
        rates = dashboard_insights.dnf_rates(datasets)
        self.assertEqual(rates["a"]["starters"], 100)
        self.assertAlmostEqual(rates["a"]["raw_rate"], 0.2)
        self.assertTrue(0.1 < rates["a"]["rate"] < 0.2)

    def test_calendar_event_ids_exist_and_are_unique(self):
        calendar = reference_data.cycle_calendar()
        ids = [entry["event_id"] for entry in calendar["events"] if entry["event_id"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(set(ids) <= set(reference_data.events()["events"]))
        for entry in calendar["events"]:
            self.assertGreaterEqual(entry["date"], calendar["window_start"])
            self.assertLessEqual(entry["date"], calendar["championship_date"])

    def test_event_calendar_reports_next_date_and_typical_month(self):
        traces = {"2024": {"counterfactual_summaries": [trace_row("Male", 1, 1)]}}
        result = dashboard_insights.event_calendar({"im_tallinn": {}, "im_x": {}}, traces)
        self.assertEqual(result["events"]["im_tallinn"]["next_slots"], 45)
        self.assertEqual(result["events"]["im_x"]["typical_month"], 6)
        self.assertIsNone(result["events"]["im_x"]["next_date"])


class BacktestTests(unittest.TestCase):
    def test_reliability_bins_and_brier(self):
        pairs = [(0.9, True), (0.9, True), (0.1, False), (0.1, True)]
        result = backtest._bins(pairs)
        self.assertEqual(result["n"], 4)
        self.assertAlmostEqual(result["brier"], (0.01 + 0.01 + 0.01 + 0.81) / 4)
        self.assertAlmostEqual(result["base_rate"], 0.75)
        self.assertEqual(sum(row["n"] for row in result["bins"]), 4)

    def test_cutoff_backtest_leaves_cycle_out(self):
        rows = [trace_row("Male", 1000, 1050, cycle=str(2017 + i), year=str(2017 + i)) for i in range(4)]
        rows.append(trace_row("Male", 1000, 1150, cycle="2030", year="2030"))
        result, _, factors = backtest.cutoff_backtest({row["kona_cycle"]: {"counterfactual_summaries": [row]} for row in rows})
        self.assertAlmostEqual(factors[("Male", "2030")], 1.05)
        self.assertAlmostEqual(factors[("Male", "2017")], 1.05)
        self.assertEqual(result["genders"]["male"]["n"], 5)
        self.assertLess(result["genders"]["male"]["strict"]["bias"], 0)

    def test_phi(self):
        self.assertAlmostEqual(backtest.phi(0), 0.5)
        self.assertAlmostEqual(backtest.phi(1.96), 0.975, places=3)

    def test_built_dataset_has_new_payloads(self):
        data = ROOT / "dist" / "dashboard_data.js"
        if not data.exists():
            self.skipTest("dashboard not built")
        text = data.read_text(encoding="utf-8")
        kona = json.loads(text[text.index("=") + 1:].strip().rstrip(";"))["im_kona"]
        self.assertGreater(kona["rolldown_calibration"]["genders"]["female"]["factor"], kona["rolldown_calibration"]["genders"]["male"]["factor"])
        self.assertIn("A_calibrated", kona["backtest"]["reliability"])
        self.assertTrue(all(0 <= entry["rate"] < 1 for entry in kona["dnf_rates"].values()))


@unittest.skipUnless(shutil.which("node"), "node is required for dashboard script tests")
class RaceFinderScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]

    def run_node(self, source):
        result = subprocess.run(["node"], input=source, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rank_factor_uses_allocated_ranks_for_both_objectives(self):
        code = self.script[self.script.index("    function calibratedStandard"):self.script.index("    function easiestQualificationStandard")]
        self.run_node(r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {fallback: true, rollDownFactor: 0};
const pool = Array.from({length: 120}, (_, index) => ({age_graded: 30000 + index * 10}));
const race = {group:"im", qualification:{pools:{2025:{male:pool}}},
    historical_qualification:{pools:{2025:{male:pool}},targets:[{year:"2025",division:"M30-34",times:pool.map(row=>row.age_graded)}]}};
const DATASETS = {race, half:{...race,group:"703"}};
""" + code + r"""
const strict = {year:"2025",division:"M30-34",scope:"gender",performanceSlots:30,ratio:0.8,winner:40000,needed:40000};
for (const [factor, rank] of [[0,30],[1,60],[2,90],[2.5,105]]) {
    qualificationAssumptions.rollDownFactor = factor;
    for (const [event, system] of [["race","current"],["race","historical"],["half","historical"]]) {
        const result = calibratedStandard(strict,event,"Male",system);
        assert.equal(result.factorRank,rank);
        assert.equal(result.needed,Math.max(40000,pool[rank-1].age_graded/0.8));
        assert.equal(result.calibrationSd,undefined);
    }
}
qualificationAssumptions.rollDownFactor = 0.5;
const legacy = calibratedStandard({...strict,scope:"age group",slots:3},"race","Male","historical");
assert.equal(legacy.factorRank,5);
assert.equal(legacy.needed,pool[4].age_graded);
assert.equal(calibratedStandard({...strict,winner:50000},"race","Male","current").needed,50000);
for (const missing of [{winner:null},{ratio:null},{performanceSlots:0}])
    assert.equal(calibratedStandard({...strict,...missing},"race","Male","current").available,false);
qualificationAssumptions.rollDownFactor = 4;
const unavailable = calibratedStandard(strict,"race","Male","current");
assert.equal(unavailable.available,false);
assert.equal(unavailable.needed,null);
assert.doesNotMatch(unavailable.cutoffSource,/fallback/i);
""")

    def test_custom_factor_changes_finder_ranking_but_not_strict_method(self):
        calculation = self.script[self.script.index("    function qualificationStandard"):self.script.index("    function easiestPoolEstimateCell")]
        renderer = self.script[self.script.index("    function renderEasiest() {"):self.script.index("    function renderEasiestTab() {")]
        fixture = r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {mode:"calibrated",extraPlaces:0,legacyExtraPlaces:0,fallback:false,rollDownFactor:0};
const pool = times => ({"2026":{male:times.map(age_graded=>({age_graded}))}});
const DATASETS = {a:{name:"A",group:"im",qualification:{pools:pool([100,120])}},b:{name:"B",group:"im",qualification:{pools:pool([110,150])}},im_kona:{}};
const strictQualificationStandard = event => {
    const poolEquivalent = event === "a" ? 100 : 110, winner = event === "a" ? 115 : 100;
    return {year:"2026",scope:"gender",division:"M30-34",ratio:1,performanceSlots:1,ageGraded:poolEquivalent,poolEquivalent,winner,
        needed:Math.max(winner,poolEquivalent),starters:10,qualifiers:1,method:"current"};
};
const activeTab="easiest", dashboardContext={distance:"im"};
const easiestDistance={value:"im"}, easiestGender={value:"Male"}, easiestAgeGroup={value:"30-34"};
const easiestTypedTime="110";
const easiestDeclines={}, easiestTime={}, easiestDetailRace={}, easiestOpenFilter={value:"all"}, easiestFinishRisk={value:"off"};
const nodes = {};
const document = {getElementById:id=>nodes[id] ||= {}};
const raceGroups=()=>({im:["a","b"]}), isQualifyingEvent=()=>true, populateAgeGroupSelect=()=>{}, compareAgeGroups=()=>[];
const divisionFor=()=>"M30-34", groupModel=()=>({fit:{overall:{residual_sd:0.036}}});
const currentAbility=()=>({profile:{used:0},transitions:0,averageTime:110});
const renderMyResults=()=>{}, renderStrengthProfile=()=>null, qualificationYears=()=>["2026"], isModifiedCourse=()=>false;
const predictRaceYear=id=>({total:id === "a" ? 105 : 115}), normalCdf=value=>1/(1+Math.exp(-value));
const finderMissingReasons=()=>[], finderFieldSummary=()=>({years:["2026"],strengthYears:[],strengthFinishers:0});
const lowerMedian=values=>values[0], courseFactor=()=>1;
let captured;
const applyEvidenceAdjustments=races=>{captured=races.map(race=>({eventId:race.eventId,chance:race.chance,needed:race.entries[0].needed}));
    races.forEach(race=>Object.assign(race,{chanceLow:race.chance,chanceHigh:race.chance,dnfRate:0,lowEvidence:false}));};
const byNumberDescending=(left,right)=>right-left, escapeHtml=String, slotText=()=>"slots", nextRaceText=()=>"next";
const cutoffLabels={calibrated:"Factor",strict:"Strict"}, duration=String, neededText=String, signedDuration=String;
const signedPercent=String, courseEffect=()=>1, easiestPoolEstimateCell=()=>"none", assumptionTime=value=>String(value.needed);
const categoryPointChart=()=>{}, yearSeries=()=>[], signedDurationShort=String;
const fillRaceSelect=(control,ids)=>{control.value=ids[0]}, yearCell=(id,year)=>year, qualificationEvidenceLink=()=>"source", factorText=String;
"""
        assertions = r"""
renderEasiest();
const baseline = captured;
assert.match(nodes.easiestRankingBody.innerHTML,/1\. A/);
qualificationAssumptions.rollDownFactor=1;
renderEasiest();
const scenario = captured;
assert.match(nodes.easiestRankingBody.innerHTML,/1\. B/);
assert.ok(scenario.find(row=>row.eventId === "b").chance > baseline.find(row=>row.eventId === "b").chance);
assert.equal(scenario.find(row=>row.eventId === "b").needed,150);
assert.match(nodes.easiestRankingBody.innerHTML,/Rank factor 1/);
qualificationAssumptions.mode="strict";
renderEasiest();
const strict = captured.map(row=>row.needed);
qualificationAssumptions.rollDownFactor=2;
renderEasiest();
assert.deepEqual(captured.map(row=>row.needed),strict);
"""
        self.run_node(fixture + calculation + renderer + assertions)

    def test_calendar_filter_and_evidence_adjustments(self):
        code = self.script[self.script.index("    const EVIDENCE_PSEUDO_YEARS"):self.script.index("    function renderBacktest")]
        self.run_node(r"""
const assert = require("node:assert/strict");
globalThis.__dashboardToday = "2026-10-31";
const DATASETS = {im_kona: {
  event_calendar: {events: {held: {next_date: "2026-09-13", next_slots: 50, typical_month: 9},
    soon: {next_date: "2026-11-07", next_slots: 55}, tba: {next_date: null, typical_month: 7}}},
  dnf_rates: {a: {rate: 0.1}, b: {rate: 0.2}, c: {rate: 0.05}}}};
""" + code + r"""
assert.equal(isEventOpen("held"), false);
assert.equal(isEventOpen("soon"), true);
assert.equal(isEventOpen("tba"), true);
assert.equal(isEventOpen("unknown"), true);
assert.match(nextRaceText("held"), /held/);
assert.match(nextRaceText("tba"), /usually Jul/);
const entries = chances => chances.map(chance => ({chance}));
const races = [
  {eventId: "a", entries: entries([0.9]), chance: 0.9},
  {eventId: "b", entries: entries([0.3, 0.7, 0.3, 0.7]), chance: 0.5},
  {eventId: "c", entries: [], chance: -Infinity},
];
applyEvidenceAdjustments(races, true);
const [a, b, c] = races;
assert.ok(a.chance < 0.9 * 0.9 && a.lowEvidence);
assert.ok(b.chance > 0.5 * 0.8 * 0.9 && !b.lowEvidence);
assert.ok(a.chanceLow < a.chance && a.chanceHigh >= a.chance);
assert.equal(c.chance, -Infinity);
const noRisk = [{eventId: "a", entries: entries([0.9]), chance: 0.9}];
applyEvidenceAdjustments(noRisk, false);
assert.ok(Math.abs(noRisk[0].chance - 0.9) < 1e-9);
""")


if __name__ == "__main__":
    unittest.main()
