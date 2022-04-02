# SSH Plugin

The SSH Plugin provides remote and local shell command execution capability for CTF. The following test instructions are available.

### SSH_RegisterTarget
Declares a target host by name. This command must be run before any other commands given the same name will work. Command may be used multiple times to declare any number of targets. If not used, the plugin will assume that all commands are intended for the same target as defined in `SSH_InitSSH`
- **data**: an object where the key is the argument name, and the value is the argument value
   - **name**: An arbitrary, unique name to identify the target in subsequent commands. Does not need be the actual hostname of the target. Name is optional in all other commands, but if not provided all such commands will share a single connection.
  
Example:
<pre><code>
    {
        "instruction": "SSH_RegisterTarget",
        "wait": 1,
        "data": {
            "name": "workstation"
         }
    }
</code></pre>

### SSH_InitSSH
Establishes an SSH connection with a target host. This command must be run before other remote commands will work. Command may be used multiple times with the same name to connect to different remote hosts in succession, or be used with different names to maintain concurrent connections to multiple hosts.
- **data**: an object where the key is the argument name, and the value is the argument value
   - **host**: hostname or IP to connect to, which may include the username and/or port.
   - **name**: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
   - **user**: User name for the connection. Do not use if you specified the user in `host`. (Optional)
   - **port**: Port number for the connection. Do not use if you specified the port in `host`. (Optional)
   - **gateway**: SSH gateway command string to proxy the connection to `host` (Optional)
   - **ssh_config_path**: Path to an ssh config file which may contain host definitions or additional parameters. If not specfied, `~/.ssh/config` will be assumed. (Optional)
   - **args**: Additional SSH connection options, as needed. See [Paramiko API docs](http://docs.paramiko.org/en/latest/api/client.html#paramiko.client.SSHClient.connect) for relevant values. (Optional)

Note - CTF does not currently handle password entry/storage. Follow the tutorial [here](https://www.ssh.com/ssh/copy-id) to set up SSH key authorization  
Example:
<pre><code>
    {
        "instruction": "SSH_InitSSH",
        "wait": 1,
        "data": {
            "name": "workstation",
            "host": "123.123.123.1",
            "user": "lander_demo"
            "port": 22
            "gateway": "ssh -W %h:%p myproxy"
            "ssh_config_path": "./ssh/config"
         }
    }
</code></pre>

### SSH_RunRemoteCommand
Executes a command on the remote host. **ExecutionInitSSH** must be called first to establish an SSH connection.
- **data**: an object where the key is the argument name, and the value is the argument value
   - **name**: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
   - **command**: The shell command to be executed. Can contain multiple commands separated with `;` 

Example:
<pre><code>
    {
        "instruction": "SSH_RunRemoteCommand",
        "wait": 1,
        "data": {
            "name": "workstation",
            "host": "cd lander_fsw_ctf/;rm -rf build; make; make install;"
         }
    }
</code></pre>

### SSH_RunLocalCommand
Executes a command on the local host (the machine running CTF), regardless of the target. This is different from calling
`SSH_RunRemoteCommand` targeting localhost, as it is invoked directly by the current process rather than passed via SSH.
- **data**: an object where the key is the argument name, and the value is the argument value
   - **name**: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
   - **command**: The shell command to be executed. Can contain multiple commands separated with `;` 

Example:
<pre><code>
    {
        "instruction": "SSH_RunLocalCommand",
        "wait": 1,
        "data": {
            "name": "workstation",
            "host": "cd lander_fsw_ctf/;rm -rf build; make; make install;"
         }
    }
</code></pre>

### SSH_CheckOutput
Compares the output of the most recently executed command. **ExecutionRunRemoteCommand** or **ExecutionRunLocalCommand** must be called first.
- **data**: an object where the key is the argument name, and the value is the argument value
   - **name**: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
   - **output_contains** (optional): A substring that must be contained in stdout. (Example: "PASS")
   - **output_does_not_contain** (optional): A substring that should _not_ be contained in stdout. (Example: "FAIL")
   - **exit_code** (optional, default = 0): The expected exit code after the shell command is executed.

Example:
<pre><code>
    {
        "instruction": "SSH_CheckOutput",
        "wait": 0,
        "data": {
            "name": "workstation",
            "output_contains": "Built target mission-install",
            "output_does_not_contain": "Error",
            "exit_code": 0
        }
    }
</code></pre>


### SSH_PutFile
Copies a path (file or directory) from the local filesystem to the remote host via rsync. Relative or absolute paths are allowed, but do not use `~`. Strings are passed directly to rsync, so the same rules apply regarding paths, patterns, etc.
- **data**: an object where the key is the argument name, and the value is the argument value
   - **name**: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
   - **local_path**: The path to the local file or directory to be copied
   - **remote_path**: The path to where the file or directory is to be copied. For remote hosts use the SSH syntax _user@host:path_.
   - **args**: An object that describes optional parameters for the transfer
      - **delete**: A boolean corresponding to `rsync`’s `--delete` option. If true, `rsync` will remove remote files that no longer exist locally. Defaults to false.
      - **exclude**: A string or array of strings corresponding to `rsync`'s `--exclude` option. Defaults to None.

Example:
<pre><code>
    {
        "instruction": "SSH_PutFile",
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
</code></pre>


### SSH_GetFile
Copies a path (file or directory) from the remote host to the local filesystem via rsync. Relative or absolute paths are allowed, but do not use `~`. Strings are passed directly to rsync, so the same rules apply regarding paths, patterns, etc.
- **data**: an object where the key is the argument name, and the value is the argument value
   - **name**: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
   - **remote_path**: The path to the source file or directory to be copied. For remote hosts use the SSH syntax _user@host:path_.
   - **local_path**: The local path to where the file or directory is to be copied
   - **args**: An object that describes optional parameters for the transfer
      - **delete**: A boolean corresponding to `rsync`’s `--delete` option. If true, `rsync` will remove remote files that no longer exist locally. Defaults to false.
      - **exclude**: A string or array of strings corresponding to `rsync`'s `--exclude` option. Defaults to None.

Example:
<pre><code>
    {
        "instruction": "SSH_GetFile",
        "wait": 0,
        "data": {
            "name": "workstation",
            "remote_path": "./data/output.dat",
            "local_path": "./results.txt"
        }
    }
</code></pre>

### SSH_GetFTP
Downloads a path (file or directory) from the FTP server to the local filesystem.
- **data**: an object where the key is the argument name, and the value is the argument value
   - **name**: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
   - **host**: The hostname or address of the FTP server
   - **remote_path**: The path to the source file or directory on the FTP server
   - **local_path**: The local path to where the file or directory is to be downloaded

Example:
<pre><code>
    {
        "instruction": "SSH_GetFTP",
        "wait": 0,
        "data": {
            "name": "workstation",
            "host": "ftphost",
            "remote_path": "./data/output.dat",
            "local_path": "./results.txt"
        }
    }
</code></pre>

### SSH_PutFTP
Uploads a path (file or directory) from the local filesystem to the FTP server.
- **data**: an object where the key is the argument name, and the value is the argument value
   - **name**: A name already registered with `SSH_RegisterTarget` to identify the connection. (Optional)
   - **host**: The hostname or address of the FTP server
   - **remote_path**: The path on the FTP server to where the file or directory is to be uploaded
   - **local_path**: The local path to the source file or directory

Example:
<pre><code>
    {
        "instruction": "SSH_PutFTP",
        "wait": 0,
        "data": {
            "name": "workstation",
            "host": "ftphost",
            "remote_path": "./data/output.dat",
            "local_path": "./results.txt"
        }
    }
</code></pre>
