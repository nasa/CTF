"""
@namespace lib.readers.json_script_reader
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


import copy
import json
import traceback
import os

from lib.exceptions import CtfTestError
from lib.test import Test
from lib.test_script import TestScript
from lib.event_types import Command
from lib.logger import logger as log


class JSONScriptReader:
    """
    The JSONScriptReader class provides methods to parse a CTF JSON test script.

    @param input_script_path: The path to the input JSON script
    """
    def __init__(self, input_script_path):
        # Load JSON Input File
        try:
            with open(input_script_path, "r") as script:
                try:
                    self.raw_data = json.load(script)
                except ValueError as exception:
                    log.error(exception)
                    log.error("Skipping Input Script")
                    log.debug(traceback.format_exc())
                    self.valid_script = False
                    return

        except (IOError, OSError) as exception:
            log.error(exception)
            log.error("Skipping Input Script")
            self.valid_script = False
            return

        self.valid_script = True
        self.script = TestScript()
        self.input_script_path = input_script_path

        self.script.input_file_path = os.path.dirname(input_script_path)
        self.script.input_file = os.path.basename(input_script_path)

        self.functions = dict()

        # ENHANCE - validate file against a schema

        self.process_header()

        self.process_watchlists()

        self.process_functions()

        self.process_tests()

    def process_header(self):
        """
        Parse and process test information from script header
        """
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
        except KeyError as exception:
            log.error("Exception: Invalid Json Script file: {} does not contain {}"
                      .format(self.input_script_path, exception))

            self.valid_script = False

    # Process watchlists
    def process_watchlists(self):
        """
        Parse the 'telemetry_watch_list' and 'command_watch_list' field in the test script
        """
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

        except KeyError as exception:
            log.error("Exception: Invalid Json Script file: {} does not contain {}"
                      .format(self.input_script_path, exception))
            raise exception

    def process_functions(self):
        """
        Parse the function definitions and imports in the test script
        """
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
                        log.error("Error opening file {} while importing functions from script: {}"
                                  .format(util, self.script.input_file))
                        raise CtfTestError("Error opening file while importing functions from script")
                    with open(util, "r") as util_file:
                        try:
                            util_raw = json.load(util_file)
                        except ValueError as exception:
                            log.error("Exception: ValueError %s", exception)
                            raise exception

                    if "functions" in util_raw.keys():
                        if self.functions:
                            self.functions.update(util_raw["functions"])
                        else:
                            self.functions = util_raw["functions"]

        except KeyError as exception:
            log.error("Exception: Invalid Json Script file: {} does not contain {}"
                      .format(self.input_script_path, exception))
            raise exception

    def sanitize_args(self, args):
        """
        Iterates over arguments within test instructions and decodes arguments if needed.
        """
        if args is None:
            return None

        try:
            # args may be a dictionary {'expectedCmdCnt': 1, 'expectedErrCnt': 0} or
            # a list [{'expectedCmdCnt': 1, 'expectedErrCnt': 0}]
            if isinstance(args, dict):
                for key, value in args.items():
                    if isinstance(value, bytes):
                        args[key] = value.decode()
            elif isinstance(args, list):
                for index, arg in enumerate(args):
                    if isinstance(arg, dict):
                        for key in arg:
                            value = arg[key]
                            if isinstance(value, bytes):
                                arg[key] = value.decode()
                    else:
                        if isinstance(arg, bytes):
                            args[index] = arg.decode()
            return args
        except (TypeError, UnicodeDecodeError) as exception:
            log.error("Cannot decode arguments in {}. Ensure command arguments are formatted as follows\n"
                      "[1, 2, 3] or \n"
                      "[{{\'arg1\': 1, \'arg2\': 2, \'arg3\': 3}}]".format(self.input_script_path))
            log.debug(exception)
            return None

    def process_tests(self):
        """
        Iterates over test cases within the test script and parses each test case.
        """
        tests = self.raw_data.get("tests")
        test_list = []
        if tests is None:
            self.script.set_tests(test_list)
            self.valid_script = False
            return

        # Build event list
        for curr_test in tests:
            event_list = []
            test = Test()
            commands = curr_test["instructions"]
            for _, command in enumerate(commands):
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
                    if not inline_commands:
                        log.error("No commands in function {}".format(command["function"]))
                        continue
                    if "wait" in command:
                        function_call_delay = command["wait"]
                    else:
                        function_call_delay = 1.0

                    disabled = bool(command.get('disabled', False))
                    for c_index, c_inline in enumerate(inline_commands):
                        # Set the default delay value of 0
                        # then obtain wait value from test script
                        delay = 0
                        if "wait" in c_inline.keys():
                            delay = c_inline["wait"]
                        if c_index == 0:
                            delay += function_call_delay
                        disabled |= bool(c_inline.get('disabled', False))
                        event_list.append(Command(delay, c_inline, len(test_list), -1, disabled))
                else:
                    delay = 0
                    if "wait" in command.keys():
                        delay = command["wait"]
                    disabled = bool(command.get('disabled', False))
                    event_list.append(Command(delay, command, len(test_list), -1, disabled))

            for i, _ in enumerate(event_list):
                event_list[i].command_index = i

            test.test_info = {"test_case": curr_test["case_number"], "description": curr_test["description"]}
            test.event_list = event_list
            test_list.append(test)
        self.script.set_tests(test_list)

    def resolve_function(self, name, params, functions):
        """
        Perform in-line replacement of function calls with the set of instructions within the function definition
        """
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
                        if key in varlist:
                            value = params[key]
                            command["params"][key] = value
                    resolved_cmds = self.resolve_function(command["function"], command["params"], functions)
                    if not resolved_cmds:
                        log.error("Command %s not resolved", name)
                        return None
                    commands = commands[:index] + resolved_cmds + commands[index + 1:]
                else:
                    command["data"] = self.resolve_command_data(params, command["data"])
        except KeyError as exception:
            log.error("Exception: Invalid Json Script file: {} does not contain {}"
                      .format(self.input_script_path, exception))
            traceback.print_exc()
            raise exception
        return commands

    def resolve_command_data(self, params, data):
        """
        Perform in-line replacement of arguments passed into a function
        """
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
