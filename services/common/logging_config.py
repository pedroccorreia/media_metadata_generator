# logging_config.py
import logging
import sys

def configure_logger():
    """
    Configures the root logger for the application.
    
    This basic configuration logs messages of level INFO and above to standard output.
    For production, you would likely use a more advanced setup, such as JSON logging
    for better integration with services like Google Cloud Logging.
    """
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')