"""
@namespace lib.test_status_manager.py
Unit Test for StatusManager: Publishes CTF status messages over a UDP socket (utilized by the CTF editor)
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

import copy
import socket
from unittest.mock import patch

import pytest

from lib.readers.json_script_reader import JSONScriptReader
from lib.status import StatusDefs
from lib.status_manager import StatusManager


@pytest.fixture(name="status_manager_instance")
def _status_manager_instance():
    return StatusManager()


@pytest.fixture(name="status_manager_instance_inited")
def _status_manager_instance_inited():
    status_manager = StatusManager()
    script_reader = JSONScriptReader('functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json')
    script_list = [script_reader.script]
    status_manager.set_scripts(script_list)
    return status_manager


def test_status_manager_init(status_manager_instance):
    """
    Test StatusManager class constructor
    """
    assert status_manager_instance.script_index == 0
    assert status_manager_instance.test_index == 0
    assert status_manager_instance.command_index == 0
    assert status_manager_instance.ip_address == '127.0.0.1'
    assert status_manager_instance.port is None
    assert status_manager_instance.socket is None
    assert status_manager_instance.start_time is None


def test_status_manager_start(status_manager_instance):
    """
    Test StatusManager class method: start
    Set the start time of test suite execution in the status message.
    """
    assert status_manager_instance.start_time is None
    assert status_manager_instance.start() is None
    assert status_manager_instance.start_time is not None


def test_status_manager_set_scripts(status_manager_instance):
    """
    Test StatusManager class method: set_scripts
    Set the script status entry for each script with default values
    """
    init_status = {'elapsed_time': 0, 'status': 'waiting', 'scripts': []}
    assert status_manager_instance.status is None

    script_reader = JSONScriptReader('functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json')
    script_list = [script_reader.script]

    script_list[0].tests[0].instructions[1].command.pop('wait')

    status_manager_instance.set_scripts(script_list)

    assert status_manager_instance.status['scripts'][0]['tests'][0]['test_number'] == 'CFE-ES-Functions-Test-1'
    assert status_manager_instance.status['scripts'][0]['tests'][0]['status'] == 'waiting'
    assert status_manager_instance.status['scripts'][0]['tests'][0]['instructions'][0]['instruction'] == 'StartCfs'
    assert status_manager_instance.status['scripts'][0]['tests'][0]['instructions'][1][
               'instruction'] == 'EnableCfsOutput'


def test_status_manager_update_suite_status(status_manager_instance):
    """
    Test StatusManager class method: update_suite_status
    Given an updated status (and details), update the suite status with the latest state.
    """
    details = 'Runing Script'
    status = 'Active'
    status_manager_instance.start_time = 0
    status_manager_instance.set_scripts([])
    status_manager_instance.update_suite_status(status, details)
    assert status_manager_instance.status["status"] == status
    assert status_manager_instance.status["details"] == details


def test_status_manager_update_test_status(status_manager_instance_inited):
    """
    Test StatusManager class method: update_test_status
    Update the status of a single script within the test suite.
    """
    details = 'StartCfs'
    status = 'passed'
    status_manager_instance_inited.start_time = 0

    status_manager_instance_inited.update_test_status(status, details)
    assert status_manager_instance_inited.status["scripts"][0]["tests"][0]["status"] == status
    assert status_manager_instance_inited.status["scripts"][0]["tests"][0]["details"] == details


def test_status_manager_update_command_status(status_manager_instance_inited):
    """
    Test StatusManager class method: update_command_status
    Update the status of a single command within a test script.
    """
    details = ''
    status = 'passed'
    status_manager_instance_inited.start_time = 0

    status_manager_instance_inited.update_command_status(status, details)
    assert status_manager_instance_inited.status["scripts"][0]["tests"][0]["instructions"][0]["status"] == status


def test_status_manager_finalize_suite_status(status_manager_instance_inited):
    """
    Test StatusManager class method: finalize_suite_status
    Set the test suit status (pass/fail) based on the status of all scripts within the suite.
    """
    status_manager_instance_inited.finalize_suite_status()
    assert status_manager_instance_inited.status["status"] == StatusDefs.failed


def test_status_manager_end_command(status_manager_instance):
    """
    Test StatusManager class method: end_command
    Set the start time of test suite execution in the status message.
    """
    assert status_manager_instance.command_index == 0
    assert status_manager_instance.end_command() is None
    assert status_manager_instance.command_index == 1
    assert status_manager_instance.end_command() is None
    assert status_manager_instance.command_index == 2


def test_status_manager_end_test(status_manager_instance):
    """
    Test StatusManager class method: end_test
    Increment the current active test case index. Reset the command index to 0.
    """
    assert status_manager_instance.end_test() is None
    assert status_manager_instance.command_index == 0
    assert status_manager_instance.test_index == 1


def test_status_manager_end_script(status_manager_instance):
    """
    Test StatusManager class method: end_script
    Increment the current active script. Reset the test and command indices to 0.
    """
    assert status_manager_instance.end_script() is None
    assert status_manager_instance.command_index == 0
    assert status_manager_instance.test_index == 0
    assert status_manager_instance.script_index == 1


def test_status_manager_sanitize_param(status_manager_instance):
    """
    Test StatusManager class static method: sanitize_param
    Sanitize a test instruction parameter by attempting to decode it if needed
    """
    assert status_manager_instance.sanitize_param('active') == 'active'
    assert StatusManager.sanitize_param(b'active') == 'active'


def test_status_manager_sanitize_data(status_manager_instance):
    """
    Test StatusManager class static method: sanitize_data
    Sanitize test instruction data by attempting to decode every field if needed
    """
    data = {"args": [{"compare": "==", "variable": "Payload.CommandCounter", "value": [1.0]}]}
    data_list = [{"compare": "==", "variable": "Payload.CommandCounter", "value": [1.0]}]
    assert status_manager_instance.sanitize_data(data) == data_list

    assert status_manager_instance.sanitize_data(data_list) == data_list

    assert status_manager_instance.sanitize_data(None) is None


def test_status_manager_sanitize_data_decode(status_manager_instance):
    """
    Test StatusManager class static method: sanitize_data  -- test case : decode binary string
    Sanitize test instruction data by attempting to decode every field if needed
    """
    data_byte = [{"compare": "==", "variable": b"Payload.CommandCounter", "value": [1.0]}]
    assert status_manager_instance.sanitize_data(data_byte) == [{"compare": "==", "variable": "Payload.CommandCounter",
                                                                 "value": [1.0]}]

    data_byte = ["compare", b"variable", "value"]
    assert status_manager_instance.sanitize_data(data_byte) == ["compare", "variable", "value"]


def test_status_manager_sanitize_data_exception(status_manager_instance, utils):
    """
    Test StatusManager class static method: sanitize_data  -- raise exception
    Sanitize test instruction data by attempting to decode every field if needed
    """
    data_byte = [{"compare": "==", "variable": b"Payload.CommandCounter", "value": [1.0]}]
    with patch('builtins.bytes') as mock_bytes:
        utils.clear_log()
        mock_bytes.return_value.decode = UnicodeDecodeError
        assert status_manager_instance.sanitize_data(data_byte) is None
        assert utils.has_log_level('ERROR')


def test_status_manager_sanitize_status(status_manager_instance):
    """
    Test StatusManager class method: sanitize_status
    Sanitize test script data by attempting to decode every field at the test script level if needed
    """
    test_status = {'elapsed_time': 0, 'status': 'waiting', 'scripts': [
        {'path': 'CfeEsTest.json', 'test_name': 'CFE ES Functions Test', 'status': 'passed', 'details': 'Running',
         'tests': [{'test_number': b'CFE-6-7-Plugin-Test-001', 'status': 'passed', 'details': '',
                    'instructions': [{'instruction': 'StartCfs', 'wait': 1, 'data': {'target': ''}, 'status': 'passed',
                                      'details': '', 'comment': '', 'description': ''},
                                     {'instruction': 'SendCfsCommand', 'wait': 0,
                                      'data': {'target': '', 'mid': 'CFE_ES_CMD_MID',
                                               'cc': 'CFE_ES_NOOP_CC', 'args': {}}
                                         , 'status': 'passed', 'details': '', 'comment': '', 'description': ''}
                                     ]}]
         }
    ]}

    status_manager_instance.status = test_status
    result = status_manager_instance.sanitize_status()

    duplicated_status = copy.deepcopy(test_status)
    duplicated_status['scripts'][0]['tests'][0]['test_number'] = 'CFE-6-7-Plugin-Test-001'

    assert result == duplicated_status


def test_status_manager_send_update(status_manager_instance_inited):
    """
    Test StatusManager class method: send_update
    Send the latest status packet over the UDP socket.
    """
    status_manager_instance_inited.start()
    status_manager_instance_inited.port = 5004
    status_manager_instance_inited.send_update()


def test_status_manager_send_update_exception_connect(status_manager_instance_inited, utils):
    """
    Test StatusManager class method: send_update - raise exception from connect
    Send the latest status packet over the UDP socket.
    """
    status_manager_instance_inited.start()
    status_manager_instance_inited.port = 5004
    utils.clear_log()

    with patch('socket.socket.connect') as mock_connect:
        mock_connect.side_effect = socket.error()
        status_manager_instance_inited.send_update()
        assert utils.has_log_level('ERROR')


def test_status_manager_send_update_exception_sendall(status_manager_instance_inited, utils):
    """
    Test StatusManager class method: send_update - raise exception from sendall
    Send the latest status packet over the UDP socket.
    """
    status_manager_instance_inited.start()
    status_manager_instance_inited.port = 5004
    utils.clear_log()

    with patch('socket.socket.sendall') as mock_sendall:
        mock_sendall.side_effect = socket.error()
        status_manager_instance_inited.send_update()
        assert utils.has_log_level('ERROR')
