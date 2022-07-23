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

from unittest.mock import patch, MagicMock

import pytest

from lib.ctf_global import Global, CtfVerificationStage
from lib.exceptions import CtfTestError
from plugins.cfs.cfs_time_manager import CfsTimeManager


@pytest.fixture(scope="session", autouse=True)
def init_global():
    Global.load_config("./configs/default_config.ini")


@pytest.fixture
def event_args():
    return [{"app": "my_app1", "id": "my_id1", "msg": "my_msg1", "msg_args": "my_msg_args1"},
            {"app": "my_app2", "id": "my_id2", "msg": "my_msg2", "is_regex": True}]


def test_cfs_plugin_init(cfs_plugin):
    assert cfs_plugin.name == "CFS Plugin"
    assert cfs_plugin.description == "Provide CFS command/telemetry support for CTF"
    assert cfs_plugin.has_attempted_register is False
    assert not cfs_plugin.targets
    assert cfs_plugin.initialize()
    assert isinstance(Global.time_manager, CfsTimeManager)
    assert not Global.time_manager.cfs_targets


def test_cfs_plugin_instruction_sets(cfs_plugin):
    assert len(cfs_plugin.command_map) == 16
    assert "RegisterCfs" in cfs_plugin.command_map
    assert "BuildCfs" in cfs_plugin.command_map
    assert "StartCfs" in cfs_plugin.command_map
    assert "EnableCfsOutput" in cfs_plugin.command_map
    assert "SendCfsCommand" in cfs_plugin.command_map
    assert "SendCfsCommandWithPayloadLength" in cfs_plugin.command_map
    assert "SendCfsCommandWithRawPayload" in cfs_plugin.command_map
    assert "CheckTlmValue" in cfs_plugin.command_map
    assert "CheckTlmPacket" in cfs_plugin.command_map
    assert "CheckNoTlmPacket" in cfs_plugin.command_map
    assert "CheckTlmContinuous" in cfs_plugin.command_map
    assert "RemoveCheckTlmContinuous" in cfs_plugin.command_map
    assert "CheckEvent" in cfs_plugin.command_map
    assert "CheckNoEvent" in cfs_plugin.command_map
    assert "ArchiveCfsFiles" in cfs_plugin.command_map
    assert "ShutdownCfs" in cfs_plugin.command_map

    assert len(cfs_plugin.verify_required_commands) == 5
    assert "CheckTlmValue" in cfs_plugin.verify_required_commands
    assert "CheckTlmPacket" in cfs_plugin.verify_required_commands
    assert "CheckNoTlmPacket" in cfs_plugin.verify_required_commands
    assert "CheckEvent" in cfs_plugin.verify_required_commands
    assert "CheckNoEvent" in cfs_plugin.verify_required_commands

    assert len(cfs_plugin.continuous_commands) == 1
    assert "CheckTlmContinuous" in cfs_plugin.continuous_commands

    assert len(cfs_plugin.end_test_on_fail_commands) == 2
    assert "RegisterCfs" in cfs_plugin.end_test_on_fail_commands
    assert "StartCfs" in cfs_plugin.end_test_on_fail_commands

    assert set(cfs_plugin.verify_required_commands) <= set(cfs_plugin.command_map.keys())
    assert set(cfs_plugin.continuous_commands) <= set(cfs_plugin.command_map.keys())
    assert set(cfs_plugin.end_test_on_fail_commands) <= set(cfs_plugin.command_map.keys())


def test_cfs_plugin_load_configured_targets(cfs_plugin):
    assert not cfs_plugin.targets
    assert cfs_plugin.load_configured_targets('cfs')
    assert 'cfs' in cfs_plugin.targets


def test_cfs_plugin_load_configured_targets_default(cfs_plugin):
    assert not cfs_plugin.targets
    assert cfs_plugin.load_configured_targets()
    assert 'cfs' in cfs_plugin.targets


def test_cfs_plugin_register_cfs(cfs_plugin):
    assert not cfs_plugin.targets
    target_name = 'cfs'
    assert cfs_plugin.register_cfs(target_name)
    assert target_name in cfs_plugin.targets
    assert cfs_plugin.targets[target_name].name == "CfsController"
    assert cfs_plugin.has_attempted_register
    assert not cfs_plugin.register_cfs(target_name)


def test_cfs_plugin_register_cfs_variable(cfs_plugin):
    assert not cfs_plugin.targets
    Global.variable_store['user_defined_cfs'] = 'cfs'
    target_name = '$user_defined_cfs$'
    assert cfs_plugin.register_cfs(target_name)


def test_cfs_plugin_register_cfs_default(cfs_plugin):
    assert not cfs_plugin.targets
    assert cfs_plugin.register_cfs('')
    assert len(cfs_plugin.targets) == 1
    assert 'cfs' in cfs_plugin.targets
    assert cfs_plugin.targets['cfs'].name == "CfsController"
    assert cfs_plugin.has_attempted_register
    assert not cfs_plugin.register_cfs('')


def test_cfs_plugin_register_cfs_invalid(cfs_plugin):
    # invalid target name
    assert not cfs_plugin.targets
    assert not cfs_plugin.register_cfs('invalid')
    assert not cfs_plugin.targets
    assert cfs_plugin.has_attempted_register

    # invalid protocol
    with patch.object(Global.config, 'get', return_value='invalid'):
        assert not cfs_plugin.register_cfs('cfs')
        assert not cfs_plugin.targets

    # config errors
    with patch('plugins.cfs.cfs_plugin.CfsConfig.get_error_count', return_value=1):
        assert not cfs_plugin.register_cfs('cfs')
        assert not cfs_plugin.targets


def test_cfs_plugin_register_cfs_fail_init(cfs_plugin):
    assert not cfs_plugin.targets
    with patch.object(cfs_plugin.protocols['local'][1].return_value, 'initialize', return_value=False):
        assert not cfs_plugin.register_cfs('cfs')
        assert not cfs_plugin.targets
        assert cfs_plugin.has_attempted_register


def test_cfs_plugin_register_cfs_local(cfs_plugin):
    assert not cfs_plugin.targets
    cfs_plugin.register_cfs('cfs')
    assert 'cfs' in cfs_plugin.targets
    assert cfs_plugin.targets['cfs'].name == "CfsController"
    assert cfs_plugin.has_attempted_register
    assert not cfs_plugin.register_cfs('cfs')


def test_cfs_plugin_register_cfs_remote(cfs_plugin):
    assert not cfs_plugin.targets
    cfs_plugin.register_cfs('local_ssh')
    assert 'local_ssh' in cfs_plugin.targets
    assert cfs_plugin.targets['local_ssh'].name == "RemoteCfsController"
    assert cfs_plugin.has_attempted_register
    assert not cfs_plugin.register_cfs('local_ssh')


def test_cfs_plugin_get_cfs_targets(cfs_plugin, utils):
    cfs_plugin.register_cfs('cfs')
    assert len(cfs_plugin.get_cfs_targets()) == 1
    assert len(cfs_plugin.get_cfs_targets('cfs')) == 1
    assert not utils.has_log_level("ERROR")


def test_cfs_plugin_get_cfs_targets_invalid(cfs_plugin, utils):
    cfs_plugin.register_cfs('cfs')
    assert cfs_plugin.get_cfs_targets('invalid') == []
    assert utils.has_log_level("ERROR")


def test_cfs_plugin_get_cfs_targets_none(cfs_plugin, utils):
    assert not cfs_plugin.targets
    assert cfs_plugin.get_cfs_targets() == []
    assert utils.has_log_level("ERROR")


def test_cfs_plugin_build_cfs_no_target(cfs_plugin):
    assert not cfs_plugin.targets
    assert cfs_plugin.build_cfs()
    assert 'cfs' in cfs_plugin.targets


def test_cfs_plugin_build_cfs_configure_error(cfs_plugin, utils):
    assert not cfs_plugin.targets
    with patch.object(cfs_plugin, 'load_configured_targets', return_value=False) as mock_load:
        assert not cfs_plugin.build_cfs()
        mock_load.assert_called_once_with(None)
    assert utils.has_log_level("ERROR")


def test_cfs_plugin_build_cfs_pass(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.build_cfs.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.build_cfs()
    assert mock_controller.build_cfs.call_count == num_controllers


def test_cfs_plugin_build_cfs_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.build_cfs.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.build_cfs()
    assert mock_controller.build_cfs.call_count == num_controllers


def test_cfs_plugin_build_cfs_single_target(cfs_plugin):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.build_cfs.return_value = True
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.build_cfs(target='1')
    cfs_plugin.targets['0'].build_cfs.assert_not_called()
    cfs_plugin.targets['1'].build_cfs.assert_called_once()
    cfs_plugin.targets['2'].build_cfs.assert_not_called()


def test_cfs_plugin_start_cfs_no_target(cfs_plugin):
    assert not cfs_plugin.targets
    assert cfs_plugin.start_cfs()
    assert 'cfs' in cfs_plugin.targets


def test_cfs_plugin_start_cfs_configure_error(cfs_plugin, utils):
    assert not cfs_plugin.targets
    with patch.object(cfs_plugin, 'load_configured_targets', return_value=False) as mock_load:
        assert not cfs_plugin.start_cfs()
        mock_load.assert_called_once_with(None)
    assert utils.has_log_level("ERROR")


def test_cfs_plugin_start_cfs_pass(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.start_cfs.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.start_cfs()
    assert mock_controller.start_cfs.call_count == num_controllers


def test_cfs_plugin_start_cfs_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.start_cfs.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.start_cfs()
    assert mock_controller.start_cfs.call_count == num_controllers


def test_cfs_plugin_start_cfs_single_target(cfs_plugin):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.start_cfs.return_value = True
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.start_cfs(target='1')
    cfs_plugin.targets['0'].start_cfs.assert_not_called()
    cfs_plugin.targets['1'].start_cfs.assert_called_once()
    cfs_plugin.targets['2'].start_cfs.assert_not_called()


def test_cfs_plugin_enable_cfs_output_no_target(cfs_plugin):
    assert not cfs_plugin.targets
    assert not cfs_plugin.enable_cfs_output(None)
    assert not cfs_plugin.targets


def test_cfs_plugin_enable_cfs_output_pass(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.enable_cfs_output.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.enable_cfs_output(None)
    assert mock_controller.enable_cfs_output.call_count == num_controllers


def test_cfs_plugin_enable_cfs_output_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.enable_cfs_output.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.enable_cfs_output(None)
    assert mock_controller.enable_cfs_output.call_count == num_controllers


def test_cfs_plugin_enable_cfs_output_single_target(cfs_plugin):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.enable_cfs_output.return_value = True
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.enable_cfs_output(target='1')
    cfs_plugin.targets['0'].enable_cfs_output.assert_not_called()
    cfs_plugin.targets['1'].enable_cfs_output.assert_called_once()
    cfs_plugin.targets['2'].enable_cfs_output.assert_not_called()


def test_cfs_plugin_send_cfs_command_no_target(cfs_plugin):
    assert not cfs_plugin.targets
    assert not cfs_plugin.send_cfs_command("", 0, {})
    assert not cfs_plugin.targets


def test_cfs_plugin_send_cfs_command_pass(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.send_cfs_command.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.send_cfs_command("mid", 1, {'args': True})
    assert mock_controller.send_cfs_command.call_count == num_controllers
    mock_controller.send_cfs_command.assert_called_with("mid", 1, {'args': True}, None, None, False)
    assert cfs_plugin.send_cfs_command("mid", 1, {'args': True},
                                       target=None, payload_length=2, header={}, ctype_args=True)
    mock_controller.send_cfs_command.assert_called_with("mid", 1, {'args': True}, {}, 2, True)
    assert cfs_plugin.send_cfs_command('CFE_ES_CMD_MID', 'CFE_ES_SHELL_CC',
                                       {'Payload': {'CmdString': 'hostname', 'OutputFilename': '/cf/test_output.txt'}})
    assert cfs_plugin.send_cfs_command('CFE_ES_CMD_MID', 'CFE_ES_SHELL_CC',
                                       {'Payload': [{'CmdString': 'hostname'}]})


def test_cfs_plugin_send_cfs_command_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.send_cfs_command.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.send_cfs_command("mid", 1, {'args': True})
    assert mock_controller.send_cfs_command.call_count == num_controllers


def test_cfs_plugin_send_cfs_command_single_target(cfs_plugin):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.send_cfs_command.return_value = True
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.send_cfs_command("mid", 1, {'args': True}, target='1')
    cfs_plugin.targets['0'].send_cfs_command.assert_not_called()
    cfs_plugin.targets['1'].send_cfs_command.assert_called_once()
    cfs_plugin.targets['2'].send_cfs_command.assert_not_called()


def test_cfs_plugin_send_raw_cfs_command_pass(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.send_cfs_command.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.send_raw_cfs_command("mid", 1, "0123456789ABCDEF")
    assert mock_controller.send_raw_cfs_command.call_count == num_controllers
    mock_controller.send_raw_cfs_command.assert_called_with("mid", 1, "0123456789ABCDEF", None)
    assert cfs_plugin.send_raw_cfs_command("mid", 1, "", target=None, header={})
    mock_controller.send_raw_cfs_command.assert_called_with("mid", 1, "", {})


def test_cfs_plugin_send_raw_cfs_command_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.send_raw_cfs_command.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.send_raw_cfs_command("mid", 1, "00")
    assert mock_controller.send_raw_cfs_command.call_count == num_controllers


def test_cfs_plugin_check_tlm_value_no_target(cfs_plugin):
    assert not cfs_plugin.targets
    assert not cfs_plugin.check_tlm_value("", {})
    assert not cfs_plugin.targets


def test_cfs_plugin_get_tlm_value(cfs_plugin):
    assert not cfs_plugin.targets
    mock_controller = MagicMock()
    cfs_plugin.targets = {i: mock_controller for i in range(1)}
    assert cfs_plugin.get_tlm_value("mid", 'var.name', target=None)
    assert mock_controller.get_tlm_value.call_count == 1
    mock_controller.get_tlm_value.assert_called_with("mid", 'var.name', False)


def test_cfs_plugin_check_tlm_value_pass(cfs_plugin):
    Global.current_verification_stage = CtfVerificationStage.first_ver
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_tlm_value.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.check_tlm_value("mid", {'args': True}, None)
    assert mock_controller.check_tlm_value.call_count == num_controllers
    mock_controller.check_tlm_value.assert_called_with("mid", {'args': True})
    assert cfs_plugin.check_tlm_value("CFE_EVS_HK_TLM_MID", [{'variable': 'Payload.CommandCounter', 'value': [0],
                                                              'compare': '=='}], None)


def test_cfs_plugin_check_tlm_value_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_tlm_value.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.check_tlm_value("mid", {'args': True}, None)
    assert mock_controller.check_tlm_value.call_count == num_controllers


def test_cfs_plugin_check_tlm_value_single_target(cfs_plugin):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.check_tlm_value.return_value = True
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.check_tlm_value("mid", {'args': True}, target='1')
    cfs_plugin.targets['0'].check_tlm_value.assert_not_called()
    cfs_plugin.targets['1'].check_tlm_value.assert_called_once()
    cfs_plugin.targets['2'].check_tlm_value.assert_not_called()


def test_cfs_plugin_check_tlm_packet_pass(cfs_plugin):
    Global.current_verification_stage = CtfVerificationStage.first_ver
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_tlm_value.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.check_tlm_packet("mid", None)
    assert mock_controller.check_tlm_value.call_count == num_controllers
    mock_controller.check_tlm_value.assert_called_with("mid")


def test_cfs_plugin_check_tlm_packet_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_tlm_value.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.check_tlm_packet("mid", None)
    assert mock_controller.check_tlm_value.call_count == num_controllers


def test_cfs_plugin_check_no_tlm_packet_pass(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_tlm_value.return_value = False
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.check_no_tlm_packet("mid")
    assert mock_controller.check_tlm_value.call_count == num_controllers
    with patch.object(Global, 'current_verification_stage', CtfVerificationStage.last_ver):
        assert cfs_plugin.check_no_tlm_packet("mid")
    assert mock_controller.check_tlm_value.call_count == num_controllers * 2
    mock_controller.check_tlm_value.assert_called_with("mid")


def test_cfs_plugin_check_no_tlm_packet_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_tlm_value.side_effect = [False, False, False, False, True, False]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.check_no_tlm_packet("mid")
    assert mock_controller.check_tlm_value.call_count == num_controllers
    with patch.object(Global, 'current_verification_stage', CtfVerificationStage.last_ver):
        assert not cfs_plugin.check_no_tlm_packet("mid")
    assert mock_controller.check_tlm_value.call_count == num_controllers * 2
    mock_controller.check_tlm_value.assert_called_with("mid")


def test_cfs_plugin_check_tlm_continuous_no_target(cfs_plugin):
    assert not cfs_plugin.targets
    assert not cfs_plugin.check_tlm_continuous("", "", {})
    assert not cfs_plugin.targets


def test_cfs_plugin_check_tlm_continuous_pass(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_tlm_continuous.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.check_tlm_continuous("id", "mid", {'args': True}, None)
    assert mock_controller.check_tlm_continuous.call_count == num_controllers
    mock_controller.check_tlm_continuous.assert_called_with("id", "mid", {'args': True})
    assert cfs_plugin.check_tlm_continuous("id", "TO_HK_TLM_MID", [{'compare': '==', 'variable': 'usCmdErrCnt', 'value': 0}], None)


def test_cfs_plugin_check_tlm_continuous_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_tlm_continuous.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.check_tlm_continuous("id", "mid", {'args': True}, None)
    assert mock_controller.check_tlm_continuous.call_count == num_controllers


def test_cfs_plugin_check_tlm_continuous_single_target(cfs_plugin):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.check_tlm_continuous.return_value = True
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.check_tlm_continuous("id", "mid", {'args': True}, target='1')
    cfs_plugin.targets['0'].check_tlm_continuous.assert_not_called()
    cfs_plugin.targets['1'].check_tlm_continuous.assert_called_once()
    cfs_plugin.targets['2'].check_tlm_continuous.assert_not_called()


def test_cfs_plugin_remove_check_tlm_continuous_no_target(cfs_plugin):
    assert not cfs_plugin.targets
    assert not cfs_plugin.remove_check_tlm_continuous("")
    assert not cfs_plugin.targets


def test_cfs_plugin_remove_check_tlm_continuous_pass(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.remove_check_tlm_continuous.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.remove_check_tlm_continuous("id", None)
    assert mock_controller.remove_check_tlm_continuous.call_count == num_controllers
    mock_controller.remove_check_tlm_continuous.assert_called_with("id")


def test_cfs_plugin_remove_check_tlm_continuous_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.remove_check_tlm_continuous.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.remove_check_tlm_continuous("id", None)
    assert mock_controller.remove_check_tlm_continuous.call_count == num_controllers


def test_cfs_plugin_remove_check_tlm_continuous_single_target(cfs_plugin):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.remove_check_tlm_continuous.return_value = True
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.remove_check_tlm_continuous("id", target='1')
    cfs_plugin.targets['0'].remove_check_tlm_continuous.assert_not_called()
    cfs_plugin.targets['1'].remove_check_tlm_continuous.assert_called_once()
    cfs_plugin.targets['2'].remove_check_tlm_continuous.assert_not_called()


def test_cfs_plugin_check_event_no_target(cfs_plugin, event_args):
    assert not cfs_plugin.targets
    assert not cfs_plugin.check_event(event_args, "")
    assert not cfs_plugin.targets


def test_cfs_plugin_check_event_pass(cfs_plugin, event_args):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_event.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.check_event(event_args, None)
    assert mock_controller.check_event.call_count == num_controllers * len(event_args)
    mock_controller.check_event.assert_called_with(**event_args[-1])


def test_cfs_plugin_check_event_fail(cfs_plugin, event_args):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_event.side_effect = [True, False, True] * len(event_args)
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.check_event(event_args, None)
    assert mock_controller.check_event.call_count == num_controllers * len(event_args)


def test_cfs_plugin_check_event_single_target(cfs_plugin, event_args):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.check_event.return_value = True
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.check_event(event_args, target='1')
    cfs_plugin.targets['0'].check_event.assert_not_called()
    assert cfs_plugin.targets['1'].check_event.call_count == len(event_args)
    cfs_plugin.targets['1'].check_event.assert_any_call(**event_args[0])
    cfs_plugin.targets['1'].check_event.assert_called_with(**event_args[-1])
    cfs_plugin.targets['2'].check_event.assert_not_called()


def test_cfs_plugin_check_noevent_no_target(cfs_plugin, event_args):
    assert not cfs_plugin.targets
    assert not cfs_plugin.check_noevent(event_args, "")
    assert not cfs_plugin.targets


def test_cfs_plugin_check_noevent_pass(cfs_plugin, event_args):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_event.return_value = False
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.check_noevent(event_args, None)
    assert mock_controller.check_event.call_count == num_controllers * len(event_args)
    with patch.object(Global, 'current_verification_stage', CtfVerificationStage.last_ver):
        assert cfs_plugin.check_noevent(event_args, None)
    assert mock_controller.check_event.call_count == num_controllers * 2 * len(event_args)
    mock_controller.check_event.assert_called_with(**event_args[-1])


def test_cfs_plugin_check_noevent_fail(cfs_plugin, event_args):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.check_event.side_effect = [False, False, False, False, True, False] * len(event_args)
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.check_noevent(event_args, None)
    assert mock_controller.check_event.call_count == num_controllers * len(event_args)
    with patch.object(Global, 'current_verification_stage', CtfVerificationStage.last_ver):
        assert not cfs_plugin.check_noevent(event_args, None)
    assert mock_controller.check_event.call_count == num_controllers * 2 * len(event_args)
    mock_controller.check_event.assert_called_with(**event_args[-1])


def test_cfs_plugin_check_noevent_single_target(cfs_plugin, event_args):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.check_event.return_value = False
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.check_noevent(event_args, target='1')
    cfs_plugin.targets['0'].check_event.assert_not_called()
    assert cfs_plugin.targets['1'].check_event.call_count == len(event_args)
    cfs_plugin.targets['1'].check_event.assert_any_call(**event_args[0])
    cfs_plugin.targets['1'].check_event.assert_called_with(**event_args[-1])
    cfs_plugin.targets['2'].check_event.assert_not_called()
    with patch.object(Global, 'current_verification_stage', CtfVerificationStage.last_ver):
        assert cfs_plugin.check_noevent(event_args, target='1')
    cfs_plugin.targets['0'].check_event.assert_not_called()
    assert cfs_plugin.targets['1'].check_event.call_count == 2 * len(event_args)
    cfs_plugin.targets['2'].check_event.assert_not_called()


def test_cfs_plugin_shutdown_cfs_no_target(cfs_plugin):
    assert not cfs_plugin.targets
    assert not cfs_plugin.shutdown_cfs(None)
    assert not cfs_plugin.targets


def test_cfs_plugin_shutdown_cfs_pass(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.shutdown_cfs.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.shutdown_cfs(None)
    assert mock_controller.shutdown_cfs.call_count == num_controllers


def test_cfs_plugin_shutdown_cfs_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.shutdown_cfs.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.shutdown_cfs(None)
    assert mock_controller.shutdown_cfs.call_count == num_controllers


def test_cfs_plugin_shutdown_cfs_single_target(cfs_plugin):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.shutdown_cfs.return_value = True
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.shutdown_cfs(target='1')
    cfs_plugin.targets['0'].shutdown_cfs.assert_not_called()
    cfs_plugin.targets['1'].shutdown_cfs.assert_called_once()
    cfs_plugin.targets['2'].shutdown_cfs.assert_not_called()


def test_cfs_plugin_archive_cfs_files_no_target(cfs_plugin):
    assert not cfs_plugin.targets
    assert not cfs_plugin.archive_cfs_files("")
    assert not cfs_plugin.targets


def test_cfs_plugin_archive_cfs_files_pass(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.archive_cfs_files.return_value = True
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.archive_cfs_files("path", None)
    assert mock_controller.archive_cfs_files.call_count == num_controllers
    mock_controller.archive_cfs_files.assert_called_with("path")


def test_cfs_plugin_archive_cfs_files_fail(cfs_plugin):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.archive_cfs_files.side_effect = [True, False, True]
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.archive_cfs_files("path", None)
    assert mock_controller.archive_cfs_files.call_count == num_controllers


def test_cfs_plugin_archive_cfs_files_single_target(cfs_plugin):
    num_controllers = 3
    for i in range(num_controllers):
        mock_controller = MagicMock()
        mock_controller.archive_cfs_files.return_value = True
        cfs_plugin.targets[str(i)] = mock_controller
    cfs_plugin.has_attempted_register = True
    assert cfs_plugin.archive_cfs_files("path", target='1')
    cfs_plugin.targets['0'].archive_cfs_files.assert_not_called()
    cfs_plugin.targets['1'].archive_cfs_files.assert_called_once()
    cfs_plugin.targets['2'].archive_cfs_files.assert_not_called()


def test_cfs_plugin_archive_cfs_files_error(cfs_plugin, utils):
    num_controllers = 3
    mock_controller = MagicMock()
    mock_controller.archive_cfs_files.side_effect = CtfTestError("Mock error")
    cfs_plugin.targets = {i: mock_controller for i in range(num_controllers)}
    cfs_plugin.has_attempted_register = True
    assert not cfs_plugin.archive_cfs_files("path", None)
    assert mock_controller.archive_cfs_files.call_count == num_controllers
    assert utils.has_log_level("ERROR")


def test_cfs_plugin_shutdown(cfs_plugin):
    cfs_plugin.load_configured_targets()
    assert cfs_plugin.targets
    with patch('plugins.cfs.pycfs.cfs_controllers.CfsController.shutdown'):
        cfs_target = cfs_plugin.targets['cfs']
        cfs_plugin.shutdown()
        cfs_target.shutdown.assert_called_once()
    assert not cfs_plugin.targets


def test_cfs_plugin_shutdown_no_targets(cfs_plugin):
    assert not cfs_plugin.targets
    cfs_plugin.shutdown()
    assert not cfs_plugin.targets
