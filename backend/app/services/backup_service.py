import shutil
from pathlib import Path
from datetime import datetime
from backend.app.core.logging import app_logger, log_audit

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
BACKUP_DIR = DATA_DIR / "backups"

class BackupService:
    @staticmethod
    def create_local_backup() -> str:
        """Create a timestamped archive of the local SQLite database and logs."""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        target_folder = BACKUP_DIR / f"backup_{timestamp}"
        target_folder.mkdir(parents=True, exist_ok=True)

        db_file = DATA_DIR / "sponsorajobs_local.db"
        if db_file.exists():
            shutil.copy2(db_file, target_folder / "sponsorajobs_local.db")

        # Copy logs
        logs_target = target_folder / "logs"
        logs_target.mkdir(exist_ok=True)
        if LOGS_DIR.exists():
            for f in LOGS_DIR.glob("*.log"):
                shutil.copy2(f, logs_target / f.name)

        log_audit(
            actor="admin",
            action="CREATE_BACKUP",
            details=f"Backup snapshot created at {target_folder}"
        )
        return str(target_folder)

backup_service = BackupService()
