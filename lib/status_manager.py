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


from lib.status import *
from lib.logger import logger as log

from copy import deepcopy

import socket
import json
import time


class StatusManager():
    def __init__(self, ip="127.0.0.1", port=None):
        self.status = self.blank_status_msg(list())
        self.script_index = 0
        self.test_index = 0
        self.command_index = 0
        self.ip = ip
        self.port = port
        self.socket = None
        self.start_time = None

    def set_start_time(self):
        self.start_time = time.time()

    def set_scripts(self, scripts):
        self.status = self.blank_status_msg(scripts)

    def blank_status_msg(self, scripts):
        status = deepcopy(SuiteStatus)
        for script in scripts:
            script_status = deepcopy(ScriptStatus)
            script_status["path"] = script.input_file
            script_status["test_name"] = script.test_name
            script_status["status"] = StatusDefs.waiting
            script_status["details"] = ""
            for test in script.tests:
                test_status = deepcopy(TestStatus)
                test_status["case_number"] = test.test_info["test_case"]
                test_status["status"] = StatusDefs.waiting
                test_status["details"] = ""
                test_status["description"] = test.test_info.get("description", "")
                for c in test.event_list:
                    command_status = deepcopy(InstructionStatus)
                    command_status["instruction"] = c.command["instruction"]
                    if ("wait" in c.command.keys()):
                        command_status["wait"] = c.command["wait"]
                    else:
                        command_status["wait"] = 0
                    # command_status["data"] = self.sanitize_data(c.command.get("data")) or {}
                    command_status["data"] = c.command.get("data")

                    command_status["status"] = StatusDefs.waiting
                    command_status["details"] = ""
                    command_status["description"] = c.command.get("description", "")
                    test_status["instructions"].append(command_status)
                script_status["tests"].append(test_status)
            status["scripts"].append(script_status)
        return status

    def update_suite_status(self, status, details):
        status = self.sanitize_param(status)
        details = self.sanitize_param(details)

        self.status["status"] = status
        self.status["details"] = details
        self.send_update()

    def finalize_suite_status(self):
        suite_passed = True
        for i in self.status["scripts"]:
            suite_passed &= i["status"] == StatusDefs.passed
        self.status["status"] = StatusDefs.passed if suite_passed else StatusDefs.failed

    def update_script_status(self, status, details):
        status = self.sanitize_param(status)
        details = self.sanitize_param(details)

        self.status["scripts"][self.script_index]["status"] = status
        self.status["scripts"][self.script_index]["details"] = details
        self.send_update()

    def update_test_status(self, status, details):
        status = self.sanitize_param(status)
        details = self.sanitize_param(details)

        self.status["scripts"][self.script_index]["tests"][self.test_index]["status"] = status
        self.status["scripts"][self.script_index]["tests"][self.test_index]["details"] = details
        self.send_update()

    def update_command_status(self, status, details, index = None):
        if (index == None):
            index = self.command_index

        status = self.sanitize_param(status)
        details = self.sanitize_param(details)

        self.status["scripts"][self.script_index]["tests"][self.test_index]["instructions"][index][
            "status"] = status
        self.status["scripts"][self.script_index]["tests"][self.test_index]["instructions"][index][
            "details"] = details
        self.send_update()

    def end_command(self):
        self.command_index += 1

    def end_test(self):
        self.command_index = 0
        self.test_index += 1

    def end_script(self):
        self.command_index = 0
        self.test_index = 0
        self.script_index += 1

    def sanitize_param(self, param):
        if not isinstance(param, str):
            param = param.decode()
        return param

    def sanitize_data(self, data):
        if isinstance(data, dict):
            args = data.get("args")
        else:
            args = data

        if args is not None:
            try:
                for index, arg in enumerate(args):
                    if isinstance(arg, dict):
                        for key in arg:
                            value = arg[key]
                            if isinstance(value, bytes):
                                args[key] = value.decode()
                    else:
                        if isinstance(arg, bytes):
                            args[index] = arg.decode()
                return args
            except Exception as e:
                log.error("Cannot decode arguments. Ensure command arguemnts are formatted as follows\n"
                          "[1, 2, 3] or \n"
                          "[{'arg1': 1, 'arg2': 2, 'arg3': 3}]")
                log.debug(e)
                return None
        return None

    def sanitize_status(self):
        status = self.status
        for script_index, script in enumerate(self.status["scripts"]):
            for test_index, test in enumerate(script["tests"]):
                test["case_number"] = self.sanitize_param(test["case_number"])
                test["details"] = self.sanitize_param(test["details"])
                for index, command in enumerate(test["instructions"]):
                    command["data"] = command.get("data")
                    test["instructions"][index] = command
                self.status["scripts"][script_index]["tests"][test_index] = test
        return status

    def send_update(self):
        # Initialize connection if the first time sending an update
        if (self.socket is None and self.port != None):
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                self.socket.connect((self.ip, self.port))
            except socket.error as e:
                log.error("Status Manager cannot connect to server {}:{}. Disabling status updates...".format(self.ip, self.port))
                self.port = None

        # If socket is connect, send status messages
        self.status["elapsed_time"] = time.time() - self.start_time
        if self.port is not None:
            self.status = self.sanitize_status()
            try:
                data = json.dumps(self.status, sort_keys=False, separators=(",", ":"), ensure_ascii=False)
                self.socket.sendall(data.encode())
            except socket.error as e:
                log.error("Status Manager cannot send status to {}:{}. Disabling status updates. Error: {}".format(self.ip, self.port, e))
                self.port = None
