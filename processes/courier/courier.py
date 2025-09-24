from gabru.qprocessor.qprocessor import QueueProcessor, T
from model.event import Event
from services.events import EventService


class Courier(QueueProcessor[Event]):
    """
    Courier class is a queue processor processing events
    and generating notifications that are tied to those events
    """

    def __init__(self):
        super().__init__("Courier", EventService())

    def filter_item(self, item: T):
        pass

    def _process_item(self, next_item: T) -> bool:
        return False
