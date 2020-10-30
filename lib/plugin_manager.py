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
import traceback

from collections import namedtuple

from inspect import signature

from copy import deepcopy

from lib.Global import Global, Config
from lib.logger import logger as log

# Template for Plugin Info Dictionary Objects:
#   - Used for serializing and exporting the CTF plugin information
#     JSON files.

ParameterInfo = {
    "name": "",
    "description": "",
    "type": ""
}

CommandInfo = {
    "name": "",
    "description": "",
    "parameters": []
}

PluginInfo = {
    "group_name": "",
    "instructions": []
}


class ArgTypes:
    # Argument types utilized by the CTF editor to render the
    # appropriate input for each argument.
    cmd_mid = "cmd_mid"
    cmd_code = "cmd_code"
    cmd_arg = "cmd_arg"
    tlm_mid = "tlm_mid"
    comparison = "comparison"
    string = "string"
    boolean = "boolean"
    number = "number"
    ignore = "ignore"
    other = "other"
    array_types = [cmd_arg, comparison]


class Plugin(object):
    """Base class that each plugin must inherit from. within this class
    you must define the methods that all of your plugins must implement
    """

    def __init__(self):
        self.name = ""
        self.description = ""
        self.command_map = {}
        self.verify_required_commands = []
        self.continuous_verification_commands = []
        self.end_test_on_fail_commands = []

    def initialize(self):
        log.warn("Plugin does not implement initialize!")

    def process_command(self, **kwargs):
        ret = False
        instruction = kwargs["instruction"]
        if "data" in kwargs.keys():
            data = kwargs["data"]

        if instruction in self.command_map.keys():
            func = self.command_map[instruction][0]
            sig = signature(func)
            req_args = 0
            optional_args = 0
            for key, value in sig.parameters.items():
                if value.default == inspect._empty:
                    req_args += 1
                else:
                    optional_args += 1

            if req_args <= len(data) <= (req_args + optional_args):
                try:
                    ret = func(**data)
                except Exception as e:
                    log.error("Error Applying Function {}".format(func))
                    traceback.format_exc(e)

            elif (len(data) == 0 and (req_args + optional_args) == 0):
                try:
                    ret = func()
                except Exception as e:
                    log.error("Error Applying Function {}".format(func))
                    raise
            else:
                log.error("Invalid number of parameters passed to %s. Expected at least %s args" % (instruction, req_args))
                ret = False
        if ret is None and instruction not in self.verify_required_commands:
            log.warn("Plugin Execution Result for {} is None. Please ensure all plugin instructions \
                     return a boolean result.".format(instruction))
        return ret

    def shutdown(self):
        pass


class PluginManager(object):
    """Upon creation, this class will read the plugins package for modules
    that contain a class definition that is inheriting from the Plugin class
    """

    def __init__(self, plugin_packages):
        """Constructor that initiates the reading of all available plugins
        when an instance of the PluginManager object is created
        """
        Global.plugin_manager = self
        self.plugin_packages = plugin_packages
        self.plugins = {}

        self.plugin_name_list = []
        self.reload_plugins()

    def initialize_plugins(self):
        for plugin in self.plugins.values():
            plugin.initialize()

    def shutdown_plugins(self):
        for plugin in self.plugins.values():
            plugin.shutdown()

    def find_plugin_for_command(self, command):
        for pluginName, plugin in self.plugins.items():
            if command in plugin.command_map.keys():
                return plugin
        return None

    def find_plugin_for_command_and_execute(self, command):
        instruction = command["instruction"]
        data = command["data"]
        ret = False
        plugin_to_use = self.find_plugin_for_command(instruction)
        if plugin_to_use is not None:
            ret = plugin_to_use.process_command(instruction=instruction, data=data)
        else:
            log.error("No plugin found for command {}".format(instruction))
        return ret

    def reload_plugins(self):
        """Reset the list of all plugins and initiate the walk over the main
        provided plugin package to load all available plugins
        """
        self.plugins = {}
        self.seen_paths = []
        self.plugin_name_list = []
        self.disabled_plugins = Config.get("core", "disabled_plugins").split(',') \
            if Config.has_option("core", "disabled_plugins") else []
        for plugin_package in self.plugin_packages:
            log.info("Looking for plugins under package: {}".format(plugin_package))
            if not os.path.exists(plugin_package) and plugin_package != "plugins":
                log.error("Invalid plugin path: {}. Skipping... ".format(plugin_package))
                continue
            cwd = os.getcwd()
            if os.path.dirname(plugin_package) != "":
                sys.path.insert(1, os.path.dirname(plugin_package))
            self.walk_package(plugin_package)
            os.chdir(cwd)
            Global.plugins_available = self.plugins


    def walk_package(self, package):
        """Recursively walk the supplied package to retrieve all plugins
        """

        # Skip pycache modules
        if 'pycache' in package:
            return

        imported_package = __import__(os.path.basename(package), fromlist=[''])
        if '.' in package and package.split('.')[-1] in self.disabled_plugins:
            log.info("    Plugin {} in disable plugins list. Skipping...".format(package))
            return

        for _, pluginname, ispkg in pkgutil.iter_modules(imported_package.__path__, imported_package.__name__ + '.'):
            if not ispkg:
                plugin_module = __import__(pluginname, fromlist=[''])
                clsmembers = inspect.getmembers(plugin_module, inspect.isclass)
                for (_, c) in clsmembers:
                    # Only add classes that are a sub class of Plugin, but NOT Plugin itself
                    if issubclass(c, Plugin) & (c is not Plugin):
                        log.info('\tFound plugin class: {}.{}'.format(
                            c.__module__,
                            c.__name__
                        ))
                        newObj = c()
                        name = newObj.name
                        self.plugins[name] = newObj
                        self.plugin_name_list.append(name)

        # Now that we have looked at all the modules in the current package, start looking
        # recursively for additional modules in sub packages
        all_current_paths = []
        if isinstance(imported_package.__path__, str):
            all_current_paths.append(imported_package.__path__)
        else:
            all_current_paths.extend([x for x in imported_package.__path__])

        for pkg_path in all_current_paths:
            if pkg_path not in self.seen_paths:
                self.seen_paths.append(pkg_path)

                # Get all sub directory of the current package path directory
                child_pkgs = [p for p in os.listdir(pkg_path) if os.path.isdir(os.path.join(pkg_path, p))]

                # For each sub directory, apply the walk_package method recursively
                for child_pkg in child_pkgs:
                    self.walk_package(package + '.' + child_pkg)

    def create_plugin_info(self, directory):
        if not os.path.exists(directory):
            os.mkdir(directory)

        if not os.path.isdir(directory):
            raise Exception("{} is not a directory! ".format(directory))

        for pluginName, plugin in self.plugins.items():
            pluginInfo = deepcopy(PluginInfo)
            pluginInfo["group_name"] = pluginName
            pluginInfo["description"] = plugin.description
            for command, func in plugin.command_map.items():
                param_index = 0
                commandInfo = deepcopy(CommandInfo)
                commandInfo["name"] = command
                commandInfo["description"] = ""
                parameters = signature(plugin.command_map[command][0]).parameters
                for key, parameter in parameters.items():
                    parameterInfo = deepcopy(ParameterInfo)
                    parameterInfo["name"] = parameter.name
                    parameterInfo["description"] = ""
                    # If the argument is optional and has no type in the command map, ignore it
                    if param_index >= len(plugin.command_map[command][1]) and parameter.default != inspect._empty:
                        log.warn("Parameter {} is optional in plugin {} and is not defined in the command map. Skipping...".format(
                            parameter.name, pluginName))
                        continue
                    elif param_index >= len(plugin.command_map[command][1]):
                        log.error("Parameter \"{}\" is required for command \"{}\".".format(parameter.name, command))
                        log.error(
                            "Plugin info generation failed. Please update the command map with the required arguments.")
                        return
                    parameterInfo["type"] = plugin.command_map[command][1][param_index]

                    # Skip parameters of type ignore (useful for mapping 2 commands to the same function w/ different parameters)
                    if (parameterInfo["type"] == ArgTypes.ignore):
                        continue
                    if (parameterInfo["type"] in ArgTypes.array_types):
                        parameterInfo["isArray"] = True
                    commandInfo["parameters"].append(parameterInfo)
                    param_index += 1
                pluginInfo["instructions"].append(commandInfo)
            with open(os.path.join(directory, pluginName) + ".json", 'w') as outfile:
                json.dump(pluginInfo, outfile, indent=2)
