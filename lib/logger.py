"""
@namespace lib.logger
Logger configuration and initialization for CTF logging
"""

# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2022 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
# distributed and modified only pursuant to the terms of that agreement.
# See the License for the specific language governing permissions and limitations under the
# License at https://software.nasa.gov/ .
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either expressed or implied.


import datetime as dt
import logging
import os
import time
from enum import IntEnum

from lib.ctf_global import Global

try:
    import colorlog
except ImportError:
    colorlog = None


class CtfLogLevel(IntEnum):
    """
    CtfLogLevel: An enum containing custom log levels used in CTF
    """
    TEST_PASS = 21
    TEST_FAIL = 22
    TEST_PASS_CONT = 5
    TEST_FAIL_CONT = 6


class TestFormatter(logging.Formatter):
    """
    TestFormatter: Customizes the logging formatter to override formatTime
    """
    def formatTime(self, record, datefmt=None):
        ct_obj = dt.datetime.fromtimestamp(record.created)
        return ct_obj.strftime(datefmt or TIME_FORMAT)


LOG_FORMAT = '[%(asctime)s.%(msecs)03d] %(module)-32s(%(lineno)-3d) *** %(levelname)s: %(message)s'
TIME_FORMAT = '%H:%M:%S'
logger = logging.getLogger()
test_formatter = TestFormatter(LOG_FORMAT)


# pylint: disable=protected-access
def test(self, passed, cont, msg, *args, **kwargs):
    """
    Passed as a callback to logging configuration for logging test results
    @note - self is an instance of class Logger
    """
    if cont:
        log_level = CtfLogLevel.TEST_PASS_CONT if passed else CtfLogLevel.TEST_FAIL_CONT
    else:
        log_level = CtfLogLevel.TEST_PASS if passed else CtfLogLevel.TEST_FAIL

    if self.isEnabledFor(log_level):
        self._log(log_level, msg, args, **kwargs)

    return passed


def init_logger(config):
    """
    Initializes the logger with CTF-specific handlers and formatting
    """
    # Add log levels and custom function for test results
    for level in CtfLogLevel:
        logging.addLevelName(level.value, level.name)
    logging.Logger.test = test

    log_level = config.get("logging", "log_level", fallback="DEBUG")
    logging.basicConfig(level=log_level, format=LOG_FORMAT, datefmt=TIME_FORMAT, filename="", filemode='a')

    # Create special console format for stdout if colorlog is available
    console_formatter = test_formatter
    if colorlog:
        # Install colorlog (pip install colorlog) to use colored logs for console
        log_colors = {'DEBUG': 'white',
                      'INFO': 'blue',
                      'WARNING': 'bold_yellow',
                      'ERROR': 'bold_red',
                      'CRITICAL': 'bold_red',
                      'TEST_PASS_CONT': 'green',
                      'TEST_PASS': 'bold_green',
                      'TEST_FAIL_CONT': 'red',
                      'TEST_FAIL': 'bold_red'}
        console_formatter = colorlog.ColoredFormatter('%(log_color)s' + LOG_FORMAT,
                                                      datefmt=TIME_FORMAT,
                                                      log_colors=log_colors)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(CtfLogLevel.TEST_PASS_CONT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)


def set_logger_options_from_config(config):
    """
    Configures the logger, and sets the log directory and first log file for this test run
    """
    init_logger(config)

    Global.CTF_log_dir = os.path.abspath(os.path.expanduser(os.path.expandvars(
        config.get("logging", "results_output_dir", fallback="./results"))))

    Global.test_start_time = time.localtime()
    Global.test_log_dir = os.path.join(Global.CTF_log_dir,
                                       "Run_" + time.strftime("%m_%d_%Y_%H_%M_%S", Global.test_start_time))
    os.makedirs(Global.test_log_dir)

    Global.CTF_log_dir_file = os.path.join(os.path.abspath(Global.test_log_dir),
                                           config.get("logging", "ctf_log_file", fallback="./CTF_Log.log"))


def change_log_file(new_log_file):
    """
    change_log_file function: Change log file to store logging information.
    @param new_log_file: the new file for logger to store logging information.
    @return None
    """
    handler = logging.FileHandler(new_log_file, 'a')
    handler.setFormatter(test_formatter)
    logger.handlers[0].flush()
    logger.handlers[0].close()
    logger.handlers[0] = handler
