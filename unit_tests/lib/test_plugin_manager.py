"""
@namespace tests.lib.test_plugin_manager.py
Unit Test for Plugin class: The Plugin Manager is a CTF core component that manages CTF plugins.
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


from unittest.mock import patch
import pytest
from mock import Mock

from lib.plugin_manager import Plugin, PluginManager, ArgTypes


@pytest.fixture(name="plugin")
def _plugin_instance():
    return Plugin()


@pytest.fixture(name="plugin_manager")
def _plugin_manager_instance():
    return PluginManager(['plugins'])


def test_plugin_init(plugin):
    """
    test Plugin class constructor
    """
    assert plugin.name == ""
    assert plugin.description == ""
    assert len(plugin.command_map) == 0
    assert len(plugin.verify_required_commands) == 0
    assert len(plugin.continuous_verification_commands) == 0
    assert len(plugin.end_test_on_fail_commands) == 0


def test_plugin_process_command(plugin, utils):
    """
    test Plugin class method: process_command
    Given a CTF Test Instruction, this function finds the first plugin that "contains" that test instruction within
    its command map. Once a valid plugin is found, the implementation of that instruction is invoked using
    keyworded variable length of arguments in kwargs.
    """
    kwargs = {'instruction': 'StartCfs', 'data': {'target': '', 'run_args': ''}}
    mock_func = Mock()
    mock_func.return_value = None

    plugin.command_map = {'StartCfs': (mock_func, ['string', 'string'])}
    plugin.verify_required_commands = ['CheckTlmValue', 'CheckTlmPacket', 'CheckNoTlmPacket']

    plugin.process_command(**kwargs)


def test_plugin_initialize(plugin, utils):
    """
    test Plugin class method: initialize
    Virtual initialize method definition. Must be overridden by child Plugin class.
    """
    utils.clear_log()
    assert plugin.initialize() is None
    assert utils.has_log_level("WARNING")


def test_plugin_shutdown(plugin, utils):
    """
    test Plugin class method: shutdown
    Virtual shutdown method definition. Must be overridden by child Plugin class.
    """
    utils.clear_log()
    assert plugin.shutdown() is None
    assert utils.has_log_level("WARNING")


def test_plugin_manager_init(plugin_manager):
    """
    test PluginManager class constructor
    """
    assert plugin_manager.plugin_packages == ['plugins']
    assert len(plugin_manager.plugins) == 8
    assert 'CCSDS Plugin' in plugin_manager.plugins
    assert 'CFS Plugin' in plugin_manager.plugins
    assert 'ExamplePlugin' in plugin_manager.plugins
    assert 'SshPlugin' in plugin_manager.plugins
    assert 'UserIOPlugin' in plugin_manager.plugins
    assert 'ControlFlow Plugin' in plugin_manager.plugins
    assert 'VariablePlugin' in plugin_manager.plugins
    assert 'ValidationPlugin' in plugin_manager.plugins
    assert len(plugin_manager.plugin_name_list) == 8
    assert 'CCSDS Plugin' in plugin_manager.plugin_name_list
    assert 'CFS Plugin' in plugin_manager.plugin_name_list
    assert 'ExamplePlugin' in plugin_manager.plugin_name_list
    assert 'SshPlugin' in plugin_manager.plugin_name_list
    assert 'UserIOPlugin' in plugin_manager.plugin_name_list
    assert 'ControlFlow Plugin' in plugin_manager.plugin_name_list
    assert 'VariablePlugin' in plugin_manager.plugin_name_list
    assert 'ValidationPlugin' in plugin_manager.plugin_name_list


def test_plugin_manager_initialize_plugins(plugin_manager):
    """
    test PluginManager class method: initialize_plugins
    After loading all plugins, this function calls initialize() on all loaded plugins within the plugin manager
    """
    assert plugin_manager.initialize_plugins() is None


def test_plugin_manager_shutdown_plugins(plugin_manager):
    """
    test PluginManager class method: shutdown_plugins
    Before CTF shutdown (or on plugin restart), this function calls shutdown() on all loaded plugins within
    the plugin manager
    """
    assert plugin_manager.shutdown_plugins() is None


def test_plugin_manager_find_plugin_for_command(plugin_manager):
    """
    test PluginManager class method: find_plugin_for_command
    Given a CTF Test Instruction, find the plugin instance that can execute that instruction.
    """
    assert plugin_manager.find_plugin_for_command('StartCfs') == plugin_manager.plugins['CFS Plugin']
    assert plugin_manager.find_plugin_for_command('FailInstruction') is None


def test_plugin_manager_find_plugin_for_command_and_execute(plugin_manager, utils):
    """
    test PluginManager class method: find_plugin_for_command_and_execute
    Given a CTF Test Instruction, find the plugin instance that can execute that instruction, execute the
    instruction and return the instruction status (pass/fail)
    """
    utils.clear_log()
    instruction = {'data': {'target': 'cfs', 'cc': 'TO_ENABLE_OUTPUT_CC',
                            'args': {'cDestIp': '127.0.0.1', 'usDestPort': 5011},
                            'mid': 10891}, 'instruction': 'Fail_Command'}
    #  no plugin found
    assert not plugin_manager.find_plugin_for_command_and_execute(instruction)
    assert utils.has_log_level('ERROR')

    instruction = {'data': {'target': 'cfs', 'cc': 'TO_ENABLE_OUTPUT_CC',
                            'args': {'cDestIp': '127.0.0.1', 'usDestPort': 5011},
                            'mid': 10891}, 'instruction': 'SendCfsCommand'}
    #  SendCfsCommand fail
    assert not plugin_manager.find_plugin_for_command_and_execute(instruction)
    #  SendCfsCommand pass
    with patch("lib.plugin_manager.Plugin.process_command", return_value=True):
        assert plugin_manager.find_plugin_for_command_and_execute(instruction)


def test_plugin_manager_walk_package_skip_disabled_plugins(plugin_manager):
    """
    test PluginManager class method: walk_package
    Recursively walk the supplied package to retrieve all plugins
    """
    plugin_manager.disabled_plugins.append('cfe')
    plugin_manager.walk_package('plugins.ccsds_plugin.cfe')


def test_plugin_manager_reload_plugins(plugin_manager, utils):
    """
    test PluginManager class method: reload_plugins
    Reset the list of all plugins and initiate the walk over the main
    provided plugin package to load all available plugins
    """
    assert plugin_manager.reload_plugins() is None
    assert len(plugin_manager.plugin_name_list) == 8
    assert 'CCSDS Plugin' in plugin_manager.plugin_name_list
    assert 'CFS Plugin' in plugin_manager.plugin_name_list
    assert 'ExamplePlugin' in plugin_manager.plugin_name_list
    assert 'SshPlugin' in plugin_manager.plugin_name_list
    assert 'UserIOPlugin' in plugin_manager.plugin_name_list
    assert 'ControlFlow Plugin' in plugin_manager.plugin_name_list
    assert 'VariablePlugin' in plugin_manager.plugin_name_list
    assert 'ValidationPlugin' in plugin_manager.plugin_name_list

    utils.clear_log()
    plugin_manager.plugin_packages = ['plugins_fail']
    assert plugin_manager.reload_plugins() is None
    assert utils.has_log_level('ERROR')

    plugin_manager.plugin_packages = ['plugins/cfs']
    assert plugin_manager.reload_plugins() is None


def test_plugin_manager_create_plugin_info(plugin_manager, utils):
    """
    test PluginManager class method: create_plugin_info
    Outputs the plugin information files in JSON format for utilization by the CTF editor or other tools.
    """
    assert plugin_manager.create_plugin_info('plugin_info_output') is None

    plugin_manager.plugins['ExamplePlugin'].command_map['TestCommand'] = \
        (plugin_manager.plugins['ExamplePlugin'].command_map['TestCommand'][0], [ArgTypes.ignore])
    assert plugin_manager.create_plugin_info('plugin_info_output') is None


def test_plugin_manager_create_plugin_info_fail(plugin_manager, utils):
    """
    test PluginManager class method: create_plugin_info  -- invalid argument list
    Outputs the plugin information files in JSON format for utilization by the CTF editor or other tools.
    """
    utils.clear_log()
    # manipulate command map to trigger error
    cfs_plugin = plugin_manager.plugins['CFS Plugin']
    command_tuple = cfs_plugin.command_map['SendCfsCommandWithPayloadLength']
    # clear command map argument list to trigger error
    command_tuple[1].clear()
    assert plugin_manager.create_plugin_info('plugin_info_output') is None
    assert utils.has_log_level('ERROR')


def test_plugin_manager_create_plugin_info_exception(plugin_manager, utils):
    """
    test PluginManager class method: create_plugin_info  -- raise exception if os.path.isdir is False
    Outputs the plugin information files in JSON format for utilization by the CTF editor or other tools.
    """
    with patch("os.path.isdir", return_value=False):
        with pytest.raises(Exception):
            plugin_manager.create_plugin_info('plugin_info_output')
