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

from unittest.mock import patch, Mock
import invoke
import pytest

from lib.exceptions import CtfTestError


def test_ssh_plugin_init(ssh_plugin_instance):
    """
    Test SSH plugin method initialize
    """
    assert ssh_plugin_instance.initialize()
    assert ssh_plugin_instance.name == "SshPlugin"
    assert ssh_plugin_instance.description == "SSH Plugin"


def test_ssh_plugin_commandmap(ssh_plugin_instance):
    """
    Test SSH plugin command content
    """
    assert "SSH_RegisterTarget" in ssh_plugin_instance.command_map
    assert "SSH_InitSSH" in ssh_plugin_instance.command_map
    assert "SSH_RunRemoteCommand" in ssh_plugin_instance.command_map
    assert "SSH_RunLocalCommand" in ssh_plugin_instance.command_map
    assert "SSH_CheckOutput" in ssh_plugin_instance.command_map
    assert "SSH_PutFile" in ssh_plugin_instance.command_map
    assert "SSH_GetFile" in ssh_plugin_instance.command_map
    assert "SSH_PutFTP" in ssh_plugin_instance.command_map
    assert "SSH_GetFTP" in ssh_plugin_instance.command_map


def test_ssh_plugin_verify_required_commands(ssh_plugin_instance):
    """
    Test SSH plugin verify_required_commands
    """
    assert len(ssh_plugin_instance.verify_required_commands) == 1
    assert "SSH_CheckOutput" in ssh_plugin_instance.verify_required_commands


def test_ssh_plugin_initialize(ssh_plugin_instance):
    """
    Test SSH plugin initialize method
    """
    assert ssh_plugin_instance.initialize()
    assert "default" in ssh_plugin_instance.targets


def test_ssh_plugin_register_target(ssh_plugin_instance):
    """
    Test SSH plugin register_target method
    """
    ssh_plugin_instance.initialize()
    assert ssh_plugin_instance.register_target("default")
    assert "workstation" not in ssh_plugin_instance.targets
    assert ssh_plugin_instance.register_target("workstation")
    assert "default" in ssh_plugin_instance.targets
    assert "workstation" in ssh_plugin_instance.targets
    # register twice
    assert ssh_plugin_instance.register_target("workstation")
    assert "workstation" in ssh_plugin_instance.targets


def test_ssh_plugin_init_connection(ssh_plugin_instance, utils):
    """
    Test SSH plugin init_connection method
    """
    utils.clear_log()

    assert "default" in ssh_plugin_instance.targets
    # ssh plugin instance has a default target with name 'default'
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    # target "workstation" is not registered yet
    assert not ssh_plugin_instance.init_connection(host='localhost', name="workstation")
    assert utils.has_log_level("ERROR")

    ssh_plugin_instance.register_target("workstation")
    # target "workstation" is registered now
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="workstation")


def test_ssh_plugin_init_connection_exception(ssh_plugin_instance):
    """
    Test SSH plugin init_connection method with exception
    """
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection') as mock_init_connection:
        mock_init_connection.side_effect = CtfTestError("Raise Exception for testing")
        assert not ssh_plugin_instance.init_connection(host='localhost', name="default")


def test_ssh_plugin_run_command(ssh_plugin_instance):
    """
    Test SSH plugin run_command method:
    Executes a command on the remote host. ExecutionInitSSH must be called first to establish an SSH connection.
    """
    ssh_plugin_instance.initialize()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.run_command', return_value=True):
        assert ssh_plugin_instance.run_command('cd lander_fsw_ctf')


def test_ssh_plugin_run_command_exception(ssh_plugin_instance, utils):
    """
    Test SSH plugin run_command method with exception:
    Executes a command on the remote host. ExecutionInitSSH must be called first to establish an SSH connection.
    """
    ssh_plugin_instance.initialize()
    utils.clear_log()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.run_command') as mock_run_command:
        mock_run_command.side_effect = invoke.exceptions.CommandTimedOut("mock failure", 10)
        assert not ssh_plugin_instance.run_command('cd lander_fsw_ctf')
        assert utils.has_log_level("ERROR")


def test_ssh_plugin_run_command_wrong_name(ssh_plugin_instance):
    """
    Test SSH plugin run_command method:
    Executes a command on the remote host. ExecutionInitSSH must be called first to establish an SSH connection.
    Call run_command with a wrong name
    """
    ssh_plugin_instance.initialize()
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.run_command', return_value=True):
        assert not ssh_plugin_instance.run_command('cd lander_fsw_ctf', name="workstation")


def test_ssh_plugin_run_command_local(ssh_plugin_instance):
    """
    Test SSH plugin run_command_local method:
    Executes a command on the local host (the machine running CTF), regardless of the target.
    """
    assert ssh_plugin_instance.initialize()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.run_command_local', return_value=True):
        assert ssh_plugin_instance.run_command_local('ls -a')


def test_ssh_plugin_run_command_local_wrong_name(ssh_plugin_instance, utils):
    """
    Test SSH plugin run_command_local method:
    Executes a command on the local host (the machine running CTF), regardless of the target.
    Call run_command_local with a wrong name
    """
    assert ssh_plugin_instance.initialize()
    utils.clear_log()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.run_command_local', return_value=True):
        assert not ssh_plugin_instance.run_command_local('ls -a', name="workstation")
        assert utils.has_log_level("ERROR")


def test_ssh_plugin_check_output(ssh_plugin_instance):
    """
    Test SSH plugin check_output method:
    Compares the output of the most recently executed command.
    ExecutionRunRemoteCommand or ExecutionRunLocalCommand must be called first
    """
    assert ssh_plugin_instance.initialize()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.check_output', return_value=True):
        assert ssh_plugin_instance.check_output()


def test_ssh_plugin_check_output_connection2(ssh_plugin_instance):
    """
    Test SSH plugin check_output method: test 2 registered targets
    Compares the output of the most recently executed command.
    ExecutionRunRemoteCommand or ExecutionRunLocalCommand must be called first
    """
    assert ssh_plugin_instance.initialize()
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    assert ssh_plugin_instance.register_target("workstation")
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.check_output', return_value=True):
        assert ssh_plugin_instance.check_output(name="workstation")


def test_ssh_plugin_check_output_wrong_name(ssh_plugin_instance, utils):
    """
    Test SSH plugin check_output method: Call check_output with a wrong name
    Compares the output of the most recently executed command.
    ExecutionRunRemoteCommand or ExecutionRunLocalCommand must be called first
    """
    assert ssh_plugin_instance.initialize()
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    utils.clear_log()
    with patch('plugins.ssh.ssh_plugin.SshController.check_output', return_value=True):
        assert not ssh_plugin_instance.check_output(name="workstation")
        assert utils.has_log_level("ERROR")


def test_ssh_plugin_check_output_without_register(ssh_plugin_instance):
    """
    Test SSH plugin check_output method: test output without registering target
    Compares the output of the most recently executed command.
    ExecutionRunRemoteCommand or ExecutionRunLocalCommand must be called first
    """
    ssh_plugin_instance.initialize()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.check_output', return_value=True):
        assert not ssh_plugin_instance.check_output(name="workstation")


def test_ssh_plugin_put_file(ssh_plugin_instance):
    """
    Test SSH plugin put_file method:
    Copies a path (file or directory) from the local filesystem to the remote host via rsync.
    """
    assert ssh_plugin_instance.initialize()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.put_file', return_value=True):
        assert ssh_plugin_instance.put_file('./cfs', '/tmp/workspace/cfs')


def test_ssh_plugin_put_file_wrong_name(ssh_plugin_instance, utils):
    """
    Test SSH plugin put_file method: Call put_file with a wrong name
    Copies a path (file or directory) from the local filesystem to the remote host via rsync.
    """
    assert ssh_plugin_instance.initialize()
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    utils.clear_log()
    with patch('plugins.ssh.ssh_plugin.SshController.put_file', return_value=True):
        assert not ssh_plugin_instance.put_file('./cfs', '/tmp/workspace/cfs', name='workstation')
        assert utils.has_log_level("ERROR")


def test_ssh_plugin_put_file_with_register(ssh_plugin_instance):
    """
    Test SSH plugin put_file method: Call put_file with registered name
    Copies a path (file or directory) from the local filesystem to the remote host via rsync.
    """
    assert ssh_plugin_instance.initialize()
    assert ssh_plugin_instance.register_target("workstation")
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.put_file', return_value=True):
        assert ssh_plugin_instance.put_file('./cfs', '/tmp/workspace/cfs', name='workstation')


def test_ssh_plugin_put_file_without_register(ssh_plugin_instance):
    """
    Test SSH plugin put_file method: Call put_file with unregistered but initialized name
    Copies a path (file or directory) from the local filesystem to the remote host via rsync.
    """
    assert ssh_plugin_instance.initialize()
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert not ssh_plugin_instance.init_connection(host='localhost', name="workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.put_file', return_value=True):
        assert not ssh_plugin_instance.put_file('./cfs', '/tmp/workspace/cfs', name='workstation')


def test_ssh_plugin_get_file(ssh_plugin_instance):
    """
    Test SSH plugin get_file method:
    Copy a path (file or directory) from the remote host to the local filesystem via rsync
    """
    assert ssh_plugin_instance.initialize()

    # SSH plugin has a default registered target named "default"
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.get_file', return_value=True):
        assert ssh_plugin_instance.get_file('./data/output.dat', './results.txt')


def test_ssh_plugin_get_file_wrong_name(ssh_plugin_instance, utils):
    """
    Test SSH plugin put_file method: Call get_file with a wrong name
    Copy a path (file or directory) from the remote host to the local filesystem via rsync
    """
    assert ssh_plugin_instance.initialize()

    # SSH plugin has a default registered target named "default"
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    utils.clear_log()
    with patch('plugins.ssh.ssh_plugin.SshController.get_file', return_value=True):
        assert not ssh_plugin_instance.get_file('./data/output.dat', './results.txt', name='workstation')
        assert utils.has_log_level("ERROR")


def test_ssh_plugin_get_file_with_register(ssh_plugin_instance):
    """
    Test SSH plugin get_file method: Call get_file with registered name
    Copy a path (file or directory) from the remote host to the local filesystem via rsync
    """
    assert ssh_plugin_instance.initialize()
    assert ssh_plugin_instance.register_target("workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.get_file', return_value=True):
        assert ssh_plugin_instance.get_file('./data/output.dat', './results.txt', name='workstation')


def test_ssh_plugin_get_file_without_register(ssh_plugin_instance):
    """
    Test SSH plugin get_file method: Call get_file with unregistered but initialized name
    Copy a path (file or directory) from the remote host to the local filesystem via rsync
    """
    assert ssh_plugin_instance.initialize()

    # target "workstation" is not registered
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert not ssh_plugin_instance.init_connection(host='localhost', name="workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.get_file', return_value=True):
        assert not ssh_plugin_instance.get_file('./data/output.dat', './results.txt', name='workstation')


def test_ssh_plugin_upload_ftp(ssh_plugin_instance):
    """
    Test SSH plugin upload_ftp method:
    Uploads a path (file or directory) from the local filesystem to the FTP server.
    """
    assert ssh_plugin_instance.initialize()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.upload_ftp', return_value=True):
        assert ssh_plugin_instance.upload_ftp('localhost', './results.txt', './data/output.dat')


def test_ssh_plugin_upload_ftp_wrong_name(ssh_plugin_instance, utils):
    """
    Test SSH plugin upload_ftp method: call upload_ftp with wrong name
    Uploads a path (file or directory) from the local filesystem to the FTP server.
    """
    assert ssh_plugin_instance.initialize()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    utils.clear_log()
    with patch('plugins.ssh.ssh_plugin.SshController.upload_ftp', return_value=True):
        assert not ssh_plugin_instance.upload_ftp('localhost', './results.txt', './data/output.dat', name='workstation')
        assert utils.has_log_level("ERROR")


def test_ssh_plugin_upload_ftp_with_register(ssh_plugin_instance):
    """
    Test SSH plugin upload_ftp method: Call upload_ftp with a registered name
    Uploads a path (file or directory) from the local filesystem to the FTP server.
    """
    assert ssh_plugin_instance.initialize()
    assert ssh_plugin_instance.register_target("workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.upload_ftp', return_value=True):
        assert ssh_plugin_instance.upload_ftp('localhost', './results.txt', './data/output.dat', name='workstation')


def test_ssh_plugin_upload_ftp_without_register(ssh_plugin_instance):
    """
    Test SSH plugin upload_ftp method: Call upload_ftp with unregistered but initialized name
    Uploads a path (file or directory) from the local filesystem to the FTP server.
    """
    assert ssh_plugin_instance.initialize()

    # target "workstation" is not registered
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert not ssh_plugin_instance.init_connection(host='localhost', name="workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.upload_ftp', return_value=True):
        assert not ssh_plugin_instance.upload_ftp('localhost', './results.txt', './data/output.dat', name='workstation')


def test_ssh_plugin_download_ftp(ssh_plugin_instance):
    """
    Test SSH plugin download_ftp method:
    Downloads a path (file or directory) from the FTP server to the local filesystem.
    """
    assert ssh_plugin_instance.initialize()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    with patch('plugins.ssh.ssh_plugin.SshController.download_ftp', return_value=True):
        assert ssh_plugin_instance.download_ftp('localhost', './data/output.dat', './results.txt', )


def test_ssh_plugin_download_ftp_wrong_name(ssh_plugin_instance, utils):
    """
    Test SSH plugin download_ftp method: call download_ftp with a wrong name
    Downloads a path (file or directory) from the FTP server to the local filesystem.
    """
    assert ssh_plugin_instance.initialize()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="default")

    utils.clear_log()
    with patch('plugins.ssh.ssh_plugin.SshController.download_ftp', return_value=True):
        assert not ssh_plugin_instance.download_ftp('localhost', './output.dat', './results.txt', name='workstation')
        assert utils.has_log_level("ERROR")


def test_ssh_plugin_download_ftp_with_registered_name(ssh_plugin_instance):
    """
    Test SSH plugin download_ftp method: call download_ftp with a registered name
    Downloads a path (file or directory) from the FTP server to the local filesystem.
    """
    assert ssh_plugin_instance.initialize()

    assert ssh_plugin_instance.register_target("workstation")
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert ssh_plugin_instance.init_connection(host='localhost', name="workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.download_ftp', return_value=True):
        assert ssh_plugin_instance.download_ftp('localhost', './output.dat', './results.txt', name='workstation')


def test_ssh_plugin_download_ftp_without_register(ssh_plugin_instance):
    """
    Test SSH plugin download_ftp method: call download_ftp with unregistered but initialized name
    Downloads a path (file or directory) from the FTP server to the local filesystem.
    """
    assert ssh_plugin_instance.initialize()

    # target "workstation" is not registered
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        assert not ssh_plugin_instance.init_connection(host='localhost', name="workstation")

    with patch('plugins.ssh.ssh_plugin.SshController.download_ftp', return_value=True):
        assert not ssh_plugin_instance.download_ftp('localhost', './output.dat', './results.txt', name='workstation')


def test_ssh_plugin_shutdown(ssh_plugin_instance):
    """
    Test SSH plugin shutdown method
    The shutdown function is called by the CTF plugin manager upon completion of a test run.
    """
    assert ssh_plugin_instance.initialize()
    assert ssh_plugin_instance.shutdown() is None


def test_ssh_controller_init(ssh_controller_instance):
    """
    Test SshController constructor
    """
    assert ssh_controller_instance.connection is None
    assert ssh_controller_instance.last_result is None
    assert ssh_controller_instance.last_pid is None


def test_ssh_controller_init_connection(ssh_controller_instance):
    """
    Test SshController init_connection method
    init_connection provides implementation of SSH plugin's init_connection method
    """
    assert ssh_controller_instance.connection is None

    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')
        assert ssh_controller_instance.connection is not None

    with pytest.raises(CtfTestError):
        ssh_controller_instance.init_connection('unknowns')


def test_ssh_controller_init_connection_with_existing_connection(ssh_controller_instance):
    """
    Test SshController init_connection method
    init_connection provides implementation of SSH plugin's init_connection method
    """
    assert ssh_controller_instance.connection is None
    ssh_controller_instance.connection = Mock()
    ssh_controller_instance.connection.is_connected = True

    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost', ssh_config_path='/')
        assert ssh_controller_instance.connection is not None


def test_ssh_controller_init_connection_twice(ssh_controller_instance):
    """
    Test SshController init_connection method: init connection twice.
    init_connection provides implementation of SSH plugin's init_connection method
    """
    assert ssh_controller_instance.connection is None

    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')
        assert ssh_controller_instance.init_connection('localhost')
        assert ssh_controller_instance.connection is not None


def test_ssh_controller_run_command(ssh_controller_instance):
    """
    Test SshController run_command method
    run_command provides implementation of SSH plugin's run_command / SSH_RunRemoteCommand method
    """
    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    with patch('fabric.connection.Connection.run') as mock_run, \
            patch('fabric.connection.Connection.is_connected', return_value=True):
        mock_result = Mock()
        mock_run.return_value = mock_result
        mock_result.exited = 0
        mock_result.stdout = ''
        assert ssh_controller_instance.run_command('cd lander_fsw_ctf')


def test_ssh_controller_run_command_exception(ssh_controller_instance, utils):
    """
    Test SshController run_command method: raise exception
    run_command provides implementation of SSH plugin's run_command / SSH_RunRemoteCommand method
    """
    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    utils.clear_log()
    with patch('fabric.connection.Connection.run') as mock_run, \
            patch('fabric.connection.Connection.is_connected', return_value=True):
        mock_run.side_effect = invoke.exceptions.CommandTimedOut("mock failure", 10)
        ssh_controller_instance.config.log_stdout = None
        assert not ssh_controller_instance.run_command('cd lander_fsw_ctf')
        assert utils.has_log_level("ERROR")


def test_ssh_controller_run_command_without_connection(ssh_controller_instance, utils):
    """
    Test SshController run_command method without connection
    run_command provides implementation of SSH plugin's run_command / SSH_RunRemoteCommand method
    """
    utils.clear_log()
    assert not ssh_controller_instance.run_command('cd lander_fsw_ctf')
    assert utils.has_log_level("ERROR")


def test_ssh_controller_run_command_persistent(ssh_controller_instance):
    """
    Test SshController run_command_persistent method
    run_command_persistent implement SSH persistent call with configurable time-out
    """
    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    assert ssh_controller_instance.get_last_pid() is None

    with patch('fabric.connection.Connection.run') as mock_run, \
            patch('fabric.connection.Connection.is_connected', return_value=True):
        mock_result = Mock()
        mock_run.return_value = mock_result
        mock_result.exited = 0
        mock_result.stdout = '65432'
        assert ssh_controller_instance.run_command_persistent('cd lander_fsw_ctf')
        assert ssh_controller_instance.get_last_pid() == '65432'

    with patch('fabric.connection.Connection.run') as mock_run, \
            patch('fabric.connection.Connection.is_connected', return_value=True):
        mock_result = Mock()
        mock_run.return_value = mock_result
        mock_result.exited = 0
        mock_result.stdout = None
        assert ssh_controller_instance.run_command_persistent('cd lander_fsw_ctf')


def test_ssh_controller_run_command_persistent_exception(ssh_controller_instance, utils):
    """
    Test SshController run_command_persistent method: raise exception
    run_command_persistent implement SSH persistent call with configurable time-out
    """
    # test case: connection is not connected
    assert not ssh_controller_instance.run_command_persistent('cd lander_fsw_ctf')

    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    assert ssh_controller_instance.get_last_pid() is None
    utils.clear_log()

    with patch('fabric.connection.Connection.run') as mock_run, \
            patch('fabric.connection.Connection.is_connected', return_value=True):
        mock_run.side_effect = invoke.exceptions.CommandTimedOut("mock failure", 10)
        with pytest.raises(invoke.exceptions.CommandTimedOut):
            ssh_controller_instance.run_command_persistent('cd lander_fsw_ctf')
            assert utils.has_log_level("ERROR")


def test_ssh_controller_run_command_local(ssh_controller_instance):
    """
    Test SshController run_command_local method
    run_command_local provides implementation of SSH plugin's run_command_local / SSH_RunLocalCommand method
    """
    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    with patch('invoke.run') as mock_run:
        mock_result = Mock()
        mock_run.return_value = mock_result
        mock_result.exited = 0
        mock_result.stdout = ''
        assert ssh_controller_instance.run_command_local('make install')

    with patch('invoke.run') as mock_run:
        mock_result = Mock()
        mock_run.return_value = mock_result
        mock_result.exited = 0
        mock_result.stdout = ''
        ssh_controller_instance.config.log_stdout = None
        assert ssh_controller_instance.run_command_local('make install')


def test_ssh_controller_run_command_local_exception(ssh_controller_instance):
    """
    Test SshController run_command_local method: raise exception
    run_command_local provides implementation of SSH plugin's run_command_local / SSH_RunLocalCommand method
    """
    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    with patch('invoke.run') as mock_run:
        mock_run.side_effect = invoke.exceptions.CommandTimedOut("mock failure", 10)
        ssh_controller_instance.run_command_local('make install')


def test_ssh_controller_check_output(ssh_controller_instance):
    """
    Test SshController check_output method
    check_output provides implementation of SSH plugin's check_output / SSH_CheckOutput method
    """
    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    with patch('invoke.run') as mock_run:
        mock_result = Mock()
        mock_run.return_value = mock_result
        mock_result.exited = 0
        mock_result.stdout = 'Built target mission-install'
        assert ssh_controller_instance.run_command_local('make install')
        assert ssh_controller_instance.check_output(exit_code=0)
        assert ssh_controller_instance.check_output(output_contains='mission-install')
        assert ssh_controller_instance.check_output(output_does_not_contain='Error')


def test_ssh_controller_check_output_fail(ssh_controller_instance):
    """
    Test SshController check_output method: check failed test cases
    check_output provides implementation of SSH plugin's check_output / SSH_CheckOutput method
    """

    assert not ssh_controller_instance.check_output(output_contains='mission-install')

    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    with patch('invoke.run') as mock_run:
        mock_result = Mock()
        mock_run.return_value = mock_result
        mock_result.exited = 0
        mock_result.stdout = 'Built target mission-install'
        assert ssh_controller_instance.run_command_local('make install')
        assert not ssh_controller_instance.check_output(exit_code=9)
        assert not ssh_controller_instance.check_output(output_contains='mock input')
        assert not ssh_controller_instance.check_output(output_does_not_contain='install')


def test_ssh_controller_upload_ftp(ssh_controller_instance):
    """
    Test SshController upload_ftp method
    upload_ftp provides implementation of SSH plugin's upload_ftp / SSH_PutFTP method
    """
    mock_ftp_interface = Mock()
    ssh_controller_instance.ftp_interface = mock_ftp_interface
    mock_ftp_interface.upload_ftputil.side_effect = [False, True]

    assert not ssh_controller_instance.upload_ftp('localhost', './results.txt', './data/output.dat')
    assert ssh_controller_instance.upload_ftp('localhost', './results.txt', './data/output.dat')


def test_ssh_controller_download_ftp(ssh_controller_instance):
    """
    Test SshController download_ftp method
    download_ftp provides implementation of SSH plugin's download_ftp / SSH_GetFTP method
    """
    mock_ftp_interface = Mock()
    ssh_controller_instance.ftp_interface = mock_ftp_interface
    mock_ftp_interface.download_ftputil.side_effect = [False, True]

    assert not ssh_controller_instance.download_ftp('localhost', './data/output.dat', './results.txt', )
    assert ssh_controller_instance.download_ftp('localhost', './data/output.dat', './results.txt', )


def test_ssh_controller_get_file(ssh_controller_instance):
    """
    Test SshController get_file method
    get_file provides implementation of SSH plugin's get_file / SSH_GetFile method
    """

    # without init_connection, it should return False
    assert not ssh_controller_instance.get_file('./data/output.dat', './results.txt')

    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    with patch('plugins.ssh.ssh_plugin.transfers.rsync', return_value=True), \
         patch('fabric.connection.Connection.is_connected', return_value=True):
        assert ssh_controller_instance.get_file('./data/output.dat', './results.txt')


def test_ssh_controller_get_file_exception(ssh_controller_instance, utils):
    """
    Test SshController get_file method: test with exception
    get_file provides implementation of SSH plugin's get_file / SSH_GetFile method
    """
    utils.clear_log()
    # without init_connection, it should return False
    assert not ssh_controller_instance.get_file('./data/output.dat', './results.txt')

    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    with patch('plugins.ssh.ssh_plugin.transfers.rsync') as mock_rsync, \
            patch('fabric.connection.Connection.is_connected', return_value=True):
        mock_rsync.side_effect = CtfTestError("mock_rsync")
        assert not ssh_controller_instance.get_file('./data/output.dat', './results.txt')
        assert utils.has_log_level("ERROR")


def test_ssh_controller_put_file(ssh_controller_instance):
    """
    Test SshController put_file method
    put_file provides implementation of SSH plugin's put_file / SSH_PutFile method
    """
    # without init_connection, it should return False
    assert not ssh_controller_instance.put_file('./data/output.dat', './results.txt')

    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    with patch('plugins.ssh.ssh_plugin.transfers.rsync', return_value=True), \
         patch('fabric.connection.Connection.is_connected', return_value=True):
        assert ssh_controller_instance.put_file('./data/output.dat', './results.txt')


def test_ssh_controller_put_file_exception(ssh_controller_instance, utils):
    """
    Test SshController put_file method: test with exception
    put_file provides implementation of SSH plugin's put_file / SSH_PutFile method
    """
    utils.clear_log()
    # without init_connection, it should return False
    assert not ssh_controller_instance.put_file('./data/output.dat', './results.txt')

    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')
    with patch('plugins.ssh.ssh_plugin.transfers.rsync') as mock_rsync, \
            patch('fabric.connection.Connection.is_connected', return_value=True):
        mock_rsync.side_effect = Exception("mock_rsync")
        assert not ssh_controller_instance.put_file('./data/output.dat', './results.txt')
        assert utils.has_log_level("ERROR")


def test_ssh_controller_rsync(ssh_controller_instance):
    """
    Test SshController rsync method
    rsync implements async file transfer
    """
    with patch('fabric.connection.Connection.open', return_value=True):
        assert ssh_controller_instance.init_connection('localhost')

    with patch('plugins.ssh.ssh_plugin.transfers.rsync', return_value=True):
        assert ssh_controller_instance.rsync('./data/output.dat', './results.txt', False)

    # test raise exception without mock
    with pytest.raises(CtfTestError):
        ssh_controller_instance.rsync('./data/output.dat', './results.txt', False)


def test_ssh_controller_shutdown(ssh_controller_instance):
    """
    Test SshController shutdown method
    shutdown provides implementation of SSH plugin's shutdown method
    """
    assert ssh_controller_instance.connection is None
    ssh_controller_instance.connection = Mock()
    ssh_controller_instance.connection.is_connected = True

    assert ssh_controller_instance.shutdown() is None
