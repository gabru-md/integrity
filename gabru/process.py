import threading
from abc import abstractmethod
from gabru.log import Logger


class Process(threading.Thread):
    """
    A Process comes with the name and log
    It is a continuous process where we define
    the sleep and run method and giving away
    the def process(self)
    """

    def __init__(self, name, enabled=False, daemon=True):
        super().__init__(name=name, daemon=daemon)
        self.log = Logger.get_log(self.name)
        self.enabled = enabled
        self.running = True

    def run(self):
        try:
            self.process()
        except Exception as e:
            self.log.exception(e)

    def stop(self):
        self.running = False

    @abstractmethod
    def process(self):
        pass


class ProcessManager(Process):
    def __init__(self, processes_to_manage: dict[str, list[Process]]):
        super().__init__('ProcessManager', daemon=True)
        self.registered_processes_by_app = processes_to_manage
        self.running_process_threads = {}
        self.all_processes_map: dict[str, Process] = {}
        self.disabled_processes = set()

        for app_name, processes in processes_to_manage.items():
            for process in processes:
                # Assuming process names are unique
                self.all_processes_map[process.name] = process

    def process(self):
        self.start_all_processes()

    def get_process_status(self, process_name: str) -> bool:
        """ Returns True if the process is currently running AND not disabled. """
        # A process is considered "alive" only if the thread is running AND it's not explicitly disabled
        is_thread_alive = process_name in self.running_process_threads and self.running_process_threads[
            process_name].is_alive()
        is_disabled = process_name in self.disabled_processes

        return is_thread_alive and not is_disabled

    def start_all_processes(self):
        for app_name, processes in self.registered_processes_by_app.items():
            for process in processes:
                # Start if enabled AND not already running
                if process.enabled:
                    if process.name not in self.disabled_processes and process.name not in self.running_process_threads:
                        self.log.info(f"Starting {process.name} for {app_name}")
                        process.start()
                        self.running_process_threads[process.name] = process

    def start_process(self, process_name: str):
        if process_name not in self.all_processes_map:
            self.log.error(f"Attempted to start unknown process: {process_name}")
            return False

        process_object = self.all_processes_map[process_name]

        self.disabled_processes.discard(process_name)

        if process_name in self.running_process_threads and process_object.is_alive() and process_object.running:
            self.log.warning(f"Process {process_name} is already running.")
            return True

        try:
            # Set internal flag and attempt start
            process_object.running = True
            process_object.start()
            self.running_process_threads[process_name] = process_object
            self.log.info(f"Process {process_name} started successfully.")
            return True
        except RuntimeError as e:
            self.disabled_processes.add(process_name)
            self.log.error(f"Failed to start {process_name}: {e}. (Thread already completed and cannot be restarted.)")
            return False

    def _stop_process_thread(self, process_name: str, process_thread: Process):
        self.log.info(f"Stopping {process_thread.name}")
        process_thread.stop()

        # Remove from running threads map
        if process_name in self.running_process_threads:
            del self.running_process_threads[process_name]

    def stop_process(self, process_name: str):
        if process_name not in self.all_processes_map:
            self.log.error(f"Attempted to stop unknown process: {process_name}")
            return

        # Critical: Add to disabled set
        self.disabled_processes.add(process_name)

        # Stop the running thread if it exists
        process_thread = self.running_process_threads.get(process_name)
        if process_thread:
            self._stop_process_thread(process_name, process_thread)
        else:
            self.log.warning(f"Process {process_name} was already marked as stopped/not running.")

    def stop_all_processes(self):
        # Stop all running threads and mark them as disabled
        for process_name, process_thread in list(self.running_process_threads.items()):
            self.disabled_processes.add(process_name)
            self._stop_process_thread(process_name, process_thread)

        self.running_process_threads.clear()
