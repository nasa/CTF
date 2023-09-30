# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2023 United States Government as represented by the
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
import socket
from unittest.mock import patch, MagicMock

import pytest

from lib.ctf_global import Global
from lib.exceptions import CtfParameterError, CtfTestError
from plugins.trick_plugin.trick.variable_server import VariableServerError
from plugins.trick_plugin.trick_plugin import TrickPlugin, convert_type, TrickController


@pytest.fixture(scope="session", autouse=True)
def init_global():
    Global.load_config("./configs/default_config.ini")


@pytest.fixture(name="trick_plugin")
def _trick_plugin_instance():
    return TrickPlugin()


@pytest.fixture(name="trick_plugin_inited")
def _trick_plugin_instance_inited():
    plugin = TrickPlugin()
    plugin.controller = MagicMock()
    return plugin


@pytest.fixture(name="trick_controller")
def _trick_controller_instance():
    with patch("plugins.trick_plugin.trick_plugin.VariableServer"):
        return TrickController(Global.config)


def test_trick_plugin_convert_type():
    assert convert_type(1, "int") == 1
    assert convert_type(1, "float") == 1.0
    assert convert_type(1, "string") == "1"
    assert convert_type(1, "boolean") is True

    assert convert_type("0", "int") == 0
    assert convert_type("0", "float") == 0.0
    assert convert_type("0", "string") == "0"
    assert convert_type("", "boolean") is False

    assert convert_type(1, "") == 1
    assert convert_type(1.0, "") == 1
    assert convert_type("1", "") == "1"
    assert convert_type(True, "") is True


def test_trick_plugin_convert_type_errors():
    with pytest.raises(CtfParameterError):
        convert_type(1, "integer")
    with pytest.raises(CtfParameterError):
        convert_type(None, "int")
    with pytest.raises(CtfParameterError):
        convert_type("foo", "float")


def test_trick_plugin_init(trick_plugin):
    assert trick_plugin.name == "TrickPlugin"
    assert trick_plugin.description == "Trick Plugin"
    assert trick_plugin.controller is None


def test_trick_plugin_initialize(trick_plugin):
    assert trick_plugin.initialize()


def test_trick_plugin_command_sets(trick_plugin):
    assert len(trick_plugin.command_map) == 3
    assert "FreezeTrickSim" in trick_plugin.command_map
    assert "SetTrickVariable" in trick_plugin.command_map
    assert "CheckTrickVariable" in trick_plugin.command_map
    assert not trick_plugin.verify_required_commands
    assert not trick_plugin.continuous_verification_commands
    assert not trick_plugin.end_test_on_fail_commands


def test_trick_get_controller(trick_plugin):
    with patch("plugins.trick_plugin.trick_plugin.VariableServer") as mock_vs:
        # first call creates controller
        assert not trick_plugin.controller
        assert trick_plugin.get_controller()
        assert trick_plugin.controller
        mock_vs.assert_called_once_with("localhost", 7000)
        # second call returns same controller
        assert trick_plugin.get_controller() == trick_plugin.controller
        mock_vs.assert_called_once()


def test_trick_get_controller_error(trick_plugin):
    with patch("plugins.trick_plugin.trick_plugin.VariableServer") as mock_vs:
        mock_vs.side_effect = socket.error()
        assert trick_plugin.get_controller() is None


def test_trick_plugin_freeze_sim(trick_plugin_inited):
    assert trick_plugin_inited.freeze_trick_sim(True)
    trick_plugin_inited.controller.freeze_sim.assert_called_with(True)


def test_trick_plugin_freeze_sim_init_error(trick_plugin):
    with patch("plugins.trick_plugin.trick_plugin.VariableServer") as mock_vs:
        mock_vs.side_effect = socket.error()
        assert trick_plugin.freeze_trick_sim(True) is False


def test_trick_plugin_set_trick_variable(trick_plugin_inited, utils):
    # nominal case
    Global.variable_store = {"var": "foo.bar", "val": 42}
    assert trick_plugin_inited.set_trick_variable("$var$", "$val$", variable_type="float", units="m")
    trick_plugin_inited.controller.set_variable.assert_called_once_with("foo.bar", 42.0, "m")

    # exception handled
    trick_plugin_inited.controller.set_variable.side_effect = CtfTestError("mock error")
    assert not trick_plugin_inited.set_trick_variable("$var$", "$val$", variable_type="float", units="m")
    assert utils.has_log_level("ERROR")


def test_trick_plugin_set_trick_variable_init_error(trick_plugin):
    with patch("plugins.trick_plugin.trick_plugin.VariableServer") as mock_vs:
        mock_vs.side_effect = socket.error()
        assert trick_plugin.set_trick_variable("var", "val") is False


def test_trick_plugin_check_trick_variable(trick_plugin_inited, utils):
    # nominal case
    Global.variable_store = {"var": "my.var", "val": "0"}
    trick_plugin_inited.controller.get_variable.return_value = 0.0
    assert trick_plugin_inited.check_trick_variable("$var$", "==", "$val$", units="ms", variable_type="float")
    trick_plugin_inited.controller.get_variable.assert_called_once_with("my.var", "ms", float)

    # false condition
    trick_plugin_inited.controller.get_variable.return_value = 1
    assert not trick_plugin_inited.check_trick_variable("$var$", "<=", "$val$", units="ms", variable_type="float")

    # invalid operator
    trick_plugin_inited.controller.get_variable.reset_mock()
    assert not trick_plugin_inited.check_trick_variable("$var$", "", "$val$", units="ms", variable_type="float")
    trick_plugin_inited.controller.get_variable.assert_not_called()

    # exception handled
    trick_plugin_inited.controller.get_variable.side_effect = CtfTestError("mock error")
    assert not trick_plugin_inited.check_trick_variable("$var$", "<", "$val$", units="ms", variable_type="float")
    assert utils.has_log_level("ERROR")


def test_trick_plugin_check_trick_variable_init_error(trick_plugin):
    with patch("plugins.trick_plugin.trick_plugin.VariableServer") as mock_vs:
        mock_vs.side_effect = socket.error()
        assert trick_plugin.check_trick_variable("var", "op", "val") is False


def test_trick_plugin_shutdown(trick_plugin, trick_plugin_inited):
    trick_plugin.shutdown()
    assert trick_plugin.controller is None

    mock = trick_plugin_inited.controller
    trick_plugin_inited.shutdown()
    mock.shutdown.assert_called_once()
    assert trick_plugin_inited.controller is None


def test_trick_controller_init(trick_controller):
    assert trick_controller.variable_server


def test_trick_controller_init_error(utils):
    with pytest.raises(socket.error):
        TrickController(Global.config)
    assert utils.has_log_level("ERROR")


def test_trick_controller_freeze_sim(trick_controller):
    trick_controller.freeze_sim(True)
    trick_controller.variable_server.freeze.assert_called_once_with(True)


def test_trick_controller_set_variable(trick_controller):
    # nominal case
    trick_controller.set_variable("foo", 1.0, "g")
    trick_controller.variable_server.set_value.assert_called_once_with("foo", 1.0, "g")

    # error
    trick_controller.variable_server.set_value.side_effect = VariableServerError()
    with pytest.raises(CtfTestError):
        trick_controller.set_variable("foo", 1.0)
    trick_controller.variable_server.set_value.assert_called_with("foo", 1.0, None)


def test_trick_controller_get_variable(trick_controller):
    # nominal case
    trick_controller.variable_server.get_value.return_value = 1.0
    assert trick_controller.get_variable("foo", "g", float) == 1.0
    trick_controller.variable_server.get_value.assert_called_once_with("foo", "g", float)

    # error
    trick_controller.variable_server.get_value.side_effect = VariableServerError()
    with pytest.raises(CtfTestError):
        trick_controller.get_variable("foo")
    trick_controller.variable_server.get_value.assert_called_with("foo", None, str)


def test_trick_controller_shutdown(trick_controller):
    mock_vs = trick_controller.variable_server
    trick_controller.shutdown()
    mock_vs.close.assert_called_once()
    assert trick_controller.variable_server is None
