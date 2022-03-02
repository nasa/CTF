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
from plugins.ssh.ssh_plugin import SshController


@pytest.fixture(scope='session', autouse=True)
def init_global():
    Global.load_config('./configs/default_config.ini')
    time_mgr = MagicMock()
    time_mgr.exec_time = 1.0
    Global.time_manager = time_mgr
    Global.current_script_log_dir = '.'


@pytest.fixture(name='remotecfs')
def remote_cfs_interface(cfs_config, mid_map, ccsdsv2):
    from plugins.cfs.pycfs.remote_cfs_interface import RemoteCfsInterface
    from plugins.cfs.pycfs.command_interface import CommandInterface
    from plugins.cfs.pycfs.tlm_listener import TlmListener
    mock_tlm = MagicMock(spec=TlmListener)
    mock_cmd = MagicMock(spec=CommandInterface)
    mock_exec = MagicMock(spec=SshController, last_result=MagicMock())
    cfs_config.build_cfs = False
    cfs_config.cfs_build_dir = '/cfs/build/dir'
    cfs_config.cfs_run_dir = '/cfs/run/dir'
    with patch('plugins.cfs.pycfs.output_app_interface.ToApi', name='mock'):
        return RemoteCfsInterface(cfs_config, mock_tlm, mock_cmd, mid_map, ccsdsv2, mock_exec)


def test_remote_cfs_interface_init(remotecfs):
    assert remotecfs.execution_controller
    assert remotecfs.init_passed


def test_remote_cfs_interface_get_start_string(remotecfs):
    assert remotecfs.get_start_string('') == './core-lx1 >> /tmp/cfs_cfs_stdout.txt'
    assert remotecfs.get_start_string('run_args') == './core-lx1 run_args >> /tmp/cfs_cfs_stdout.txt'
    remotecfs.config.cfs_port_arg = True
    assert remotecfs.get_start_string('') == './core-lx1 -p 5010 >> /tmp/cfs_cfs_stdout.txt'


def test_remote_cfs_interface_build_cfs_pass(remotecfs, utils):
    with patch('os.path.exists', return_value=False):
        remotecfs.execution_controller.get_file.return_value = False
        remotecfs.execution_controller.last_result.return_value.stdout.return_value = 'mock stdout'
        assert remotecfs.build_cfs()
        remotecfs.execution_controller.run_command.assert_called_once_with(
            'make; make install 2>&1 | tee /tmp/cfs_build_cfs_output.txt',
            cwd='/cfs/build/dir')
        assert utils.has_log_level('WARNING')


def test_remote_cfs_interface_build_cfs_fail(remotecfs, utils):
    with patch('os.path.exists', return_value=True):
        remotecfs.execution_controller.run_command.return_value = False
        assert not remotecfs.build_cfs()
        assert utils.has_log_level('ERROR')


def test_remote_cfs_interface_start_cfs_pass(remotecfs):
    remotecfs.execution_controller.run_command_persistent.return_value = True
    remotecfs.execution_controller.get_last_pid.return_value = 42
    remotecfs.execution_controller.run_command.return_value = True
    start = remotecfs.start_cfs('args')
    remotecfs.execution_controller.run_command_persistent.assert_called_once_with(
        './core-lx1 args >> /tmp/cfs_cfs_stdout.txt',
        cwd='/cfs/run/dir')
    remotecfs.execution_controller.run_command.assert_called_once_with('ps -p 42 > /dev/null 2>&1')
    assert start['result'] is True
    assert start['pid'] == 42


def test_remote_cfs_interface_start_cfs_fail(remotecfs, utils):
    remotecfs.execution_controller.run_command_persistent.return_value = False
    start = remotecfs.start_cfs('args')
    remotecfs.execution_controller.run_command_persistent.assert_called_once_with(
        './core-lx1 args >> /tmp/cfs_cfs_stdout.txt',
        cwd='/cfs/run/dir')
    remotecfs.execution_controller.run_command.assert_not_called()
    assert start['result'] is False
