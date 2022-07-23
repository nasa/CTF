"""
@namespace lib.test_test_script.py
Unit Test for TestScript: Loads and validates input CTF test scripts. Manages execution of loaded test scripts.
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

from unittest.mock import Mock

import pytest

from lib.exceptions import CtfTestError
from lib.status import StatusDefs
from lib.status_manager import StatusManager
from lib.test_script import TestScript


@pytest.fixture(name="test_script_instance")
def _test_script_instance():
    return TestScript()


def test_test_script_init(test_script_instance):
    """
    Test TestScript class constructor
    """
    assert test_script_instance.test_number is None
    assert test_script_instance.test_name is None
    assert test_script_instance.requirements is None
    assert test_script_instance.test_description is None
    assert test_script_instance.options is None
    assert test_script_instance.telem_watch_list is None
    assert test_script_instance.cmd_watch_list is None
    assert test_script_instance.test_owner is None
    assert test_script_instance.test_setup is None
    assert test_script_instance.verify_timeout is None
    assert not test_script_instance.tests
    assert test_script_instance.input_file_path is None
    assert test_script_instance.input_file is None
    assert test_script_instance.params == ""
    assert test_script_instance.status == ""
    assert test_script_instance.start_time == 0
    assert test_script_instance.exec_time == 0
    assert test_script_instance.num_tests == 0
    assert test_script_instance.num_passed == 0
    assert test_script_instance.failed_tests == []
    assert test_script_instance.num_error == 0


def test_test_script_set_header_info(test_script_instance):
    """
    Test TestScript class method: set_header_info
    Set the TestScript's header information from the input test script file.
    """
    test_number = 'CFE-ES-Functions-Test'
    test_name = 'CFE ES Functions Test'
    requirements = 'MyRequirement'
    test_description = 'Testing CFE ES Functions'
    test_owner = 'CTF'
    test_setup = 'Example Script Showing ES function usage'
    verify_timeout=None
    test_script_instance.set_header_info(test_number, test_name, requirements, test_description,
                                         test_owner, test_setup, verify_timeout)

    assert test_script_instance.test_number == test_number
    assert test_script_instance.test_name == test_name
    assert test_script_instance.requirements == requirements
    assert test_script_instance.test_description == test_description
    assert test_script_instance.test_owner == test_owner
    assert test_script_instance.test_setup == test_setup
    assert test_script_instance.verify_timeout == verify_timeout


def test_test_script_set_watch_lists(test_script_instance):
    """
    Test TestScript class method: set_watch_lists
    Set the TestScript's telemetry and command watch lists.
    """
    telem_watch_list = ['CFE_EVS_HK_TLM_MID']
    cmd_watch_list = ['CFE_EVS_CMD_MID']
    test_script_instance.set_watch_lists(telem_watch_list, cmd_watch_list)
    assert test_script_instance.telem_watch_list == telem_watch_list
    assert test_script_instance.cmd_watch_list == cmd_watch_list


def test_test_script_set_options(test_script_instance):
    """
    Test TestScript class method: set_options
    Set the TestScript's options from the input test script file.
    """
    options = {}
    assert test_script_instance.set_options(options) is None
    assert test_script_instance.options == options


def test_test_script_run_script_exception(test_script_instance):
    """
    Test TestScript class method run_script: raise exception
    Execute a complete test script, updating the status_manager as needed.
    """
    status_manager = StatusManager(port=None)
    script = {'status': 'waiting','details':'','elapsed_time': 0}
    status_manager.start_time = 0
    status_manager.set_scripts([])
    status_manager.status["scripts"] = [script]
    with pytest.raises(CtfTestError):
        test_script_instance.run_script(status_manager)


def test_test_script_run_script(test_script_instance,utils):
    """
    Test TestScript class method run_script:
    Execute a complete test script, updating the status_manager as needed.
    """
    status_manager = StatusManager(port=None)
    script = {'status': 'waiting','details':'','elapsed_time': 0}
    status_manager.start_time = 0
    status_manager.set_scripts([])
    status_manager.status["scripts"] = [script]

    test_script_instance.set_header_info('CFE-ES-Functions-Test', 'CFE ES Functions Test', 'MyRequirement',
                                         'Testing CFE ES Functions', 'CTF', 'Example Script', 4)
    test_script_instance.input_file = 'CfeEsTest.json'

    test1 = Mock()
    test1.run_test.side_effect = [ StatusDefs.aborted ]
    test_list = [test1]
    test_script_instance.set_tests(test_list)
    utils.clear_log()

    assert test_script_instance.run_script(status_manager) is None
    assert utils.has_log_level('ERROR')



def test_test_script_set_tests(test_script_instance):
    """
    Test TestScript class method: set_tests
    Set the list of test cases within this test script
    """
    test_list = []
    assert test_script_instance.set_tests(test_list) is None
    assert test_script_instance.tests == test_list


def test_test_script_log_test_header(test_script_instance):
    """
    Test TestScript class method: log_test_header
    Log the test header (metadata) before beginning test execution
    """
    test_script_instance.set_header_info('CFE-ES-Functions-Test', 'CFE ES Functions Test', 'MyRequirement',
                                         'Testing CFE ES Functions', 'CTF', 'Example Script', 4)
    test_script_instance.input_file = 'CfeEsTest.json'
    assert test_script_instance.log_test_header() is None


def test_test_script_generate_test_results(test_script_instance):
    """
    Test TestScript class method: generate_test_results
    Generate and Log the test results after test execution
    """
    test1 = Mock()
    test1.test_info = {"test_number": "test1"}
    test1.test_run = True
    test1.test_result = True

    test2 = Mock()
    test2.test_info = {"test_number": "test2"}
    test2.test_run = True
    test2.test_result = False

    test_list = [test1, test2, test1, test2]
    test_script_instance.set_tests(test_list)
    test_script_instance.set_header_info('CFE-ES-Functions-Test', 'CFE ES Functions Test', 'MyRequirement',
                                         'Testing CFE ES Functions', 'CTF', 'Example Script', 4)
    test_script_instance.input_file = 'CfeEsTest.json'

    assert test_script_instance.generate_test_results() is None
    assert test_script_instance.num_passed == 2
    assert test_script_instance.failed_tests == ['test2', 'test2']



