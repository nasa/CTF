"""
@namespace plugins.variable_plugin
The Variable Plugin module allows users to set / update / check variables defined in json test scripts.
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
import ast

from lib import ctf_utility
from lib.exceptions import CtfTestError
from lib.logger import logger as log
from lib.ctf_global import Global
from lib.ctf_utility import resolve_variable
from lib.plugin_manager import Plugin, ArgTypes


class VariablePlugin(Plugin):
    """
    The Variable Plugin Class Definition

    @note The Variable Plugin allows users to set / read / test variables defined in json test scripts.

    @note All plugin functions mapped to a test instruction *must* return true/false to indicate pass/fail of
        that instruction.
    """

    def __init__(self):
        """
        Constructor of variable plugin.

        @note The __init__ function is called once a plugin is loaded.

        @note The __init__ function should not reference/interact with any other plugin since the other plugin may not
            be loaded at this stage.

        @note The constructor of a plugin must define the following fields:
            - name
            - description
            - command map: dictionary mapping CTF instructions to a tuple defining the
                          python function to use for that instruction, and a list of argument types
            - [optional] verify_required_commands: List of instructions that require verification (i.e polling
            until verification passes or timeout.
            - other class variables that can store state, etc...
        """
        super().__init__()

        ## Plugin Name
        self.name = "VariablePlugin"

        ## Plugin Description
        self.description = "Variable Plugin"

        ## Plugin Command Map
        self.command_map = {
            "SetUserVariable": (self.set_user_defined_variable,
                                [ArgTypes.string, ArgTypes.string, ArgTypes.other, ArgTypes.string]),
            "SetUserVariableFromTlm": (self.set_user_variable_from_tlm,
                                       [ArgTypes.string, ArgTypes.string, ArgTypes.string, ArgTypes.string]),
            "SetUserVariableFromTlmHeader": (self.set_user_variable_from_tlm_header,
                                             [ArgTypes.string, ArgTypes.string, ArgTypes.string, ArgTypes.string]),
            "CheckUserVariable": (self.check_user_defined_variable, [ArgTypes.string, ArgTypes.string, ArgTypes.other])
        }

    def initialize(self):
        """
        Initialize implementation for the variable plugin.

        @note The initialize function is called by the CTF plugin manager *after* all plugins have been loaded.

        @note This function may interact with other plugins, since all plugins have been loaded at this stage.

        @return bool: True if successful, False otherwise.
        """

        VariablePlugin.add_variables_from_config()

        log.info("Initialized Variable Plugin!")
        return True

    @staticmethod
    def add_variables_from_config():
        """
        Add the test variables defined in INI config files to the global user defined variables dictionary.
        Supported types: int, float, bool, str.
        @return None
        """
        if "test_variable" not in Global.config.sections():
            return

        # exclude default variables from os.environ
        variables_defined = [item for item in Global.config.items("test_variable")
                             if item not in Global.config.defaults().items()]

        log.debug("Test variables defined in section 'test_variables' : {}".format(variables_defined))
        casted_types = {int: "int", float: "float", str: "string", bool: "boolean"}

        for key, value in variables_defined:
            if value in ("false", "true"):
                value = value.capitalize()
            try:
                casted_value = ast.literal_eval(value)
            except (ValueError, SyntaxError) as exception:
                log.error("Could not type cast value '{}'".format(value))
                log.error("Invoke exception {}".format(exception))
                continue
            variable_type = type(casted_value)
            if variable_type in casted_types:
                log.info("Add '{}':{} to User Defined Variable Dictionary".format(key, casted_value))
                VariablePlugin.set_user_defined_variable(key, "=", casted_value, casted_types[variable_type])
            else:
                log.warning("The type of variable {}={} is not supported".format(key, casted_value))

        return

    @staticmethod
    def set_user_defined_variable(variable_name: str, operator: str, value: any, variable_type: str = None):
        """
        Set / update the value of user defined variable (defined in json test scripts)

        @return bool: True if successful, False otherwise.
        """
        status = ctf_utility.set_variable(variable_name, operator, value, variable_type)
        variable_value = ctf_utility.get_variable(variable_name)
        if status:
            log.info("The variable {} becomes {}".format(variable_name, variable_value))
        else:
            log.error("Failed to set variable {}".format(variable_name))
        return status

    @staticmethod
    def set_user_variable_from_tlm(variable_name: str, mid: str, tlm_variable: str,
                                   target: str = None, is_header: bool = False):
        """
        Get the latest telemetry value from queue, and set it to the specified variable.
        @return bool: True if successful, False otherwise.
        """
        log.info("Set user variable: '{}' from tlm mid: '{}' variable: '{}'".format(variable_name, mid, tlm_variable))
        resolved_mid = resolve_variable(mid)
        resolved_tlm_variable = resolve_variable(tlm_variable)
        resolved_variable_name = resolve_variable(variable_name)
        resolved_target = resolve_variable(target)
        cfs_plugin = Global.plugin_manager.find_plugin_for_command("StartCfs")
        tlm_value = cfs_plugin.get_tlm_value(resolved_mid, resolved_tlm_variable, is_header, resolved_target)
        status = VariablePlugin.set_user_defined_variable(resolved_variable_name, "=", tlm_value)
        return status

    @staticmethod
    def set_user_variable_from_tlm_header(variable_name: str, mid: str, header_variable: str, target: str = None):
        """
        Get the latest telemetry header value from queue, and set it to the specified variable.
        @return bool: True if successful, False otherwise.
        """
        return VariablePlugin.set_user_variable_from_tlm(variable_name, mid, header_variable, target, True)

    @staticmethod
    def set_label(label: str) -> bool:
        """
        Set the a test-script scope label for control flow instructions. It is a placeholder.
        Process_control_flow_label in test will validate the labels.

        @return bool: True
        """
        log.info("Set label '{}' for control flow instructions".format(label))
        return True

    @staticmethod
    def get_user_defined_variable(variable_name: str) -> bool:
        """
        Get the value of user defined variable

        @return bool: True if successful, False if variable not defined.
       """
        value = ctf_utility.get_variable(variable_name)
        status = value is not None
        log.info("Variable {} = {}".format(variable_name, value))
        return status

    @staticmethod
    def check_user_defined_variable(variable_name: str, operator: str, value) -> bool:
        """
        Compare the user-defined variable with value using the operator
        @return bool: the bool outcome of the operation performed on the variables and values.
       """
        op_func = ctf_utility.operator_map.get(operator, None)
        variable_value = ctf_utility.get_variable(variable_name)
        if variable_value is None:
            log.warning("Variable {} is None ".format(variable_name))
            return False
        if op_func is None:
            log.warning("operator {} is not supported ".format(operator))
            return False

        log.info("Variable {} = {}".format(variable_name, variable_value))

        value = resolve_variable(value)

        # pylint: disable=unidiomatic-typecheck
        if type(variable_value) != type(value):
            log.warning("Variable and value are not the same type! The check will likely fail.")
            if isinstance(value, str):
                try:
                    value = ast.literal_eval(value)
                    log.warning("The compared value is string, which is evaluated to the literal {}".format(value))
                except Exception as exception:
                    log.error('Evaluating {} trigger exception {}'.format(value, exception))
                    raise CtfTestError("Error in ast.literal_eval") from exception

        status = op_func(variable_value, value)
        log_func = log.info if status else log.warning
        log_func("Checking {} {} {} => {}".format(variable_value, operator, value, status))
        return status

    def shutdown(self):
        """
        Shutdown implementation for the variable plugin.
        @note The shutdown function is called by the CTF plugin manager upon completion of a test run.
        @note The shutdown function can be exposed to test scripts by adding it to the command map.
        """
        log.info("Optional shutdown/cleanup implementation for Variable Plugin")
