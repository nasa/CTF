The `external` sub-directory is not part of the CTF code base and exists only to provide new CTF users with a venue to evaluate/test CTF functionalities.

## Setting up Sample CFS Workspace

Being a cFS test tool, CTF needs to interact with a running cFS system. A project would typically create a repository/workspace to develop, test, build and run its cFS system.  The `Sample CFS Workspace` is a sample of such. For a recommended cFS workspace, see https://github.com/nasa/cfs.

Note - In a git repository for a cFS workspace, CTF repo can be submoduled inside that cFS repository, under the `tools` sub-directory, to track CTF version used by the project.

To setup this workspace for CTF checkout:

First, from a terminal window, navigate to `external` directory and untar the `sample_cfs_workspace` to a directory outside of the CTF home directory, e.g., the user's home

`tar -C ~/ -xvf sample_cfs_workspace.tgz`

Next, navigate to that directory and build cFS to ensure all dependencies are installed

```
cd ~/sample_cfs_workspace
make prep; make; make install
```

Note - On a fresh CentOS 7 installation, the following dependencies are required to build a cFS project

`sudo yum install cmake glibc-devel.i686 libgcc.i686`

Note - Install xterm as follows for CTF to run the cFS instance in a separate terminal window

`sudo yum install xterm`

Ensure that the cFS instance can be started by executing

`cd build/exe/lx1; ./core-lx1`

Let cFS runs for about 1-2 minutes and enter `<Ctrl-C>` to cancel the execution for now.

Now that you have verified cFS can be built and executed, you can now proceed to configure CTF to run test scripts against that cFS system.

## Configuring CTF to work with the Sample CFS Workspace

From the same terminal window, navigate to the CTF home directory and run `source setup_ctf_env.sh` to install the required CTF dependencies into a conda environment. The default location of the conda environment is the user's home directory. However, another directory can be specified when prompted by the setup script.

Note - First time installation may take a while depending on network speed.

The CTF environment is properly installed and activated when a `(pythonEnv3)` prompt appears in your terminal window.

Note - During the sourcing of `setup_ctf_env.sh`, you might see warning statements.  It is okay to ignore them as long as the `(pythonEnv3)` is shown at the end of the sourcing.

Next, navigate to the `sample_cfs_workspace/ctf_tests` directory. This directory contains the project's CTF environment setup script, configuration files, and workspace for the CTF editor.

## Running CTF scripts 

Ensure the CTF environment is activated. (`(pythonEnv3)` should be shown in your terminal).

Sample CFS Workspace does not contain test scripts. To run CTF tests, navigate to `ctf` directory. And run `ctf --config_file configs/default_config.ini scripts/cfe_6_7_tests`. 
This command runs CTF with the default configuration for that cFS project, and executes all test scripts present in the `scripts/cfe_6_7_tests` directory.

After all the CTF tests have been executed, you can examine the test results at `ctf/CTF_Results/Run_<mm_dd_yyyy_hh_mm_ss>` directory.

Note - The `default_config.ini` defines the `sample_cfs_workspace` and `ctf` home directory paths to be at the user's home directory.  If that is not so, either (1) move them to the user's home directory, or (2) create symbolic links for them at the user's home directory, or (3) edit this file for `project_dir` and `CCSDS_header_path` settings to point to the correct directory locations.

## Activating CTF environment after Setup

After running `source setup_ctf_env.sh`, the CTF environment will be automatically active in the current session. This allows users to run `ctf` or `ctf_editor` from the `ctf` directory.

To activate the CTF environment in a new terminal window after installation, run the `activate_ctf_env.sh` either from the CTF repo, or from the `ctf_tests` directory. This will prompt you for the conda environment location to specify (only needed if a different directory was specified in the setup script).


