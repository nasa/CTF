"""
@namespace lib.plugin_manager
The Plugin Manager is a CTF core component that manages CTF plugins.
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

# Note - this module is adapted from the following open source code-base with the MIT License.
#
# https://gist.github.com/mepcotterell/6004997
#
# The MIT License (MIT)
#
# Copyright (c) 2013 Michael E. Cotterell
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import inspect
import os
import pkgutil
import json
import sys
from inspect import signature

from lib.ctf_global import Global
from lib.exceptions import CtfTestError
from lib.logger import logger as log

# Template for Plugin Info Dictionary Objects:
#   - Used for serializing and exporting the CTF plugin information
#     JSON files.
from lib.status import ObjectFactory


class ArgTypes:
    """
    Argument types support by plugin instructions. The argument types are exported to the CTF Editor for autosuggestion
    and input validation.
    """
    cmd_mid = "cmd_mid"
    cmd_code = "cmd_code"
    cmd_arg = "cmd_arg"
    tlm_mid = "tlm_mid"
    comparison = "comparison"
    string = "string"
    boolean = "boolean"
    number = "number"
    ignore = "ignore"
    condition = "loop_condition"
    event = "event"
    other = "other"
    array_types = [cmd_arg, comparison, condition, event]


class Plugin():
    """Base class that each plugin must inherit from. This class defines methods and properties that all plugins may
    override or implement.
    """

    def __init__(self):
        """
        Constructor of Plugin Class: Initiate instance properties
        """
        ## Plugin Name
        self.name = ""

        ## Plugin Description
        self.description = ""

        ## Plugin Command Map. The command map utilizes the instruction name as the key, with the value being a tuple of
        #  instruction implementation and argument types.
        #
        #  @note Example:
        #  {"TestCommand": (self.test_command, [ArgTypes.string] * 2)}
        self.command_map = {}

        ## List of verification type instructions
        self.verify_required_commands = []

        ## List of continuously verified instructions (i.e executed every poll without an explicit instruction)
        self.continuous_verification_commands = []

        ## List of instructions that end test on failure (i.e critical instructions that the test script cannot proceed
        #  without)
        self.end_test_on_fail_commands = []

    def initialize(self):
        """
        Virtual initialize method definition. Must be overridden by child Plugin class.
        @note - The initialize method is called for each plugin after *all* plugins are loaded.
        """
        log.warning("Plugin does not implement initialize. Plugin Name: {}".format(self.name))

    def process_command(self, **kwargs):
        """
        Given a CTF Test Instruction, this function finds the first plugin that "contains" that test instruction within
        its command map. Once a valid plugin is found, the implementation of that instruction is invoked using
        keyworded variable length of arguments in kwargs.

        @note - This function will ensure that the number of argument provided to the plugin's function is greater than
                the number of required arguments (non-optional), and less than or equal to the total number of arguments
                (required + optional)
        """
        result = False
        instruction = kwargs["instruction"]
        if "data" in kwargs.keys():
            data = kwargs["data"]

        if instruction in self.command_map.keys():
            func = self.command_map[instruction][0]
            sig = signature(func)
            req_args = 0
            optional_args = 0
            for value in sig.parameters.values():
                if value.default == sig.empty:
                    req_args += 1
                else:
                    optional_args += 1

            if req_args <= len(data) <= (req_args + optional_args):
                try:
                    result = func(**data)
                except Exception as exception:
                    log.error("Error Applying Function {}".format(func))
                    raise CtfTestError("Error Applying Function") from exception
            else:
                log.error("Invalid number of parameters passed to {}. Expected at least {} args".format(instruction,
                                                                                                        req_args))
                result = False
        if result is None and instruction not in self.verify_required_commands:
            log.warning("Plugin Execution Result for {} is None. Please ensure all plugin instructions \
                     return a boolean result.".format(instruction))
        return result

    def shutdown(self):
        """
        Virtual shutdown method definition. Must be overridden by child Plugin class.
        @note - The shutdown method is called for each plugin after test execution is complete. Use this function to
                shutdown/cleanup any external interfaces or data.
        """
        log.warning("Plugin does not implement shutdown. Plugin Name: {}".format(self.name))


class PluginManager:
    """
    Upon creation, this class will read the plugins package for modules
    that contain a class definition that is inheriting from the Plugin class
    """

    def __init__(self, plugin_packages):
        """
        Constructor of PluginManager Class: initiates the reading of all available plugins
        when an instance of the PluginManager object is created
        """
        Global.plugin_manager = self
        self.plugin_packages = plugin_packages
        self.plugins = {}

        self.plugin_name_list = []
        self.reload_plugins()

    def initialize_plugins(self):
        """
        After loading all plugins, this function calls initialize() on all loaded plugins within the plugin manager
        """
        for plugin in self.plugins.values():
            plugin.initialize()

    def shutdown_plugins(self):
        """
        Before CTF shutdown (or on plugin restart), this function calls shutdown() on all loaded plugins within
        the plugin manager
        """
        for plugin in self.plugins.values():
            plugin.shutdown()

    def find_plugin_for_command(self, command):
        """
        Given a CTF Test Instruction, find the plugin instance that can execute that instruction.

        @note - CTF Test Instructions must be named uniquely across different plugins.
        @note - It is recommended to prefix the instruction name with a plugin identifier to avoid ambiguity. For
                example: MyPlugin_DoSomething

        @return Plugin: Plugin instance found that implements the given instruction. None of no plugins found.
        """
        for plugin in self.plugins.values():
            if command in plugin.command_map.keys():
                return plugin
        return None

    def find_plugin_for_command_and_execute(self, command):
        """
        Given a CTF Test Instruction, find the plugin instance that can execute that instruction, execute the
        instruction and return the instruction status (pass/fail)

        @return Plugin: Boolean: CTF Instruction Status (True/False)
        """
        instruction = command["instruction"]
        data = command["data"]
        result = False
        plugin_to_use = self.find_plugin_for_command(instruction)
        if plugin_to_use is not None:
            result = plugin_to_use.process_command(instruction=instruction, data=data)
        else:
            log.error("No plugin found for command {}".format(instruction))
        return result

    def reload_plugins(self):
        """Reset the list of all plugins and initiate the walk over the main
        provided plugin package to load all available plugins
        """
        self.plugins = {}
        self.seen_paths = []
        self.plugin_name_list = []
        self.disabled_plugins = Global.config.get("core", "disabled_plugins").split(',') \
            if Global.config.has_option("core", "disabled_plugins") else []

        for plugin_package in self.plugin_packages:
            cwd = os.getcwd()
            log.info("Looking for plugins under package: {} ".format(plugin_package))
            if not os.path.exists(plugin_package) and plugin_package != "plugins":
                log.error("Invalid plugin path: {}. Skipping... ".format(plugin_package))
                continue
            if os.path.dirname(plugin_package) != "":
                sys.path.insert(1, os.path.dirname(plugin_package))
            self.walk_package(plugin_package)
            os.chdir(cwd)
            Global.plugins_available = self.plugins

    def walk_package(self, package):
        """Recursively walk the supplied package to retrieve all plugins

        @param package - Given a package path, this function recursively walks through the package and imports any
                        modules available within the package.
        """

        # Skip pycache modules
        if 'pycache' in package:
            return

        imported_package = __import__(os.path.basename(package), fromlist=[''])
        if '.' in package and package.split('.')[-1] in self.disabled_plugins:
            log.info("    Plugin {} in disable plugins list. Skipping...".format(package))
            return

        # Load any modules ending in '_plugin' and not containing 'tests' in the path to check for Plugin classes
        for _, pluginname, ispkg in pkgutil.iter_modules(imported_package.__path__, imported_package.__name__ + '.'):
            if not ispkg and 'tests' not in pluginname and str(pluginname).endswith('_plugin'):
                plugin_module = __import__(pluginname, fromlist=[''])
                class_members = inspect.getmembers(plugin_module, inspect.isclass)
                for (_, class_member) in class_members:
                    # Only add classes that are a sub class of Plugin, but NOT Plugin itself
                    if issubclass(class_member, Plugin) & (class_member is not Plugin):
                        log.info('\tFound plugin class: {}.{}'.format(
                            class_member.__module__,
                            class_member.__name__
                        ))
                        new_object = class_member()
                        name = new_object.name
                        if name not in self.plugin_name_list:
                            self.plugins[name] = new_object
                            self.plugin_name_list.append(name)

        # Now that we have looked at all the modules in the current package, start looking
        # recursively for additional modules in sub packages
        all_current_paths = []
        if isinstance(imported_package.__path__, str):
            all_current_paths.append(imported_package.__path__)
        else:
            all_current_paths.extend(imported_package.__path__)

        for pkg_path in all_current_paths:
            if pkg_path not in self.seen_paths:
                self.seen_paths.append(pkg_path)

                # Get all sub directory of the current package path directory
                child_pkgs = [p for p in os.listdir(pkg_path) if os.path.isdir(os.path.join(pkg_path, p))]

                # For each sub directory, apply the walk_package method recursively
                for child_pkg in child_pkgs:
                    self.walk_package(package + '.' + child_pkg)

    def create_plugin_info(self, directory):
        """
        Outputs the plugin information files in JSON format for utilization by the CTF editor or other tools.

        @param directory - Directory to write the plugin information files.
        @note - The directory is created automatically if it does not exist.
        """
        if not os.path.exists(directory):
            os.mkdir(directory)

        if not os.path.isdir(directory):
            raise Exception("{} is not a directory! ".format(directory))

        for plugin_name, plugin in self.plugins.items():
            plugin_info = ObjectFactory.create_object("PluginInfo")
            plugin_info["group_name"] = plugin_name
            plugin_info["description"] = plugin.description
            for command in plugin.command_map.keys():
                param_index = 0
                command_info = ObjectFactory.create_object("CommandInfo")
                command_info["name"] = command
                command_info["description"] = ""
                sig = signature(plugin.command_map[command][0])
                parameters = sig.parameters
                for parameter in parameters.values():
                    parameter_info = ObjectFactory.create_object("ParameterInfo")
                    parameter_info["name"] = parameter.name
                    parameter_info["description"] = ""
                    # If the argument is optional and has no type in the command map, ignore it
                    if param_index >= len(plugin.command_map[command][1]) and parameter.default != sig.empty:
                        log.warning("Parameter {} is optional in plugin {} and is not defined in the  \
                                    command map. Skipping...".format(parameter.name, plugin_name))
                        continue

                    if param_index >= len(plugin.command_map[command][1]):
                        log.error("Parameter \"{}\" is required for command \"{}\".".format(parameter.name, command))
                        log.error(
                            "Plugin info generation failed. Please update the command map with the required arguments.")
                        return

                    parameter_info["type"] = plugin.command_map[command][1][param_index]

                    # Skip parameters of type ignore (useful for mapping 2 commands to the same function w/
                    # different parameters)
                    if parameter_info["type"] == ArgTypes.ignore:
                        continue
                    if parameter_info["type"] in ArgTypes.array_types:
                        parameter_info["isArray"] = True
                    command_info["parameters"].append(parameter_info)
                    param_index += 1
                plugin_info["instructions"].append(command_info)
            with open(os.path.join(directory, plugin_name) + ".json", 'w') as outfile:
                json.dump(plugin_info, outfile, indent=2)
