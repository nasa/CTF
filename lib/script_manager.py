"""
@namespace lib.script_manager
Load and manage test scripts during a test run
"""

# =========================================================================================
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
# distributed and modified only pursuant to the terms of that agreement.
# See the License for the specific language governing permissions and limitations under the
# License at https://software.nasa.gov/ .
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either expressed or implied.
#
# Copyright © 2019-2026 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# File: script_manager.py
#
# Purpose: This file defines ScriptManager which loads and manages test scripts during test run.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================


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
        self.skipped_script_list = []
        self.config = ScriptManagerConfig()
        self.regression_summary_file_path = ""
        self.regression_summary_json_file_path = ""
        self.curr_script_log_dir_path = ""
        self.plugin_manager = plugin_manager
        self.status_manager = status_manager
        self.summary_file = None
        self.aggregated_metrics = {}

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
            if self.validate_instructions(script_reader.script):
                self.add_script(script_reader.script)
                log.info("Loaded Script: {}".format(script_reader.input_script_path))
        else:
            # if file has invalid json format, script_reader does not have 'script' attribute
            if hasattr(script_reader, 'script'):
                if not script_reader.functions_only_script:
                    self.skipped_script_list.append(script_reader.script)
                    log.error("Skipping invalid test script: {} ...".format(file))
                else:
                    log.warning("Skipping function-only test script: {} ...".format(file))

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
                "Test_Results": [],
                "Results_Summary": [],
                "ExpectedFails_Summary": []
            }
            test_count = 1
            wait_time = Global.config.getfloat("core", "delay_between_scripts", fallback=1.0)

            for i, script in enumerate(self.script_list):
                # Create directory to log each script output
                logs_dirname = Global.test_log_dir + "/logs/" + script.input_file + script.params
                current_time = time.time()
                self.curr_script_log_dir_path = str("%0s_%0d" % (logs_dirname, current_time))
                Global.current_script_log_dir = self.curr_script_log_dir_path
                log.info("Ready to run test script {}".format(script.input_file))

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
                except CtfTestError as ex:
                    log.error(ex)

                # When finished, update the script status
                script_details = "Running"
                # If any tests have failed, script has failed
                for test in script.tests:
                    if test.test_result is not True:
                        script.status = StatusDefs.failed
                        script_details = "One or more tests failed"

                if script.failed_tests:
                    script.status = StatusDefs.failed

                if script.status not in [StatusDefs.failed, StatusDefs.aborted, StatusDefs.error,
                                         StatusDefs.timeout, StatusDefs.stopped]:
                    script.status = StatusDefs.passed

                self.status_manager.update_script_status(script.status, script_details)

                self.status_manager.end_script()

                log.debug("Going to update results summary file ... ")
                self.write_summary_line(script)
                self.append_json_results(script, results)

                test_count = test_count + 1

                if self.config.reset_plugins_between_scripts:
                    self.plugin_manager.shutdown_plugins()

                try:
                    # Revert logging back to CTF main log
                    change_log_file(Global.CTF_log_dir_file)
                except Exception as ex:
# Cannot be reached - change_log_file does not throw an exception, even with an invalid log path/file
                    log.warning("Failed to revert logging to CTF. Does {} still exist?".format(Global.CTF_log_dir_file))
                    raise CtfTestError("Error in run_all_scripts") from ex

                prompt_str = "to run the next test" if i < (len(self.script_list) - 1) else "to clean up plugins"
                log.info("Test execution complete. Waiting {} seconds {} ...".format(wait_time, prompt_str))
                Global.time_manager.wait(wait_time)

            for script in self.skipped_script_list:
                script.status = "skipped"
                script.num_error = 1
                self.write_summary_line(script)
                self.append_json_results(script, results)

            if not self.config.reset_plugins_between_scripts:
                self.plugin_manager.shutdown_plugins()

            self.status_manager.finalize_suite_status()

            # Collect aggregated metrics
            self.calculate_summary_metrics()
            # Write aggregated summary to both text and json results files
            self.write_test_suite_summary()
            self.append_summary_metrics_to_json_results(results)

            expected_fail_summary = self.get_expected_fails_summary()
            self.write_expected_fails_summary(expected_fail_summary)
            self.append_expected_fails_summary_to_json_results(expected_fail_summary, results)

            if self.config.json_results is True:
                with open(self.regression_summary_json_file_path, "a") as file:
                    json.dump(results, file, indent=4)

        except Exception as ex:
            log.error("Exception: ", exc_info=True)
            suite_status = StatusDefs.error
            suite_details = str(traceback.format_exc())
            self.status_manager.update_suite_status(suite_status, suite_details)
            raise CtfTestError("Error in run_all_scripts") from ex

    def append_json_results(self, script, results):
        """
        Append the test script result to the json results object.
        """
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

    def append_summary_metrics_to_json_results(self, results):
        """
        Append the aggregated test metrics to the json results object.
        """
        if self.config.json_results is True:
            results["Results_Summary"].append({
                "Runtime_Secs": self.aggregated_metrics["runtime_secs"],
                "TestScripts_Passed": self.aggregated_metrics["num_passed_scripts"],
                "TestScripts_Failed": self.aggregated_metrics["num_failed_scripts"],
                "TestScripts_Skipped": len(self.skipped_script_list),
                "Num_Tests": self.aggregated_metrics["num_tests"],
                "Tests_Passed": self.aggregated_metrics["num_passed_tests"],
                "Tests_Failed": self.aggregated_metrics["num_failed_tests"],
                "Tests_Error": self.aggregated_metrics["num_script_error"],
                "TestScripts_Run": len(self.script_list)
            })

    def append_expected_fails_summary_to_json_results(self, expected_fail_summary, results):
        """
        Append the expected fails summary to the json results object.
        """
        if self.config.json_results is True:
            results["ExpectedFails_Summary"].extend(expected_fail_summary)

    def validate_instructions(self, script):
        """
        Returns true if all instructions in provided TestScript are valid and processable by a loaded plugin.
        Raises exception otherwise.
        """
        # Grab all unique instructions
        instructions = set()
        for test in script.tests:
            for instruction in test.instructions:
                # Grab the instruction string from the object
                instructions.add(instruction.command['instruction'])

        # Ignore ExpectedFail instruction which is not handled by a plugin.
        instructions.discard("ExpectedFail")

        # Verify each instruction is supported by a plugin
        for instruction in instructions:
            plugin_for_instruction = self.plugin_manager.find_plugin_for_command(instruction)
            if plugin_for_instruction is None:
                log.error('No suitable plugin found for instruction: "{}"'.format(instruction))
                raise CtfTestError('Unsupported instruction: "{}"'.format(instruction))

        return True

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
                - # of tests that failed
                - # of tests with an error
                - Script input file (.JSON)
        """
        if self.summary_file is not None:
            try:
                self.summary_file.close()
                self.summary_file = None
            except IOError:
                log.error("Failed to close CTF results summary file!")
                return

        formatted_time = "%3.2f" % script.exec_time
        try:
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
            self.summary_file = None
        except IOError:
            log.error("Failed to write to CTF results summary file!")

    def calculate_summary_metrics(self):
        """
        Calculates and stores cummulative test run information
        """
        # Calculate test metrics
        runtime_secs = 0
        num_tests = 0
        num_passed_tests = 0
        num_failed_tests = 0
        num_script_error = 0

        for script in self.script_list:
            runtime_secs += script.exec_time
            num_tests += script.num_tests
            num_passed_tests += script.num_passed
            num_failed_tests += len(script.failed_tests)
            num_script_error += script.num_error

        num_passed_scripts = sum(1 for script in self.script_list if script.status == StatusDefs.passed)
        num_failed_scripts = sum(1 for script in self.script_list if script.status == StatusDefs.failed)

        # Store metrics in dictionary
        self.aggregated_metrics["runtime_secs"] = runtime_secs
        self.aggregated_metrics["num_tests"] = num_tests
        self.aggregated_metrics["num_passed_tests"] = num_passed_tests
        self.aggregated_metrics["num_failed_tests"] = num_failed_tests
        self.aggregated_metrics["num_script_error"] = num_script_error
        self.aggregated_metrics["num_passed_scripts"] = num_passed_scripts
        self.aggregated_metrics["num_failed_scripts"] = num_failed_scripts

    def write_test_suite_summary(self):
        """
        Writes cumulative run information to the end of the results file.

        @note: calculate_summary_metrics() needs to be called prior to calling this function.
        """
        if not self.aggregated_metrics:
            log.error("Aggregated metrics must be calculated before being written.")
            return

        if self.summary_file is not None:
            try:
                self.summary_file.close()
                self.summary_file = None
            except IOError:
                log.error("Failed to close CTF results summary file!")
                return

        runtime_secs = self.aggregated_metrics["runtime_secs"]
        runtime_mins = runtime_secs / 60
        formatted_times = ("%3.2f" % runtime_mins,"%3.2f" % runtime_secs)
        runtime_summary = "{} mins ({} seconds)".format(formatted_times[0], formatted_times[1])

        # Write results
        try:
            self.summary_file = open(self.regression_summary_file_path, "a+", buffering=10)
            self.summary_file.write("\n" + ("-" * 200) + "\n")

            self.summary_file.write(str("%0s   %0s   %0s   %0s   %0s   %0s"
                                        % ("Totals:   ",
                                        runtime_summary.ljust(114),
                                        str(self.aggregated_metrics["num_tests"]).ljust(12),
                                        str(self.aggregated_metrics["num_passed_tests"]).ljust(12),
                                        str(self.aggregated_metrics["num_failed_tests"]).ljust(12),
                                        str(self.aggregated_metrics["num_script_error"]).ljust(12))))

            self.summary_file.write("\n\n")
            self.summary_file.write("Scripts run".ljust(12) + ":  {} \n".format(len(self.script_list)))
            self.summary_file.write("Run result".ljust(12) +  ":  {} passed | {} failed | {} skipped \n".
                                    format(self.aggregated_metrics["num_passed_scripts"],
                                        self.aggregated_metrics["num_failed_scripts"],
                                        len(self.skipped_script_list)))

            self.summary_file.close()
            self.summary_file = None
        except IOError:
            log.error("Failed to write aggregate metrics to CTF results summary file!")

    def get_expected_fails_summary(self):
        """
        Generates a summary of all expected fails in test scripts.
        """
        expected_fail_summary = []
        # Expected fails are summarized on a per test-script (not per-test) basis.
        for script in self.script_list:
            has_expected_fails = False
            has_failed_expected_fail_instructions = False
            associated_crs_drs = []
            for test in script.tests:
                for instruction in test.instructions:
                    if "ExpectedFail" in instruction.command['instruction']:
                        has_expected_fails = True
                        if instruction.execution_result is False:
                            has_failed_expected_fail_instructions = True
                        # Retrieve associated CRs/DRs specified in the instruction parameters, if applicable.
                        instruction_crs_drs = instruction.command.get("data", {}).get("associated_crs_drs", "")
                        if instruction_crs_drs:
                            associated_crs_drs.append(instruction_crs_drs)

            # Add summary for each script that contains expected fails
            if has_expected_fails:
                associated_crs_drs_str = ", ".join(f"({x})" for x in associated_crs_drs)
                failed_expected_fail_str = "One or more expected fail instructions did not behave as expected"
                passed_expected_fail_str = "All expected fail instructions behaved as expected"
                summary_str = failed_expected_fail_str if has_failed_expected_fail_instructions \
                    else passed_expected_fail_str

                expected_fail_summary.append({
                    "Test Script Name": script.input_file,
                    "Summary": summary_str,
                    "Associated CRs/DRs": associated_crs_drs_str
                })

        return expected_fail_summary

    def write_expected_fails_summary(self, expected_fail_summary):
        """
        Writes a summary of expected fails to the results summary file.
        """
        if not expected_fail_summary:
            return

        if self.summary_file is not None:
            try:
                self.summary_file.close()
                self.summary_file = None
            except IOError:
                log.error("Failed to close CTF results summary file!")
                return

        try:
            self.summary_file = open(self.regression_summary_file_path, "a+", buffering=10)

            # Write the summary to the file
            self.summary_file.write("\n" + "<" +("-" * 198) + ">" + "\n")
            self.summary_file.write("Expected Fail(s) Summary: \n\n")

            # Column widths
            name_w    = 45
            summary_w = 70
            cr_dr_w   = 30

            # Header row
            header = ("%0s | %0s | %0s \n" % (
                "Test Script Name".ljust(name_w),
                "Summary".ljust(summary_w),
                "Associated CRs/DRs".ljust(cr_dr_w)
            ))

            # Separator length
            separator = "-" * (name_w + summary_w + cr_dr_w + 3 * 2)

            # Write header + separator
            self.summary_file.write(header)
            self.summary_file.write(separator + "\n")

            for exp_fail_row in expected_fail_summary:
                line = ("%0s | %0s | %0s\n" % (
                    str(exp_fail_row["Test Script Name"]).ljust(name_w),
                    str(exp_fail_row["Summary"]).ljust(summary_w),
                    str(exp_fail_row["Associated CRs/DRs"]).ljust(cr_dr_w)
                ))
                self.summary_file.write(line)

            self.summary_file.write(separator + "\n")
            self.summary_file.close()
            self.summary_file = None
        except IOError:
            log.error("Failed to write expected fail summary to CTF results summary file!")

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
