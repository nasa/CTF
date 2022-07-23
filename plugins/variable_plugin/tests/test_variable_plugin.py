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
from unittest.mock import patch

import pytest

from lib.ctf_global import Global
from lib.exceptions import CtfTestError
from lib.plugin_manager import PluginManager
from plugins.variable_plugin.variable_plugin import VariablePlugin


@pytest.fixture(scope="session", autouse=True)
def init_global():
    Global.load_config("./configs/default_config.ini")
    # Global.plugin_manager is set by PluginManager constructor
    PluginManager(['plugins'])


@pytest.fixture(name="variable_plugin")
def _variable_plugin_instance():
    return VariablePlugin()


def test_variable_plugin_init(variable_plugin):
    """
    Test VariablePlugin initialize method
    """
    assert variable_plugin.initialize()
    assert variable_plugin.description == "Variable Plugin"
    assert variable_plugin.name == "VariablePlugin"


def test_variable_plugin_commandmap(variable_plugin):
    """
    Test VariablePlugin command content
    """
    assert len(variable_plugin.command_map) == 4
    assert "SetUserVariable" in variable_plugin.command_map
    assert "SetUserVariableFromTlm" in variable_plugin.command_map
    assert "SetUserVariableFromTlmHeader" in variable_plugin.command_map
    assert "CheckUserVariable" in variable_plugin.command_map


def test_variable_verify_required_commands(variable_plugin):
    assert len(variable_plugin.verify_required_commands) == 0


def test_add_variables_from_config(variable_plugin):
    assert variable_plugin.add_variables_from_config() is None
    assert Global.variable_store["variable_1"] == 10
    assert not Global.variable_store["variable_2"]
    assert Global.variable_store["variable_3"] == 5.0
    assert Global.variable_store["variable_4"] == 'abc'
    Global.variable_store.clear()
    Global.load_config("./configs/lx1_lx2_config.ini")
    assert variable_plugin.add_variables_from_config() is None
    assert "variable_1" not in Global.variable_store
    assert "variable_2" not in Global.variable_store
    assert "variable_3" not in Global.variable_store
    assert "variable_4" not in Global.variable_store
    Global.load_config("./configs/default_config.ini")


def test_add_variables_from_config_exception(variable_plugin, utils):
    Global.config.set('test_variable', 'added_var', '10x')
    Global.config.set('test_variable', 'added_var2', '[1,2]')
    utils.clear_log()
    assert variable_plugin.add_variables_from_config() is None
    Global.load_config("./configs/default_config.ini")
    assert utils.has_log_level('ERROR')


def test_variable_set_user_defined_variable(variable_plugin):
    assert variable_plugin.set_user_defined_variable('variable_1', '=', 10)
    assert variable_plugin.set_user_defined_variable('variable_1', '==', 10)
    assert not variable_plugin.set_user_defined_variable('variable_2_none', '==', 10)
    Global.variable_store.clear()


def test_variable_set_user_defined_variable_str(variable_plugin):
    assert variable_plugin.set_user_defined_variable('variable_1', '=', '10')
    assert not variable_plugin.check_user_defined_variable('variable_1', '==', '9')
    assert variable_plugin.check_user_defined_variable('variable_1', '==', '10')
    assert variable_plugin.set_user_defined_variable('variable_1', '=', '10')
    assert not variable_plugin.check_user_defined_variable('variable_1', '==', 10)
    Global.variable_store.clear()


def test_variable_set_user_defined_variable_str_convert(variable_plugin):
    assert variable_plugin.set_user_defined_variable('variable_1', '=', 10)
    assert variable_plugin.check_user_defined_variable('variable_1', '==', '10')
    Global.variable_store.clear()


def test_variable_set_user_defined_variable_exception(variable_plugin, utils):
    assert variable_plugin.set_user_defined_variable('variable_1', '=', 10)
    with pytest.raises(CtfTestError):
        utils.clear_log()
        variable_plugin.check_user_defined_variable('variable_1', '==', '10x')
        assert utils.has_log_level("ERROR")
    Global.variable_store.clear()


def test_variable_get_user_defined_variable(variable_plugin):
    assert not variable_plugin.get_user_defined_variable('variable_1')
    assert variable_plugin.set_user_defined_variable('variable_1', '=', 10)
    assert variable_plugin.get_user_defined_variable('variable_1')
    Global.variable_store.clear()


def test_variable_check_user_defined_variable(variable_plugin, utils):
    utils.clear_log()
    assert not variable_plugin.check_user_defined_variable('variable_1', '<', 10)
    assert utils.has_log_level('WARNING')

    utils.clear_log()
    assert variable_plugin.set_user_defined_variable('variable_1', '=', 6)
    assert not variable_plugin.check_user_defined_variable('variable_1', '$', 10)
    assert utils.has_log_level('WARNING')

    assert variable_plugin.check_user_defined_variable('variable_1', '<', 10)
    Global.variable_store.clear()


def test_variable_set_user_variable_from_tlm(variable_plugin):
    with patch('lib.ctf_global.Global.plugin_manager.find_plugin_for_command') as mock_get_plugin:
        mock_get_plugin.return_value.get_tlm_value.return_value = 2
        assert variable_plugin.set_user_variable_from_tlm('tlm_var', 'TO_HK_TLM_MID', 'usCmdCnt')
        assert Global.variable_store.get('tlm_var') == 2


def test_variable_set_user_variable_from_tlm_header(variable_plugin):
    with patch('lib.ctf_global.Global.plugin_manager.find_plugin_for_command') as mock_get_plugin:
        mock_get_plugin.return_value.get_tlm_value.return_value = 12345
        assert variable_plugin.set_user_variable_from_tlm_header('hdr_var', 'TO_HK_TLM_MID', 'sheader.timestamp')
        assert Global.variable_store.get('hdr_var') == 12345


def test_variable_set_label(variable_plugin):
    assert variable_plugin.set_label('label_1')


def test_variable_shutdown(variable_plugin):
    assert variable_plugin.shutdown() is None



