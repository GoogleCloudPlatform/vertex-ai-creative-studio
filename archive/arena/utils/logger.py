#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Logger configuration for GenMedia Arena"""
import logging


class LogLevel:
    """Enum for log levels"""

    OFF = 0
    ON = 1
    WARNING = 2
    ERROR = 3
    _names = {0: "OFF", 1: "ON", 2: "WARNING", 3: "ERROR"}

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self._names.get(self.value, "UNKNOWN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%H:%M:%S",
)


def log(message: str, level: LogLevel = LogLevel.ON):
    """Log a message at the specified level."""
    log_methods = {
        LogLevel.ON: logging.info,
        LogLevel.WARNING: logging.warning,
        LogLevel.ERROR: logging.error,
    }

    if level == LogLevel.OFF:
        return  # Do not log if level is OFF

    log_method = log_methods.get(level)
    if log_method:
        log_method(message)
    else:
        raise ValueError(
            f"Invalid log level specified: {level}. Use LogLevel.ON, LogLevel.OFF, LogLevel.WARNING, or LogLevel.ERROR."
        )
