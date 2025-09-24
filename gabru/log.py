import logging
import os


class Logger:
    @staticmethod
    def get_log(name: str, log_dir: str = '/Users/manish/rasbhari/logs'):
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
            log_file_path = os.path.join(log_dir, f"{name}.log")

            # Create a FileHandler instead of a StreamHandler
            handler = logging.FileHandler(log_file_path)

            # Create a formatter for the log messages
            formatter = logging.Formatter(
                '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s'
            )

            handler.setFormatter(formatter)

            logger.addHandler(handler)

        return logger