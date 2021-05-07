"""
@namespace lib.script_manager
Loads and manages test scripts during a test run
"""

# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2021 United States Government as represented by the
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

from lib.exceptions import CtfTestError
from lib.logger import logger as log, change_log_file
from lib.status_manager import StatusDefs
from lib.ctf_global import Global
from lib.ctf_utility import expand_path


class ScriptManagerConfig:
    """
    Configuration parameters used by the ScriptManager class, obtained from the loaded INI config
    """

    def __init__(self):
        ## Results output directory
        self.regression_dir = expand_path(Global.config.get("logging", "results_output_dir"))

        # Temporary results output directory
        self.script_output_dir = expand_path(Global.config.get("logging", "temp_script_output_dir"))

        # Whether the script manager should reset plugins between scripts (shutdown all loaded plugins,
        # reload and initialize all plugins)
        self.reset_plugins_between_scripts = Global.config.getboolean("core", "reset_plugins_between_scripts")

        # Whether to output results in JSON format
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
        self.regression_summary_file = ""
        self.regression_summary_json_file = ""
        self.curr_regression_dir = ""
        self.curr_script_log_dir = ""
        self.plugin_manager = plugin_manager
        self.status_manager = status_manager
        self.summary_file = None

    def add_script(self, script):
        """
        Adds a script to the list of scripts managed by the script manager
        """
        self.script_list.append(script)

    def run_all_scripts(self):
        """
        Run all added scripts, updating the status packets, and ensuring plugins are reloaded between scripts if needed.
        """
        self.status_manager.set_start_time()
        self.status_manager.set_scripts(self.script_list)

        suite_status = StatusDefs.active
        suite_details = "Running Script"
        self.status_manager.update_suite_status(suite_status, suite_details)

        try:
            # Initialize plugins before running scripts only once in the beginning
            self.plugin_manager.initialize_plugins()

            # Prepare logging files/dirs
            self.prep_logging()

            # Run each script in the script_list sequentially
            results = {
                "Test_Results": []
            }
            test_count = 1
            for script in self.script_list:
                # Create directory to log each script output
                logs_dirname = self.curr_regression_dir + "/logs/" + script.input_file + script.params
                current_time = time.time()
                self.curr_script_log_dir = str("%0s_%0d" % (logs_dirname, current_time))
                Global.current_script_log_dir = self.curr_script_log_dir
                Global.telemetry_watch_list_mids = script.telem_watch_list
                Global.command_watch_list_mids = script.cmd_watch_list

                if self.config.reset_plugins_between_scripts and test_count > 1:
                    # Re-initialize to re-run plugin __init__ function (constructor)
                    self.plugin_manager.reload_plugins()

                    # Run the initialize() function on each plugin
                    self.plugin_manager.initialize_plugins()

                # Start logging in script's log directory
                os.makedirs(self.curr_script_log_dir)
                change_log_file(os.path.join(Global.current_script_log_dir, script.input_file + ".log"))

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

                script.status = StatusDefs.passed if script.num_failed == 0 else StatusDefs.failed

                self.write_summary_line(script)

                if self.config.json_results is True:
                    results["Test_Results"].append({
                        "Status": script.status,
                        "Time": script.time_taken,
                        "Ver_Num": script.test_number,
                        "Req_Num": script.requirements,
                        "Test_Run": script.num_tests,
                        "Test_Passed": script.num_passed,
                        "Test_Failed": script.num_failed,
                        "Test_Error": script.num_error,
                        "Script": script.input_file
                    })

                test_count = test_count + 1

                # If we are resetting plugins between scripts reinitialize all plugins
                if self.config.reset_plugins_between_scripts:
                    self.plugin_manager.shutdown_plugins()

                try:
                    # Revert logging back to CTF main log
                    change_log_file(Global.CTF_log_dir_file)
                except Exception as exception:
                    log.warning("Failed to revert logging to CTF. Does {} still exist?".format(Global.CTF_log_dir_file))
                    raise CtfTestError("Error in run_all_scripts") from exception

                # Wait the configured amount time between scripts for any cleanup to occur
                wait_time = Global.config.getfloat("core", "delay_between_scripts", fallback=1.0)
                log.info("Waiting {} seconds for plugins to cleanup...".format(wait_time))
                Global.time_manager.wait(wait_time)

            # Shutdown all plugins if they were not already shut down between scripts
            if not self.config.reset_plugins_between_scripts:
                self.plugin_manager.shutdown_plugins()

            self.status_manager.finalize_suite_status()
            if self.config.json_results is True:
                with open(self.regression_summary_json_file, "a") as file:
                    json.dump(results, file, indent=4)

        except Exception as exception:
            log.error("Exception: ", exc_info=True)
            suite_status = StatusDefs.error
            suite_details = str(traceback.format_exc())
            self.status_manager.update_suite_status(suite_status, suite_details)
            raise CtfTestError("Error in run_all_scripts") from exception

    def prep_logging(self):
        """
        Prepares logging directories for a CTF test run. Logging directories will include script-specific log
        directories, as well as high-level log files and results summary.
        """
        Global.test_start_time = time.localtime()
        self.curr_regression_dir = os.path.join(self.config.regression_dir, "Run_" + \
                                                time.strftime("%m_%d_%Y_%H_%M_%S", Global.test_start_time))

        Global.test_log_dir = self.curr_regression_dir

        self.regression_summary_file = self.curr_regression_dir + "/results_summary.txt"

        self.regression_summary_json_file = self.curr_regression_dir + "/results_summary.json"

        try:
            os.makedirs(self.curr_regression_dir)
        except OSError as exception:
            log.error("Directory {} could not be created.".format(self.curr_regression_dir))
            raise exception

        try:
            os.makedirs(self.curr_regression_dir + "/logs")
        except OSError as exception:
            log.error("Directory: {} could not be created.".format(self.curr_regression_dir + "/logs"))
            raise exception

        log.debug("Successfully created the test results and log directories at {}".format(self.curr_regression_dir))

        self.summary_file = open(self.regression_summary_file, "w", buffering=10)

        self.summary_file.write(str("%0s | %0s | %0s | %0s | %0s | %0s | %0s | %0s | %0s\n"
                                    % ("Status".ljust(10), "Time (s)".ljust(8), "Verification Number".ljust(30),
                                       "Requirement Verified".ljust(30), "Test Run".ljust(
            8), "Test Passed".ljust(12),
                                       "Test Failed".ljust(12), "Test Error".ljust(12), "Script".ljust(60))))
        self.summary_file.write(
            "------------------------------------------------------------------------------------------------------"
            "------------------------------------------\n")
        self.summary_file.close()

    def write_summary_line(self, summary_line):
        """
        Write an entry to the summary results file(s).
        @note - An entry consists of:
                - Script status (pass/fail)
                - Execution Time
                - Verification Number
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

        formatted_time = "%3.2f" % summary_line.time_taken
        self.summary_file = open(self.regression_summary_file, "a+", buffering=10)
        self.summary_file.write(str("%0s   %0s   %0s   %0s   %0s   %0s   %0s   %0s   %0s\n"
                                    % (str(summary_line.status).ljust(10),
                                       formatted_time.ljust(8),
                                       str(summary_line.test_number).ljust(30),
                                       str(summary_line.requirements).ljust(30),
                                       str(summary_line.num_tests).ljust(8),
                                       str(summary_line.num_passed).ljust(12),
                                       str(summary_line.num_failed).ljust(12),
                                       str(summary_line.num_error).ljust(12),
                                       summary_line.input_file.ljust(60))))
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

    def test_json(self):
        """
        Helper function to test JSON results output
        """
        if not self.regression_summary_json_file:
            return

        with open(self.regression_summary_json_file) as json_file:
            data = json.load(json_file)
            for result in data['Test_Results']:
                print('Status: ', result['Status'])
                print('Time: ', result['Time'])
                print('Ver_Num: ', result['Ver_Num'])
                print('Req_Num: ', result['Req_Num'])
                print('Test_Run: ', result['Test_Run'])
                print('Test_Passed: ', result['Test_Passed'])
                print('Test_Failed: ', result['Test_Failed'])
                print('Test_Error: ',result['Test_Error'])
                print('Script: ',  result['Script'])
