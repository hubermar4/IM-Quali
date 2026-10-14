import argparse
from pathlib import Path

from gpx_course_model import Rider, duration, read_gpx, simulate
from project_paths import DIST_DIR, GPX_TRACK_DIR, ensure_output_directories


DEFAULT_INPUT = GPX_TRACK_DIR
DEFAULT_OUTPUT = DIST_DIR / "gpx_track_statistics.md"


def race_name(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def signed(value: float, decimals: int = 0) -> str:
    return f"{value:+.{decimals}f}"


def quality_notes(result: dict) -> list[str]:
    notes = []
    steepest = max(
        result["maximum_uphill_grade"], result["maximum_downhill_grade"]
    )
    if steepest > 0.25:
        notes.append(
            "maximum smoothed grade exceeds 25%; inspect the elevation profile "
            "for discontinuities"
        )
    if abs(result["net_elevation_change_m"]) > 50:
        notes.append(
            "start and finish elevations differ by more than 50 m; the track "
            "may not be a closed loop"
        )
    if result["simulated_maximum_speed_kmh"] >= 89.9:
        notes.append("simulated speed reaches the configured 90 km/h cap")
    return notes


def build_report(paths: list[Path], rider: Rider, spacing: float, smoothing: float) -> str:
    rows = []
    skipped = []
    for path in paths:
        try:
            points = read_gpx(path)
        except ValueError as error:
            skipped.append((path, str(error)))
            continue
        result = simulate(points, rider, spacing, smoothing)
        rows.append((path, result, quality_notes(result)))

    lines = [
        "# GPX bike-course statistics",
        "",
        "All tracks use the same terrain-dependent-power reference-rider model. Values "
        "describe the supplied GPX files, not official course certification.",
        "",
        "## Model settings",
        "",
        f"- Total rider and bike mass: {rider.total_mass_kg:g} kg",
        f"- Flat-terrain crank power: {rider.power_w:g} W",
        f"- Ascent crank power: {rider.power_w * rider.ascent_power_factor:g} W (+{100 * (rider.ascent_power_factor - 1):g}%)",
        f"- Descent crank power: {rider.power_w * rider.descent_power_factor:g} W ({100 * (rider.descent_power_factor - 1):g}%)",
        f"- Flat-terrain threshold: ±{100 * rider.flat_grade_threshold:g}% grade",
        f"- CdA: {rider.cda_m2:g} m²",
        f"- Rolling-resistance coefficient: {rider.rolling_resistance:g}",
        f"- Drivetrain efficiency: {100 * rider.drivetrain_efficiency:g}%",
        f"- Air density: {rider.air_density_kg_m3:g} kg/m³",
        f"- Headwind: {rider.headwind_m_s:g} m/s",
        f"- Maximum simulated speed: {3.6 * rider.maximum_speed_m_s:g} km/h",
        f"- Elevation resampling: {spacing:g} m",
        f"- Centered elevation smoothing: {smoothing:g} m",
        "",
        "## Comparison",
        "",
        "| Course | Length | Altitude | Gain / loss | 95th-percentile grade up / down | Reference time | Flat time | Average speed | CDF |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for path, result, _ in rows:
        lines.append(
            f"| {race_name(path)} | {result['distance_m'] / 1000:.2f} km "
            f"| {result['minimum_elevation_m']:.0f}–{result['maximum_elevation_m']:.0f} m "
            f"| +{result['elevation_gain_m']:.0f} / -{result['elevation_loss_m']:.0f} m "
            f"| {100 * result['p95_uphill_grade']:.1f}% / "
            f"-{100 * result['p95_downhill_grade']:.1f}% "
            f"| {duration(result['t_observed_s'])} "
            f"| {duration(result['t_flat_s'])} "
            f"| {result['simulated_average_speed_kmh']:.2f} km/h "
            f"| {result['course_difficulty_factor']:.5f} |"
        )

    lines.extend(
        [
            "",
            "CDF is the simulated reference-rider course time divided by the "
            "same rider's time over an equally long flat route. Values above "
            "1 indicate a slower course under the model.",
            "",
        ]
    )
    if skipped:
        lines.extend(["## Skipped tracks", ""])
        lines.extend(f"- `{path.name}`: {reason}" for path, reason in skipped)
        lines.append("")
    lines.extend(["## Detailed track statistics", ""])
    for path, result, notes in rows:
        lines.extend(
            [
                f"### {race_name(path)}",
                "",
                f"- Source: `{path.name}` ({result['source_points']:,} track points)",
                f"- Horizontal / slope-adjusted length: {result['distance_m'] / 1000:.2f} / {result['road_distance_m'] / 1000:.2f} km",
                f"- Start / finish / net elevation: {result['start_elevation_m']:.0f} / {result['finish_elevation_m']:.0f} / {signed(result['net_elevation_change_m'])} m",
                f"- Minimum / maximum elevation: {result['minimum_elevation_m']:.0f} / {result['maximum_elevation_m']:.0f} m",
                f"- Smoothed elevation gain / loss: +{result['elevation_gain_m']:.0f} / -{result['elevation_loss_m']:.0f} m",
                f"- Uphill / flat / downhill distance: {result['uphill_distance_m'] / 1000:.2f} / {result['flat_distance_m'] / 1000:.2f} / {result['downhill_distance_m'] / 1000:.2f} km",
                f"- 95th-percentile uphill / downhill grade: {100 * result['p95_uphill_grade']:.1f}% / -{100 * result['p95_downhill_grade']:.1f}%",
                f"- Maximum smoothed uphill / downhill grade: {100 * result['maximum_uphill_grade']:.1f}% / -{100 * result['maximum_downhill_grade']:.1f}%",
                f"- Simulated speed, average / minimum / maximum: {result['simulated_average_speed_kmh']:.2f} / {result['simulated_minimum_speed_kmh']:.2f} / {result['simulated_maximum_speed_kmh']:.2f} km/h",
                f"- Reference / flat time: {duration(result['t_observed_s'])} / {duration(result['t_flat_s'])}",
                f"- Course difficulty factor: {result['course_difficulty_factor']:.5f}",
            ]
        )
        if notes:
            lines.append(f"- Data-quality warning: {'; '.join(notes)}.")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ensure_output_directories()
    parser = argparse.ArgumentParser(description="Generate a Markdown report for GPX bike tracks.")
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-distance", type=float, default=25.0)
    parser.add_argument("--smoothing-window", type=float, default=100.0)
    arguments = parser.parse_args()
    paths = sorted(arguments.input.glob("*.gpx"))
    if not paths:
        parser.error(f"no GPX files found in {arguments.input}")
    report = build_report(
        paths, Rider(), arguments.sample_distance, arguments.smoothing_window
    )
    arguments.output.write_text(report, encoding="utf-8")
    print(f"Saved {len(paths)} tracks to {arguments.output.resolve()}")


if __name__ == "__main__":
    main()