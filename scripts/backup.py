"""
SponsorAJobs Local Engine Backup Utility
Creates a timestamped snapshot of the local database and application logs.
"""
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.services.backup_service import backup_service

def main():
    print("Initiating local backup snapshot...")
    backup_path = backup_service.create_local_backup()
    print(f"[OK] Backup snapshot successfully created at: {backup_path}")

if __name__ == "__main__":
    main()
