from __future__ import annotations

import atexit
import logging
import os
import time

import psutil

from pakk import DEFAULT_CFG_DIR
from pakk import ENVS

logger = logging.getLogger(__name__)

config_dir = os.environ.get(ENVS.CONFIG_DIR, DEFAULT_CFG_DIR)
lockfile_path = os.path.join(config_dir, "pakk_lock.lock")


# Helper class to manage the lockfile, which is just a text file containing the PID of the process that created it
# The logfile is automatically created if it does not exist
# The lockfile is automatically removed when the object is destroyed or when the program exits
# The lockfile contains the PID of the process that created it
# If there is already a lockfile, we want to check, if the creating process is still running. If not, we can delete the stale lockfile and create a new one.
class PakkLock:
    def __init__(self, operation: str, create_lock=True):

        self.access = False
        self.operation = operation
        atexit.register(self.unlock)

        # Check if the lockfile exists
        if os.path.exists(lockfile_path):
            # Read the PID from the lockfile
            with open(lockfile_path, "r") as f:
                pid = f.readline()
                operation = f.readline()

            # Check if the process is still running
            if not self._is_process_running(pid):
                # Delete the stale lockfile
                os.remove(lockfile_path)
                logger.warn(f"Stale lockfile found and removed: {lockfile_path}")

        if not os.path.exists(lockfile_path):
            # Create the lockfile
            if create_lock:
                with open(lockfile_path, "w") as f:
                    s = f"{os.getpid()}\n{operation}"
                    f.write(s)
            self.access = True
        else:
            logger.error(f"Another pakk instance is running with operation: {operation} ({pid}).")

    def unlock(self):
        if self.access and os.path.exists(lockfile_path):
            os.remove(lockfile_path)
            self.access = False

    @staticmethod
    def _is_process_running(pid: str) -> bool:
        """Check if a process is running."""
        return psutil.pid_exists(int(pid))


if __name__ == "__main__":
    lock = PakkLock("test")
    if lock.access:
        print("Access granted")
        time.sleep(10)
    else:
        print("Access denied")
