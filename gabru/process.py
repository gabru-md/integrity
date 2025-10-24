import threading
from abc import abstractmethod
from typing import Optional

from gabru.log import Logger


class Process(threading.Thread):
    """
    A Process comes with the name and log
    It is a continuous process where we define
    the sleep and run method and giving away
    the def process(self):
    """

    def __init__(self, name, enabled=False, daemon=True, **kwargs):
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

        self.registered_process_blueprints = processes_to_manage
        self.all_processes_map: dict[str, Process] = {}
        self.process_blueprints: dict[str, tuple] = {}

        self.running_process_threads = {}

        self._initialize_processes()

    def _initialize_processes(self):
        """Initializes the processes map by creating the initial instances."""
        for app_name, blueprints in self.registered_process_blueprints.items():
            for process_class, args, kwargs in blueprints:
                # Check for the 'name' argument, or default to class name
                name = kwargs.get('name', process_class.__name__)
                kwargs['name'] = name  # Ensure name is in kwargs for instance creation

                # Create the initial instance
                process_instance = process_class(*args, **kwargs)

                # Store the instance and the blueprint
                self.all_processes_map[name] = process_instance
                self.process_blueprints[name] = (process_class, args, kwargs)

    def _recreate_process_instance(self, process_name: str) -> Optional[Process]:
        """Creates a new Process instance from its stored blueprint."""
        blueprint = self.process_blueprints.get(process_name)
        if not blueprint:
            self.log.error(f"Blueprint for {process_name} not found for recreation.")
            return None

        process_class, args, kwargs = blueprint

        new_kwargs = kwargs.copy()
        new_kwargs['enabled'] = True


        new_instance = process_class(*args, **new_kwargs)
        self.all_processes_map[process_name] = new_instance
        return new_instance

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
        for process_name, process in self.all_processes_map.items():
            # 'process' here is the instance created in _initialize_processes
            if process.enabled:
                self.log.info(f"Starting initial enabled process: {process_name}")
                try:
                    process.running = True
                    process.start()
                    self.running_process_threads[process_name] = process
                except RuntimeError as e:
                    # This should not happen since they are fresh instances
                    self.log.error(f"Failed to start initial process {process_name}: {e}")

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

    def run_process(self, process_name: str):
        if process_name not in self.all_processes_map:
            self.log.error(f"Attempted to run unknown process: {process_name}")
            return False

        process_object = self.all_processes_map[process_name]

        if not process_object.enabled:
            self.log.error(f"Cannot run process {process_name}. It must be enabled first.")
            return False

        # check if the current thread is alive (running)
        if process_object.is_alive():
            process_object.running = True
            self.log.warning(f"Process {process_name} is already running.")
            return True

        if not process_object.is_alive():
            self.log.info(f"Process {process_name} thread is completed. Recreating instance...")
            new_process_object = self._recreate_process_instance(process_name)
            if not new_process_object:
                return False

            process_object = new_process_object

        try:
            process_object.running = True
            process_object.enabled = True
            process_object.start()
            self.running_process_threads[process_name] = process_object
            self.log.info(f"Process {process_name} started successfully.")
            return True
        except RuntimeError as e:
            self.log.error(f"Failed to start {process_name}: {e}. (Should not happen after recreation.)")
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