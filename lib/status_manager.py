"""
@namespace lib.status_manager
Publishes CTF status messages over a UDP socket (utilized by the CTF editor)
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
import traceback
import socket
import json
import time

from lib.status import StatusDefs, ObjectFactory
from lib.logger import logger as log


class StatusManager:
    """
    The StatusManager class established a status stream with the current test suite status. The status packets are sent
    over a UDP socket over the specified port. Clients listening on that port will receive periodic CTF status messages
    during test execution

    @param ip_address: IP of the external listener to connect to
    @param: port: Port used by the external listener to receive status messages
    """

    def __init__(self, ip_address="127.0.0.1", port=None):
        """
        Constructor of StatusManager Class: initiate instance properties.
        """
        self.status = None
        self.script_index = 0
        self.test_index = 0
        self.command_index = 0
        self.ip_address = ip_address
        self.port = port
        self.socket = None
        self.start_time = None

    def start(self):
        """
        Set the start time of test suite execution in the status message.
        """
        self.start_time = time.time()

    def set_scripts(self, scripts):
        """
        Set the script status entry for each script with default values
        """
        self.status = self.blank_status_msg(scripts)

    @staticmethod
    def blank_status_msg(scripts):
        """
        Get a blank status message that contains status objects for each script loaded by CTF
        """
        status = ObjectFactory.create_object("SuiteStatus")
        for script in scripts:
            script_status = ObjectFactory.create_object("ScriptStatus")
            script_status["path"] = script.input_file
            script_status["test_script_number"] = script.test_name
            script_status["status"] = StatusDefs.waiting
            script_status["details"] = ""
            for test in script.tests:
                test_status = ObjectFactory.create_object("TestStatus")
                test_status["test_number"] = test.test_info["test_number"]
                test_status["status"] = StatusDefs.waiting
                test_status["details"] = ""
                test_status["description"] = test.test_info.get("description", "")
                for command_obj in test.instructions:
                    command_status = ObjectFactory.create_object("InstructionStatus")
                    command_status["instruction"] = command_obj.command["instruction"]
                    command_status["wait"] = command_obj.command.get("wait", 0)

                    # command_status["data"] = self.sanitize_data(c.command.get("data")) or {}
                    command_status["data"] = command_obj.command.get("data")

                    command_status["status"] = StatusDefs.waiting
                    command_status["details"] = ""
                    command_status["description"] = command_obj.command.get("description", "")
                    test_status["instructions"].append(command_status)
                script_status["tests"].append(test_status)
            status["scripts"].append(script_status)
        return status

    def update_suite_status(self, status, details):
        """
        Given an updated status (and details), update the suite status with the latest state.
        """
        status = self.sanitize_param(status)
        details = self.sanitize_param(details)

        self.status["status"] = status
        self.status["details"] = details
        self.send_update()

    def finalize_suite_status(self):
        """
        Set the test suit status (pass/fail) based on the status of all scripts within the suite.
        """
        suite_passed = True
        for i in self.status["scripts"]:
            suite_passed &= i["status"] == StatusDefs.passed
        self.status["status"] = StatusDefs.passed if suite_passed else StatusDefs.failed

    def update_script_status(self, status, details=""):
        """
        Update the status of a single script within the test suite.
        """
        status = self.sanitize_param(status)
        details = self.sanitize_param(details)

        # ENHANCE: details seem unneeded at this level, as the only calls to this method use redundant details:
        # (StatusDefs.active, "")
        # (StatusDefs.passed, "Running")
        # (StatusDefs.failed, "One or more tests failed")
        # (StatusDefs.error, "Error")

        self.status["scripts"][self.script_index]["status"] = status
        self.status["scripts"][self.script_index]["details"] = details
        self.send_update()

    def update_test_status(self, status, details=""):
        """
        Update the status of a single script within the test suite.
        """
        status = self.sanitize_param(status)
        details = self.sanitize_param(details)

        self.status["scripts"][self.script_index]["tests"][self.test_index]["status"] = status
        self.status["scripts"][self.script_index]["tests"][self.test_index]["details"] = details
        self.send_update()

    def update_command_status(self, status, details, index=None):
        """
        Update the status of a single command within a test script.
        """
        if index is None:
            index = self.command_index

        status = self.sanitize_param(status)
        details = self.sanitize_param(details)

        # for looping control flow, reset statuses of instructions after the current index be to 'waiting'
        instruction_list = self.status["scripts"][self.script_index]["tests"][self.test_index]["instructions"]
        for i in range(index + 1, len(instruction_list)):
            instruction_list[i]["status"] = "waiting"

        self.status["scripts"][self.script_index]["tests"][self.test_index]["instructions"][index][
            "status"] = status
        self.status["scripts"][self.script_index]["tests"][self.test_index]["instructions"][index][
            "details"] = details
        self.send_update()

    def end_command(self):
        """
        Increment the current active command index.
        """
        self.command_index += 1

    def end_test(self):
        """
        Increment the current active test index. Reset the command index to 0.
        """
        self.command_index = 0
        self.test_index += 1

    def end_script(self):
        """
        Increment the current active script. Reset the test and command indices to 0.
        """

        self.command_index = 0
        self.test_index = 0
        self.script_index += 1

    @staticmethod
    def sanitize_param(param):
        """
        Sanitize a test instruction parameter by attempting to decode it if needed
        """
        try:
            param = param.decode()
        except AttributeError:
            pass
        return param

    @staticmethod
    def sanitize_data(data):
        """
        Sanitize test instruction data by attempting to decode every field if needed
        """
        if isinstance(data, dict):
            args = data.get("args")
        else:
            args = data

        if args is not None:
            try:
                for args_index, arg in enumerate(args):
                    if isinstance(arg, dict):
                        for arg_key in arg:
                            value = arg[arg_key]
                            if isinstance(value, bytes):
                                arg[arg_key] = value.decode()
                    else:
                        if isinstance(arg, bytes):
                            args[args_index] = arg.decode()
                return args
            except (TypeError, UnicodeDecodeError) as exception:
                log.error("Cannot decode arguments. Ensure command arguments are formatted as follows\n"
                          "[{'arg1': 1, 'arg2': 2, 'arg3': 3}]")
                log.debug(exception)
                return None
        return None

    def sanitize_status(self):
        """
        Sanitize test script data by attempting to decode every field at the test script level if needed
        """
        status = self.status
        for script_index, script in enumerate(self.status["scripts"]):
            for test_index, test in enumerate(script["tests"]):
                test["test_number"] = self.sanitize_param(test["test_number"])
                test["details"] = self.sanitize_param(test["details"])
                for index, command in enumerate(test["instructions"]):
                    command["data"] = command.get("data")
                    test["instructions"][index] = command
                self.status["scripts"][script_index]["tests"][test_index] = test
        return status

    def send_update(self):
        """
        Send the latest status packet over the UDP socket.

        @note - If the UDP socket encounters an error for any reason, the port will be set to None and CTF will not
        send updates to the Editor any more. The socket failure is most likely to be a computer issue, not CTF issue.
        """
        # Initialize connection if the first time sending an update
        if self.socket is None and self.port is not None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                self.socket.connect((self.ip_address, self.port))
            except socket.error as exception:
                log.error(exception)
                log.error("Status Manager cannot connect to server {}:{}. Disabling status updates..."
                          .format(self.ip_address, self.port))
                log.debug(traceback.format_exc())
                self.port = None

        # If socket is connected, send status messages
        self.status["elapsed_time"] = time.time() - self.start_time
        if self.port is not None:
            self.status = self.sanitize_status()
            try:
                data = json.dumps(self.status, sort_keys=False, separators=(",", ":"), ensure_ascii=False)
                self.socket.sendall(data.encode())
            except socket.error as exception:
                log.error("Status Manager cannot send status to {}:{}. Disabling status updates. Error: {}"
                          .format(self.ip_address, self.port, exception))
                self.port = None
