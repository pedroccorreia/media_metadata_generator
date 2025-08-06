# logging_config.py
import logging
import json
from datetime import datetime
import sys # Import sys for stdout

def configure_logger():
    """
    Configures the root logger or a specific logger to output structured JSON logs
    to stdout, which are automatically picked up by Google Cloud Logging.
    """
    # Get the root logger or a specific named logger
    # Using __name__ in other modules will get a child logger that inherits this config
    logger = logging.getLogger() # Get the root logger
    logger.setLevel(logging.INFO) # Set the default logging level for the application

    # Prevent adding multiple handlers if this function is called multiple times
    # (e.g., in some development/testing environments or if imported multiple times)
    if not logger.handlers:
        # Create a custom JSON formatter
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_record = {
                    "severity": record.levelname,
                    "message": record.getMessage(),
                    "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
                    "python_logger": record.name, # Name of the logger (e.g., 'MediaAssetManager')
                    "line": record.lineno,
                    "file": record.filename,
                }
                # Add extra attributes passed via logger.info("msg", extra={"key": "value"})
                if hasattr(record, 'extra_fields'):
                    log_record.update(record.extra_fields)
                return json.dumps(log_record)

        # Create a stream handler that outputs to stdout
        handler = logging.StreamHandler(sys.stdout) # Explicitly use sys.stdout
        handler.setFormatter(JsonFormatter())

        # Add the handler to the logger
        logger.addHandler(handler)

    # Optional: Suppress verbose logs from third-party libraries if needed
    # logging.getLogger('google.cloud.firestore').setLevel(logging.WARNING)
    # logging.getLogger('google.cloud.pubsub').setLevel(logging.WARNING)

    logging.info("Logger configured successfully.")