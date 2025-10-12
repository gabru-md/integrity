import threading
from abc import abstractmethod
from gabru.log import Logger


class Process(threading.Thread):
    """
    A Process comes with the name and log
    It is a continuous process where we define
    the sleep and run method and giving away
    the def process(self):
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
        # The disabled_processes set is no longer needed as we use Process.enabled and Process.running
        # self.disabled_processes = set()

        for app_name, processes in processes_to_manage.items():
            for process in processes:
                # Assuming process names are unique
                self.all_processes_map[process.name] = process

    def process(self):
        self.start_all_processes_on_init()

    def get_process_status(self, process_name: str) -> bool:
        """ Returns True if the process is currently enabled AND its thread is alive. """
        process = self.all_processes_map.get(process_name)
        if not process or not process.enabled:
            return False  # Not alive if not enabled

        # The thread object in running_process_threads might be an old, completed thread.
        # We check the thread's actual status.
        return process.is_alive() and process.running

    def start_all_processes_on_init(self):
        for app_name, processes in self.registered_processes_by_app.items():
            for process in processes:
                # Start if enabled AND not already running
                if process.enabled and process.name not in self.running_process_threads:
                    self.log.info(f"Starting {process.name} for {app_name}")
                    # Ensure running is True before start
                    process.running = True
                    process.start()
                    self.running_process_threads[process.name] = process

    def enable_process(self, process_name: str):
        if process_name not in self.all_processes_map:
            self.log.error(f"Attempted to enable unknown process: {process_name}")
            return False

        process_object = self.all_processes_map[process_name]

        if process_object.enabled:
            self.log.warning(f"Process {process_name} is already enabled.")
            return True

        # Set the persistent state to enabled
        process_object.enabled = True
        self.log.info(f"Process {process_name} is now enabled.")
        return True

    def disable_process(self, process_name: str):
        if process_name not in self.all_processes_map:
            self.log.error(f"Attempted to disable unknown process: {process_name}")
            return False

        process_object = self.all_processes_map[process_name]

        if not process_object.enabled:
            self.log.warning(f"Process {process_name} is already disabled.")
            return True

        # Stop the process first if it is running
        if process_object.is_alive():
            self._stop_process_thread(process_name, process_object)

        # Set the persistent state to disabled
        process_object.enabled = False
        self.log.info(f"Process {process_name} is now disabled.")
        return True

    # Renaming start_process to run_process to reflect runtime control under an 'enabled' state
    def run_process(self, process_name: str):
        if process_name not in self.all_processes_map:
            self.log.error(f"Attempted to run unknown process: {process_name}")
            return False

        process_object = self.all_processes_map[process_name]

        if not process_object.enabled:
            self.log.error(f"Cannot run process {process_name}. It must be enabled first.")
            return False

        if process_object.is_alive() and process_object.running:
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
            # This happens if a thread has already completed and cannot be restarted.
            self.log.error(f"Failed to start {process_name}: {e}. (Thread already completed and cannot be restarted.)")
            return False

    def _stop_process_thread(self, process_name: str, process_thread: Process):
        self.log.info(f"Stopping {process_thread.name}")
        process_thread.stop()

        # Remove from running threads map
        if process_name in self.running_process_threads:
            del self.running_process_threads[process_name]

    # Renaming stop_process to pause_process to reflect runtime control under an 'enabled' state
    def pause_process(self, process_name: str):
        if process_name not in self.all_processes_map:
            self.log.error(f"Attempted to pause unknown process: {process_name}")
            return

        process_object = self.all_processes_map[process_name]

        if not process_object.enabled:
            self.log.error(f"Cannot pause process {process_name}. It must be enabled first.")
            return

        # Stop the running thread if it exists
        process_thread = self.running_process_threads.get(process_name)
        if process_thread:
            self._stop_process_thread(process_name, process_thread)
        else:
            self.log.warning(f"Process {process_name} was already paused/not running.")

    def stop_all_processes(self):
        # Stop all running threads
        for process_name, process_thread in list(self.running_process_threads.items()):
            self._stop_process_thread(process_name, process_thread)
            # Ensure the state is still 'enabled' but paused
            process_thread.enabled = True

        self.running_process_threads.clear()