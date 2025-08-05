import logging
import sys
from pathlib import Path
from PySide6.QtCore import QStandardPaths

log_dir = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

    
def setup_logging(module_name:str = "app"):
    """
    Set up the logging module to log messages to both a file and the
    console.

    The logging level is set to INFO, which means that all messages with
    severity INFO and above will be logged. The logging format will
    include the timestamp, logger name, log level, and message. The
    logging handlers will log messages to the file 'marka_app.log' and
    the console.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "marka_app.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(module_name)
    return logger