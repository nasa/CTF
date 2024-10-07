# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2024 United States Government as represented by the
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
"""
@namespace plugins.trick_plugin
The Trick plugin provides instructions to integrate with a Trick simulation
"""
import configparser
import socket
import traceback

from lib.ctf_global import Global
from lib.exceptions import CtfTestError, CtfParameterError
from lib.logger import logger as log
from lib.plugin_manager import Plugin, ArgTypes
from lib.ctf_utility import resolve_variable, operator_map, type_map
from plugins.trick_plugin.trick.variable_server import VariableServer, VariableServerError


def convert_type(value: any, variable_type: str = None) -> any:
    """
    Utility function to convert a value to a type found in the type map of ctf_utility
    @param value The value to be converted
    @param variable_type The name of the type from the type map (int, float, string, or boolean)
    @return The converted value, or the original value if variable_type is not provided
    @raises CtfParameterError if variable_type is not valid, or if value cannot be converted
    """
    if variable_type:
        if variable_type in type_map:
            try:
                value = type_map[variable_type](value)
                return value
            except (ValueError, TypeError) as ex:
                raise CtfParameterError("Unable to convert value {} to {}".format(value, variable_type), value) from ex
        else:
            raise CtfParameterError("Unknown variable type", variable_type)
    return value


class TrickPlugin(Plugin):
    """
    The Trick Plugin provides Trick simulation integration for CTF.

    @note The Trick Plugin uses values from the [trick] section of the CTF config file.
          This section must be present if any Trick Plugin instructions are used in the test.
    """
    def __init__(self):
        """
        Constructor for the Trick Plugin.
        """
        super().__init__()

        self.name = "TrickPlugin"
        self.description = "Trick Plugin"
        self.command_map = {
            "FreezeTrickSim": (self.freeze_trick_sim, [ArgTypes.boolean]),
            "SetTrickVariable": (self.set_trick_variable, [ArgTypes.string] * 4),
            "CheckTrickVariable": (self.check_trick_variable, [ArgTypes.string, ArgTypes.comparison, ArgTypes.string,
                                                               ArgTypes.string, ArgTypes.string])
        }
        self.controller = None

    def initialize(self) -> bool:
        """
        Initializes the Trick Plugin.
        @note The controller is lazily initialized when an instruction is executed.
        """
        log.info("Initialized Trick Plugin!")
        return True

    def get_controller(self):
        """
        Helper method to return the controller, or attempt to create it if it does not exist.
        @return TrickController instance, or None if it could not be created
        """
        if not self.controller:
            try:
                self.controller = TrickController(Global.config)
            except (socket.error, configparser.Error) as ex:
                log.error("Unable to connect to Trick variable server: {}".format(ex))
                log.debug(traceback.format_exc())
                return None

        return self.controller

    def freeze_trick_sim(self, freeze: bool) -> bool:
        """
        Implements the instruction FreezeTrickSim.
        @note If the controller has not yet been created, it will be created now.
        @param freeze True to freeze the sim or False to un-freeze it
        @return True if successful or False if there is an error
        """
        log.info("{} Trick simulation".format('Freezing' if freeze else 'Unfreezing'))
        if not self.get_controller():
            return False

        self.get_controller().freeze_sim(freeze)
        return True

    def set_trick_variable(self, variable_name: str, value: str, variable_type: str = None, units=None) -> bool:
        """
        Implements the instruction SetTrickVariable.
        @note If the controller has not yet been created, it will be created now.
        @param variable_name The name of the Trick variable to set
        @param value The value to be set
        @param variable_type The name of the type to convert value before setting
            (int, float, string, or boolean) (Optional)
        @param units The name of the Trick units to set (Optional)
        @return True if successful or False if there is an error
        """
        log.info("Setting {} to ({}){} {}".format(variable_name, variable_type, value, units))
        if not self.get_controller():
            return False

        variable_name = resolve_variable(variable_name)
        value = convert_type(resolve_variable(value), variable_type)

        try:
            self.get_controller().set_variable(variable_name, value, units)
        except CtfTestError as ex:
            log.error("Failed to set variable {}: {}".format(variable_name, ex))
            log.debug(traceback.format_exc())
            return False

        return True

    def check_trick_variable(self, variable_name: str, operator: str, value: str,
                             units: str = None, variable_type: str = None) -> bool:
        """
        Implements the instruction CheckTrickVariable.
        @note If the controller has not yet been created, it will be created now.
        @param variable_name The name of the Trick variable to check
        @param operator The comparison operator to use to check value (==, <, <=, >=, >, or !=)
        @param value The value to check against the variable
        @param units The name of the Trick units with which to get the variable (Optional)
        @param variable_type The name of the type to convert value before checking
               (int, float, string, or boolean) (Optional)
        @return True if successful or False if there is an error
        """
        log.info("Checking {} {} ({}){} {}".format(variable_name, operator, variable_type, value, units))
        if not self.get_controller():
            return False

        variable_name = resolve_variable(variable_name)
        value = convert_type(resolve_variable(value), variable_type)
        variable_type = type(value)
        op_func = operator_map.get(operator)
        if not op_func:
            log.error("Operator {} is not supported".format(operator))
            return False

        try:
            actual_value = self.get_controller().get_variable(variable_name, units, variable_type)
        except CtfTestError as ex:
            log.error("Failed to get variable {}: {}".format(variable_name, ex))
            log.debug(traceback.format_exc())
            return False

        log.debug("Value of {} is {}".format(variable_name, actual_value))
        return op_func(actual_value, value)

    def shutdown(self) -> None:
        """
        Shuts down the plugin, releasing resources.
        """
        log.info("Trick Plugin shutdown")
        if self.controller:
            self.get_controller().shutdown()
            self.controller = None


class TrickController:
    """
    TrickController class definition: implements Trick functionality
    """
    def __init__(self, config):
        """
        Constructor for TrickController.
        Extracts values from the [trick] section of the config and attempts to connect to the variable server.
        @raises socket.error if it fails to connect to the variable server
        """
        try:
            hostname = config.get("trick", "hostname")
            port = config.getint("trick", "port")
            self.variable_server = VariableServer(hostname, port)
            log.info("Connected to Trick variable server at {}:{}".format(hostname, port))
        except socket.error as ex:
            log.error("VariableServer client failed to connect: {}".format(ex))
            raise ex

    def freeze_sim(self, freeze: bool) -> None:
        """
        Commands the variable server to change the freeze state of the sim.
        """
        self.variable_server.freeze(freeze)

    def set_variable(self, variable_name: str, value: any, units: str = None) -> None:
        """
        Sets a value on the variable server.
        @raises CtfTestError if the variable server raises an error
        """
        try:
            self.variable_server.set_value(variable_name, value, units or None)
        except VariableServerError as ex:
            raise CtfTestError(ex) from ex

    def get_variable(self, variable_name: str, units: str = None, variable_type: any = None) -> any:
        """
        Gets a value from the variable server.
        @raises CtfTestError if the variable server raises an error
        """
        try:
            return self.variable_server.get_value(variable_name, units or None, variable_type or str)
        except VariableServerError as ex:
            raise CtfTestError(ex) from ex

    def shutdown(self) -> None:
        """
        Closes and releases the variable server instance. Should be called when the controller is no longer needed.
        """
        # close variable server
        if self.variable_server:
            log.debug("Closing Trick variable server")
            self.variable_server.close()
            self.variable_server = None
