import logging
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        file_handler = logging.FileHandler(LOGS_DIR / log_file, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger

# Dedicated loggers
app_logger = setup_logger("app", "application.log")
email_logger = setup_logger("email", "email.log")
matching_logger = setup_logger("matching", "matching.log")
verification_logger = setup_logger("verification", "verification.log")
audit_logger = setup_logger("audit", "audit.log")

def log_audit(actor: str, action: str, details: str = "", result: str = "SUCCESS"):
    audit_logger.info(f"ACTOR={actor} | ACTION={action} | RESULT={result} | DETAILS={details}")
