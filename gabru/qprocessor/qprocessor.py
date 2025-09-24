import threading
import time
from abc import abstractmethod
from typing import Generic, TypeVar

from gabru.log import Logger
from gabru.db.service import ReadOnlyService
from gabru.qprocessor.qservice import QueueService
from gabru.qprocessor.qstats import QueueStats

T = TypeVar('T')


class QueueProcessor(Generic[T], threading.Thread):
    """
        A generic, single-threaded queue processor that continuously pulls items
        from a database, processes them, and updates its state to ensure
        it only processes new items.

        This class is designed to be a background worker that handles a stream
        of data (like events or contracts) in a robust, resilient manner. It uses
        a database to persist its progress, ensuring that if the processor
        restarts, it knows where to pick up.
    """

    def __init__(self, name, service: ReadOnlyService[T]):
        super().__init__(name=name, daemon=True)
        self.service = service
        self.log = Logger.get_log(name)
        self.sleep_time_sec = 5
        self.q_service = QueueService()
        self._set_up_queue_stats()
        self.queue = []
        self.max_queue_size = 10
        self.q_stats: QueueStats

    def _set_up_queue_stats(self):
        filters = {
            "name": self.name
        }
        q_stats = self.q_service.find_all(filters=filters)
        if q_stats is None or len(q_stats) == 0:
            q_stats_dict = {
                "name": self.name,
                "last_consumed_id": 0
            }
            q_stats = QueueStats(**q_stats_dict)
            q_stats.id = self.q_service.create(q_stats)
            self.log.info("Initialised QueueStats")
            self.q_stats = q_stats
        else:
            self.log.info("QueueStats already exist")
            self.q_stats = q_stats[0]

    def sleep(self):
        self.log.info(f"Nothing to do, waiting for {self.sleep_time_sec}s")
        time.sleep(self.sleep_time_sec)

    def run(self):
        while True:
            next_item = self.get_next_item()
            if not next_item:
                # no item to process, sleep for a bit
                self.sleep()
            else:
                next_item = self.filter_item(next_item)
                if next_item:
                    if not self.process_item(next_item):
                        self.log.error("Error processing item from the queue")
                else:
                    # nothing to do since this item is filtered
                    pass

    def process_item(self, item: T) -> bool:
        result = self._process_item(item)
        if result:
            self.log.info("Item processed successfully")
        else:
            self.log.warn("Failure to process item")

        # update the id in any case to keep things moving
        self.q_stats.last_consumed_id = item.id

        return result

    def get_next_item(self) -> T:
        if len(self.queue) > 0:
            return self.queue.pop(0)

        # if in-memory queue length is 0 then first update qstats
        if self.q_service.update(self.q_stats):
            self.log.info("Updated up-to-date stats")

        # then fetch next batch of items from db
        items_from_queue = self.service.get_all_items_after(self.q_stats.last_consumed_id, limit=self.max_queue_size)
        if items_from_queue:
            self.queue.extend(items_from_queue)
            return self.get_next_item()
        return None

    @abstractmethod
    def filter_item(self, item: T):
        """ returns None if this item can be excluded else return the item """
        return item

    @abstractmethod
    def _process_item(self, next_item: T) -> bool:
        pass
