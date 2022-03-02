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
import pytest

from lib.exceptions import CtfTestError
from plugins.example_plugin.example_plugin import ExamplePlugin


@pytest.fixture(name="plugin")
def example_plugin():
    return ExamplePlugin()


# test plugin init
def test_initialize(plugin):
    assert plugin.initialize()
    assert plugin.example_counter == 0


# test plugin contents
def test_command_map(plugin):
    assert len(plugin.command_map) == 3
    assert "TestCommand" in plugin.command_map
    assert "TestVerifyCommand" in plugin.command_map
    assert "TestSharedLibraryCommand" in plugin.command_map


# test each plugin command
def test_verify_required_commands(plugin):
    assert len(plugin.verify_required_commands) == 1
    assert "TestVerifyCommand" in plugin.verify_required_commands


def test_test_command(plugin):
    assert plugin.test_command("foo", "bar")
    # test log contents?


def test_example_plugin_process_command_exception(plugin):
    """
    test Plugin class method: process_command  -- raise exception
    Given a CTF Test Instruction, this function finds the first plugin that "contains" that test instruction within
    its command map. Once a valid plugin is found, the implementation of that instruction is invoked using
    keyword variable length of arguments in kwargs.
    """
    instruction = 'TestVerifyCommand'
    data = []
    with pytest.raises(CtfTestError):
        plugin.process_command(instruction=instruction, data=data)

    plugin.process_command(instruction=instruction, data={})


def test_test_verify_command(plugin):
    assert plugin.example_counter == 0
    assert not plugin.test_verify_command()
    assert plugin.example_counter == 1
    assert not plugin.test_verify_command()
    assert plugin.example_counter == 2
    assert not plugin.test_verify_command()
    assert plugin.example_counter == 3
    assert not plugin.test_verify_command()
    assert plugin.example_counter == 4
    assert not plugin.test_verify_command()
    assert plugin.example_counter == 5
    assert plugin.test_verify_command()
    assert plugin.example_counter == 6


def test_test_shared_library(plugin):
    assert ExamplePlugin.test_shared_library()
    # test log contents?


def test_shutdown(plugin):
    assert plugin.shutdown() is None
