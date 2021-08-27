"""
@namespace plugins.variable_plugin
The Variable Plugin module allows users to set / update / check variables defined in json test scripts.
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


from lib import ctf_utility
from lib.ctf_global import Global
from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log


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
            "SetUserVariable": (self.set_user_defined_variable, [ArgTypes.string, ArgTypes.string, ArgTypes.other]),
            "SetLabel": (self.set_label, [ArgTypes.string]),
            "SetUserVariableFromTlm": (self.set_user_variable_from_tlm, [ArgTypes.string, ArgTypes.string,
                                                                         ArgTypes.string]),
            "CheckUserVariable": (self.check_user_defined_variable, [ArgTypes.string, ArgTypes.string, ArgTypes.other])
        }

    @staticmethod
    def initialize():
        """
        Initialize implementation for the variable plugin.

        @note The initialize function is called by the CTF plugin manager *after* all plugins have been loaded.

        @note This function may interact with other plugins, since all plugins have been loaded at this stage.

        @return bool: True if successful, False otherwise.
        """
        log.info("Initialized Variable Plugin!")
        return True

    @staticmethod
    def set_user_defined_variable(variable_name: str, operator: str, value):
        """
        Set / update the value of user defined variable (defined in json test scripts)

        @return bool: True if successful, False otherwise.
        """
        status = ctf_utility.set_variable(variable_name, operator, value)
        variable_value = ctf_utility.get_variable(variable_name)
        log.info("The variable {} becomes {}".format(variable_name, variable_value))
        return status

    @staticmethod
    def set_user_variable_from_tlm(user_variable: str, mid: str, tlm_variable: str):
        """
        Get the latest telemetry value from queue, and set it to the specified variable.
        @return bool: True if successful, False otherwise.
        """
        log.info("Set user variable: '{}' from tlm mid: '{}' variable: '{}'".format(user_variable, mid, tlm_variable))
        cfs_plugin = Global.plugin_manager.find_plugin_for_command("StartCfs")
        tlm_value = cfs_plugin.get_tlm_value(mid, tlm_variable)
        status = VariablePlugin.set_user_defined_variable(user_variable, "=", tlm_value)
        return status

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
