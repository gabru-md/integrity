import logging
import os
from dotenv import load_dotenv

load_dotenv()


class Logger:
    @staticmethod
    def get_log(name: str, log_dir: str = os.getenv('LOG_DIR')):
        """
        Retrieves a logger instance, configuring it to write to multiple files
        based on log level and purpose.

        Args:
            name (str): The name of the logger.
            log_dir (str): The directory where the log files should be stored.
        """
        logger = logging.getLogger(name)

        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # Ensure the log directory exists
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # --- Define File Paths ---
            main_logfile_path = os.path.join(log_dir, f"main.log")
            warnings_errors_logfile_path = os.path.join(log_dir, f"warnings.log")
            exceptions_logfile_path = os.path.join(log_dir, f"exceptions.log")
            specific_logfile_path = os.path.join(log_dir, f"{name}.log")

            # --- Define Formatter ---
            formatter = logging.Formatter(
                '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s'
            )
            # A more verbose formatter for exceptions might be useful
            exception_formatter = logging.Formatter(
                '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s\n%(exc_info)s'
            )

            # 1. Main log file (INFO and above)
            main_handler = logging.FileHandler(main_logfile_path)
            main_handler.setFormatter(formatter)
            main_handler.setLevel(logging.INFO)

            # 2. Specific log file for the module (INFO and above)
            specific_handler = logging.FileHandler(specific_logfile_path)
            specific_handler.setFormatter(formatter)
            specific_handler.setLevel(logging.INFO)

            warnings_errors_handler = logging.FileHandler(warnings_errors_logfile_path)
            warnings_errors_handler.setFormatter(formatter)
            warnings_errors_handler.setLevel(logging.WARNING)

            exceptions_handler = logging.FileHandler(exceptions_logfile_path)
            # Use the more verbose formatter for the exceptions log
            exceptions_handler.setFormatter(exception_formatter)
            exceptions_handler.setLevel(logging.ERROR)


            # --- Add Handlers to Logger ---
            logger.addHandler(main_handler)
            logger.addHandler(specific_handler)
            logger.addHandler(warnings_errors_handler)
            logger.addHandler(exceptions_handler)

        return logger