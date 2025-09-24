import logging


class Logger:
    @staticmethod
    def get_log(name: str):
        logger = logging.getLogger(name)

        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()

            # Create a formatter for the log messages
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            handler.setFormatter(formatter)

            logger.addHandler(handler)

        return logger