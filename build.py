import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def run(script: str) -> None:
    subprocess.run([sys.executable, str(SRC / script)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build IRONMAN analysis artifacts.")
    parser.add_argument(
        "--with-tests", action="store_true", help="Run the regression suite first."
    )
    parser.add_argument(
        "--legacy-plots",
        action="store_true",
        help="Also regenerate older Excel-based plots and CSV exports.",
    )
    arguments = parser.parse_args()

    if arguments.with_tests:
        subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=ROOT,
            check=True,
        )

    run("build_dashboard.py")
    run("build_gpx_report.py")

    if arguments.legacy_plots:
        for script in (
            "qualification_full.py",
            "qualification_703.py",
            "overall_time_analysis.py",
            "split_time_analysis.py",
        ):
            run(script)

    print(f"Build complete: {ROOT / 'dist'}")


if __name__ == "__main__":
    main()
