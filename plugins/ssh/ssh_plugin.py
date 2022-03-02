"""
@namespace plugins.ssh_plugin
The SSH Plugin provides remote and local shell command execution capability for CTF.
The module defines SshPlugin class and SshConfig, SshController helper class.
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

import fabric
import invoke

from lib.exceptions import CtfTestError
from lib.patchwork.patchwork import transfers
from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log
from lib.ctf_global import Global
from lib.ctf_utility import expand_path
from lib.ftp_interface import FtpInterface


class SshConfig:
    """
    The SshConfig helper Class Definition

    @note it gets the command_timeout, print_stdout and print_stdout from configuration Json file
    """
    def __init__(self):
        """
        Constructor implementation for SshConfig helper class.
        """
        # Retrieve all required data from the configuration file
        ## SshConfig command_timeout property
        self.command_timeout = Global.config.getfloat("ssh", "command_timeout")
        ## SshConfig print_stdout property
        self.print_stdout = Global.config.getboolean("ssh", "print_stdout")
        ## SshConfig log_stdout property
        self.log_stdout = Global.config.getboolean("ssh", "log_stdout")


class SshPlugin(Plugin):
    """
    The SSH Plugin Class Definition

    @note The SSH Plugin provides remote and local shell command execution capability for CTF.

    @note The following test instructions are available:

    @note SSH_RegisterTarget;SSH_InitSSH; SSH_RunRemoteCommand;SSH_RunLocalCommand; SSH_CheckOutput; SSH_PutFile;

    @note SSH_GetFile; SSH_GetFTP; SSH_PutFTP;

    @note A custom CTF plugin can be created to add new CTF instructions that can then be utilized within a JSON test
        script.

    @note All plugin functions mapped to a test instruction *must* return true/false to indicate pass/fail of
        that instruction.
    """
    def __init__(self):
        """
        Constructor implementation for SSH plugin.

        @note The __init__ function is called once a plugin is loaded.

        @note The __init__ function should not reference/interact with any other plugin since the other plugin may not
            be loaded at this stage.

        @note The constructor of a plugin must define the following fields:
            - name
            - description
            - command map: dictionary mapping CTF instructions to a tuple defining the
                          python function to use for that instruction, and a list of argument types
            - [optional] verify_required_commands: List of instructions that require verification (i.e polling
            until verification passes or timeout.
            - other class variables that can store state, etc...
        """
        super().__init__()
        self.name = "SshPlugin"
        self.description = "SSH Plugin"
        self.targets = {}
        self.command_map = {
            # name
            "SSH_RegisterTarget":
                (self.register_target, [ArgTypes.string]),
            # host, user=None, port=None, gateway=None, ssh_config_path=None, args=None, name="default"
            "SSH_InitSSH":
                (self.init_connection,
                 [ArgTypes.string, ArgTypes.string, ArgTypes.number, ArgTypes.string,
                  ArgTypes.string, ArgTypes.cmd_arg, ArgTypes.string]),
            # command, cwd="", prefix=":", name="default"
            "SSH_RunRemoteCommand":
                (self.run_command, [ArgTypes.string, ArgTypes.string, ArgTypes.string, ArgTypes.string]),
            # command, name="default"
            "SSH_RunLocalCommand":
                (self.run_command_local, [ArgTypes.string, ArgTypes.string]),
            # output_contains=None, output_does_not_contain=None, exit_code=0, name="default"
            "SSH_CheckOutput":
                (self.check_output, [ArgTypes.string, ArgTypes.string, ArgTypes.number, ArgTypes.string]),
            # local_path, remote_path, args=None, name="default"
            "SSH_PutFile":
                (self.put_file, [ArgTypes.string, ArgTypes.string, ArgTypes.cmd_arg, ArgTypes.string]),
            # remote_path, local_path, args=None, name="default"
            "SSH_GetFile":
                (self.get_file, [ArgTypes.string, ArgTypes.string, ArgTypes.cmd_arg, ArgTypes.string]),
            # host, local_path, remote_path, name="default"
            "SSH_PutFTP":
                (self.upload_ftp, [ArgTypes.string, ArgTypes.string, ArgTypes.string, ArgTypes.string]),
            # host, remote_path, local_path, name="default"
            "SSH_GetFTP":
                (self.download_ftp, [ArgTypes.string, ArgTypes.string, ArgTypes.string, ArgTypes.string])
        }
        self.verify_required_commands = ["SSH_CheckOutput"]

        self.initialize()

    def initialize(self):
        """
           Initialize implementation for the SSH plugin.

           @note The initialize function is called by the CTF plugin manager *after* all plugins have been loaded.

           @note This function may interact with other plugins, since all plugins have been loaded at this stage.

           @return bool: True if successful, False otherwise.
        """
        self.register_target("default")
        return True

    def register_target(self, name=""):
        """
        Declares a target host by name. This command must be run before any other commands given the same name.
        Command may be used multiple times to declare any number of targets.
        If not used,the plugin will assume that all commands are intended for the same target as defined in SSH_InitSSH.

        @param name: An arbitrary, unique name to identify the target in subsequent commands.
        Does not need be the actual hostname of the target. Name is optional in all other commands,
        but if not provided all such commands will share a single connection.

        @return bool: True if successful, False otherwise.

        @par Example
        @code
        {
            "command": "SSH_RegisterTarget",
            "wait": 1,
            "data": {
                 "name": "workstation"
            }
        }
        """
        if name in self.targets:
            if name != "default":
                log.warning("SSH target {} is already registered".format(name))
                log.warning("Overriding Target {} SSH Configuration".format(name))

        self.targets[name] = SshController(SshConfig())
        return True

    def init_connection(self, host, user=None, port=None, gateway=None,
                        ssh_config_path=None, args=None, name="default"):
        """
        Establishes an SSH connection with a target host.
        This command must be run before other remote commands will work.
        Command may be used multiple times with the same name to connect to different remote hosts in succession,
        or be used with different names to maintain concurrent connections to multiple hosts.
           - **host**: hostname or IP to connect to, which may include the username and/or port.

        @param name: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
        @param user: User name for the connection. Do not use if you specified the user in `host`. (Optional)
        @param port: Port number for the connection. Do not use if you specified the port in `host`. (Optional)
        @param gateway: SSH gateway command string to proxy the connection to `host` (Optional)
        @param ssh_config_path: Path to an ssh config file which may contain host definitions or additional parameters.
                                If not specfied, `~/.ssh/config` will be assumed. (Optional)
        @param args: Additional SSH connection options, as needed. See [Paramiko API docs] (Optional)
            (http://docs.paramiko.org/en/latest/api/client.html#paramiko.client.SSHClient.connect) for relevant values.

        @return bool: True if successful, False otherwise.
        """
        log.debug("SshPlugin.init_connection")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False
        try:
            result = self.targets[name].init_connection(host, user, port, gateway, ssh_config_path, args)
        except CtfTestError:
            result = False
        return result

    def run_command(self, command, cwd="", prefix=":", name="default"):
        """
        Executes a command on the remote host. ExecutionInitSSH must be called first to establish an SSH connection.

        @param name: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
        @param command: The shell command to be executed. Can contain multiple commands separated with `;`
        @return bool: True if successful, False otherwise.
        @par Example:
        @code
        {
            "command": "SSH_RunLocalCommand",
            "wait": 1,
            "data": {
                "name": "workstation",
                "host": "cd lander_fsw_ctf/;rm -rf build; make; make install;"
            }
        }
        """
        log.debug("SshPlugin.run_command")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False
        try:
            result = self.targets[name].run_command(command, cwd, prefix)
        except invoke.exceptions.CommandTimedOut:
            log.error("Timed out running command. Please increase command timeout if this is a valid command.")
            result = False
        return result

    def run_command_local(self, command, name="default"):
        """
        Executes a command on the local host (the machine running CTF), regardless of the target.
        This is different from calling SSH_RunRemoteCommand targeting localhost,
        as it is invoked directly by the current process rather than passed via SSH.

        @param name: A name already registered with SSH_RegisterTarget to identify the connection. (Optional)
        @param command: The shell command to be executed. Can contain multiple commands separated with ;
        @return bool: True if successful, False otherwise.
        @par Example:
        @code
        {
            "command": "SSH_RunLocalCommand",
            "wait": 1,
            "data": {
                "name": "workstation",
                "host": "cd lander_fsw_ctf/;rm -rf build; make; make install;"
            }
        }
        """
        log.debug("SshPlugin.run_command_local")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].run_command_local(command)

    def check_output(self, output_contains=None, output_does_not_contain=None, exit_code=0, name="default"):
        """
        Compares the output of the most recently executed command.
        ExecutionRunRemoteCommand or ExecutionRunLocalCommand must be called first.

        @param name: A name already registered with SSH_RegisterTarget to identify the connection. (Optional)
        @param output_contains: A substring that must be contained in stdout. (Example: "PASS") (Optional)
        @param output_does_not_contain: A substring that should not be contained in stdout. (Example: "FAIL") (Optional)
        @param exit_code: The expected exit code after the shell command is executed. (Optional default = 0)

        @return bool: True if successful, False otherwise.

        @par Example:
        @code
        {
            "command": "SSH_CheckOutput",
            "wait": 0,
            "data": {
                "name": "workstation",
                "output_contains": "Built target mission-install",
                "output_does_not_contain": "Error",
                "exit_code": 0
            }
        }
        """
        log.debug("SshPlugin.check_output")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].check_output(output_contains, output_does_not_contain, exit_code)

    def put_file(self, local_path, remote_path, args=None, name="default"):
        """
        Copies a path (file or directory) from the local filesystem to the remote host via rsync.
        Relative or absolute paths are allowed, but do not use ~. Strings are passed directly to rsync,
        so the same rules apply regarding paths, patterns, etc.

        @param name: A name already registered with SSH_RegisterTarget to identify the connection. (Optional)
        @param local_path: The path to the local file or directory to be copied.
        @param remote_path: The path to where the file or directory is to be copied.
                            For remote hosts use the SSH syntax user@host:path.
        @param args: An object that describes optional parameters for the transfer.
                     delete: A boolean corresponding to rsync’s --delete option.
                     If true, rsync will remove remote files that no longer exist locally. Defaults to false.
                     exclude: A string or array of strings corresponding to rsync's --exclude option. Defaults to None.

        @return bool: True if successful, False otherwise.
        @par Example:
        @code
        {
            "command": "SSH_PutFile",
            "wait": 0,
            "data": {
                "name": "workstation",
                "local_path": "./cfs",
                "remote_path": "/tmp/workspace/cfs",
                "args": {
                    "delete": true,
                    "exclude": "*.git"
                }
            }
        }
        """
        log.debug("SshPlugin.put_file")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].put_file(local_path, remote_path, args)

    def get_file(self, remote_path, local_path, args=None, name="default"):
        """
        Copies a path (file or directory) from the remote host to the local filesystem via rsync.
        Relative or absolute paths are allowed, but do not use ~. Strings are passed directly to rsync,
        so the same rules apply regarding paths, patterns, etc.

        @param name: A name already registered with SSH_RegisterTarget to identify the connection. (Optional)
        @param remote_path: The path to where the file or directory is to be copied.
                            For remote hosts use the SSH syntax user@host:path.
        @param local_path: The path to the local file or directory to be copied.

        @param args: An object that describes optional parameters for the transfer.
                     delete: A boolean corresponding to rsync’s --delete option.
                     If true, rsync will remove remote files that no longer exist locally. Defaults to false.
                     exclude: A string or array of strings corresponding to rsync's --exclude option. Defaults to None.

        @return bool: True if successful, False otherwise.
        @par Example:
        @code
        {
            "command": "SSH_GetFile",
            "wait": 0,
            "data": {
                "name": "workstation",
                "remote_path": "./data/output.dat",
                "local_path": "./results.txt"
            }
        }
        """
        log.debug("SshPlugin.get_file")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].get_file(remote_path, local_path, args)

    def upload_ftp(self, host, local_path, remote_path, name="default"):
        """
        Uploads a path (file or directory) from the local filesystem to the FTP server.

        @param name: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
        @param host: The hostname or address of the FTP server.
        @param remote_path: The path on the FTP server to where the file or directory is to be uploaded.
        @param local_path: The local path to the source file or directory.

        @return bool: True if successful, False otherwise.

        @par Example:
        @code
        {
            "command": "SSH_PutFTP",
            "wait": 0,
            "data": {
                "name": "workstation",
                 "host": "ftphost",
                 "remote_path": "./data/output.dat",
                 "local_path": "./results.txt"
            }
        }
        """
        log.debug("SshPlugin.upload_ftp")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].upload_ftp(host, local_path, remote_path)

    def download_ftp(self, host, remote_path, local_path, name="default"):
        """
        Downloads a path (file or directory) from the FTP server to the local filesystem.

        @param name: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
        @param host: The hostname or address of the FTP server.
        @param remote_path: The path to the source file or directory on the FTP server.
        @param local_path: The local path to where the file or directory is to be downloaded.

        @return bool: True if successful, False otherwise.

        @par Example:
        @code
        {
            "command": "SSH_GetFTP",
            "wait": 0,
            "data": {
                "name": "workstation",
                "host": "ftphost",
                "remote_path": "./data/output.dat",
                "local_path": "./results.txt"
            }
        }
        """
        log.debug("SshPlugin.download_ftp")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].download_ftp(host, remote_path, local_path)

    def shutdown(self):
        """
        Shutdown implementation for the SSH plugin.
        @note The shutdown function is called by the CTF plugin manager upon completion of a test run.
        @note The shutdown function can be exposed to test scripts by adding it to the command map.
        """
        log.info("SshPlugin.shutdown")
        for name in self.targets:
            log.debug("Shutting down Execution target {}".format(name))
            self.targets[name].shutdown()

        self.targets.clear()


class SshController():
    """
    The SshController helper Class Definition

    @note SshController provides an instance of SSH plugin's target:  self.targets[name] = SshController(SshConfig())

    @note SshController provides the implementation SSH plugin's commands. For example, upload_ftp commands calls
          self.targets[name].download_ftp(host, remote_path, local_path)
    """
    def __init__(self, config):
        """
        Constructor implementation for SshController helper class.
        """
        self.config = config
        self.connection = None
        self.last_result = None
        self.last_pid = None
        self.ftp_interface = FtpInterface()

    def init_connection(self, host, user=None, port=None, gateway=None, ssh_config_path=None, args=None):
        """
        init_connection provides implementation of SSH plugin's init_connection method:
                self.targets[name].init_connection(host, user, port, gateway, ssh_config_path, args)
        """
        try:
            if self.connection and self.connection.is_connected:
                log.debug("Closing connection to {}".format(self.connection.host))
                self.connection.close()

            if ssh_config_path:
                ssh_config_path = expand_path(ssh_config_path)
            config = fabric.Config(runtime_ssh_path=ssh_config_path)
            self.connection = fabric.Connection(host,
                                                user=user,
                                                port=port,
                                                gateway=gateway,
                                                config=config,
                                                connect_kwargs=args)
            log.debug("Opening connection to {}...".format(self.connection.host))
            self.connection.open()
            return True
        except Exception as exception:
            log.error("Remote connection failed: {}".format(exception))
            raise CtfTestError("Error in init_connection") from exception

    def run_command(self, command, cwd="", prefix=":"):
        """
        run_command provides implementation of SSH plugin's run_command / SSH_RunRemoteCommand method:
                self.targets[name].run_command(command, cwd, prefix)
        """
        log.info("Remote Command with command: {}".format(command))

        if not self.connection or not self.connection.is_connected:
            log.error("No connection to remote host.")
            return False
        with self.connection.cd(cwd):
            with self.connection.prefix(prefix):
                try:
                    result = self.connection.run(command,
                                                 hide=(not self.config.print_stdout),
                                                 timeout=self.config.command_timeout)
                except (invoke.exceptions.UnexpectedExit, invoke.exceptions.CommandTimedOut):
                    result = invoke.Result(exited=1)
                    log.error("Remote run command {} failed".format(command))
        if self.config.log_stdout:
            log.info("Remote {cmd} complete with result:\n {res}\n Exit Code = {code}"
                     .format(cmd=command, res=result.stdout.strip(), code=result.exited))
        else:
            log.info("Remote {cmd} complete. Exit Code = {code}".format(cmd=command, code=result.exited))

        self.last_result = result
        return result.exited == 0

    def run_command_persistent(self, command, cwd="", prefix=":"):
        """
        run_command_persistent implement SSH persistent call with configurable time-out
        """
        log.info("Remote persistent command: {}".format(command))

        if not self.connection or not self.connection.is_connected:
            log.error("No connection to remote host.")
            return False

        # ENHANCE Investigate ways to pipe the output back and capture it live instead of directing to /dev/null.
        #  The interaction of fabric and nohup etc. limit our options
        pid_file = "/tmp/pid"
        cmd_str = "nohup sh -c '{command} & echo $! > {pid_file}' & 2>&1".format(command=command, pid_file=pid_file)
        with self.connection.cd(cwd):
            with self.connection.prefix(prefix):
                try:
                    result = self.connection.run(cmd_str,
                                                 hide=(not self.config.print_stdout),
                                                 timeout=self.config.command_timeout)
                except (invoke.exceptions.UnexpectedExit, invoke.exceptions.CommandTimedOut):
                    result = invoke.Result(exited=1)
                    log.error("Remote run command persistent {} failed".format(command))

        # ENHANCE Investigate ways this could go wrong in various error conditions. There may be a more
        #  reliable method to preserve the PID and/or avoid possibly picking up an old one.
        pid = self.connection.run('cat {pid_file} && > {pid_file}'.format(pid_file=pid_file))
        if pid.exited == 0 and pid.stdout:
            self.last_pid = pid.stdout.rstrip()
        else:
            self.last_pid = None
            log.error("Unable to get PID of last command!")
        log.info("Remote {cmd} complete. Exit Code = {code}. PID = {pid}"
                 .format(cmd=cmd_str, code=result.exited, pid=self.last_pid))

        self.last_result = result
        return result.exited == 0

    def get_last_pid(self):
        """
          return  last_pid
         """
        return self.last_pid

    def run_command_local(self, command):
        """
        run_command_local provides implementation of SSH plugin's run_command_local / SSH_RunLocalCommand method:
                self.targets[name].run_command_local(command)
        """
        log.info("Local Command with command: {}".format(command))
        try:
            result = invoke.run(command, hide=(not self.config.print_stdout), timeout=self.config.command_timeout)
            if self.config.log_stdout:
                log.info("Local {cmd} complete with result:\n {res}\n Exit Code = {code}"
                         .format(cmd=command, res=result.stdout.strip(), code=result.exited))
            else:
                log.info("Local {cmd} complete. Exit Code = {code}".format(cmd=command, code=result.exited))

            self.last_result = result
            return result.exited == 0

        except (invoke.exceptions.UnexpectedExit, invoke.exceptions.CommandTimedOut) as exception:
            self.last_result = exception.result
            log.error(exception.result)
            return False

    def check_output(self, output_contains=None, output_does_not_contain=None, exit_code=0):
        """
        check_output provides implementation of SSH plugin's check_output / SSH_CheckOutput method:
                self.targets[name].check_output(output_contains, output_does_not_contain, exit_code)
        """
        result = True
        log.info("Remote Verify Command with output containing: \"{cont}\","
                 " not containing: \"{ncont}\""
                 ", and exit code: {code}"
                 .format(cont=output_contains, ncont=output_does_not_contain, code=exit_code))

        if self.last_result is None:
            log.warning("No output received from remote connection...")
            result = False
        else:
            # Check if stdout contains the nominal output
            if output_contains is not None and output_contains not in self.last_result.stdout.strip():
                log.warning("Output does not contain: {}".format(output_contains))
                result = False

            # Check if stdout doesn't contain offnomial output
            if output_does_not_contain is not None and len(output_does_not_contain) > 0 \
                    and output_does_not_contain in self.last_result.stdout.strip():
                log.warning("Output contains: {}...".format(output_does_not_contain))
                result = False

            # Check if command exit code matches expected exit code
            if exit_code != self.last_result.exited:
                log.warning("Exit code {} does not equal expected exit code {}...".format(
                    self.last_result.exited, exit_code
                ))
                result = False

        if result:
            log.info("RemoteCheckOutput Passed with exit code {}".format(exit_code))
        else:
            log.warning("RemoteCheckOutput Failed")
        return result

    def put_file(self, local_path, remote_path, args=None):
        """
         put_file provides implementation of SSH plugin's put_file / SSH_PutFile method:
                self.targets[name].put_file(local_path, remote_path, args)
         """
        log.info("Remote Put File with local path: {loc} and remote path: {rem}"
                 .format(loc=local_path, rem=remote_path))

        if not self.connection or not self.connection.is_connected:
            log.error("No connection to remote host.")
            return False

        try:
            result = self.rsync(local_path, remote_path, True, args)
        except CtfTestError:
            result = False
        return result

    def get_file(self, remote_path, local_path, args=None):
        """
          get_file provides implementation of SSH plugin's get_file / SSH_GetFile method:
                self.targets[name].get_file(remote_path, local_path, args)
        """
        log.info("Remote Get File with remote path: {rem} and local path: {loc}"
                 .format(rem=remote_path, loc=local_path))

        if not self.connection or not self.connection.is_connected:
            log.error("No connection to remote host.")
            return False

        try:
            result = self.rsync(remote_path, local_path, False, args)
        except CtfTestError:
            result = False
        return result

    def rsync(self, source, dest, push, args=None):
        """
          rsync implements async file transfer
        """
        try:
            exclude = args.get("exclude", ()) if args and "exclude" in args else ()
            delete = bool(args.get("delete", False)) if args else False
            ssh_opts = args.get("ssh_opts", "") if args else ""
            rsync_opts = args.get("rsync_opts", "") if args else ""
            transfers.rsync(self.connection,
                            source,
                            dest,
                            from_local=push,
                            exclude=exclude,
                            delete=delete,
                            ssh_opts=ssh_opts,
                            rsync_opts=rsync_opts)
        except Exception as exception:
            log.warning("Failed to transfer file(s): {}".format(exception))
            raise CtfTestError("Error in rsync") from exception
        else:
            return True

    def upload_ftp(self, host, local_path, remote_path):
        """
          upload_ftp provides implementation of SSH plugin's upload_ftp / SSH_PutFTP method:
                self.targets[name].upload_ftp(host, local_path, remote_path)
        """
        return self.ftp_interface.upload_ftputil(host, local_path, remote_path)

    def download_ftp(self, host, remote_path, local_path):
        """
          download_ftp provides implementation of SSH plugin's download_ftp / SSH_GetFTP method:
                self.targets[name].download_ftp(host, remote_path, local_path)
        """
        return self.ftp_interface.download_ftputil(host, remote_path, local_path)

    def shutdown(self):
        """
           shutdown provides implementation of SSH plugin's shutdown method:
           SSH plugin calls self.targets[name].shutdown()
         """
        if self.connection is not None and self.connection.is_connected:
            self.connection.close()
