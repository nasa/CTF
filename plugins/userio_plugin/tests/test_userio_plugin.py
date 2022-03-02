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

"""
 test_userio_plugin.py: Unit Test for UserIO Plugin.
"""

from unittest.mock import patch
import pytest

from lib.exceptions import CtfTestError
from lib.plugin_manager import ArgTypes


def test_userio_name(userio_instance):
    """
    Test UserIOPlugin name
    """
    assert userio_instance.name == 'UserIOPlugin'


def test_userio_description(userio_instance):
    """
    Test UserIOPlugin description
    """
    assert userio_instance.description == 'CTF UserIO Plugin'


def test_userio_command_map(userio_instance):
    """
    Test UserIOPlugin command_map attribute
    """
    assert "WaitForUserInput" in userio_instance.command_map
    assert userio_instance.command_map == {"WaitForUserInput":
                                               (userio_instance.waituserinput_command, [ArgTypes.string])}


def test_userio_end_test_on_fail_commands(userio_instance):
    """
    Test UserIOPlugin end_test_on_fail_commands attribute
    """
    assert "WaitForUserInput" in userio_instance.end_test_on_fail_commands


def test_userio_initialize(userio_instance):
    """
    Test UserIOPlugin initialize method
    """
    assert userio_instance.initialize()


def test_userio_waituserinput_enter_y(userio_instance):
    """
    Test UserIOPlugin waituserinput_command method: emulate user input 'y'
    """
    with patch('plugins.userio_plugin.userio_plugin.input', return_value='y'):
        assert userio_instance.waituserinput_command('wait for user input:')


def test_userio_process_command(userio_instance):
    """
    test Plugin class method: process_command
    Given a CTF Test Instruction, this function finds the first plugin that "contains" that test instruction within
    its command map. Once a valid plugin is found, the implementation of that instruction is invoked using
    keyword variable length of arguments in kwargs.
    """
    instruction= 'WaitForUserInput'
    data = {'prompt': '  '}
    with patch('plugins.userio_plugin.userio_plugin.input') as mock_input:
        mock_input.return_value = 'Y'
        assert userio_instance.process_command(instruction=instruction, data=data)


def test_userio_process_command_fail(userio_instance):
    """
    test Plugin class method: process_command  -- invalid argument
    Given a CTF Test Instruction, this function finds the first plugin that "contains" that test instruction within
    its command map. Once a valid plugin is found, the implementation of that instruction is invoked using
    keyword variable length of arguments in kwargs.
    """
    instruction= 'WaitForUserInput'
    data = {'prompt': '  ', 'prompt1': '  ', 'prompt2': '  ' }
    with patch('plugins.userio_plugin.userio_plugin.input') as mock_input:
        mock_input.return_value = 'Y'
        assert not userio_instance.process_command(instruction=instruction, data=data)


def test_userio_process_command_exception(userio_instance):
    """
    test Plugin class method: process_command -- raise exception
    Given a CTF Test Instruction, this function finds the first plugin that "contains" that test instruction within
    its command map. Once a valid plugin is found, the implementation of that instruction is invoked using
    keyword variable length of arguments in kwargs.
    """
    instruction= 'WaitForUserInput'
    data = {'prompt': '  '}
    with patch('plugins.userio_plugin.userio_plugin.input') as mock_input:
        mock_input.side_effect = Exception("Raise Exception from WaitForUserInput")
        with pytest.raises(CtfTestError):
            assert userio_instance.process_command(instruction=instruction, data=data)
            mock_input.assert_called_once()


def test_userio_waituserinput_enter_yes(userio_instance):
    """
    Test UserIOPlugin waituserinput_command method: emulate user input 'yes',
    expect return False for any input other than 'y' or 'Y'
    """
    with patch('plugins.userio_plugin.userio_plugin.input') as mock_input:
        mock_input.return_value = 'yes'
        assert not userio_instance.waituserinput_command('wait for user input:')


def test_userio_waituserinput_enter_abc(userio_instance):
    """
    Test UserIOPlugin waituserinput_command method: emulate user input 'abc',
    expect return False for any input other than 'y' or 'Y'
    """
    with patch('plugins.userio_plugin.userio_plugin.input') as mock_input:
        mock_input.return_value = 'abc'
        assert not userio_instance.waituserinput_command('wait for user input:')


def test_userio_waituserinput_enter_any(userio_instance):
    """
    Test UserIOPlugin waituserinput_command method: emulate user input 'any',
    expect return False for any input other than 'y' or 'Y'
    """
    with patch('plugins.userio_plugin.userio_plugin.input') as mock_input:
        mock_input.return_value = 'any'
        assert not userio_instance.waituserinput_command('wait for user input:')


def test_userio_waituserinput_enter_yy(userio_instance):
    """
    Test UserIOPlugin waituserinput_command method: emulate user input 'yy',
    expect return False for any input other than 'y' or 'Y'
    """
    with patch('plugins.userio_plugin.userio_plugin.input', return_value='yy'):
        assert not userio_instance.waituserinput_command('wait for user input:')


def test_userio_waituserinput_enter_upper_y(userio_instance):
    """
    Test UserIOPlugin waituserinput_command method: emulate user input 'Y'
    """
    with patch('plugins.userio_plugin.userio_plugin.input', return_value='Y'):
        assert userio_instance.waituserinput_command('wait for user input:')


def test_userio_waituserinput_enter_n(userio_instance):
    """
    Test UserIOPlugin waituserinput_command method: emulate user input 'n'
    """
    with patch('plugins.userio_plugin.userio_plugin.input') as mock_input:
        mock_input.return_value = 'n'
        assert not userio_instance.waituserinput_command('wait for user input:')


def test_userio_waituserinput_enter_upper_n(userio_instance):
    """
    Test UserIOPlugin waituserinput_command method: emulate user input 'N'
    """
    with patch('plugins.userio_plugin.userio_plugin.input') as mock_input:
        mock_input.return_value = 'N'
        assert not userio_instance.waituserinput_command('wait for user input:')


def test_userio_shutdown(userio_instance):
    """
    Test UserIOPlugin shutdown method
    """
    assert userio_instance.shutdown() is None
