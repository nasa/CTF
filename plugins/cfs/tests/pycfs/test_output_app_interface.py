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

from lib.ctf_global import Global
from lib.logger import set_logger_options_from_config
from plugins.cfs.pycfs.output_app_interface import OutputManager, ToApi


@pytest.fixture(scope="session", autouse=True)
def init_global():
    Global.load_config("./configs/default_config.ini")


@pytest.fixture(name='outmgr')
def output_manager():
    return OutputManager('local_ip', 'local_port', 'command_interface', 'ccsds_ver')


@pytest.fixture(name='toapi')
def to_api():
    mid_map = {
        0xA00B: {
            "TO_ENABLE_OUTPUT_CC": {
                "ARG_CLASS": MagicMock(),
                "CODE": 2
            }
        }
    }
    return ToApi('local_ip', 'local_port', 'command_interface', 'ccsds_ver', mid_map, "name")


def test_output_manager_init(outmgr):
    assert outmgr.local_ip == 'local_ip'
    assert outmgr.local_port == 'local_port'
    assert outmgr.command_interface == 'command_interface'
    assert outmgr.ccsds_ver == 'ccsds_ver'
    assert outmgr.command_args is None
    assert outmgr.command_mids is None


def test_out_manager_enable_output(outmgr):
    with pytest.raises(NotImplementedError):
        outmgr.enable_output()


def test_out_manager_disable_output(outmgr):
    with pytest.raises(NotImplementedError):
        outmgr.disable_output()


def test_to_api_init(toapi):
    assert toapi.local_ip == 'local_ip'
    assert toapi.local_port == 'local_port'
    assert toapi.command_interface == 'command_interface'
    assert toapi.ccsds_ver == 'ccsds_ver'
    assert toapi.cmd_cc == 2
    assert toapi.mid == 0xA00B
    assert toapi.command_args
    assert toapi.name == 'name'


def test_to_api_init_None(utils):
    mid_map = {
        0xA00B: {
            "TO_ENABLE_OUTPUT_CC_NONE": {
                "ARG_CLASS": MagicMock(),
                "CODE": 2
            }
        }
    }
    toapi = ToApi('local_ip', 'local_port', 'command_interface', 'ccsds_ver', mid_map, "name")

    assert toapi.local_ip == 'local_ip'
    assert toapi.local_port == 'local_port'
    assert toapi.command_interface == 'command_interface'
    assert toapi.ccsds_ver == 'ccsds_ver'
    utils.has_log_level('WARNING')


def test_to_api_disable_output(toapi):
    assert toapi.disable_output()


def test_to_api_enable_output(toapi):
    with patch.object(Global, 'plugin_manager') as pm:
        assert toapi.enable_output()
        pm.find_plugin_for_command_and_execute.assert_called_with({
            "data": {
                "target": "name",
                "cc": "TO_ENABLE_OUTPUT_CC",
                "args": {"cDestIp": "local_ip", "usDestPort": "local_port"},
                "mid": 0xA00B
            },
            "instruction": "SendCfsCommand"
        })


def test_to_api_enable_output_fail(toapi, utils):
    toapi.command_args = None
    with patch.object(Global, 'plugin_manager') as pm:
        assert not toapi.enable_output()
        assert utils.has_log_level("ERROR")
        pm.find_plugin_for_command_and_execute.assert_not_called()
