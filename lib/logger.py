# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2020 United States Government as represented by the
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
import types
import shutil
from lib.Global import Global, Config, expand_path



try:
    import colorlog

    have_colorlog = True
except ImportError:
    have_colorlog = False

TEST_PASS = 21
TEST_FAIL = 22
TEST_PASS_CONT = 5
TEST_FAIL_CONT = 6

Test_Fail_List = []

# this file needs to be static so that all scripts will log to the same file
# copy this file to a different name after the main test script is finished

log_outputDir = ""
log_output = ""
#shutil.rmtree(log_outputDir, ignore_errors=True)
#log_output = log_outputDir + "/test_framework_output.log"


def set_logger_options_from_config():
    log_outputDir = expand_path(Config.get("logging", "temp_script_output_dir", fallback="./temp"))
    shutil.rmtree(log_outputDir, ignore_errors=True)
    log_output = os.path.join(os.path.abspath(log_outputDir), Config.get("logging", "ctf_log_file", fallback="./CTF_Log.log"))
    Global.CTF_log_dir = os.path.abspath(log_outputDir)
    Global.CTF_log_dir_file = log_output
    if (os.path.exists(Global.CTF_log_dir)):
        shutil.rmtree(Global.CTF_log_dir, ignore_errors=True)
    os.makedirs(Global.CTF_log_dir)

    change_log_file(Global.CTF_log_dir_file)


logformat = '[%(asctime)s] %(module)-32s(%(lineno)-3d) *** %(levelname)s: %(message)s'

''' Overwrite the formatTime method to get exactly what we want '''



class testFormatter(logging.Formatter):
    converter = dt.datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime('%H:%M:%S')
            s = "%s.%03d" % (t, record.msecs)
        return s


# instantiate custom formatter
logformatter = testFormatter(logformat)

# Install colorlog (pip install colorlog) to use colored logs for console
if have_colorlog:
    log_colors = {'DEBUG': 'white', 'INFO': 'bold_white',
                  'TEST_PASS': 'green', 'TEST_FAIL': 'red',
                  'WARNING': 'bold_yellow', 'ERROR': 'bold_yellow',
                  'CRITICAL': 'bold_red', 'TEST_PASS_CONT': 'green', 'TEST_FAIL_CONT': 'red'}
    consoleformat = '%(log_color)s%(levelname)-9s%(reset)s | %(message)s%(reset)s'
    consoleformatter = colorlog.ColoredFormatter(consoleformat, log_colors=log_colors)
else:
    consoleformatter = logformatter

mytimeformat = '%H:%M:%S'

# Add Test logger level
logging.addLevelName(TEST_PASS, "TEST_PASS")
logging.addLevelName(TEST_FAIL, "TEST_FAIL")
logging.addLevelName(TEST_PASS_CONT, "TEST_PASS_CONT")
logging.addLevelName(TEST_FAIL_CONT, "TEST_FAIL_CONT")

# TODO - Utilize log_error for counting test instruction failures and other errors. Possibly override base
#        log.error.

def log_error(self, msg, *args, **kwargs):
    self.runCountError += 1
    self.error(msg, *args, **kwargs)


def test(self, passed, cont, msg, *args, **kwargs):
    if self.report:
        self.runCountTest += 1
    if cont:
        if passed:
            if self.isEnabledFor(TEST_PASS_CONT):
                self._log(TEST_PASS_CONT, msg, args, **kwargs)
        else:
            if self.isEnabledFor(TEST_FAIL_CONT):
                self._log(TEST_FAIL_CONT, msg, args, **kwargs)
                Test_Fail_List.append([msg, args])

    else:
        if passed:
            if self.isEnabledFor(TEST_PASS):
                self._log(TEST_PASS, msg, args, **kwargs)
        else:
            if self.isEnabledFor(TEST_FAIL):
                self._log(TEST_FAIL, msg, args, **kwargs)
                Test_Fail_List.append([msg, args])
    """
    if self.report:
        if passed:
            self.passedTest+=1
        else:
            self.failedTest+=1
    """
    return passed


logging.Logger.test = test
logging.Logger.log_error = log_error

logging.Logger.runCountTest = 0
logging.Logger.runCountError = 0
logging.Logger.passedTest = 0
logging.Logger.failedTest = 0
logging.Logger.report = True


# Print new line(s)
def log_newline(self, how_many_lines=1):
    # Switch handler, output a blank line
    self.removeHandler(self.console_handler)
    self.addHandler(self.blank_handler)
    for i in range(how_many_lines):
        self.info('')

    # Switch back
    self.removeHandler(self.blank_handler)
    self.addHandler(self.console_handler)


# create basic config
logging.basicConfig(level=Global.log_level,
                    format=logformat,
                    datefmt=mytimeformat,
                    filename=log_output,
                    filemode='a')

# Create new line handler
blank_handler = logging.StreamHandler()
blank_handler.setLevel(logging.INFO)
blank_handler.setFormatter(logging.Formatter(fmt=''))

# create config for stdout

console_handler = logging.StreamHandler()
console_handler.setLevel(TEST_PASS_CONT)
console_handler.setFormatter(consoleformatter)
logger = logging.getLogger()
logger.addHandler(console_handler)
logger.console_handler = console_handler
logger.blank_handler = blank_handler
logger.newline = types.MethodType(log_newline, logger)

# set default logger to use the logformatter
logger.handlers[0].setFormatter(logformatter)


def enableContinuousLogPassMsg():
    logging.disable(logging.NOTSET)


def enableContinuousLogFailMsg():
    logging.disable(logging.NOTSET)
    logging.disable(TEST_PASS_CONT)


def disableContinuousLogPassMsg():
    logging.disable(TEST_PASS_CONT)


def disableContinuousLogFailMsg():
    logging.disable(TEST_FAIL_CONT)


def shutdownlogging():
    logging.shutdown()

def change_log_file(new_log_file):
    fileh = logging.FileHandler(new_log_file, 'a')
    fileh.setFormatter(logformatter)
    logger.handlers[0].flush()
    logger.handlers[0].close()
    logger.handlers[0] = fileh  # set the new handler