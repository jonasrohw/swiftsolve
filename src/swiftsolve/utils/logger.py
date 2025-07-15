import logging, pathlib, sys
from utils.config import get_settings

def get_logger(name: str) -> logging.Logger:
    log_dir = pathlib.Path(get_settings().log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
        ch = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
        fh.setFormatter(fmt); ch.setFormatter(fmt)
        logger.addHandler(fh); logger.addHandler(ch)
    return logger
