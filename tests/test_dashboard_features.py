import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import build_dashboard
import kona_trace


class DashboardUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = build_dashboard.build_html({})

    def test_cutoff_method_selector_is_removed_and_all_five_methods_are_present(self):
        for selector in ("contextCutoff", "easiestCutoffMode"):
            self.assertNotIn(selector, self.html)
        for label in (
            "Strict allocation", "Manual extra places", "Reported last accepted",
            "Density estimate", "15-absence scan",
        ):
            self.assertIn(label, self.html)
        self.assertIn("No compatible target", self.html)
        self.assertIn("No estimate", self.html)
        self.assertIn("Match-density boundary", self.html)
        self.assertIn("positive BIC improvement after the penalty", self.html)
        self.assertIn("not evidence of actual acceptance or declines", self.html)
        self.assertIn("Strict fallback", self.html)
        self.assertIn("Historically correct rules", self.html)
        self.assertIn("Current performance pool on historical results", self.html)

    def test_qualification_views_share_model_and_cross_race_panels_are_reparented_once(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text()
        self.assertNotIn('class="qualification-system"', self.html)
        self.assertEqual(source.count('name="contextRules" value='), 2)
        self.assertIn('views: ["qualification", "easiest", "odds", "kona", "crossrace"]', source)
        self.assertIn('crossrace: "Cross-race Analysis"', source)
        for view in ("qualification", "easiest", "odds"):
            start = source.index(f"function {'renderSelectedQualification' if view == 'qualification' else 'renderFinderApproaches' if view == 'easiest' else 'renderOddsApproaches'}()")
            end = source.find("\nfunction ", start + 1)
            self.assertIn("qualificationSystem", source[start:end])
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
        self.assertIn('crossRacePanel.setAttribute("aria-labelledby", "view-crossrace")', source)
        self.assertIn('qualification: "Race Targets"', source)
        self.assertIn('document.querySelector(`.legacy-tabs [data-tab="${view}"]`)', source)
        self.assertIn("if (legacyButton) legacyButton.click();", source)
        self.assertIn('activeTab = view;', source)
        self.assertIn('dashboardReturnView = activeTab;', source)
        self.assertRegex(source, r"if \(workspace \|\| view\) clearDashboardReturn\(\);")
        self.assertIn('data-evidence-race="${escapeHtml(standard.eventId)}"', source)
        self.assertIn('document.getElementById("contextReturn")', source)

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
const pool = {event_id:"race",year:"2019",gender:"Male",slot_scope:"age group",division:"M50-54",pool_slots:2,
    cutoff_estimate:{time:35000},cutoff_scan:{time:36000,consecutive_absences:3},reported_cutoff:31000};
const DATASETS = {race:{group:"im",qualification:{standard_cycle:"2026"},
    historical_qualification:{targets:[{year:"2019",division:"M50-54",standard_cycle:"2019"}]}},
    im_kona:{kona_traces:{2019:{year:"2019",standards:{},summaries:{all:[pool]}},
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
assert.equal(get("historical","density").available,false);
assert.equal(get("historical","density").needed,null);
assert.equal(get("historical","density").strictNeeded,33000);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_counterfactual_calendar_uses_current_slots_for_every_historical_im_year(self):
        events = {
            "race": {"group": "im", "qualifying": True, "qualification_slots": 50,
                     "years": {"2019": ["old.csv"], "2025": ["recent.csv"]}},
            "half": {"group": "703", "qualifying": True, "qualification_slots": 30,
                     "years": {"2025": ["half.csv"]}},
            "nonqualifying": {"group": "im", "qualifying": False, "qualification_slots": 40,
                              "years": {"2025": ["other.csv"]}},
        }
        cycle = build_dashboard.qualification_full.CURRENT_CYCLE
        calendar = build_dashboard.current_pool_counterfactual_calendar(
            events, {"race": "Race", "half": "Half", "nonqualifying": "Other"}, cycle,
        )
        self.assertEqual(calendar, [
            {"qualification_cycle": cycle, "race_name": "Race", "event_year": "2019", "total_qualifiers": 50},
            {"qualification_cycle": cycle, "race_name": "Race", "event_year": "2025", "total_qualifiers": 50},
        ])
        self.assertEqual(build_dashboard.current_pool_counterfactual_calendar(events, {}, "2019"), [])

    def test_course_analysis_exposes_only_distance_percent_and_shared_years(self):
        for selector in (
            "experimentalSplit", "experimentalGender", "experimentalAgeGroup",
            "experimentalBreakdownRace", "experimentalRaceA", "experimentalRaceB",
            "experimentalAthleteSearch",
        ):
            self.assertNotIn(selector, self.html)
        self.assertIn("experimentalPercentile", self.html)
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
    def test_extra_places_controls_follow_distance_and_qualification_system(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.js").read_text()
        helper = source[source.index("function updateExtraPlacesControls()"):
                        source.index("function updateDashboardScope()")]
        fixture = r"""
const assert = require("node:assert/strict");
const dashboardContext = {distance: "im"};
let qualificationSystem = "historical";
let activeTab = "qualification";
const controls = Object.fromEntries(["contextExtraPlaces", "contextLegacyPlaces"].map(id => [id, {
    value: id === "contextLegacyPlaces" ? "3" : "2", disabled: false,
    label: {hidden: false}, closest() { return this.label; },
}]));
const document = {getElementById(id) { return controls[id]; }};
const selectedKonaTrace = () => null;
"""
        assertions = r"""
updateExtraPlacesControls();
assert.equal(controls.contextLegacyPlaces.label.hidden, false);
assert.equal(controls.contextLegacyPlaces.disabled, false);
assert.equal(controls.contextExtraPlaces.label.hidden, true);
assert.equal(controls.contextExtraPlaces.disabled, true);
assert.equal(controls.contextLegacyPlaces.value, "3");

dashboardContext.distance = "703";
updateExtraPlacesControls();
assert.equal(controls.contextLegacyPlaces.label.hidden, true);
assert.equal(controls.contextLegacyPlaces.disabled, true);
assert.equal(controls.contextExtraPlaces.label.hidden, true);
assert.equal(controls.contextExtraPlaces.disabled, true);

dashboardContext.distance = "im";
qualificationSystem = "current";
updateExtraPlacesControls();
assert.equal(controls.contextLegacyPlaces.label.hidden, true);
assert.equal(controls.contextLegacyPlaces.disabled, true);
assert.equal(controls.contextExtraPlaces.label.hidden, false);
assert.equal(controls.contextExtraPlaces.disabled, false);
"""
        result = subprocess.run(["node"], input=fixture + helper + assertions,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class KonaTraceTests(unittest.TestCase):
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
        self.assertEqual(row["cutoff_scan"]["consecutive_absences"], 3)
        self.assertEqual(row["slot_scope"], "age group")
        self.assertEqual(row["division"], "M50-54")
        self.assertEqual(row["pool_slots"], 2)
        self.assertEqual(row["strict_cutoff"], 9 * 3600 + 20 * 60)
        self.assertEqual(row["candidate_deepest_rank"], 3)
        self.assertEqual(row["candidate_cutoff"], 9 * 3600 + 30 * 60)
        self.assertEqual(trace["starters"][0]["matches"][0]["initial_slot"], "Strict age-group slot")
        target["source"]["cycles"] = ["2018"]
        incompatible = kona_trace.build_kona_trace(race, calendar, events, lambda files: race.copy(),
                                                 {"race": "Race"}, year="2019", historical_targets={("race", "2019"): [target]})
        self.assertEqual(incompatible["covered_races"], [])
        self.assertIn("cycle-compatible", incompatible["missing_races"][0]["reason"])

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
                self.assertEqual(row["reported_cutoff_url"], kona_trace.HAMBURG_CUTOFF_URL)
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
        for absence_limit in (3, 15):
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
        pool_helper = script[script.index("    function easiestPoolEstimateCell"):script.index("    function renderEasiest")]
        fixture = r"""
const assert = require("node:assert/strict");
const escapeHtml = value => String(value ?? "");
const qualificationDuration = value => `T${value}`;
const duration = value => `T${value}`;
const DATASETS = {im_kona:{kona_trace:{year:"2026"}}};
"""
        assertions = r"""
const legacy = {year:"2019",slot_scope:"age group",pool_slots:2,cutoff_scan:{time:30000,rank:3,
    athlete:"Athlete",consecutive_absences:3,gap_start_rank:4,gap_end_rank:6}};
const current = {...legacy,slot_scope:"gender",cutoff_scan:{...legacy.cutoff_scan,consecutive_absences:15}};
assert.match(scannedKonaCutoffCell(legacy),/age-group rank 3/);
assert.match(scannedKonaCutoffCell(legacy),/3 absences/);
assert.match(scannedKonaCutoffCell(current),/gender-pool rank 3/);
assert.match(easiestPoolEstimateCell(legacy),/3-absence age-group scan/);
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
const historicalStandard = {scope:"age group",division:"M50-54",slots:2,needed:33000,winner:30000};
const currentStandard = {scope:"gender",division:"M50-54",slots:2,performanceSlots:20,ratio:0.8,needed:35000,winner:30000};
const strictQualificationStandard = (id, year, gender, ageGroup, system) => system === "historical" ? historicalStandard : currentStandard;
const oldPool = {event_id:"race",year:"2019",gender:"Male",slot_scope:"age group",division:"M50-54",pool_slots:2,
    cutoff_estimate:{time:35000},cutoff_scan:{time:36000,consecutive_absences:3},reported_cutoff:31000};
const counterfactualPool = {event_id:"race",year:"2019",gender:"Male",slot_scope:"gender",division:null,pool_slots:20,
    cutoff_estimate:{time:32000},cutoff_scan:{time:32400,consecutive_absences:15}};
const DATASETS = {race:{group:"im",qualification:{standard_cycle:"2026"},
    historical_qualification:{targets:[{year:"2019",division:"M50-54",standard_cycle:"2019"}]}},
    im_kona:{kona_traces:{2019:{year:"2019",standards:{},summaries:{all:[oldPool]}},
        2026:{year:"2026",standards:{"M50-54":0.8},summaries:{all:[]},counterfactual_summaries:[counterfactualPool]}}}};
const get = (system, mode) => easiestQualificationStandard("race","2019","Male","50-54",system,mode,0);
const actual = get("historical","scan");
assert.equal(actual.needed,36000);
assert.equal(actual.cutoffPool.slot_scope,"age group");
assert.match(actual.cutoffSource,/3-absence age-group scan/);
assert.equal(get("historical","reported").available,false);
const current = get("current","scan");
assert.equal(current.needed,40500);
assert.equal(current.cutoffPool.slot_scope,"gender");
assert.equal(current.cutoffCycle,"2026");
assert.match(current.cutoffSource,/15-absence gender-pool scan/);
assert.equal(get("current","reported").available,false);
assert.equal(get("current","density").needed,40000);
oldPool.cutoff_estimate.time = 32000;
assert.equal(get("historical","density").needed,33000);
assert.match(get("historical","density").cutoffSource,/Match-density boundary.*bounded by strict allocation/);
counterfactualPool.cutoff_estimate.time = 24000;
assert.equal(get("current","density").needed,35000);
assert.match(get("current","density").cutoffSource,/Match-density boundary.*bounded by strict allocation/);
"""
        result = subprocess.run(["node"], input=fixture + helper, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_historical_age_group_estimate_is_not_age_graded_or_reused_for_current_rules(self):
        script = re.findall(r"<script>(.*?)</script>", build_dashboard.build_html({}), re.S)[0]
        helper = script[script.index("    function easiestQualificationStandard"):script.index("    function easiestPoolEstimateCell")]
        fixture = r"""
const assert = require("node:assert/strict");
const qualificationAssumptions = {fallback:false};
const isModifiedCourse = () => false;
const standard = {scope:"age group",division:"M50-54",slots:2,needed:33000,winner:30000};
const strictQualificationStandard = () => standard;
const pool = {event_id:"race",year:"2019",gender:"Male",slot_scope:"age group",division:"M50-54",pool_slots:2,
    cutoff_estimate:{time:35000},cutoff_scan:{time:36000}};
const DATASETS = {race:{group:"im",historical_qualification:{targets:[{year:"2019",division:"M50-54",source:{cycles:["2019"]}}]}},
 im_kona:{kona_traces:{2019:{year:"2019",standards:{},summaries:{all:[pool]}}}}};
const get = (system="historical",mode="density") => easiestQualificationStandard("race","2019","Male","50-54",system,mode,10);
assert.equal(get().needed,35000);
assert.equal(get().strictNeeded,33000);
assert.equal(get().ageGraded,null);
assert.equal(get().cutoffCycle,"2019");
assert.equal(get("historical","scan").needed,36000);
assert.equal(get("current").available,false);
assert.equal(get("historical","reported").available,false);
pool.pool_slots=3;
assert.equal(get().available,false);
assert.match(get().unavailableReason,/allocation/);
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
    cutoff_estimate:{time:35000},cutoff_scan:{time:36000,consecutive_absences:3},
    reported_cutoff:31000,reported_cutoff_source:"Reviewed race report"};
const DATASETS = {race:{group:"im",historical_qualification:{targets:[{year:"2019",division:"M50-54"}]}},
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
    assert.match(result.unavailableReason,/confirmed compatible evidence cycle/);
    assert.equal(result.cutoffPool,null);
    assert.equal(result.cutoffCycle,null);
}
assert.equal(get("strict").available,true);
assert.equal(get("places").available,true);
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
    const qualificationAssumptions = {mode: "strict", extraPlaces: 1, legacyExtraPlaces: 0, fallback: false};
    const isModifiedCourse = (id, year) => year === "2024";
    const pool = {male: [{division:"M30-34", age_graded:30000}, {division:"M30-34", age_graded:31000}], winners:{"M30-34":29000}, automatic:{male:["M30-34"]}};
    const ds = {group:"im", division_stats:{"2026":{"M30-34":{starters:10,finishers:9,median:40000}}}, qualification:{standard_cycle:"2026",ratios:{"M30-34":1},pools:{"2026":pool},summaries:[{year:"2026",male_perf:1,male_auto:1}]}};
    const DATASETS = {race:ds, im_kona:{kona_trace:{year:"2026",standards:{"M30-34":1},summaries:{all:[{event_id:"race",year:"2026",gender:"Male",pool_slots:1,cutoff_scan:{time:32000}}]}}}};
    """
        assertions = r"""
    const get = () => qualificationStandard("race","2026","Male","30-34","current");
    assert.equal(get().needed,30000);
    qualificationAssumptions.mode="places";
    assert.equal(get().needed,31000);
    assert.equal(get().strictNeeded,30000);
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
const pool = {event_id: "race", year: "2026", gender: "Male",
    pool_slots: 20, cutoff_estimate: {time: 32000}, cutoff_scan: {time: 32400}};
const DATASETS = {race: {group: "im"}, half: {group: "703"},
    im_kona: {kona_trace: {year: "2026", standards: {"M50-54": 0.8}, summaries: {all: [pool]}}}};
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
assert.equal(get("places").needed, 36000);
assert.equal(appliedPlaces, 10);
let result = get("density");
assert.equal(appliedPlaces, 0);
assert.equal(result.needed, 40000);
assert.equal(result.ageGraded, 32000);
assert.equal(result.ratio, 0.8);
assert.equal(result.estimatedCutoffUsed, true);
assert.match(result.cutoffSource, /Density.*2026.*unverified/);
assert.equal(get("scan").needed, 40500);
assert.equal(get("scan").qualifiers, 2);
DATASETS.race.historical_qualification = {targets: [{year: "2026", division: "M50-54", standard_cycle: "2026"}]};
let historic = easiestQualificationStandard("race", "2026", "Male", "50-54", "historical", "scan", 10);
assert.equal(historic.needed, 40500);
DATASETS.race.historical_qualification.targets[0].standard_cycle = "2027";
historic = easiestQualificationStandard("race", "2026", "Male", "50-54", "historical", "scan", 10);
assert.equal(historic.needed, 35000);
assert.match(historic.cutoffSource, /different qualifying cycle/);
for (const args of [["scan", "2025"], ["scan", "2026", "Female"], ["scan", "2026", "Male", "half"]]) {
    result = get(...args);
    assert.equal(result.needed, 35000);
    assert.equal(result.estimatedCutoffUsed, false);
    assert.match(result.cutoffSource, /Strict fallback/);
}
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
assert.equal(get("reported").needed, 40350);
assert.equal(get("reported").precision, "minute");
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
            'assert.match(scannedKonaCutoffCell(scanned), /Pool rank 40/);',
            'assert.match(scannedKonaCutoffCell(scanned), /15 absences: ranks 41 to 55/);',
            'assert.match(scannedKonaCutoffCell(scanned), /&lt;Person&gt;/);',
            'assert.doesNotMatch(scannedKonaCutoffCell(scanned), /Range|BIC|Reported/);',
            'assert.match(scannedKonaCutoffCell({cutoff_scan: {time: null, reason: "Pool ends before the absence criterion is met"}}), /Pool ends before the absence criterion is met/);',
        )
        result = subprocess.run(["node"], input="\n".join(statements),
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()