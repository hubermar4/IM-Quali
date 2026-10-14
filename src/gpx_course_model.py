import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path


EARTH_RADIUS_M = 6_371_008.8
GRAVITY_M_S2 = 9.80665


@dataclass(frozen=True)
class TrackPoint:
    latitude: float
    longitude: float
    elevation_m: float


@dataclass(frozen=True)
class Rider:
    total_mass_kg: float = 82.0
    power_w: float = 200.0
    ascent_power_factor: float = 1.20
    descent_power_factor: float = 0.75
    flat_grade_threshold: float = 0.005
    cda_m2: float = 0.25
    rolling_resistance: float = 0.004
    drivetrain_efficiency: float = 0.975
    air_density_kg_m3: float = 1.225
    headwind_m_s: float = 0.0
    maximum_speed_m_s: float = 25.0


def tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def read_gpx(path: Path) -> list[TrackPoint]:
    root = ET.parse(path).getroot()
    points = []
    for element in root.iter():
        if tag_name(element.tag) != "trkpt":
            continue
        elevation = next(
            (
                child.text
                for child in element
                if tag_name(child.tag) == "ele" and child.text
            ),
            None,
        )
        if elevation is not None:
            points.append(
                TrackPoint(
                    latitude=float(element.attrib["lat"]),
                    longitude=float(element.attrib["lon"]),
                    elevation_m=float(elevation),
                )
            )
    if len(points) < 2:
        raise ValueError("GPX needs at least two track points with elevation")
    return points


def distance_m(first: TrackPoint, second: TrackPoint) -> float:
    latitude_1 = math.radians(first.latitude)
    latitude_2 = math.radians(second.latitude)
    latitude_delta = latitude_2 - latitude_1
    longitude_delta = math.radians(second.longitude - first.longitude)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(haversine))


def resample(
    points: list[TrackPoint], spacing_m: float
) -> tuple[list[float], list[float]]:
    source_distances = [0.0]
    for first, second in zip(points, points[1:]):
        source_distances.append(source_distances[-1] + distance_m(first, second))
    total_distance = source_distances[-1]
    if total_distance <= 0:
        raise ValueError("GPX track has zero distance")

    segment_count = max(1, math.ceil(total_distance / spacing_m))
    distances = [
        total_distance * index / segment_count
        for index in range(segment_count + 1)
    ]
    elevations = []
    source_index = 0
    for target in distances:
        while (
            source_index + 1 < len(source_distances) - 1
            and source_distances[source_index + 1] < target
        ):
            source_index += 1
        start = source_distances[source_index]
        end = source_distances[source_index + 1]
        fraction = 0.0 if end <= start else (target - start) / (end - start)
        elevations.append(
            points[source_index].elevation_m
            + fraction
            * (points[source_index + 1].elevation_m - points[source_index].elevation_m)
        )
    return distances, elevations


def smooth(elevations: list[float], spacing_m: float, window_m: float) -> list[float]:
    if window_m <= 0:
        return elevations.copy()
    radius = max(1, round(window_m / spacing_m / 2))
    prefix = [0.0]
    for elevation in elevations:
        prefix.append(prefix[-1] + elevation)
    result = []
    for index in range(len(elevations)):
        first = max(0, index - radius)
        last = min(len(elevations), index + radius + 1)
        result.append((prefix[last] - prefix[first]) / (last - first))

    # Keep the original net elevation change after smoothing the endpoints.
    start_error = elevations[0] - result[0]
    end_error = elevations[-1] - result[-1]
    denominator = max(len(result) - 1, 1)
    return [
        value + start_error + (end_error - start_error) * index / denominator
        for index, value in enumerate(result)
    ]


def crank_power(speed_m_s: float, grade: float, rider: Rider) -> float:
    angle = math.atan(grade)
    rolling_force = (
        rider.total_mass_kg
        * GRAVITY_M_S2
        * rider.rolling_resistance
        * math.cos(angle)
    )
    gravity_force = rider.total_mass_kg * GRAVITY_M_S2 * math.sin(angle)
    air_speed = speed_m_s + rider.headwind_m_s
    aerodynamic_force = (
        0.5
        * rider.air_density_kg_m3
        * rider.cda_m2
        * air_speed
        * abs(air_speed)
    )
    return (
        speed_m_s * (rolling_force + gravity_force + aerodynamic_force)
        / rider.drivetrain_efficiency
    )


def target_power(grade: float, rider: Rider) -> float:
    if grade > rider.flat_grade_threshold:
        return rider.power_w * rider.ascent_power_factor
    if grade < -rider.flat_grade_threshold:
        return rider.power_w * rider.descent_power_factor
    return rider.power_w


def solve_speed(grade: float, rider: Rider) -> float:
    power = target_power(grade, rider)
    lower = 0.01
    upper = rider.maximum_speed_m_s
    if crank_power(upper, grade, rider) <= power:
        return upper
    for _ in range(70):
        middle = (lower + upper) / 2
        if crank_power(middle, grade, rider) < power:
            lower = middle
        else:
            upper = middle
    return (lower + upper) / 2


def simulate(
    points: list[TrackPoint],
    rider: Rider,
    spacing_m: float,
    smoothing_window_m: float,
) -> dict:
    distances, elevations = resample(points, spacing_m)
    elevations = smooth(elevations, distances[-1] / (len(distances) - 1), smoothing_window_m)
    observed_time_s = 0.0
    road_distance_m = 0.0
    elevation_gain_m = 0.0
    elevation_loss_m = 0.0
    uphill_distance_m = 0.0
    downhill_distance_m = 0.0
    flat_distance_m = 0.0
    grades = []
    speeds = []
    for index in range(len(distances) - 1):
        horizontal_distance = distances[index + 1] - distances[index]
        elevation_change = elevations[index + 1] - elevations[index]
        grade = elevation_change / horizontal_distance
        road_distance = math.hypot(horizontal_distance, elevation_change)
        speed = solve_speed(grade, rider)
        observed_time_s += road_distance / speed
        road_distance_m += road_distance
        elevation_gain_m += max(elevation_change, 0.0)
        elevation_loss_m += max(-elevation_change, 0.0)
        grades.append(grade)
        speeds.append(speed)
        if grade > rider.flat_grade_threshold:
            uphill_distance_m += road_distance
        elif grade < -rider.flat_grade_threshold:
            downhill_distance_m += road_distance
        else:
            flat_distance_m += road_distance

    flat_time_s = distances[-1] / solve_speed(0.0, rider)
    uphill_grades = sorted(grade for grade in grades if grade > 0)
    downhill_grades = sorted(-grade for grade in grades if grade < 0)

    def percentile(values: list[float], fraction: float) -> float:
        if not values:
            return 0.0
        return values[round((len(values) - 1) * fraction)]

    return {
        "source_points": len(points),
        "simulation_segments": len(distances) - 1,
        "distance_m": distances[-1],
        "road_distance_m": road_distance_m,
        "start_elevation_m": elevations[0],
        "finish_elevation_m": elevations[-1],
        "minimum_elevation_m": min(elevations),
        "maximum_elevation_m": max(elevations),
        "net_elevation_change_m": elevations[-1] - elevations[0],
        "elevation_gain_m": elevation_gain_m,
        "elevation_loss_m": elevation_loss_m,
        "uphill_distance_m": uphill_distance_m,
        "downhill_distance_m": downhill_distance_m,
        "flat_distance_m": flat_distance_m,
        "maximum_uphill_grade": max(uphill_grades, default=0.0),
        "maximum_downhill_grade": max(downhill_grades, default=0.0),
        "p95_uphill_grade": percentile(uphill_grades, 0.95),
        "p95_downhill_grade": percentile(downhill_grades, 0.95),
        "t_observed_s": observed_time_s,
        "t_flat_s": flat_time_s,
        "simulated_average_speed_kmh": road_distance_m / observed_time_s * 3.6,
        "simulated_minimum_speed_kmh": min(speeds) * 3.6,
        "simulated_maximum_speed_kmh": max(speeds) * 3.6,
        "course_difficulty_factor": observed_time_s / flat_time_s,
        "rider": asdict(rider),
    }


def duration(seconds: float) -> str:
    rounded = round(seconds)
    hours, remainder = divmod(rounded, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def positive(value: str) -> float:
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def nonnegative(value: str) -> float:
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return number


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Simulate a terrain-dependent-power reference rider over a GPX track."
    )
    result.add_argument("gpx", type=Path)
    result.add_argument(
        "--mass",
        type=positive,
        default=82.0,
        help="Rider + triathlon bike/kit mass in kg (default: 82)",
    )
    result.add_argument(
        "--power", type=positive, default=200.0, help="Crank power in W (default: 200)"
    )
    result.add_argument(
        "--ascent-factor",
        type=positive,
        default=1.20,
        help="Ascent power multiplier (default: 1.20)",
    )
    result.add_argument(
        "--descent-factor",
        type=positive,
        default=0.75,
        help="Descent power multiplier (default: 0.75)",
    )
    result.add_argument(
        "--flat-grade",
        type=nonnegative,
        default=0.5,
        help="Absolute grade treated as flat in percent (default: 0.5)",
    )
    result.add_argument(
        "--cda",
        type=positive,
        default=0.25,
        help="Aerobar CdA in m^2 (default: 0.25)",
    )
    result.add_argument("--crr", type=positive, default=0.004)
    result.add_argument("--efficiency", type=positive, default=0.975)
    result.add_argument("--air-density", type=positive, default=1.225)
    result.add_argument("--headwind", type=nonnegative, default=0.0, help="m/s")
    result.add_argument("--max-speed", type=positive, default=90.0, help="km/h")
    result.add_argument("--sample-distance", type=positive, default=25.0, help="m")
    result.add_argument("--smoothing-window", type=nonnegative, default=100.0, help="m")
    result.add_argument("--json", action="store_true")
    return result


def main() -> int:
    arguments = parser().parse_args()
    if arguments.efficiency > 1:
        print("error: --efficiency must be at most 1", file=sys.stderr)
        return 2
    rider = Rider(
        total_mass_kg=arguments.mass,
        power_w=arguments.power,
        ascent_power_factor=arguments.ascent_factor,
        descent_power_factor=arguments.descent_factor,
        flat_grade_threshold=arguments.flat_grade / 100,
        cda_m2=arguments.cda,
        rolling_resistance=arguments.crr,
        drivetrain_efficiency=arguments.efficiency,
        air_density_kg_m3=arguments.air_density,
        headwind_m_s=arguments.headwind,
        maximum_speed_m_s=arguments.max_speed / 3.6,
    )
    try:
        result = simulate(
            read_gpx(arguments.gpx),
            rider,
            arguments.sample_distance,
            arguments.smoothing_window,
        )
    except (ET.ParseError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    result["t_observed"] = duration(result["t_observed_s"])
    result["t_flat"] = duration(result["t_flat_s"])
    if arguments.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Route: {arguments.gpx}")
        print(f"Track points: {result['source_points']:,}")
        print(f"Horizontal length: {result['distance_m'] / 1000:.2f} km")
        print(f"Road length (including slope): {result['road_distance_m'] / 1000:.2f} km")
        print(
            "Altitude (smoothed): "
            f"{result['minimum_elevation_m']:.0f}–{result['maximum_elevation_m']:.0f} m "
            f"(start {result['start_elevation_m']:.0f} m, "
            f"finish {result['finish_elevation_m']:.0f} m, "
            f"net {result['net_elevation_change_m']:+.0f} m)"
        )
        print(
            f"Smoothed elevation: +{result['elevation_gain_m']:.0f} m "
            f"/ -{result['elevation_loss_m']:.0f} m"
        )
        print(
            "Terrain distance (>0.5% / ±0.5% / <-0.5%): "
            f"{result['uphill_distance_m'] / 1000:.2f} / "
            f"{result['flat_distance_m'] / 1000:.2f} / "
            f"{result['downhill_distance_m'] / 1000:.2f} km"
        )
        print(
            "Smoothed grade (up / down): "
            f"95th percentile {100 * result['p95_uphill_grade']:.1f}% / "
            f"-{100 * result['p95_downhill_grade']:.1f}%; "
            f"maximum {100 * result['maximum_uphill_grade']:.1f}% / "
            f"-{100 * result['maximum_downhill_grade']:.1f}%"
        )
        print(f"Simulated reference-rider t_observed: {result['t_observed']}")
        print(f"Flat reference time: {result['t_flat']}")
        print(
            "Simulated speed (average / minimum / maximum): "
            f"{result['simulated_average_speed_kmh']:.2f} / "
            f"{result['simulated_minimum_speed_kmh']:.2f} / "
            f"{result['simulated_maximum_speed_kmh']:.2f} km/h"
        )
        print(f"Course difficulty factor: {result['course_difficulty_factor']:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())