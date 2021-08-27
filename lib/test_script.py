"""
@namespace lib.test_script
Loads and validates input CTF test scripts. Manages execution of loaded test scripts.
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
import pwd
import time

from lib.exceptions import CtfTestError
from lib.logger import logger as log
from lib.status import StatusDefs


class TestScript:
    """
    The TestScript class represents a CTF test script, storing script data and status.
    """
    def __init__(self):
        """
        Constructor of TestScript Class: Initiate instance properties
        """
        self.test_number = None
        self.test_name = None
        self.requirements = None
        self.test_description = None
        self.options = None
        self.telem_watch_list = None
        self.cmd_watch_list = None
        self.test_owner = None
        self.test_setup = None
        self.verify_timeout = None
        self.tests = []
        self.input_file_path = None
        self.input_file = None
        self.params = ""
        self.status = ""
        self.start_time = 0
        self.exec_time = 0
        self.num_tests = 0
        self.num_passed = 0
        self.num_failed = 0
        self.num_error = 0

    def set_header_info(self, test_number, test_name, requirements, test_description, test_owner, test_setup,
                        verif_timeout):
        """
        Set the TestScript's header information from the input test script file.

        @param test_number: Test number
        @param test_name: Test name
        @param requirements: Requirements validated by this test
        @param test_description: Test Description
        @param test_owner: Test Owner
        @param test_setup: Test Setup
        @param verif_timeout: Test Specific Verification Timeout (Overrides Config Timeout)
        """
        self.test_number = test_number
        self.test_name = test_name
        self.requirements = requirements
        self.test_description = test_description
        self.test_owner = test_owner
        self.test_setup = test_setup
        self.verify_timeout = verif_timeout

    def set_options(self, options):
        """
        Set the TestScript's options from the input test script file.
        @param options: Test Script Options (Dict)
        """
        self.options = options

    def set_watch_lists(self, telem_watch_list, cmd_watch_list):
        """
        Set the TestScript's telemetry and command watch lists.
        @note Telemetry and Command watch list are currently not used by CTF.
        @param telem_watch_list: Test Script Telemetry Watch List
        @param cmd_watch_list: Test Script Command Watch List
        """
        self.telem_watch_list = telem_watch_list
        self.cmd_watch_list = cmd_watch_list

    def set_tests(self, tests):
        """
        Set the list of test cases within this test script
        """
        self.tests = tests

    def run_script(self, status_manager):
        """
        Execute a complete test script, updating the status_manager as needed.
        """
        script_status = StatusDefs.active

        # Set script as active
        status_manager.update_script_status(script_status, "")

        try:
            self.num_tests = len(self.tests)
            self.log_test_header()
            self.start_time = time.time()
            for test in self.tests:
                if self.verify_timeout:
                    test.ctf_verification_timeout = self.verify_timeout

                test_status = test.run_test(status_manager)
                if test_status == StatusDefs.aborted:
                    log.error("Aborted Test Script: {}".format(self.input_file))
                    break

            self.exec_time = time.time() - self.start_time
            self.generate_test_results()

        except Exception as exception:
            script_status = StatusDefs.error
            status_manager.update_script_status(script_status, "Error")
            raise CtfTestError("Error in run_script") from exception

    def log_test_header(self):
        """
        Log the test header (metadata) before beginning test execution
        """
        localtime = time.localtime()
        time_string = time.strftime("%m/%d/%Y / %H:%M:%S", localtime)
        sys_info = os.uname()
        log.info("Verification Test Name: {}".format(self.test_name))
        log.info("Verification Test Number: {}".format(self.test_number))
        log.info("Test Conductor: {}".format(pwd.getpwuid(os.getuid())[0]))
        log.info("Run Date/Time: {}".format(time_string))
        log.info("Platform: {}".format(sys_info[3]))
        log.info("Requirement Verification Targets: {}".format(self.requirements))
        log.info("Test Description : {}".format(self.test_description))
        log.info("Input file utilized : {}".format(os.path.relpath(self.input_file)))

    def generate_test_results(self):
        """
        Generate and Log the test results after test execution
        """
        self.num_tests = len(self.tests)
        self.num_passed = 0
        self.num_failed = 0
        for test in self.tests:
            if test.test_run:
                if test.test_result:
                    self.num_passed += 1
                else:
                    self.num_failed += 1

        self.log_test_header()
        log.info("Number tests To Run:                {}".format(self.num_tests))
        log.info("Number tests Ran:                   {}".format(self.num_passed + self.num_failed))
        log.info("Number tests Passed:                {}".format(self.num_passed))
        log.info("Number tests Failed:                {}".format(self.num_failed))
