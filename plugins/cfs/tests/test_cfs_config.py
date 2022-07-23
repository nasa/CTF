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

import os
from unittest.mock import Mock, patch

import pytest

from lib.ctf_global import Global
from lib.exceptions import CtfTestError
from plugins.cfs.cfs_config import CfsConfig, RemoteCfsConfig


def test_cfs_config_init(cfs_config):
    assert set(cfs_config.sections) == {"ccsds", "cfs", "core", "local_ssh", "logging", "ssh", 'test_variable'}
    assert cfs_config.validation.get_error_count() == 0
    assert cfs_config.name == "cfs"
    assert cfs_config.cfs_protocol == "local"
    assert cfs_config.build_cfs is True
    assert cfs_config.ccsds_data_dir == os.path.expanduser("~/sample_cfs_workspace/ccdd/json")
    assert cfs_config.ccsds_target == "set1"
    assert cfs_config.log_ccsds_imports is True
    assert cfs_config.cfs_build_dir == os.path.expanduser("~/sample_cfs_workspace")
    assert cfs_config.cfs_build_cmd == "make; make install"
    assert cfs_config.cfs_run_dir == os.path.expanduser("~/sample_cfs_workspace/build/exe/lx1")
    assert cfs_config.cfs_port_arg is False
    assert cfs_config.cfs_exe == "core-lx1"
    assert cfs_config.cfs_run_args == ""
    assert cfs_config.cfs_run_cmd == "core-lx1"
    assert cfs_config.cfs_output_file == "cfs_stdout.txt"
    assert cfs_config.remove_continuous_on_fail is True
    assert cfs_config.cfs_target_ip == "127.0.0.1"
    assert cfs_config.ctf_ip == "127.0.0.1"
    assert cfs_config.cmd_udp_port == 5010
    assert cfs_config.tlm_udp_port == 5011
    assert cfs_config.evs_log_file == "evs_event_msgs.log"
    assert cfs_config.cfs_debug is False
    assert cfs_config.cfs_run_in_xterm is True
    assert cfs_config.tlm_app_choice == "ToApi"
    assert cfs_config.ccsds_ver == 2
    assert cfs_config.evs_long_event_mid_name == "CFE_EVS_LONG_EVENT_MSG_MID"
    assert cfs_config.evs_short_event_mid_name == "CFE_EVS_SHORT_EVENT_MSG_MID"
    assert cfs_config.evs_messages_clear_after_time == 5
    assert cfs_config.endianess_of_target == "little"
    assert cfs_config.ccsds_header_info_included is False


def test_cfs_config_init_error(caplog):
    Global.load_config("./configs/default_config.ini")
    caplog.clear()
    with patch.object(Global.config, 'get') as mock_config:
        mock_config.side_effect = Exception("Mock Error")
        cfs_config = CfsConfig("cfs")
    assert cfs_config.get_error_count() > 0


def test_cfs_config_init_invalid(caplog):
    Global.load_config("./configs/default_config.ini")
    caplog.clear()
    cfs_config = CfsConfig("invalid")
    assert cfs_config.get_error_count() == 1
    # assert "No CFS configuration defined in config file for invalid." in caplog.text


def test_cfs_config_configure_invalid(cfs_config, caplog):
    caplog.clear()
    assert cfs_config.get_error_count() == 0
    cfs_config.configure("invalid")
    assert "No CFS configuration defined for invalid" in caplog.text
    assert cfs_config.get_error_count() == 1


def test_cfs_config_configure_exception(cfs_config, caplog, utils):
    caplog.clear()
    assert cfs_config.get_error_count() == 0
    with patch.object(Global.config, 'get') as mock_config:
        mock_config.side_effect = Exception("Mock Error")
        with pytest.raises(CtfTestError):
            cfs_config.configure("cfs")
    assert cfs_config.get_error_count() == 1
    assert utils.has_log_level("ERROR")


def test_cfs_config_load_field(cfs_config, caplog, utils):
    caplog.clear()
    caplog.set_level("INFO")
    assert cfs_config.load_field("cfs", "cfs_protocol", Global.config.get, None) == "local", "Valid field is loaded"
    assert not caplog.messages, "Nothing was logged"
    assert cfs_config.load_field("invalid", "cfs_protocol", Global.config.get, None) \
        == "local", "Invalid section falls back to CFS"
    assert utils.has_log_level("INFO")
    caplog.clear()
    assert cfs_config.load_field("cfs", "invalid", Global.config.get, None) is None, "Invalid field produces None"
    assert utils.has_log_level("ERROR")
    caplog.clear()
    validator = Mock(side_effect=TypeError('Test'))
    assert cfs_config.load_field("cfs", "cfs_protocol", Global.config.get, validator) is None, \
        "Validation exception produces None"
    assert utils.has_log_level("ERROR")


def test_cfs_config_load_config_data_invalid(cfs_config, caplog):
    caplog.set_level("WARNING")
    cfs_config.load_config_data("invalid")
    assert "No CFS configuration defined for invalid" in caplog.text
    assert cfs_config.validation.get_error_count() == 1
    assert cfs_config.name == "cfs"
    assert cfs_config.cfs_protocol == "local"
    assert cfs_config.build_cfs is True
    assert cfs_config.ccsds_data_dir == os.path.expanduser("~/sample_cfs_workspace/ccdd/json")
    assert cfs_config.ccsds_target == "set1"
    assert cfs_config.log_ccsds_imports is True
    assert cfs_config.cfs_build_dir == os.path.expanduser("~/sample_cfs_workspace")
    assert cfs_config.cfs_build_cmd == "make; make install"
    assert cfs_config.cfs_run_dir == os.path.expanduser("~/sample_cfs_workspace/build/exe/lx1")
    assert cfs_config.cfs_port_arg is False
    assert cfs_config.cfs_exe == "core-lx1"
    assert cfs_config.cfs_run_args == ""
    assert cfs_config.cfs_run_cmd == "core-lx1"
    assert cfs_config.cfs_output_file == "cfs_stdout.txt"
    assert cfs_config.remove_continuous_on_fail is True
    assert cfs_config.cfs_target_ip == "127.0.0.1"
    assert cfs_config.ctf_ip == "127.0.0.1"
    assert cfs_config.cmd_udp_port == 5010
    assert cfs_config.tlm_udp_port == 5011
    assert cfs_config.evs_log_file == "evs_event_msgs.log"
    assert cfs_config.cfs_debug is False
    assert cfs_config.cfs_run_in_xterm is True
    assert cfs_config.tlm_app_choice == "ToApi"
    assert cfs_config.ccsds_ver == 2
    assert cfs_config.evs_long_event_mid_name == "CFE_EVS_LONG_EVENT_MSG_MID"
    assert cfs_config.evs_short_event_mid_name == "CFE_EVS_SHORT_EVENT_MSG_MID"
    assert cfs_config.evs_messages_clear_after_time == 5
    assert cfs_config.endianess_of_target == "little"
    assert cfs_config.ccsds_header_info_included is False


def test_cfs_config_set_ctf_ip(cfs_config):
    import socket
    assert cfs_config.ctf_ip == "127.0.0.1"
    my_ip = socket.gethostbyname(socket.getfqdn())
    cfs_config.cfs_target_ip = my_ip
    cfs_config.set_ctf_ip()
    assert cfs_config.ctf_ip == my_ip


def test_cfs_set_run_cmd(cfs_config):
    assert cfs_config.cfs_exe == "core-lx1"
    assert cfs_config.cfs_run_args == ""
    assert cfs_config.cfs_run_cmd == "core-lx1"
    cfs_config.set_cfs_run_cmd(cfs_exe="cfs_exe1", cfs_run_args="cfs_run_args1")
    assert cfs_config.cfs_run_cmd == "cfs_exe1 cfs_run_args1", "Both parameters are updated"
    cfs_config.set_cfs_run_cmd(cfs_exe="cfs_exe2")
    assert cfs_config.cfs_run_cmd == "cfs_exe2 cfs_run_args1", "cfs_exe is updated"
    cfs_config.set_cfs_run_cmd(cfs_run_args="cfs_run_args3")
    assert cfs_config.cfs_run_cmd == "cfs_exe2 cfs_run_args3", "cfs_run_args is updated"
    cfs_config.set_cfs_run_cmd()
    assert cfs_config.cfs_run_cmd == "cfs_exe2 cfs_run_args3", "Neither parameter is updated"


def test_cfs_config_get_error_count(cfs_config):
    cfs_config.validation.parameter_errors = 3
    assert cfs_config.get_error_count() == cfs_config.validation.parameter_errors


@pytest.fixture
def remote_cfs_config():
    Global.load_config("./configs/example_configs/cfe_6_7_config_examples.ini")
    return RemoteCfsConfig("local_ssh")


def test_remote_cfs_config_init(remote_cfs_config):
    assert set(remote_cfs_config.sections) == \
           {"ccsds", "cfs", "cfs_LX1", "cfs_LX2", "core", "local_ssh", "logging", "ssh"}
    assert remote_cfs_config.validation.get_error_count() == 0
    assert remote_cfs_config.name == "local_ssh"
    assert remote_cfs_config.cfs_protocol == "ssh"
    assert remote_cfs_config.build_cfs is False
    assert remote_cfs_config.ccsds_data_dir == os.path.expanduser("~/sample_cfs_workspace/ccdd/json")
    assert remote_cfs_config.ccsds_target == "set1"
    assert remote_cfs_config.log_ccsds_imports is True
    assert remote_cfs_config.cfs_build_dir == os.path.expanduser("~/sample_cfs_workspace")
    assert remote_cfs_config.cfs_build_cmd == "make; make install"
    assert remote_cfs_config.cfs_run_dir == os.path.expanduser("~/sample_cfs_workspace/build/exe/lx1")
    assert remote_cfs_config.cfs_port_arg is False
    assert remote_cfs_config.cfs_exe == "core-lx1"
    assert remote_cfs_config.cfs_run_args == ""
    assert remote_cfs_config.cfs_run_cmd == "core-lx1"
    assert remote_cfs_config.cfs_output_file == "cfs_stdout.txt"
    assert remote_cfs_config.remove_continuous_on_fail is True
    assert remote_cfs_config.cfs_target_ip == "127.0.0.1"
    assert remote_cfs_config.ctf_ip == "127.0.0.1"
    assert remote_cfs_config.cmd_udp_port == 5010
    assert remote_cfs_config.tlm_udp_port == 5011
    assert remote_cfs_config.evs_log_file == "evs_event_msgs.log"
    assert remote_cfs_config.cfs_debug is False
    assert remote_cfs_config.cfs_run_in_xterm is False
    assert remote_cfs_config.tlm_app_choice == "ToApi"
    assert remote_cfs_config.ccsds_ver == 2
    assert remote_cfs_config.evs_long_event_mid_name == "CFE_EVS_LONG_EVENT_MSG_MID"
    assert remote_cfs_config.evs_short_event_mid_name == "CFE_EVS_SHORT_EVENT_MSG_MID"
    assert remote_cfs_config.evs_messages_clear_after_time == 5
    assert remote_cfs_config.endianess_of_target == "little"
    assert remote_cfs_config.ccsds_header_info_included is False
    assert remote_cfs_config.destination == "localhost"


