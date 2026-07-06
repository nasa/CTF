# =========================================================================================
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
# distributed and modified only pursuant to the terms of that agreement.
# See the License for the specific language governing permissions and limitations under the
# License at https://software.nasa.gov/ .
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either expressed or implied.
#
# Copyright © 2019-2026 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# File: test_script_manager.py
#
# Purpose: This file contains test cases for unit testing of CTF ScriptManager class.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

"""
@namespace lib.test_script_manager.py
Unit Test for ScriptManager: Loads and manages test scripts during a test run
"""

import time
import os
from unittest.mock import patch, Mock, mock_open

import pytest

from lib.ctf_global import Global
from lib.exceptions import CtfTestError
from lib.plugin_manager import PluginManager
from lib.readers.json_script_reader import JSONScriptReader
from lib.script_manager import ScriptManagerConfig, ScriptManager
from lib.status_manager import StatusManager
from lib.test_script import TestScript


@pytest.fixture(scope="session", autouse=True)
def init_global():
    Global.load_config("./configs/default_config.ini")
    Global.set_time_manager(Mock())


@pytest.fixture(scope="session")
def example_script():
    script_reader = JSONScriptReader('./functional_tests/plugin_tests/Test_CTF_Basic_Example.json')
    return script_reader.script


@pytest.fixture(name="script_manager_config")
def _script_manager_config_instance():
    return ScriptManagerConfig()


@pytest.fixture(name="script_manager")
def _script_manager_instance():
    status_manager = StatusManager()
    plugin_manager = PluginManager(['core_plugins'])
    return ScriptManager(plugin_manager, status_manager)

@pytest.fixture(name="test_script_instance")
def test_script_instance():
    def _create_instance():
        return TestScript()
    return _create_instance

def test_script_manager_config_init(script_manager_config):
    """
    Test ScriptManagerConfig class constructor
    """
    assert not script_manager_config.reset_plugins_between_scripts
    assert script_manager_config.json_results


def test_script_manager_init(script_manager):
    """
    Test ScriptManager class constructor
    """
    assert len(script_manager.script_list) == 0
    assert script_manager.regression_summary_file_path == ''
    assert script_manager.regression_summary_json_file_path == ''
    assert script_manager.curr_script_log_dir_path == ''
    assert script_manager.summary_file is None


def test_script_manager_add_script(script_manager):
    """
    Test ScriptManager class method: add_script
    Adds a script to the list of scripts managed by the script manager
    """
    assert len(script_manager.script_list) == 0
    script_reader = JSONScriptReader('functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json')
    script_manager.add_script(script_reader.script)
    assert len(script_manager.script_list) == 1


def test_script_manager_add_script_file(script_manager, utils):
    """
    Test ScriptManager class method: add_script_file
    Adds a script file to the list of scripts. If the file is not valid, skip it.
    """
    # valid json file
    assert script_manager.add_script_file('functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json') is None

    # valid json file, only contains function, no tests
    assert script_manager.add_script_file('functional_tests/cfe_6_7_tests/libs/CfeEsFunctions.json') is None

    # invalid json file: the exception is processed by caller function
    utils.clear_log()
    assert script_manager.add_script_file('functional_tests/cfe_6_7_tests/cfe_tests/NOFILE.json') is None

    # SendCheckCfeEsNoopCmd is referred by CfeEsTest.json
    os.system("sed -i '15s/.*/\"SendInvalidCmd\": {/' functional_tests/cfe_6_7_tests/libs/CfeEsFunctions.json")
    assert script_manager.add_script_file('functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json') is None
    os.system("git restore functional_tests/cfe_6_7_tests/libs/")


def test_script_manager_add_script_file_exception(script_manager, utils):
    """
    Test ScriptManager class method: add_script_file raises exception when provided script contains invalid instruction(s)
    Attempts to add a script file that contains an invalid instruction, and ensure exception is raised.
    """
    utils.clear_log()

    # path to json file containing invalid instruction
    invalid_script_dir = 'example_scripts/example_failing_tests/Invalid_Instruction.json'

    with pytest.raises(CtfTestError, match='Unsupported instruction'):
        script_manager.add_script_file(invalid_script_dir)
        assert utils.has_log_level('ERROR')

def test_script_manager_add_script_file_exp_fail(script_manager, utils):
    """
    Test ScriptManager class method: add_script_file correctly ignores "ExpectedFail" instructions 
    as part of inner instruction validation and adds the associated script
    """
    utils.clear_log()

    # path to json file containing ExpectedFail instruction(s)
    script_dir = 'functional_tests/plugin_tests/Test_CTF_ExpectedFail_Example.json'

    script_manager.add_script_file(script_dir)
    assert not utils.has_log_level('ERROR')

def test_script_manager_run_all_scripts(script_manager, example_script):
    """
    Test ScriptManager class method: run_all_scripts
    Run all added scripts, updating the status packets, and ensuring plugins are reloaded between scripts if needed.
    """
    script_manager.add_script(example_script)
    # add the second script to script_list
    script_manager.add_script(example_script)

    with patch("lib.test_script.TestScript.run_script", return_value=None),\
         patch('builtins.open', new_callable=mock_open()), \
         patch('os.makedirs'), \
         patch("lib.script_manager.change_log_file"),\
         patch.object(script_manager, 'plugin_manager', Mock(spec=PluginManager)):
        script_manager.config.reset_plugins_between_scripts = False
        assert script_manager.run_all_scripts() is None


def test_script_manager_run_all_scripts_reset_plugins(script_manager, example_script):
    """
    Test ScriptManager class method: run_all_scripts
    Run all added scripts, updating the status packets, and ensuring plugins are reloaded between scripts if needed.
    """
    script_manager.add_script(example_script)
    # add the second script to script_list
    script_manager.add_script(example_script)

    with patch("lib.test_script.TestScript.run_script", return_value=None),\
         patch('builtins.open', new_callable=mock_open()), \
         patch('os.makedirs'), \
         patch("lib.script_manager.change_log_file"),\
         patch.object(script_manager, 'plugin_manager', Mock(spec=PluginManager)):
        script_manager.config.reset_plugins_between_scripts = True
        assert script_manager.run_all_scripts() is None


def test_script_manager_run_all_scripts_exception(script_manager, example_script, utils):
    """
    Test ScriptManager class method: run_all_scripts  raise exception when calling run_script
    Run all added scripts, updating the status packets, and ensuring plugins are reloaded between scripts if needed.
    """
    script_manager.add_script(example_script)
    utils.clear_log()

    with patch("lib.test_script.TestScript.run_script") as mock_run_script,\
         patch('builtins.open', new_callable=mock_open()), \
         patch('os.makedirs'), \
         patch("lib.script_manager.change_log_file"),\
         patch.object(script_manager, 'plugin_manager', Mock(spec=PluginManager)):
        mock_run_script.side_effect = CtfTestError("Raise Exception for testing")
        assert script_manager.run_all_scripts() is None
        assert utils.has_log_level('ERROR')
        mock_run_script.assert_called_once()

    # sleep 1 seconds so that CTF can create a different folder under ./CTF_Results/ for the next unit test
    time.sleep(1)


def test_script_manager_run_all_scripts_exception2(script_manager, example_script, utils):
    """
    Test ScriptManager class method: run_all_scripts  raise exception when calling first change_log_file
    Run all added scripts, updating the status packets, and ensuring plugins are reloaded between scripts if needed.
    """
    script_manager.add_script(example_script)
    utils.clear_log()

    with patch("lib.script_manager.change_log_file") as mock_change_log_file,\
         patch.object(script_manager, 'plugin_manager', Mock(spec=PluginManager)):
        mock_change_log_file.side_effect = CtfTestError("Raise Exception for testing")
        with pytest.raises(CtfTestError):
            script_manager.run_all_scripts()
            assert utils.has_log_level('ERROR')
            mock_change_log_file.assert_called_once()

    # sleep 1 seconds so that CTF can create a different folder under ./CTF_Results/ for the next unit test
    time.sleep(1)


def test_script_manager_run_all_scripts_exception3(script_manager, example_script, utils):
    """
    Test ScriptManager class method: run_all_scripts  raise exception when calling the second change_log_file
    Run all added scripts, updating the status packets, and ensuring plugins are reloaded between scripts if needed.
    """
    script_manager.add_script(example_script)
    utils.clear_log()

    with patch("lib.script_manager.change_log_file") as mock_change_log_file,\
         patch("lib.test_script.TestScript.run_script", return_value=None),\
         patch.object(script_manager, 'plugin_manager', Mock(spec=PluginManager)):
        mock_change_log_file.side_effect = [None, CtfTestError("Raise Exception for testing")]
        with pytest.raises(CtfTestError):
            script_manager.run_all_scripts()
            assert utils.has_log_level('ERROR')

    # sleep 1 seconds so that CTF can create a different folder under ./CTF_Results/ for the next unit test
    time.sleep(1)


def test_script_manager_run_all_scripts_test_fail(script_manager, example_script):
    """
    Test ScriptManager class method: run_all_scripts  mock tests fail
    Run all added scripts, updating the status packets, and ensuring plugins are reloaded between scripts if needed.
    """
    script_manager.add_script(example_script)
    script_manager.script_list[0].run_script = Mock()
    script_manager.script_list[0].tests[0].test_result = False
    script_reader = JSONScriptReader('./functional_tests/plugin_tests/Test_CTF_Basic_Example.json')
    script_manager.skipped_script_list.append(script_reader.script)
    with patch('builtins.open', new_callable=mock_open()), \
         patch('os.makedirs'), \
         patch("lib.script_manager.change_log_file"),\
         patch.object(script_manager, 'plugin_manager', Mock(spec=PluginManager)):
        assert script_manager.run_all_scripts() is None

    script_manager.skipped_script_list.append(Mock())
    with patch('builtins.open', new_callable=mock_open()), \
         patch('os.makedirs'), \
         patch("lib.script_manager.change_log_file"),\
         patch.object(script_manager, 'plugin_manager', Mock(spec=PluginManager)):
        with pytest.raises(CtfTestError):
            script_manager.run_all_scripts()


def test_script_manager__del__(script_manager):
    """
    Test ScriptManager Destructor:
    """
    script_manager.summary_file = Mock()
    script_manager.__del__()


def test_script_manager__del__exception(script_manager, utils):
    """
    Test ScriptManager Destructor: raise exception
    """
    utils.clear_log()
    script_manager.summary_file = Mock()
    with patch.object(script_manager.summary_file, 'close') as mock_close:
        mock_close.side_effect = IOError
        script_manager.__del__()
        assert utils.has_log_level('ERROR')
        mock_close.assert_called_once()


def test_script_manager_write_summary_line_exception(script_manager):
    """
    Test ScriptManager class method: write_summary_line  raise exception when calling self.summary_file.close()
    """
    script_manager.summary_file = Mock()
    with patch.object(script_manager.summary_file, 'close') as mock_close:
        mock_close.side_effect = IOError
        script_manager.write_summary_line('mock summary line')
        mock_close.assert_called_once()


def test_script_manager_write_summary_line_open_exception(script_manager,example_script, utils):
    """
    Test ScriptManager class method: write_summary_line  raise exception when calling self.summary_file.open()
    """
    script_manager.summary_file = Mock()
    utils.clear_log()
    with patch.object(script_manager.summary_file, 'open') as mocked_open:
        mocked_open.side_effect = IOError
        script_manager.write_summary_line(example_script)
        assert utils.has_log_level('ERROR')

def test_script_manager_write_test_suite_summary_exception(script_manager):
    """
    Test ScriptManager class method: write_test_suite_summary  raise exception when calling self.summary_file.close()
    """
    script_manager.summary_file = Mock()

    # Summary metrics must be calculated first
    script_manager.calculate_summary_metrics()

    with patch.object(script_manager.summary_file, 'close') as mock_close:
        mock_close.side_effect = IOError
        script_manager.write_test_suite_summary()
        mock_close.assert_called_once()

def test_script_manager_write_test_suite_summary_open_exception(script_manager, utils):
    """
    Test ScriptManager class method: write_test_suite_summary  raise exception when calling self.summary_file.open()
    """
    script_manager.summary_file = Mock()
    utils.clear_log()

    # Summary metrics must be calculated first
    script_manager.calculate_summary_metrics()

    with patch.object(script_manager.summary_file, 'open') as mocked_open:
        mocked_open.side_effect = IOError
        script_manager.write_test_suite_summary()
        assert utils.has_log_level('ERROR')


def test_script_manager_write_test_suite_summary_without_prereq_call_exception(script_manager, utils):
    """
    Test ScriptManager class method: write_test_suite_summary  logs an error when run without calling prereq function
    """
    script_manager.summary_file = Mock()
    utils.clear_log()

    # Writing summary without calculating the aggregate results
    script_manager.write_test_suite_summary()

    assert utils.has_log_level('ERROR')

def test_script_manager_write_test_suite_summary(script_manager, utils):
    """
    Test ScriptManager class method: write_test_suite_summary   executes without error in nominal case.
    """
    script_manager.summary_file = Mock()
    utils.clear_log()

    script_manager.calculate_summary_metrics()

    print(script_manager.__class__.__module__)

    with patch("builtins.open", new_callable=mock_open()):
        script_manager.write_test_suite_summary()

    assert not utils.has_log_level('ERROR')

def test_script_manager_calculate_summary_metrics(script_manager, test_script_instance):
    """
    Test ScriptManager class method: calculate_summary_metrics correctly aggregates test metrics
    """
    # Test script with some failing tests
    script1 = test_script_instance()
    script1.exec_time = 30
    script1.num_tests = 5
    script1.num_passed = 3
    script1.failed_tests = [Mock(), Mock()]
    script1.status = 'failed'

    script_manager.add_script(script1)

    # Test script with all passing tests
    script2 = test_script_instance()
    script2.exec_time = 20
    script2.num_tests = 3
    script2.num_passed = 3
    script2.failed_tests = []
    script2.status = 'passed'

    script_manager.add_script(script2)

    script_manager.calculate_summary_metrics()

    assert(len(script_manager.script_list) == 2)
    assert(script_manager.aggregated_metrics["runtime_secs"] == 50)
    assert(script_manager.aggregated_metrics["num_tests"] == 8)
    assert(script_manager.aggregated_metrics["num_passed_tests"] == 6)
    assert(script_manager.aggregated_metrics["num_failed_tests"] == 2)
    assert(script_manager.aggregated_metrics["num_passed_scripts"] == 1)
    assert(script_manager.aggregated_metrics["num_failed_scripts"] == 1)

def test_script_manager_get_expected_fails_summary_no_exp_fails(script_manager, test_script_instance, example_script, utils):
    """
    Test ScriptManager class method: write_expected_fails_summary no sripts or scripts with no expected fails
    """
    script_manager.summary_file = Mock()
    utils.clear_log()
    # No scripts added, so expected fails summary should be empty
    assert script_manager.get_expected_fails_summary() == []
    assert not utils.has_log_level('ERROR')

    # Empty script added, expected fails summary should be empty
    dummy_script = test_script_instance()
    dummy_script.status = 'passed'
    script_manager.add_script(dummy_script)
    assert script_manager.get_expected_fails_summary() == []
    assert not utils.has_log_level('ERROR')

    # Script added with no ExpectedFail instructions - expected fails summary should be empty
    script_manager.add_script(example_script)
    assert script_manager.get_expected_fails_summary() == []
    assert not utils.has_log_level('ERROR')

def test_script_manager_get_expected_fails_summary_nominal_fail(script_manager, utils):
    """
    Test ScriptManager class method: write_expected_fails_summary contains an expectedfail instruction that behaved nominally (failed as expected)
    """
    script_manager.summary_file = Mock()
    utils.clear_log()

    # Script added with one ExpectedFail instruction - expected fails summary should contain that instruction
    script_name = 'Test_CTF_ExpectedFail_Example.json'
    script_reader = JSONScriptReader('./functional_tests/plugin_tests/{}'.format(script_name))
    example_script = script_reader.script
    script_manager.add_script(example_script)

    with patch("lib.test_script.TestScript.run_script", return_value=None),\
         patch('builtins.open', new_callable=mock_open()), \
         patch('os.makedirs'), \
         patch("lib.script_manager.change_log_file"),\
         patch.object(script_manager, 'plugin_manager', Mock(spec=PluginManager)):
        script_manager.config.reset_plugins_between_scripts = False
        # Ensure the script runs and 'fails' due to the ExpectedFail instruction. 
        script_manager.script_list[0].status = 'failed'
        # Ensure the ExpectedFail instruction 'passes' execution (i.e - the nested instruction failed as expected)
        for script in script_manager.script_list:
            for test in script.tests:
                for instruction in test.instructions:
                    if "ExpectedFail" in instruction.command['instruction']:
                        instruction.execution_result = True
        assert script_manager.run_all_scripts() is None

    expected_summary_str = 'All expected fail instructions behaved as expected'
    expected_summary = {'Test Script Name': script_name, 'Summary': expected_summary_str,
                         'Associated CRs/DRs': '(CR:#123, DR:#789)'}
    
    assert len(script_manager.get_expected_fails_summary()) == 1
    assert script_manager.get_expected_fails_summary()[0] == expected_summary
    assert not utils.has_log_level('ERROR')

def test_script_manager_get_expected_fails_summary_unexpec_fail(script_manager, utils):
    """
    Test ScriptManager class method: write_expected_fails_summary contains an expectedfail instruction that did not fail as expected. 
    """
    script_manager.summary_file = Mock()
    utils.clear_log()

    # Script added with one ExpectedFail instruction - expected fails summary should contain that instruction
    script_name = 'Test_CTF_ExpectedFail_Example.json'
    script_reader = JSONScriptReader('./functional_tests/plugin_tests/{}'.format(script_name))
    example_script = script_reader.script
    script_manager.add_script(example_script)

    with patch("lib.test_script.TestScript.run_script", return_value=None),\
         patch('builtins.open', new_callable=mock_open()), \
         patch('os.makedirs'), \
         patch("lib.script_manager.change_log_file"),\
         patch.object(script_manager, 'plugin_manager', Mock(spec=PluginManager)):
        script_manager.config.reset_plugins_between_scripts = False
        # Ensure the script runs but unexpectedly 'passes' despite the ExpectedFail instruction.
        script_manager.script_list[0].status = 'passed'
        # Ensure the ExpectedFail instruction 'fails' execution (i.e - the nested instruction did not fail as expected)
        for script in script_manager.script_list:
            for test in script.tests:
                for instruction in test.instructions:
                    if "ExpectedFail" in instruction.command['instruction']:
                        instruction.execution_result = False
        assert script_manager.run_all_scripts() is None

    expected_summary_str = 'One or more expected fail instructions did not behave as expected'
    expected_summary = {'Test Script Name': script_name, 'Summary': expected_summary_str,
                         'Associated CRs/DRs': '(CR:#123, DR:#789)'}
    
    print(script_manager.get_expected_fails_summary())
    print(example_script.tests[0].instructions)

    assert len(script_manager.get_expected_fails_summary()) == 1
    assert script_manager.get_expected_fails_summary()[0] == expected_summary
    assert not utils.has_log_level('ERROR')

def test_script_manager_write_expected_fails_summary_empty_summary(script_manager, utils):
    """
    Test ScriptManager class method: write_expected_fails_summary no exception or error when passed in empty summary list
    """
    script_manager.summary_file = Mock()
    utils.clear_log()

    script_manager.write_expected_fails_summary([])

    assert not utils.has_log_level('ERROR')

def test_script_manager_write_expected_fails_summary_open_exception(script_manager, utils):
    """
    Test ScriptManager class method: write_expected_fails_summary 
    """
    script_manager.summary_file = Mock()
    utils.clear_log()

    with patch.object(script_manager.summary_file, 'open') as mocked_open:
        mocked_open.side_effect = IOError
        script_manager.write_expected_fails_summary([{'Dummy Summary'}])
        assert utils.has_log_level('ERROR')

def test_script_manager_write_expected_fails_summary_close_exception(script_manager):
    """
    Test ScriptManager class method: write_expected_fails_summary  raise exception when calling self.summary_file.close()
    """
    script_manager.summary_file = Mock()
    with patch.object(script_manager.summary_file, 'close') as mock_close:
        mock_close.side_effect = IOError
        script_manager.write_expected_fails_summary([{'Dummy Summary'}])
        mock_close.assert_called_once()