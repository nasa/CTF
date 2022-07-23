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

from subprocess import PIPE, STDOUT
from unittest.mock import patch, MagicMock, mock_open, Mock

import pytest

from lib.ctf_global import Global
from lib.exceptions import CtfTestError


@pytest.fixture(scope='session', autouse=True)
def init_global():
    Global.load_config('./configs/default_config.ini')
    time_mgr = MagicMock()
    time_mgr.exec_time = 1.0
    Global.time_manager = time_mgr
    Global.current_script_log_dir = '/logs'


@pytest.fixture(name='localcfs')
def local_cfs_interface(cfs_config, mid_map, ccsdsv2):
    from plugins.cfs.pycfs.local_cfs_interface import LocalCfsInterface
    from plugins.cfs.pycfs.command_interface import CommandInterface
    from plugins.cfs.pycfs.tlm_listener import TlmListener
    mock_tlm = MagicMock(spec=TlmListener)
    mock_cmd = MagicMock(spec=CommandInterface)
    cfs_config.build_cfs = False
    cfs_config.cfs_build_dir = '/cfs/build/dir'
    cfs_config.cfs_run_dir = '/cfs/run/dir'
    with patch('plugins.cfs.pycfs.output_app_interface.ToApi', name='mock'):
        return LocalCfsInterface(cfs_config, mock_tlm, mock_cmd, mid_map, ccsdsv2)


@pytest.fixture(name='localcfs_error')
def local_cfs_interface_build_error(cfs_config, mid_map, ccsdsv2):
    from plugins.cfs.pycfs.local_cfs_interface import LocalCfsInterface
    from plugins.cfs.pycfs.command_interface import CommandInterface
    from plugins.cfs.pycfs.tlm_listener import TlmListener
    mock_tlm = MagicMock(spec=TlmListener)
    mock_cmd = MagicMock(spec=CommandInterface)
    cfs_config.build_cfs = True
    with patch('plugins.cfs.pycfs.output_app_interface.ToApi', name='mock'), \
         patch('builtins.open', new_callable=mock_open()), \
         patch('plugins.cfs.pycfs.local_cfs_interface.Popen', side_effect=Exception('mock exception')):
        return LocalCfsInterface(cfs_config, mock_tlm, mock_cmd, mid_map, ccsdsv2)


def test_local_cfs_interface_init(localcfs):
    assert localcfs.init_passed


def test_local_cfs_interface_init_error(localcfs_error):
    assert not localcfs_error.init_passed


def test_local_cfs_interface_get_start_string(localcfs, utils):
    with patch('plugins.cfs.pycfs.local_cfs_interface.find_executable') as mock_find:
        mock_find.return_value = None
        assert localcfs.get_start_string('') == './core-lx1 >> /logs/cfs_cfs_stdout.txt 2>&1'
        assert utils.has_log_level('ERROR')
        mock_find.return_value = True
        assert localcfs.get_start_string('') == \
            'xterm -T core-lx1 -l -geometry 130X24+800+0 -e ' \
            '\"script -c \' ./core-lx1\' -q -f /logs/cfs_cfs_stdout.txt\"'
        localcfs.config.cfs_debug = True
        localcfs.config.cfs_port_arg = True
        assert localcfs.get_start_string('run_args') == \
            'xterm -T core-lx1 -l -geometry 130X24+800+0 -e ' \
            '\"script -c \'gdb -tui ./core-lx1 run_args -p 5010\' -q -f /logs/cfs_cfs_stdout.txt\"'


def test_local_cfs_interface_build_cfs_pass(localcfs):
    with patch('builtins.open', new_callable=mock_open()) as mock_file, \
            patch('plugins.cfs.pycfs.local_cfs_interface.Popen') as mock_popen:
        mock_process = Mock(returncode=0, stdout=['mock build stdout'])
        mock_popen.return_value.__enter__.return_value = mock_process
        assert localcfs.build_cfs()
        mock_popen.assert_called_once_with('make; make install', cwd='/cfs/build/dir', shell=True,
                                           stdout=PIPE, stderr=STDOUT, universal_newlines=True)
        mock_process.communicate.assert_called_once()
        mock_file.return_value.__enter__.return_value.write.assert_called_once_with('mock build stdout')


def test_local_cfs_interface_build_cfs_fail(localcfs, utils):
    with patch('builtins.open', new_callable=mock_open()) as mock_file, \
            patch('plugins.cfs.pycfs.local_cfs_interface.Popen') as mock_popen:
        mock_process = Mock(returncode=-1, stdout=['mock build stdout'])
        mock_popen.return_value.__enter__.return_value = mock_process
        assert not localcfs.build_cfs()
        assert utils.has_log_level('ERROR')
        mock_popen.assert_called_once()
        mock_process.communicate.assert_called_once()
        mock_file.return_value.__enter__.return_value.write.assert_called_once_with('mock build stdout')


def test_local_cfs_interface_build_cfs_error(localcfs, utils):
    with patch('builtins.open', new_callable=mock_open()), \
         patch('plugins.cfs.pycfs.local_cfs_interface.Popen') as mock_popen:
        mock_process = Mock(returncode=0, stdout=['mock build stdout'])
        mock_process.communicate.side_effect = Exception('mock exception')
        mock_popen.return_value.__enter__.return_value = mock_process
        with pytest.raises(CtfTestError):
            localcfs.build_cfs()
        assert utils.has_log_level('ERROR')


def test_local_cfs_interface_start_cfs_pass(localcfs):
    with patch('plugins.cfs.pycfs.local_cfs_interface.time'), \
         patch('os.path.exists', return_value=True), \
         patch('plugins.cfs.pycfs.local_cfs_interface.run') as mock_run, \
         patch('plugins.cfs.pycfs.local_cfs_interface.Popen') as mock_popen:
        mock_popen.return_value.pid = 42
        mock_popen.return_value.returncode = 0
        mock_popen.return_value.poll.return_value = None
        mock_stdout = MagicMock(name='mock_stdout')
        mock_run.return_value.stdout = mock_stdout
        mock_stdout.decode.return_value = ''
        start = localcfs.start_cfs('args')
        mock_popen.assert_called_once_with(
            'xterm -T core-lx1 -l -geometry 130X24+800+0 -e '
            '\"script -c \' ./core-lx1 args\' -q -f /logs/cfs_cfs_stdout.txt\"',
            cwd='/cfs/run/dir', shell=True, universal_newlines=True)
        assert start['result'] is True
        assert start['pid'] == 42


def test_local_cfs_interface_start_cfs_pid_exist(localcfs,utils):
    with patch('plugins.cfs.pycfs.local_cfs_interface.time'), \
         patch('os.path.exists', return_value=True), \
         patch('plugins.cfs.pycfs.local_cfs_interface.run') as mock_run, \
         patch('plugins.cfs.pycfs.local_cfs_interface.Popen') as mock_popen:
        mock_stdout = MagicMock(name='mock_stdout')
        mock_run.return_value.stdout = mock_stdout
        mock_stdout.decode.return_value = '1234'
        utils.clear_log()
        start = localcfs.start_cfs('args')
        assert not start['result']
        assert utils.has_log_level('ERROR')


def test_local_cfs_interface_start_cfs_exist_cfs(localcfs, utils):
    with patch('plugins.cfs.pycfs.local_cfs_interface.time'), \
         patch('os.path.exists', return_value=False), \
         patch('plugins.cfs.pycfs.local_cfs_interface.Popen') as mock_popen:
        mock_popen.return_value.pid = 42
        mock_popen.return_value.returncode = 0
        mock_popen.return_value.poll.return_value = False
        utils.clear_log()
        start = localcfs.start_cfs('args')
        mock_popen.assert_not_called()
        assert start['result'] is False
        assert start['pid'] is None
        assert utils.has_log_level('ERROR')


def test_local_cfs_interface_start_cfs_invalid_path(localcfs, utils):
    with patch('plugins.cfs.pycfs.local_cfs_interface.time'), \
         patch('os.path.exists', return_value=False), \
         patch('plugins.cfs.pycfs.local_cfs_interface.run') as mock_run, \
         patch('plugins.cfs.pycfs.local_cfs_interface.Popen') as mock_popen:
        mock_stdout = MagicMock(name='mock_stdout')
        mock_run.return_value.stdout = mock_stdout
        mock_stdout.decode.return_value = ''
        mock_popen.return_value.pid = 42
        mock_popen.return_value.returncode = 0
        mock_popen.return_value.poll.return_value = False
        utils.clear_log()
        start = localcfs.start_cfs('args')
        mock_popen.assert_not_called()
        assert start['result'] is False
        assert start['pid'] is None
        assert utils.has_log_level('ERROR')


def test_local_cfs_interface_start_cfs_fail(localcfs, utils):
    with patch('plugins.cfs.pycfs.local_cfs_interface.time'), \
         patch('os.path.exists', return_value=True), \
         patch('plugins.cfs.pycfs.local_cfs_interface.run') as mock_run, \
         patch('plugins.cfs.pycfs.local_cfs_interface.Popen') as mock_popen:
        mock_stdout = MagicMock(name='mock_stdout')
        mock_run.return_value.stdout = mock_stdout
        mock_stdout.decode.return_value = ''
        mock_popen.return_value.pid = 42
        mock_popen.return_value.returncode = 0
        mock_popen.return_value.poll.return_value = False
        utils.clear_log()
        start = localcfs.start_cfs('args')
        mock_popen.assert_called_once()
        assert start['result'] is False
        assert start['pid'] == 42
        assert utils.has_log_level('ERROR')


def test_local_cfs_interface_start_cfs_errors(localcfs, utils):
    with patch('plugins.cfs.pycfs.local_cfs_interface.time'), \
         patch('os.path.exists'), \
         patch('plugins.cfs.pycfs.local_cfs_interface.run') as mock_run, \
         patch('plugins.cfs.pycfs.local_cfs_interface.Popen') as mock_popen:
        mock_stdout = MagicMock(name='mock_stdout')
        mock_run.return_value.stdout = mock_stdout
        mock_stdout.decode.return_value = ''
        mock_popen.side_effect = Exception('mock exception')
        utils.clear_log()
        with pytest.raises(Exception):
            localcfs.start_cfs('args')
        assert utils.has_log_level('ERROR')
