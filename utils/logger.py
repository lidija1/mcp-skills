import logging  # Import the standard logging library
from pathlib import Path  # Import Path for modern and easier file system interactions
from datetime import datetime  # Import datetime to timestamp our log files

def setup_logger(name="PlaywrightTest"):
    # Define the directory where logs will be stored
    log_dir = Path("logs")
    
    # Create the directory if it doesn't exist; exist_ok=True prevents errors if it does
    log_dir.mkdir(exist_ok=True)

    # Get a logger instance with the specified name
    logger = logging.getLogger(name)
    
    # Check if the logger already has handlers to prevent duplicate logs in the same session
    if logger.handlers:
        return logger

    # Set the base logging level; DEBUG captures everything (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    logger.setLevel(logging.DEBUG)

    # Define the format for log entries: Timestamp - Logger Name - Severity Level - Message
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Generate a unique filename for the log file using the current date and time
    log_filename = log_dir / f"test_run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    
    # Initialize a FileHandler to write logs to the file with UTF-8 encoding support
    fh = logging.FileHandler(log_filename, encoding='utf-8')
    
    # Set the level for the file handler specifically to DEBUG
    fh.setLevel(logging.DEBUG)
    
    # Attach our defined formatter to the file handler
    fh.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(fh)

    # Return the configured logger instance
    return logger