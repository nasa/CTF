"""
@namespace lib.test_script_manager.py
Unit Test for ScriptManager: Loads and manages test scripts during a test run
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

import time
from unittest.mock import patch, Mock, mock_open

import pytest

from lib.ctf_global import Global
from lib.exceptions import CtfTestError
from lib.plugin_manager import PluginManager
from lib.readers.json_script_reader import JSONScriptReader
from lib.script_manager import ScriptManagerConfig, ScriptManager
from lib.status_manager import StatusManager


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
    plugin_manager = PluginManager(['plugins'])
    return ScriptManager(plugin_manager, status_manager)


def test_script_manager_config_init(script_manager_config):
    """
    Test ScriptManagerConfig class constructor
    """
    assert script_manager_config.reset_plugins_between_scripts
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

    # invalid json file
    utils.clear_log()
    assert script_manager.add_script_file('functional_tests/cfe_6_7_tests/cfe_tests/NOFILE.json') is None
    assert utils.has_log_level('WARNING')


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
    with patch('builtins.open', new_callable=mock_open()), \
         patch('os.makedirs'), \
         patch("lib.script_manager.change_log_file"),\
         patch.object(script_manager, 'plugin_manager', Mock(spec=PluginManager)):
        assert script_manager.run_all_scripts() is None


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
