# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2020 United States Government as represented by the
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

from lib.patchwork.patchwork import transfers
from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log
from lib.Global import Config, expand_path
from lib.ftp_interface import ftp_interface


class SshConfig(object):
    def __init__(self):
        # Retrieve all required data from the configuration file
        self.command_timeout = Config.getfloat("ssh", "command_timeout")
        self.print_stdout = Config.getboolean("ssh", "print_stdout")
        self.log_stdout = Config.getboolean("ssh", "log_stdout")


class SshPlugin(Plugin):
    def __init__(self):
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
        self.register_target("default")
        return True

    def register_target(self, name=""):
        if name in self.targets:
            if name != "default":
                log.warn("SSH target {} is already registered".format(name))
                log.warn("Overriding Target {} SSH Configuration".format(name))

        self.targets[name] = SshController(SshConfig())
        return True

    def init_connection(self, host, user=None, port=None, gateway=None,
                        ssh_config_path=None, args=None, name="default"):
        log.debug("SshPlugin.init_connection")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].init_connection(host, user, port, gateway, ssh_config_path, args)

    def run_command(self, command, cwd="", prefix=":", name="default"):
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
        log.debug("SshPlugin.run_command_local")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].run_command_local(command)

    def check_output(self, output_contains=None, output_does_not_contain=None, exit_code=0, name="default"):
        log.debug("SshPlugin.check_output")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].check_output(output_contains, output_does_not_contain, exit_code)

    def put_file(self, local_path, remote_path, args=None, name="default"):
        log.debug("SshPlugin.put_file")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].put_file(local_path, remote_path, args)

    def get_file(self, remote_path, local_path, args=None, name="default"):
        log.debug("SshPlugin.get_file")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].get_file(remote_path, local_path, args)

    def upload_ftp(self, host, local_path, remote_path, name="default"):
        log.debug("SshPlugin.upload_ftp")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].upload_ftp(host, local_path, remote_path)

    def download_ftp(self, host, remote_path, local_path, name="default"):
        log.debug("SshPlugin.download_ftp")
        if name not in self.targets:
            log.error("No Execution target named {}".format(name))
            return False

        return self.targets[name].download_ftp(host, remote_path, local_path)

    def shutdown(self):
        log.debug("SshPlugin.shutdown")
        for name in self.targets:
            log.debug("Shutting down Execution target {}".format(name))
            self.targets[name].shutdown()

        self.targets.clear()


class SshController(object):
    def __init__(self, config):
        self.config = config
        self.connection = None
        self.last_result = None
        self.last_pid = None
        self.ftp_interface = ftp_interface()

    def init_connection(self, host, user=None, port=None, gateway=None, ssh_config_path=None, args=None):
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
        except Exception as e:
            log.error("Remote connection failed: {}".format(e))
            return False

    def run_command(self, command, cwd="", prefix=":"):
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
                except (invoke.exceptions.UnexpectedExit, invoke.exceptions.CommandTimedOut) as e:
                    result = invoke.Result(exited=e.result.exited)
        if self.config.log_stdout:
            log.info("Remote {cmd} complete with result:\n {res}\n Exit Code = {code}"
                     .format(cmd=command, res=result.stdout.strip(), code=result.exited))
        else:
            log.info("Remote {cmd} complete. Exit Code = {code}".format(cmd=command, code=result.exited))

        self.last_result = result
        return result.exited == 0

    def run_command_persistent(self, command, cwd="", prefix=":"):
        log.info("Remote persistent command: {}".format(command))

        if not self.connection or not self.connection.is_connected:
            log.error("No connection to remote host.")
            return False

        # TODO Investigate ways to pipe the output back and capture it live instead of directing to /dev/null.
        #  The interaction of fabric and nohup etc. limit our options
        pid_file = "/tmp/pid"
        cmd_str = "nohup sh -c '{command} & echo $! > {pid_file}' & 2>&1".format(command=command, pid_file=pid_file)
        with self.connection.cd(cwd):
            with self.connection.prefix(prefix):
                try:
                    result = self.connection.run(cmd_str,
                                                 hide=(not self.config.print_stdout),
                                                 timeout=self.config.command_timeout)
                except (invoke.exceptions.UnexpectedExit, invoke.exceptions.CommandTimedOut) as e:
                    result = invoke.Result(exited=e.result.exited)

        # TODO Investigate ways this could go wrong in various error conditions. There may be a more
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
        return self.last_pid

    def run_command_local(self, command):
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

        except (invoke.exceptions.UnexpectedExit, invoke.exceptions.CommandTimedOut) as e:
            self.last_result = e.result
            log.error(e.result)
            return e.result.exited == 0

    def check_output(self, output_contains=None, output_does_not_contain=None, exit_code=0):
        result = True
        log.info("Remote Verify Command with output containing: \"{cont}\","
                 " not containing: \"{ncont}\""
                 ", and exit code: {code}"
                 .format(cont=output_contains, ncont=output_does_not_contain, code=exit_code))

        if self.last_result is None:
            log.warn("No output received from remote connection...")
            result = False
        else:
            # Check if stdout contains the nominal output
            if output_contains is not None and output_contains not in self.last_result.stdout.strip():
                log.warn("Output does not contain: {}".format(output_contains))
                result = False

            # Check if stdout doesn't contain offnomial output
            if output_does_not_contain is not None and len(output_does_not_contain) > 0 \
                    and output_does_not_contain in self.last_result.stdout.strip():
                log.warn("Output contains: {}...".format(output_does_not_contain))
                result = False

            # Check if command exit code matches expected exit code
            if exit_code != self.last_result.exited:
                log.warn("Exit code {} does not equal expected exit code {}...".format(
                    self.last_result.exited, exit_code
                ))
                result = False

        if result:
            log.info("RemoteCheckOutput Passed with exit code {}".format(exit_code))
        else:
            log.warn("RemoteCheckOutput Failed")
        return result

    def put_file(self, local_path, remote_path, args=None):
        log.info("Remote Put File with local path: {loc} and remote path: {rem}"
                 .format(loc=local_path, rem=remote_path))

        if not self.connection or not self.connection.is_connected:
            log.error("No connection to remote host.")
            return False
        return self.rsync(local_path, remote_path, True, args)

    def get_file(self, remote_path, local_path, args=None):
        log.info("Remote Get File with remote path: {rem} and local path: {loc}"
                 .format(rem=remote_path, loc=local_path))

        if not self.connection or not self.connection.is_connected:
            log.error("No connection to remote host.")
            return False
        return self.rsync(remote_path, local_path, False, args)

    def rsync(self, source, dest, push, args=None):
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
        except Exception as e:
            log.warn("Failed to transfer file(s): {}".format(e))
            return False
        else:
            return True

    def upload_ftp(self, host, local_path, remote_path):

        return self.ftp_interface.upload_ftputil(host, local_path, remote_path)

    def download_ftp(self, host, remote_path, local_path):

        return self.ftp_interface.download_ftputil(host, remote_path, local_path)

    def shutdown(self):
        if self.connection is not None and self.connection.is_connected:
            self.connection.close()
