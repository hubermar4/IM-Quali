---
description: "Use when handling any question, code change, or analysis about the standard course: converting race, split or finish times to a common reference course via repeat athletes (course_difficulty) or bike GPX simulation (gpx_course_model); course factors, season effects, modified courses."
applyTo: "src/course_difficulty.py, src/gpx_course_model.py, src/build_gpx_report.py, src/build_dashboard.py, src/kona_trace.py, tests/test_course_difficulty.py, tests/test_gpx_course_model.py, docs/standard_course.md, data/reference/modified_courses.json, src/dashboard_app.js, src/dashboard_ui.js"
---
Read [docs/standard_course.md](../../docs/standard_course.md) first. Standard course = 3.8 km / 180 km / 42.2 km (70.3: 1.9 / 90 / 21.1), average qualifying course and season. Repeat-athlete factors drive all conversions; the GPX model is a bike-only cross-check. Keep the doc in sync with code changes.
