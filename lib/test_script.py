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
import pwd
import time

from lib.Global import Global
from lib.logger import logger as log, log_output
from lib.status import StatusDefs

class TestScript(object):
    def __init__(self):
        self.test_number = None
        self.test_name = None
        self.requirements = None
        self.test_description = None
        self.options = None
        self.telem_watch_list = None
        self.cmd_watch_list = None
        self.tests = []
        self.input_file_path = None
        self.input_file = None
        self.params = ""
        self.status = ""
        self.start_time = 0
        self.time_taken = 0
        self.num_tests = 0
        self.num_passed = 0
        self.num_failed = 0
        self.num_error = 0

    def set_header_info(self, test_number, test_name, requirements, test_description, test_owner, test_setup, verif_timeout):
        self.test_number = test_number
        self.test_name = test_name
        self.requirements = requirements
        self.test_description = test_description
        self.test_owner = test_owner
        self.test_setup = test_setup
        self.verify_timeout = verif_timeout

    def set_options(self, options):
        self.options = options

    def set_watch_lists(self, telem_watch_list, cmd_watch_list):
        self.telem_watch_list = telem_watch_list
        self.cmd_watch_list = cmd_watch_list

    def set_tests(self, tests):
        self.tests = tests

    def run_script(self, status_manager):

        script_status = StatusDefs.active
        script_details = ""

        # Set script as active
        status_manager.update_script_status(script_status, "")

        try:
            self.num_tests = len(self.tests)
            self.logTestProlog()
            self.start_time = time.time()
            for test in self.tests:
                if self.verify_timeout: test.ctf_verification_timeout = self.verify_timeout

                test_status = test.run_test(status_manager)
                if test_status == StatusDefs.aborted:
                    log.error("Aborted Test Script: {}".format(self.input_file))
                    break

            self.time_taken = time.time() - self.start_time
            self.generateTestResults()

        except Exception as e:
            script_status = StatusDefs.error
            status_manager.update_script_status(script_status, "")
            raise

    def logTestProlog(self):
        localtime = time.localtime()
        timeString = time.strftime("%m/%d/%Y / %H:%M:%S", localtime)
        sysinfo = os.uname()
        log.info("Verification Test Name: %s" % self.test_name)
        log.info("Verification Test Number: %s" % self.test_number)
        log.info("Test Conductor: %s" % pwd.getpwuid(os.getuid())[0])
        log.info("Run Date/Time: %s" % timeString)
        log.info("Platform: %s" % sysinfo[3])
        log.info("Requirement Verification Targets: %s" % self.requirements)
        log.info("Test Description : %s" % self.test_description)
        log.info("Input file utilized : %s" % os.path.relpath(self.input_file))

    def generateTestResults(self):
        self.num_tests = len(self.tests)
        self.num_passed = 0
        self.num_failed = 0
        for test in self.tests:
            if test.test_run:
                if test.test_result:
                   self.num_passed += 1
                else:
                   self.num_failed += 1

        self.logTestProlog()
        log.info("Number tests To Run:                %s" % self.num_tests)
        log.info("Number tests Ran:                   %s" % (self.num_passed+self.num_failed))
        log.info("Number tests Passed:                %s" % self.num_passed)
        log.info("Number tests Failed:                %s" % self.num_failed)
        # if self.SkippedCommands > 0:
        #     log.info("Number TrickCFS Commands Skipped:   %s" % self.SkippedCommands)
        # log.runCountTest = self.num_tests
        log.passedTest = self.num_passed
        log.failedTest = self.num_failed
