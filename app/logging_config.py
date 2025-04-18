import logging
import os

def get_logger(name: str = "mcp_rag") -> logging.Logger:
    """
    Configures and returns a logger with a consistent format.
    """
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)

        log_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_format)

        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler("logs/mcp_rag.log")
        file_handler.setFormatter(log_format)

        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)

    return logger
