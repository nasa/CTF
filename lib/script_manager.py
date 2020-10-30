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


import os
import time
import traceback
import json

from lib.logger import logger as log, change_log_file
from lib.status_manager import StatusManager, StatusDefs
from lib.Global import Global, Config, expand_path

try:
    import junit_xml

    junit_installed = True
except ImportError:
    junit_installed = False


class ScriptManagerConfig(object):
    def __init__(self):
        self.regression_dir = expand_path(Config.get("logging", "results_output_dir"))
        self.script_output_dir = expand_path(Config.get("logging", "temp_script_output_dir"))
        self.reset_plugins_between_scripts = Config.getboolean("core", "reset_plugins_between_scripts")
        self.json_results = Config.getboolean("logging", "json_results")


class ScriptManager(object):
    def __init__(self, plugins, status_manager):
        self.script_list = []
        self.config = ScriptManagerConfig()
        self.regression_summary_file = ""
        self.regression_summary_json_file = ""
        self.curr_regression_dir = ""
        self.curr_script_log_dir = ""
        self.plugins = plugins
        self.status_manager = status_manager
        self.summary_file = None


    def add_script(self, script):
        self.script_list.append(script)

    def run_all_scripts(self):
        self.status_manager.set_start_time()
        self.status_manager.set_scripts(self.script_list)

        suite_status = StatusDefs.active
        suite_details = "Running Script"
        self.status_manager.update_suite_status(suite_status, suite_details)

        try:
            # Initialize plugins before running scripts only once in the beginning
            self.plugins.initialize_plugins()

            # Prepare logging files/dirs
            self.prep_logging()

            # Run each script in the script_list sequentially
            results = {
                "Test_Results": []
            }
            test_count = 1
            for s in self.script_list:
                # Create directory to log each script output
                logs_dirname = self.curr_regression_dir + "/logs/" + s.input_file + s.params
                t = time.time()
                self.curr_script_log_dir = str("%0s_%0d" % (logs_dirname, t))
                Global.current_script_log_dir = self.curr_script_log_dir
                Global.telemetry_watch_list_mids = s.telem_watch_list
                Global.command_watch_list_mids = s.cmd_watch_list

                if self.config.reset_plugins_between_scripts and test_count > 1:
                    # Re-initialize to re-run plugin __init__ function (constructor)
                    self.plugins.reload_plugins()

                    # Run the initialize() function on each plugin
                    self.plugins.initialize_plugins()

                # Start logging in script's log directory
                os.makedirs(self.curr_script_log_dir)
                change_log_file(os.path.join(Global.current_script_log_dir, s.input_file + ".log"))

                try:
                    s.run_script(self.status_manager)
                except Exception as E:
                    s.status = StatusDefs.failed
                    self.write_summary_line(s)
                    raise

                # When finished, update the script status
                script_status = StatusDefs.passed
                script_details = "Running"
                # If any tests have failed, script has failed
                for test in s.tests:
                    if test.test_result is not True:
                        script_status = StatusDefs.failed
                        script_details = "One or more tests failed"

                self.status_manager.update_script_status(script_status, script_details)

                self.status_manager.end_script()

                s.status = StatusDefs.passed if s.num_failed == 0 else StatusDefs.failed
                formatted_time = "%3.2f"%s.time_taken

                self.write_summary_line(s)

                if self.config.json_results is True:
                    results["Test_Results"].append({
                        "Status": s.status,
                        "Time": s.time_taken,
                        "Ver_Num": s.test_number,
                        "Req_Num": s.requirements,
                        "Test_Run": s.num_tests,
                        "Test_Passed": s.num_passed,
                        "Test_Failed": s.num_failed,
                        "Test_Error": s.num_error,
                        "Script": s.input_file
                    })

                test_count = test_count + 1

                # If we are resetting plugins between scripts reinitialize all plugins
                if self.config.reset_plugins_between_scripts:
                    self.plugins.shutdown_plugins()

                try:
                    # Revert logging back to CTF main log
                    change_log_file(Global.CTF_log_dir_file)
                except Exception as E:
                    log.warn("Failed to revert logging to CTF. Does {} still exist?".format(Global.CTF_log_dir_file))

                # Wait the configured amount time between scripts for any cleanup to occur
                wait_time = Config.getfloat("core", "delay_between_scripts", fallback=1.0)
                log.info("Waiting {} seconds for plugins to cleanup...".format(wait_time))
                Global.time_manager.wait(wait_time)

            #Shutdown all plugins if they were not already shut down between scripts
            if not self.config.reset_plugins_between_scripts:
                self.plugins.shutdown_plugins()

            self.status_manager.finalize_suite_status()
            if self.config.json_results is True:
                with open(self.regression_summary_json_file, "a") as file:
                    json.dump(results, file, indent=4)

        except Exception as e:
            log.error("Exception: ", exc_info=True)
            suite_status = StatusDefs.error
            suite_details = str(traceback.format_exc())
            self.status_manager.update_suite_status(suite_status, suite_details)
            raise

    def prep_logging(self):
        Global.test_start_time = time.localtime()
        self.curr_regression_dir = os.path.join(self.config.regression_dir, "Run_" + \
                             time.strftime("%m_%d_%Y_%H_%M_%S", Global.test_start_time))

        Global.test_log_dir = self.curr_regression_dir

        self.regression_summary_file = self.curr_regression_dir + "/results_summary.txt"

        self.regression_summary_json_file = self.curr_regression_dir + "/results_summary.json"

        try:
            os.makedirs(self.curr_regression_dir)
        except Exception as e:
            log.error("Directory %s could not be created." % self.curr_regression_dir)
            raise e
            pass

        try:
            os.makedirs(self.curr_regression_dir + "/logs")
        except Exception as e:
            log.error("Directory %s could not be created." % self.curr_regression_dir + "/logs")
            raise e
            pass

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

    def write_summary_line(self, s):
        if self.summary_file is not None:
            try:
                self.summary_file.close()
            except:
                pass
        formatted_time = "%3.2f" % s.time_taken
        self.summary_file = open(self.regression_summary_file, "a+", buffering=10)
        self.summary_file.write(str("%0s   %0s   %0s   %0s   %0s   %0s   %0s   %0s   %0s\n"
                                    % (str(s.status).ljust(10),
                                       formatted_time.ljust(8),
                                       str(s.test_number).ljust(30),
                                       str(s.requirements).ljust(30),
                                       str(s.num_tests).ljust(8),
                                       str(s.num_passed).ljust(12),
                                       str(s.num_failed).ljust(12),
                                       str(s.num_error).ljust(12),
                                       s.input_file.ljust(60))))
        self.summary_file.close()

    def __del__(self):
        if self.summary_file:
            try:
                self.summary_file.close()
            except Exception as e:
                log.error("Failed to write CTF results summary file!")
                log.error(e)

    def test_json(self):
        with open(self.regression_summary_json_file) as json_file:
            data = json.load(json_file)
            for p in data['Test_Results']:
                print('Status: ' + p['Status'])
                print('Time: ' + p['Time'])
                print('Ver_Num: ' + p['Ver_Num'])
                print('Req_Num: ' + p['Req_Num'])
                print('Test_Run: ' + p['Test_Run'])
                print('Test_Passed: ' + p['Test_Passed'])
                print('Test_Failed: ' + p['Test_Failed'])
                print('Test_Error: ' + p['Test_Error'])
                print('Script: ' + p['Script'])
