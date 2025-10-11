import threading
from abc import abstractmethod

from gabru.log import Logger


class Process(threading.Thread):
    """
        A Process comes with the name and log
        It is a continuous process where we define
        the sleep and run method and giving away
        def process(self)
    """

    def __init__(self, name, daemon=True):
        super().__init__(name=name, daemon=daemon)
        self.log = Logger.get_log(self.name)

    def run(self):
        try:
            self.process()
        except Exception as e:
            self.log.exception(e)

    @abstractmethod
    def process(self):
        pass
