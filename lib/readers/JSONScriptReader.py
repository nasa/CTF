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


import copy
import json
import traceback

from lib.test import Test
from lib.test_script import TestScript
from lib.event_types import *
from lib.logger import logger as log
import os


class JSONScriptReader(object):
    def __init__(self, input_script_path):
        # Load JSON Input File
        try:
            with open(input_script_path, "r") as f:
                try:
                    self.raw_data = json.load(f)
                except ValueError as e:
                    log.error(e)
                    log.error("Skipping Input Script")
                    self.valid_script = False
                    return

        except Exception as e:
            log.error(e)
            log.error("Skipping Input Script")
            self.valid_script = False
            return

        self.valid_script = True
        self.script = TestScript()
        self.input_script_path = input_script_path

        self.script.input_file_path = os.path.dirname(input_script_path)
        self.script.input_file = os.path.basename(input_script_path)

        self.functions = dict()

        # TODO - validate file against a schema

        self.process_header()

        self.process_ctf_options()

        self.process_watchlists()

        self.process_functions()

        self.process_tests()

    # Process test information from script header
    def process_header(self):
        try:
            verification_test_number = self.raw_data["test_number"]
            verification_test_name = self.raw_data["test_name"]
            requirements = ", ".join([str(x) for x in self.raw_data["requirements"].keys()])
            test_description = str(self.raw_data["description"])
            test_owner = str(self.raw_data["owner"])
            test_setup = self.raw_data.get("test_setup") or ""
            ctf_options = self.raw_data.get("ctf_options")
            verif_timeout = ctf_options.get("verif_timeout") if ctf_options else 0

            self.script.set_header_info(verification_test_number, verification_test_name,
                                        requirements, test_description, test_owner, test_setup, verif_timeout)
        except KeyError as e:
            log.error("Exception: Invalid Json Script file: %s does not contain %s", self.input_script_path, e, )
            self.valid_script = False

    # Process CTF Options
    def process_ctf_options(self):
        options = {}
        if ("ctf_options" in self.raw_data.keys()):
            options = self.raw_data["ctf_options"]

    # Process watchlists
    def process_watchlists(self):
        try:
            telemetry_watch_list_mids = []
            cmd_watch_list_mids = []
            # Process Telemetry watch list
            if "telemetry_watch_list" in self.raw_data:
                for mid_str in self.raw_data["telemetry_watch_list"].keys():
                    telemetry_watch_list_mids.append(str(mid_str))
            # Process Command watch list
            if "command_watch_list" in self.raw_data:
                for mid_str in self.raw_data["command_watch_list"].keys():
                    cmd_watch_list_mids.append(str(mid_str))
            self.script.set_watch_lists(telemetry_watch_list_mids, cmd_watch_list_mids)

        except KeyError as e:
            log.error("Exception: Invalid Json Script file: %s does not contain %s", self.input_script_path, e, )
            raise e

    def process_functions(self):
        util_raw = None

        try:
            # Process user-defined functions
            if "functions" in self.raw_data.keys():
                self.functions = self.raw_data["functions"]
            # Process function imports
            if "import" in self.raw_data.keys():
                for util in self.raw_data["import"].keys():
                    if not os.path.exists(util):
                        util = os.path.join(self.script.input_file_path, util)
                    if not os.path.exists(util):
                        util = os.path.realpath(util)
                    if not os.path.exists(util):
                        log.error("Error importing functions from script: {}. Import Error:"
                                  .format(self.script.input_file, util))
                    with open(util, "r") as f:
                        try:
                            util_raw = json.load(f)
                        except ValueError as e:
                            log.error("Exception: ValueError %s", e)
                            raise e
                    if "functions" in util_raw.keys():
                        if self.functions:
                            self.functions.update(util_raw["functions"])
                        else:
                            self.functions = util_raw["functions"]

        except KeyError as e:
            log.error("Exception: Invalid Json Script file: %s does not contain %s", self.input_script_path, e, )
            raise e

    def sanitize_args(self, args):
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

    def process_tests(self):
        cur_time = 0.0
        tests = self.raw_data.get("tests")
        test_list = []
        if tests is None:
            self.script.tests = test_list
            self.valid_script = False
            return

        # Build event list
        for curr_test in tests:
            event_list = []
            test = Test()
            commands = curr_test["instructions"]
            for index, command in enumerate(commands):
                data = command.get("data")
                args = None if data is None else data.get("args")
                args = self.sanitize_args(args)
                if args is not None:
                    command["args"] = args

                if "function" in command:
                    params = None if command is None else command.get("params")
                    params = self.sanitize_args(params)
                    if params is not None:
                        command["params"] = params

                    inline_commands = self.resolve_function(command["function"], command["params"], self.functions)
                    if inline_commands is None:
                        log.error("Failed to process test case due to the error(s) above. Skipping {}".format(
                            curr_test["case_number"]
                        ))
                        event_list = []
                        break
                    if not commands:
                        log.error("No commands in function {}".format(command["function"]))
                        continue
                    if "wait" in command:
                        function_call_delay = command["wait"]
                    else:
                        function_call_delay = 1.0
                    for c_index, c in enumerate(inline_commands):
                        # Set the default delay value of 0
                        # then obtain wait value from test script
                        delay = 0
                        if "wait" in c.keys():
                            delay = c["wait"]
                        if c_index == 0:
                            delay += function_call_delay
                        event_list.append(Command(delay, c, len(test_list), -1))
                else:
                    delay = 0
                    if "wait" in command.keys():
                        delay = command["wait"]
                    event_list.append(Command(delay, command, len(test_list), -1))

            for i in range(len(event_list)):
                event_list[i].command_index = i

            test.test_info = {"test_case": curr_test["case_number"], "description": curr_test["description"]}
            test.event_list = event_list
            test_list.append(test)
        self.script.tests = test_list

    def resolve_function(self, name, params, functions):
        try:
            if name not in functions.keys():
                log.error("Function %s not found in JSON input file", name)
                return None

            commands = copy.deepcopy(functions[name]["instructions"])
            varlist = functions[name]["varlist"]
            if len(varlist) > 0 and len(params.keys()) > 0:
                if set(varlist) != set(params.keys()):
                    log.error("Function %s parameter mismatch", name)
                    return None

            for index, command in enumerate(commands):
                if "function" in command:
                    for key, value in command["params"].items():
                        if value in varlist:
                            value = params[value]
                            command["params"][key] = value
                    resolved_cmds = self.resolve_function(command["function"], command["params"], functions)
                    if not resolved_cmds:
                        log.error("Command %s not resolved", name)
                        return None
                    commands = commands[:index] + resolved_cmds + commands[index + 1:]
                else:
                    command["data"] = self.resolve_command_data(params, command["data"])
        except KeyError as e:
            log.error("Exception: Invalid Json Script file: {} does not contain {}", self.input_script_path, e)
            traceback.print_exc()
            raise e
        return commands

    def resolve_command_data(self, params, data):
        field = copy.deepcopy(data)
        if isinstance(field, dict):
            for key, value in field.items():
                if not isinstance(value, dict) and not isinstance(value, list) and value in params.keys():
                    field[key] = params[value]
                else:
                    field[key] = self.resolve_command_data(params, value)
        elif isinstance(field, list):
            for index, item in enumerate(field):
                if not isinstance(item, dict) and item in params.keys():
                    field[index] = params[item]
                else:
                    field[index] = self.resolve_command_data(params, item)
        return field
