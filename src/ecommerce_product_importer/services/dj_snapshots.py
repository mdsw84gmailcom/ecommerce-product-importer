from datetime import datetime
from pathlib import Path
import shutil


def create_dj_status_snapshot(
    report_path: Path,
    snapshot_dir: Path = Path("data/dj/snapshots"),
    *,
    timestamp: datetime | None = None,
) -> Path:
    """Copy a generated D&J status report into a timestamped local snapshot."""
    if not report_path.exists():
        raise FileNotFoundError(report_path)

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    current_time = timestamp or datetime.now()
    filename = current_time.strftime("%Y-%m-%d_%H%M%S_status.csv")
    destination = snapshot_dir / filename

    if destination.exists():
        raise FileExistsError(destination)

    shutil.copy2(report_path, destination)
    return destination


def list_dj_status_snapshots(
    snapshot_dir: Path = Path("data/dj/snapshots"),
) -> list[Path]:
    """Return local D&J status snapshots in chronological filename order."""
    if not snapshot_dir.exists():
        return []

    return sorted(snapshot_dir.glob("*_status.csv"))
