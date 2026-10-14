from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent if MODULE_DIR.name == "src" else MODULE_DIR

DATA_DIR = PROJECT_ROOT / "data"
DIST_DIR = PROJECT_ROOT / "dist"
DOCS_DIR = PROJECT_ROOT / "docs"
ARCHIVE_DIR = PROJECT_ROOT / "archive"

RACE_HISTORY_DIR = (
    DATA_DIR / "race_history"
    if (DATA_DIR / "race_history").exists()
    else PROJECT_ROOT / "RaceHistoryData"
)
CACHE_DIR = (
    DATA_DIR / "cache"
    if (DATA_DIR / "cache").exists()
    else PROJECT_ROOT / "DataArchive"
)
GPX_TRACK_DIR = (
    DATA_DIR / "gpx_tracks"
    if (DATA_DIR / "gpx_tracks").exists()
    else PROJECT_ROOT / "GPX Tracks"
)
DERIVED_DATA_DIR = DATA_DIR / "derived"
LEGACY_DATA_DIR = DATA_DIR / "legacy"
COACHCOX_ALLOCATION_FILE = (
    DERIVED_DATA_DIR / "coachcox_age_group_allocations.json"
    if (DERIVED_DATA_DIR / "coachcox_age_group_allocations.json").exists()
    else PROJECT_ROOT / "coachcox_age_group_allocations.json"
)


def ensure_output_directories() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    LEGACY_DATA_DIR.mkdir(parents=True, exist_ok=True)