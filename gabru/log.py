import logging
import os
from dotenv import load_dotenv

load_dotenv()


class Logger:
    @staticmethod
    def get_log(name: str, log_dir: str = os.getenv('LOG_DIR')):
        """
        Retrieves a logger instance, configuring it to write to a file in a specified directory.

        Args:
            name (str): The name of the logger.
            log_dir (str): The directory where the log file should be stored. Defaults to 'logs'.
        """
        logger = logging.getLogger(name)

        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # Ensure the log directory exists
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Construct the log file path
            main_logfile_path = os.path.join(log_dir, f"main.log")
            specific_logfile_path = os.path.join(log_dir, f"{name}.log")

            # Create a FileHandler instead of a StreamHandler
            specific_logfile_handler = logging.FileHandler(specific_logfile_path)
            main_logfile_handler = logging.FileHandler(main_logfile_path)

            # Create a formatter for the log messages
            formatter = logging.Formatter(
                '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s'
            )

            specific_logfile_handler.setFormatter(formatter)
            main_logfile_handler.setFormatter(formatter)

            logger.addHandler(specific_logfile_handler)
            logger.addHandler(main_logfile_handler)

        return logger
