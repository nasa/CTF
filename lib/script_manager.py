"""
@namespace lib.script_manager
Loads and manages test scripts during a test run
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


import os
import time
import traceback
import json

from lib import ctf_utility
from lib.exceptions import CtfTestError
from lib.logger import logger as log, change_log_file
from lib.readers.json_script_reader import JSONScriptReader
from lib.status_manager import StatusDefs
from lib.ctf_global import Global


class ScriptManagerConfig:
    """
    Configuration parameters used by the ScriptManager class, obtained from the loaded INI config
    """

    def __init__(self):
        """
        Constructor of ScriptManagerConfig class. Initialize properties from INI file
        """

        # Whether the script manager should reset plugins between scripts (shutdown all loaded plugins,
        # reload and initialize all plugins)
        self.reset_plugins_between_scripts = Global.config.getboolean("core", "reset_plugins_between_scripts")

        self.json_results = Global.config.getboolean("logging", "json_results")


class ScriptManager:
    """
    The ScriptManager class adds and manages all loaded CTF test scripts.
    @note - The script manager's add_script is called with each script loaded by the JSONScriptReader.
    @note - The script manager handles execution of test scripts, including logging the results and managing the
    test suite status

    @param plugin_manager: Initialized instance of the plugin manager, used to interact with the loaded plugins
    @param status_manager: Initialized instance of the status manager, used to send status to external listeners
    """

    def __init__(self, plugin_manager, status_manager):
        self.script_list = []
        self.config = ScriptManagerConfig()
        self.regression_summary_file_path = ""
        self.regression_summary_json_file_path = ""
        self.curr_script_log_dir_path = ""
        self.plugin_manager = plugin_manager
        self.status_manager = status_manager
        self.summary_file = None

    def add_script(self, script):
        """
        Adds a script to the list of scripts managed by the script manager
        """
        self.script_list.append(script)

    def add_script_file(self, file):
        """
        Adds a script file to the list of scripts. If the file is not valid, skip it.
        """
        script_reader = JSONScriptReader(file)
        if script_reader.valid_script:
            self.add_script(script_reader.script)
            log.info("Loaded Script: {}".format(script_reader.input_script_path))
        else:
            log.warning("Invalid Input Test JSON Script: {}. Skipping.".format(file))

    def run_all_scripts(self):
        """
        Run all added scripts, updating the status packets, and ensuring plugins are reloaded between scripts if needed.
        """
        self.status_manager.start()
        self.status_manager.set_scripts(self.script_list)

        suite_status = StatusDefs.active
        suite_details = "Running Script"
        self.status_manager.update_suite_status(suite_status, suite_details)

        try:
            self.plugin_manager.initialize_plugins()

            self.prep_logging()

            # Run each script in the script_list sequentially
            results = {
                "Test_Results": []
            }
            test_count = 1
            wait_time = Global.config.getfloat("core", "delay_between_scripts", fallback=1.0)

            for script in self.script_list:
                # Create directory to log each script output
                logs_dirname = Global.test_log_dir + "/logs/" + script.input_file + script.params
                current_time = time.time()
                self.curr_script_log_dir_path = str("%0s_%0d" % (logs_dirname, current_time))
                Global.current_script_log_dir = self.curr_script_log_dir_path

                if self.config.reset_plugins_between_scripts and test_count > 1:
                    # Re-initialize to re-run plugin __init__ function (constructor)
                    self.plugin_manager.reload_plugins()

                    # Run the initialize() function on each plugin
                    self.plugin_manager.initialize_plugins()

                # Start logging in script's log directory
                os.makedirs(self.curr_script_log_dir_path)
                change_log_file(os.path.join(Global.current_script_log_dir, script.input_file + ".log"))

                # update build-in variable
                ctf_utility.set_variable("_CTF_LOG_DIR", "=", self.curr_script_log_dir_path, "string")

                try:
                    script.run_script(self.status_manager)
                except CtfTestError:
                    script.status = StatusDefs.failed
                    self.write_summary_line(script)
                    log.error("Failed to execute script: {}".format(script.input_file))

                # When finished, update the script status
                script_status = StatusDefs.passed
                script_details = "Running"
                # If any tests have failed, script has failed
                for test in script.tests:
                    if test.test_result is not True:
                        script_status = StatusDefs.failed
                        script_details = "One or more tests failed"

                self.status_manager.update_script_status(script_status, script_details)

                self.status_manager.end_script()

                script.status = StatusDefs.failed if script.failed_tests else StatusDefs.passed

                self.write_summary_line(script)

                if self.config.json_results is True:
                    results["Test_Results"].append({
                        "Status": script.status,
                        "Time": script.exec_time,
                        "Test_Num": script.test_number,
                        "Req_Num": script.requirements,
                        "Tests_Run": script.num_tests,
                        "Tests_Passed": script.num_passed,
                        "Tests_Failed": len(script.failed_tests),
                        "Tests_Error": script.num_error,
                        "Script": script.input_file
                    })

                test_count = test_count + 1

                if self.config.reset_plugins_between_scripts:
                    self.plugin_manager.shutdown_plugins()

                try:
                    # Revert logging back to CTF main log
                    change_log_file(Global.CTF_log_dir_file)
                except Exception as ex:
                    log.warning("Failed to revert logging to CTF. Does {} still exist?".format(Global.CTF_log_dir_file))
                    raise CtfTestError("Error in run_all_scripts") from ex

                log.info("Test execution complete. Waiting {} seconds for plugins to clean up...".format(wait_time))
                Global.time_manager.wait(wait_time)

            if not self.config.reset_plugins_between_scripts:
                self.plugin_manager.shutdown_plugins()

            self.status_manager.finalize_suite_status()
            if self.config.json_results is True:
                with open(self.regression_summary_json_file_path, "a") as file:
                    json.dump(results, file, indent=4)

        except Exception as ex:
            log.error("Exception: ", exc_info=True)
            suite_status = StatusDefs.error
            suite_details = str(traceback.format_exc())
            self.status_manager.update_suite_status(suite_status, suite_details)
            raise CtfTestError("Error in run_all_scripts") from ex

    def prep_logging(self):
        """
        Prepares logging directories for a CTF test run. Logging directories will include script-specific log
        directories, as well as high-level log files and results summary.
        """
        self.regression_summary_file_path = Global.test_log_dir + "/results_summary.txt"
        self.regression_summary_json_file_path = Global.test_log_dir + "/results_summary.json"

        self.summary_file = open(self.regression_summary_file_path, "w", buffering=10)
        self.summary_file.write(str("%0s | %0s | %0s | %0s | %0s | %0s | %0s | %0s | %0s\n"
                                    % ("Status".ljust(10),
                                       "Time (s)".ljust(8),
                                       "Test Script Number".ljust(50),
                                       "Requirements Verified".ljust(50),
                                       "Tests Run".ljust(12),
                                       "Tests Passed".ljust(12),
                                       "Tests Failed".ljust(12),
                                       "Tests Error".ljust(12),
                                       "Script".ljust(50))))

        self.summary_file.write("-" * 200 + "\n")
        self.summary_file.close()

    def write_summary_line(self, script):
        """
        Write an entry to the summary results file(s).
        @note - An entry consists of:
                - Script status (pass/fail)
                - Execution Time
                - Test Script Number
                - Requirements Verified
                - # of tests that ran
                - # of tests that passed
                - # of tests the failed
                - # of tests with an error
                - Script input file (.JSON)
        """
        if self.summary_file is not None:
            try:
                self.summary_file.close()
            except IOError:
                log.error("Failed to close CTF results summary file!")
                return

        formatted_time = "%3.2f" % script.exec_time
        self.summary_file = open(self.regression_summary_file_path, "a+", buffering=10)
        self.summary_file.write(str("%0s   %0s   %0s   %0s   %0s   %0s   %0s   %0s   %0s\n"
                                    % (str(script.status).ljust(10),
                                       formatted_time.ljust(8),
                                       str(script.test_number).ljust(50),
                                       str(script.requirements).ljust(50),
                                       str(script.num_tests).ljust(12),
                                       str(script.num_passed).ljust(12),
                                       str(len(script.failed_tests)).ljust(12),
                                       str(script.num_error).ljust(12),
                                       script.input_file.ljust(50))))
        self.summary_file.close()

    def __del__(self):
        """
        Destructor implementation to close summary file on deletion of the ScriptManager
        """
        if self.summary_file:
            try:
                self.summary_file.close()
            except IOError as exception:
                log.error("Failed to write CTF results summary file!")
                log.error(exception)
