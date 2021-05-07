# Table of Contents
   * [cFS Test Framework](#cfs-test-framework)
      * [Getting Started](#getting-started)
         * [CTF Prerequisites](#ctf-prerequisites)
         * [CTF Directory Structure](#ctf-directory-structure)
         * [Configuration](#configuration)
         * [Sample cFS Workspace](#sample-cfs-workspace)
            * [Running the Sample cFS Workspace Scripts](#running-the-sample-cfs-workspace-scripts)
      * [Using CTF on a New cFS Project](#using-ctf-on-a-new-cfs-project)
         * [CCSDS Message Definitions](#ccsds-message-definitions)
            * [CCDD Auto Export](#ccdd-auto-export)
            * [Other](#other)
         * [New cFS Project Configuration](#new-cfs-project-configuration)
         * [Developing New Test Scripts](#developing-new-test-scripts)
      * [Developing or Extending CTF Plugins](#developing-or-extending-ctf-plugins)
      * [Updating CTF](#updating-ctf)
      * [CTF Validation Tools](#ctf-validation-tools)
      * [Release Notes](#release-notes)
      * [License](#license)

# cFS Test Framework

The cFS Test Framework (CTF) provides cFS projects with the capability to develop and run automated test and verification scripts. The CTF tool parses and executes JSON-based test scripts containing test instructions, while logging and reporting the results. CTF utilizes a plugin-based architecture to allow developers to extend CTF with new test instructions, external interfaces, and custom functionality.

CTF is currently in active development, and is available under the NASA Open Source Agreement license (NOSA). See the [license](#license) section for more information.

## Getting Started

To get started, clone the CTF repository using the following:

`git clone https://github.com/nasa/CTF`

### CTF Prerequisites

CTF has been developed and tested on Linux (CentOS 7) and requires Python 3.x. The CTF Editor requires an installation of NodeJS/NPM.

There are two methods to install dependencies. 

1. An Anaconda environment setup script is provided to install all OS/Python dependencies into a self contained Anaconda environment. This method does not require sudo privileges. However, the CTF Python 3 environment must be activated prior to running CTF.

2. a PIP `requirements.txt` file is provided to install all Python 3 CTF dependencies. OS dependencies need to be installed manually and may require sudo privileges. This method provides the most light-weight dependency installation, but is more involved than the Anaconda setup.

#### CTF Prerequisites: Satisfied with Anaconda Environment 

The `setup_ctf_env.sh` script will setup an Anaconda 3 environment, which contains Python3, along with the python components identified in `requirements.txt` along with NodeJS/NPM.

To set up the CTF environment execute `source setup_ctf_env.sh`. Note: this may take several minutes depending on your network connection, and will consume about 5Gb of disk space for Anaconda 3 and NPM dependencies.

After the initial setup to activate the ctf environment execute `source activate_ctf_env.sh`.

If the Anaconda environment is corrupted, the environment can be reinstalled by executing `source setup_ctf_env.sh -u`.

#### CTF Prerequisites: Satisfied Without Anaconda Environment

Install Python3 (on CentOS run `sudo yum install python3-devel python3 python3-pip`)

Install NodeJS/NPM, visit https://nodejs.org/en/ and install Node version >= 10.12.0 (tested with v12.5.0). NPM will be included in the installation.

With NPM installed, the editor and its dependencies can be installed with `cd tools/ctf_ui && npm install`. Note: this may take several minutes depending on your network connection, and will consume about 0.5Gb of disk space.

With Python 3 installed, PIP dependencies can be installed using `pip install -r requirements.txt`. Note: ensure that dependencies are installed to a PIP venv in order to easily update/reinstall packages, or install using  `--user` in the above pip command.


#### CTF Prerequisites: Other applications needed

`xterm` is required in order to run cFS in a separate terminal. Install `xterm` by using `sudo yum install xterm` or `sudo apt install xterm` if on Debian.

`cmake3` is required in order to build cFS projects. Install cmake3 using `sudo yum install cmake3` if needed.

A working cFS project is also needed. Note that CTF provides the [sample_cfs_workspace](#sample-cfs-workspace) if no existing cFS project is available.

### CTF Directory Structure
```
├── activate_ctf_env.sh
├── ctf (executable)
├── README.md
├── requirements.txt
├── run_editor.sh
├── setup_ctf_env.sh
├── configs/
├── external/
├── lib/
├── plugins/
├── schemas/
└── tools/
    └── ctf_ui/
    └── schema_validator/
```

### Configuration

The configuration file contains configuration options for each CTF plugin. To run CTF with a selected configuration, add the `--config_file <path_to_config_file>` command line argument when running CTF. Each plugin can define one (or more) sections with specific configuration values as follows

```
[some_plugin_config]
some_field = true
some_other_field = xyz
```

Please refer to each plugin's `README` document for information on the required configuration fields for each plugin. In addition, example configuration files are provided under `configs/examples`.

###### Note: More variants of the config can be created, and loaded via the ctf command-line argument (`--config_file`). It is recommended to create different configurations for different testing use-cases such as a CI config, a Test Authoring/Debugging config, etc..

###### Note: Environment variables can be used as a value using similar syntax as follows `${env_variable}`

###### Note: Other INI field values can be referenced using the following syntax `field2 = ${section:field1}`. 

### Sample cFS Workspace

By default, The CTF tool contains a minimal cFS workspace (`external/sample_cfs_workspace.tgz`) for CTF testing and evaluation purposes. It also provides a reference cFS/CTF workspace layout that is applicable to other cFS projects. 

The `sample_cfs_workspace` contains a set of cFS apps that receive CCSDS commands and output CCSDS telemetry messages through the CI/TO apps. It also contains a set of sample CTF test scripts that can be executed against the compiled cFS system from `sample_cfs_workspace`.

To get started using the `sample_cfs_workspace`, follow the documentation under [external/README.md](external/README.md). After completing the instructions, CTF will be set up as a cFS tool *within* the `sample_cfs_workspace` and can be used to execute test scripts against that cFS workspace. A similar approach can be followed to add CTF to an existing cFS project.

###### Note: If cFS does not build, you may have missing dependencies. Install of `gcc-multilib` in order to build cFS projects successfully. On CentOS 7, run the following command `sudo yum install libgcc.i686 glibc-devel.i686`

#### Running the Sample cFS Workspace Scripts
First, review the contents of `configs/default_config.ini`. Update any fields as needed. Specifically, the `[cfs]: workspace_dir` may need to be update with the appropriate path according to where `sample_cfs_workspace` is extracted.

To run the provided example scripts, simply run the `ctf` executable (ensure the CTF environment is activated) with the configuration file and the script to run as follows.

```
cd ~/sample_cfs_workspace/ctf_tests
source activate_ctf_env.sh
ctf --config_file configs/default_config.ini --script_dir test_scripts/sample_test_suite
```

###### Note: Ensure `build_cfs` is set to `true` in the `configs/default_config.ini` file, if the cFS executable has not been built manually.

CTF will proceed to build and start the cFS project and execute the test script. An `xterm` window showing the output of the cFS instance will launch, after which the test script begins execution.

###### Note: run `sudo sysctl -w fs.mqueue.msg_max=1024` if you see an error from cFS regarding the msg_max queue size.

Sample CTF output is shown below.

```
[13:00:47.209] ctf                             (42 ) *** INFO: Status_Manager created
[13:00:47.209] ctf                             (48 ) *** INFO: Loading Plugins - Start
[13:00:47.209] plugin_manager                  (202) *** INFO: Looking for plugins under package: plugins
[13:00:47.214] plugin_manager                  (235) *** INFO:     Found plugin class: plugins.ccsds_plugin.ccsds_plugin.CCSDSPlugin
[13:00:47.214] ccsds_plugin                    (35 ) *** WARNING: CFS Plugin not yet loaded... 
[13:00:47.345] plugin_manager                  (235) *** INFO:     Found plugin class: plugins.cfs.cfs_plugin.CfsPlugin
[13:00:47.346] plugin_manager                  (235) *** INFO:     Found plugin class: plugins.example_plugin.example_plugin.ExamplePlugin
[13:00:47.348] plugin_manager                  (235) *** INFO:     Found plugin class: plugins.sp0_plugin.sp0_plugin.sp0Plugin
[13:00:47.348] plugin_manager                  (235) *** INFO:     Found plugin class: plugins.ssh.ssh_plugin.SshPlugin
[13:00:47.349] plugin_manager                  (211) *** INFO: From package: plugins  - Loaded the following plugins: ['CCSDS Plugin', 'CFS Plugin', 'ExamplePlugin', 'sp0_plugin', 'SshPlugin']
[13:00:47.349] ctf                             (50 ) *** INFO: Loading Plugins - End
[13:00:47.349] ctf                             (58 ) *** INFO: Status_Manager created
[13:00:47.349] ctf                             (62 ) *** INFO: Script_Manager created
[13:00:47.349] ctf                             (64 ) *** INFO: Reading Test Scripts
[13:00:47.350] ctf                             (95 ) *** INFO: Loaded Script: <lib.test_script.TestScript object at 0x7f9d731e7bb0>
[13:00:47.350] ctf                             (108) *** INFO: Completed reading in the json script file/files passed in the arguments
[13:00:47.350] ctf                             (111) *** INFO: Script Manager - Start
[13:00:47.350] ccsds_plugin                    (38 ) *** INFO: Initialized CCSDS Plugin
[13:00:47.350] cfs_time_manager                (45 ) *** INFO: CfsTimeManager Initialized. Verification Poll Period = 0.05.
[13:00:47.350] cfs_plugin                      (152) *** INFO: Initialized CfsPlugin
[13:00:47.350] sp0_plugin                      (64 ) *** INFO: Initialized SP0 plugin
[13:00:47.351] test_script                     (92 ) *** INFO: Verification Test Name: CFS CI Functions Test
[13:00:47.351] test_script                     (93 ) *** INFO: Verification Test Number: CFS-CI-Functions-Test
[13:00:47.351] test_script                     (94 ) *** INFO: Test Conductor: ashehata
[13:00:47.351] test_script                     (95 ) *** INFO: Run Date/Time: 10/08/2020 / 13:00:47
[13:00:47.351] test_script                     (96 ) *** INFO: Platform: #1 SMP Tue Mar 31 23:36:51 UTC 2020
[13:00:47.351] test_script                     (97 ) *** INFO: Requirement Verification Targets: MyRequirement
[13:00:47.351] test_script                     (98 ) *** INFO: Test Description : Testing CI Functions
[13:00:47.351] test_script                     (99 ) *** INFO: Input file utilized : CiFunctionTests.json
[13:00:47.352] test                            (199) *** INFO: Test CI-Function-Test-001: Starting
[13:00:47.352] test                            (200) *** INFO: Test CI Enable TO command
[13:00:47.352] test                            (157) *** INFO: Waiting 1 time-units before executing RegisterCfs
[13:00:48.374] cfs_plugin                      (161) *** INFO: RegisterCfs: Name cfs_LX1
[13:00:48.379] cfs_config                      (93 ) *** WARNING: Config Value cfs_LX1:evs_messages_clear_after_time does not exist or is not the right type. Attempting to load from base section [cfs].
[13:00:48.379] cfs_controllers                 (56 ) *** INFO: Creating MID Map from CCDD Data at /home/ashehata/sample_cfs_workspace/ccdd/json
[13:00:48.396] ccsds_packet_interface          (69 ) *** INFO: Importing CCSDS header definitions from /home/ashehata/sample_cfs_workspace/tools/ctf/plugins/ccsds_plugin/cfe/ccsds_v2/ccsds_v2.py
[13:00:48.397] cfs_controllers                 (71 ) *** INFO: Starting Local CFS Interface
[13:00:48.397] cfs_controllers                 (85 ) *** WARNING: Not starting CFS executable... Expecting "StartCfs" in test script...
[13:00:48.397] cfs_controllers                 (88 ) *** INFO: CfsController Initialized
[13:00:48.397] cfs_plugin                      (197) *** INFO: Register for cfs_LX1 finished.
[13:00:48.397] test                            (74 ) *** TEST_PASS: Instruction RegisterCfs: {'name': 'cfs_LX1'}
[13:00:48.397] test                            (157) *** INFO: Waiting 1 time-units before executing StartCfs
[13:00:49.412] cfs_plugin                      (254) *** INFO: StartCfs: Name cfs_LX1
[13:00:49.412] cfs_controllers                 (96 ) *** INFO: Starting CFS on cfs_LX1
[13:00:49.413] local_cfs_interface             (100) *** INFO: Starting CFS Executable
xterm: cannot load font '-misc-fixed-medium-r-semicondensed--13-120-75-75-c-60-iso10646-1'
[13:00:52.518] cfs_controllers                 (105) *** INFO: Skipping enable output...
[13:00:52.519] test                            (74 ) *** TEST_PASS: Instruction StartCfs: {'name': 'cfs_LX1'}
[13:00:52.519] test                            (157) *** INFO: Waiting 1 time-units before executing SendCfsCommand
[13:00:53.584] cfs_controllers                 (123) *** INFO: Sending CFS Command to target: cfs_LX1, CI_CMD_MID:CI_ENABLE_TO_CC with Args: {"cDestIp": "127.0.0.1", "usDestPort": 5011, "usRouteMask": 0, "iFileDesc": 0}
[13:00:53.585] test                            (74 ) *** TEST_PASS: Instruction SendCfsCommand: {'name': '', 'mid': 'CI_CMD_MID', 'cc': 'CI_ENABLE_TO_CC', 'args': {'cDestIp': '127.0.0.1', 'usDestPort': 5011, 'usRouteMask': 0, 'iFileDesc': 0}}
[13:00:53.585] test                            (157) *** INFO: Waiting 0 time-units before executing CheckTlmValue
[13:00:53.585] test                            (96 ) *** INFO: Waiting up to 2.0 time-units for verification of CheckTlmValue: {'name': '', 'mid': 'CI_HK_TLM_MID', 'args': [{'variable': 'usCmdCnt', 'value': [1], 'compare': '=='}, {'variable': 'usCmdErrCnt', 'value': [0], 'compare': '=='}]}
[13:00:53.585] cfs_plugin                      (289) *** INFO: CheckTlmValue: CFS Target: , MID CI_HK_TLM_MID, Args [{"variable": "usCmdCnt", "value": [1], "compare": "=="}, {"variable": "usCmdErrCnt", "value": [0], "compare": "=="}]
[13:00:53.636] cfs_interface                   (225) *** INFO: Receiving Telemetry Packets for Data Type: CFE_SB_HousekeepingTlm_t with MID: 0x2008
[13:00:53.636] cfs_interface                   (225) *** INFO: Receiving Telemetry Packets for Data Type: CFE_EVS_LongEventTlm_t with MID: 0x2006
[13:00:53.842] cfs_interface                   (225) *** INFO: Receiving Telemetry Packets for Data Type: CFE_TIME_HousekeepingTlm_t with MID: 0x200e
[13:00:54.047] cfs_interface                   (225) *** INFO: Receiving Telemetry Packets for Data Type: CFE_TBL_HousekeepingTlm_t with MID: 0x200c
[13:00:54.047] cfs_interface                   (225) *** INFO: Receiving Telemetry Packets for Data Type: CFE_ES_HousekeepingTlm_t with MID: 0x2001
[13:00:54.253] cfs_interface                   (225) *** INFO: Receiving Telemetry Packets for Data Type: SCH_HkPacket_t with MID: 0x240b
[13:00:54.357] cfs_interface                   (225) *** INFO: Receiving Telemetry Packets for Data Type: CI_HkTlm_t with MID: 0x2404
[13:00:54.408] cfs_interface                   (503) *** INFO: PASSED Intermediate Check - usCmdCnt: Actual: 1, Expected: 1, Comparison: ==, Tol: +0, -0
[13:00:54.408] cfs_interface                   (503) *** INFO: PASSED Intermediate Check - usCmdErrCnt: Actual: 0, Expected: 0, Comparison: ==, Tol: +0, -0
[13:00:54.408] cfs_controllers                 (319) *** INFO: PASSED Final Check for MID:{'MID': 9220, 'name': 'CI_HkTlm_t', 'PARAM_CLASS': <class 'plugins.cfs.ccsds.ccdd_export_reader.CI_HkTlm_t'>}, Args:[{'variable': 'usCmdCnt', 'value': [1], 'compare': '=='}, {'variable': 'usCmdErrCnt', 'value': [0], 'compare': '=='}]
[13:00:54.408] test                            (134) *** TEST_PASS: Verification Passed CheckTlmValue: {'name': '', 'mid': 'CI_HK_TLM_MID', 'args': [{'variable': 'usCmdCnt', 'value': [1], 'compare': '=='}, {'variable': 'usCmdErrCnt', 'value': [0], 'compare': '=='}]}
```

## Using CTF on a New cFS Project

### CCSDS Message Definitions

To use CTF for a new cFS project, message definition files must first be generated. The message information files allow CTF to create the command/telemetry C structures in python in order to build CCSDS commands and process CCSDS telemetry.

#### CCDD Auto Export

Currently, CTF obtains the CCSDS message definitions by parsing a set of files that adhere to a CTF-supported JSON schema to define command/telemetry message structures. These files can be created manually for testing, or created automatically using a tool such as CCDD.

For the `sample_cfs_workspace` project, the CCSDS message definition JSONs are automatically generated by the [CCDD](https://github.com/nasa/CCDD) tool.

CTF utilizes a CCDD export reader that parses and stores the message definitions JSON into a format usable by CTF.

###### Note: Ensure that the CCSDS JSON files directory is correctly set in the INI configuration file under `[cfs]: CCSDS_data_dir` in order for CTF to correctly process these files.

#### Other

Projects that do not use CCDD to maintain their command and telemetry dictionary can utilize the same current JSON schema to define message information. This can be done automatically (generated from some external tool), or manually. In addition, more complex projects may implement their own `Custom CCSDS Reader` using the provided CCSDS Interface calls to set up the message information in CTF. An example of that is shown under `plugins/cfs/ccsds/ccdd_export_reader.py`.

Essentially, each reader will need to read the message information files from some source, and relay that information to CTF using the following functions

```python
add_telem_msg(self, mid_name, mid, name, parameters, parameter_enums = None)

add_cmd_msg(self, mid_name, mid, command_code_map, command_enums = None)

add_enumeration(self, key, value)
```

Example usage can be found in the `plugins/cfs/ccsds/ccsds_export_reader.py`

### New cFS Project Configuration

To configure CTF for a new project, simply create a configuration INI file that is specific to the project's testing needs. `config_template.ini` is provided under the `configs/` directory as a template for new projects to use.

It is recommended to start with simple tests that start/stop cFS to verify that the build and run capability is working. Once that is achieved, more complicated test scripts can be created.

### Developing New Test Scripts

The CTF tool provides a [CTF Editor](tools/ctf_ui/README.md) to assist in the creation, modification, and running of scripts. Currently, the editor can be obtained from the repository above. Please refer to the [CTF Editor User's Guide](docs/ctf_editor/usage_guide.md) for information on how to run and use the editor.


Refer to the following [guide](docs/ctf/ctf_json_test_script_guide.md) for information on the JSON input script file description. This is useful when scripts are to be written manually without the aid of the editor.

Plugin READMEs include documentation of their own instructions and configuration fields:

* [CCSDS Plugin](plugins/ccsds_plugin/README.md)
* [CFS Plugin](plugins/cfs/README.md)
* [Example Plugin](plugins/example_plugin/README.md)
* [SSH Plugin](plugins/ssh/README.md)
* [UserIO Plugin](plugins/userio_plugin/README.md)

## Developing or Extending CTF Plugins

Refer to the [plugin guide](docs/ctf/ctf_plugin_guide.md) for information on creating custom CTF plugins.

## Updating CTF

CTF versions can be checked out by running `git checkout <version_tag>`. This updates the CTF submodule/repository to the selected version.

In addition, the configuration (and test script) files may need to be updated with new configuration fields, or test script additions/changes.

It is also recommended to [rerun setup](#ctf-prerequisites) after updating CTF to ensure that you have all of the latest dependencies.

The sections below describe the changes needed to quickly update to a specific version. Note that the release notes contain a more complete set of changes.

### Updating to v1.X

CTF v1.0 introduces major additions to the configuration file, as well as changes to the test script schema and instructions.

* Existing CTF Test Scripts
    * Using a find & replace tool, update all references within a test script as follows
        * All Instances
            * `"commands"` -> `"instructions"`
            * `"command`   -> `"instruction"`
        * CFS Plugin Instructions
            * `"name"`     -> `"target"` 
            * `"set_length"` to `"payload_length"`
            
* Config changes (reference `configs/default_config.ini` for descriptions and examples)
    * Add fields
        * core:additional_plugin_path
        * core:ignored_instructions
        * core:delay_between_scripts
        * cfs:CCSDS_target
        * cfs:evs_event_mid_name
    * Delete fields
        * cfs:evs_event_msg_mid

* CCSDS Message Definitions
    * **Update to CCSDS Definition Schema (JSON) to support multiple MID values for the same message definitions**
        * For command structure definitions
            * Rename `command_id_name` to `cmd_mid_name`
            * Remove `command_message_id`. Now maintained in a separate MID map file
            * Add `cmd_description`
            * Rename `command_codes` to `cmd_codes`
                * Rename `name` to `cc_name`
                * Rename `code` to `cc_value`
                * Rename `description` to `cc_description`
                * Add `cc_data_type`
                * Rename `args` to `cc_parameters`
                    * No changes needed within `cc_parameters` (previously `args`)
        
        * For telemetry structure definitions
            * Rename `name` to `tlm_mid_name`
            * Remove `mid`. Now maintained in a separate MID map file
            * Rename `mid_name` to `tlm_data_type`
            * Add `tlm_description`
            * Rename `parameters` to `tlm_parameters`
                * No changes to `name`, `array_size`, `description`, `bit_length`, `parameters`

        * For alias and constant definitions
            * Rename `cfs_type_name` to `alias_name`
            * Rename `c_type` to `actual_name`
            * Rename `cfs_macro_name` to `constant_name`
            * Rename `c_macro` to `constant_value`

        * MID Map JSON
            * Move the "mid" field from each message definition to a separate MIDs map file, mapping between MID names and raw MID values per cFS target.
            
            * An array of objects mapping target to MID value as follows
                ```
                [
                    {
                        "target": "my_target",
                        "mids": [ 
                                    {"mid_name": "CFS_MID_NAME", "mid_value": "0x1234"}
                                    ...
                                ]
                    }
                ]
                ```
    * Refer to the `sample_cfs_workspace/ccdd/json` for reference (after extracting the workspace from `external/`)

## CTF Validation Tools

#### Pylint Static Code Analysis.
"Pylint is a tool that checks for errors in Python code, tries to enforce a coding standard and looks for code smells.
 It can also look for certain type errors, it can recommend suggestions about how particular blocks can be refactored
 and can offer you details about the code's complexity." - From Pylint User Manual

To run CTF static code analysis, enter the following commands (ensure the CTF environment is activated).

```
cd ~/sample_cfs_workspace/tools/ctf/
source activate_ctf_env.sh
cd ../
pylint --rcfile=./ctf/.pylintrc ./ctf
```

#### CTF Unit Test.
Pytest is one of the widely used open-source python testing frameworks. It supports unit testing, functional testing 
and API testing as well. The CTF unit test files are organized under the `tests` folder. Each plugin has its own unit tests, 
which are symbolically linked under the `tests/plugins` folder.
 
To run CTF unit tests, enter the following commands (ensure the CTF environment is activated).

```
cd ~/sample_cfs_workspace/tools/ctf/
source activate_ctf_env.sh
pytest -v ./tests/ --cov-config=.ctf_coveragerc --cov=plugins --cov=lib --cov-report=html
```
Upon completion, a summary will be printed to the console and the CTF unit test coverage report can be found in `UnitTests_Coverage/index.html`.

## Release Notes
### v1.2
05/06/2021

* CTF Core Changes
    * Minor improvements and bug fixes.

* CFS Plugin Changes
    * Update SP0 Protocol and FTP Interface with changes from GSFC functional testing.
    
    * Fix the use of CCDD macros in test scripts.
    
    * Improve argument type checking in `SendCfsCommand` instruction.
    
    * Improve validation of the SP0 and Remote CFS configs. `RegisterCfs` will fail if any errors are found.
    
    * Change `ValidateCcsdsData` parameter from `name` to `target` to match CFS instructions. 
   
    * Minor improvements and bug fixes.
    
* CTF Editor Changes
    * Fix the bug of deleting arguments for `CheckTlmValue` and `CheckTlmContinuous` instructions. 
      
    * Minor improvements and bug fixes.
    
* CTF Documentation and Tool Changes
    * Add pylint static code analysis.
    
    * Add pytest unit tests for plugins and library source files.
    
    * Update open source file header.
    
    * Split CI pipeline into two stages.
             
        
### v1.1
12/18/2020

* CTF Core Changes
    * Add support for a `disable` field to CTF instructions within a test script to temporarily disable that instruction.
    
    * Add support for a `description` field to CTF instructions within a test script to capture comments.
    
    * Add `end_test_on_fail_commands` attribute to the `Plugin` class, allowing plugins to define a list of critical commands that end the current test script on failure.
    
    * Minor improvements and bug fixes.

* CFS Plugin Changes
    * Add the `RegisterCfs` and `StartCfs` instructions to the `end_test_on_fail_commands` such that test execution is halted if registering or starting cFS fails.
    
    * Add support for Short Event Messages by setting the `cfs:evs_short_event_mid_name` field in the config to match the MID name of the `CFE_EVS_ShortEventTlm_t` within the CCSDS JSON definitions.
    
    * Add the CheckNoEvent instruction to check that an event message was *not* sent during the verification timeout.
    
    * Ensure args do not get malformed while sending a command to multiple cFS targets
    
    * Resolve CheckTlmValue passing if one or more variables fails to be evaluated from the telemetry packet.
    
    * Resolve connection and deployment issues with cFS targets running with the SP0 protocol (WIP)
    
    * Minor improvements and bug fixes.

    
* CTF Editor Changes
    * Add support for disabling/enabling test instructions or test cases
    
    * Add support for viewing/editing descriptions (comments) within the test script
    
    * Add the ability to rename folders or test scripts within the editor
    
    * Minor improvements and bug fixes.
     
### v1.0
10/30/2020

Major Release

This is the first open source release for CTF. Note that CTF remains in active development.

Existing users should review the change logs below and ensure current configurations and scripts are updated.

* Release Additions
    * Add `external/` directory with a self contained example CFS project. This project can be configured to utilize CTF out of the box. Refer to `external/README.md` for more information.

* CTF Core Changes
    
    * **Update test script JSON schema with more accurate field names**
        * Update `commands` array to `instructions`
        * Update `command` object to `instruction`
        * Refer to [Updating to v1.0](updating-to-v10) 
        
    * Add an option to provide an additional plugin path within the configuration file. Custom plugins are loaded from that directory, in addition to CTF default plugins.
        * Add the `additional_plugin_path = <path_to_custom_plugins_dir>` field to the config ini.
        * Note - Give the custom plugin directory a unique name (do not use `plugins`, `lib`, etc...), so as to not shadow any modules within the CTF repo.
    
    * Add an option to ignore specific CTF instructions within the configuration file. This is useful for CI or specific-configurations that may not have the ability to run certain instructions.
        * Add the `ignored_instructions = <instruction_1>, <instruction_2>, ...` field to the config ini. Specify the instructions to ignore (comma-seperated).
    
    * Minor improvements and bug-fixes.
        
* CCSDS Plugin Changes
    * **Update to CCSDS Definition Schema (JSON) to support multiple MID values for the same message definitions**
        * Refer to [Updating to v1.0](updating-to-v10) 
        
    * **Change config field `evs_event_msg_mid` to `evs_event_mid_name` which should now be set to the MID name for the Event Messages (for example `CFE_EVS_LONG_EVENT_MSG_MID`).** 
        * The actual MID value will be retrieved from the CCSDS message definitions.

* CFS Plugin Changes
    * **Update `name` field to `target`**
        * The `name` field is used for *all* cFS Plugin Instructions. This field is now renamed to `target` for clarity, and specifies the cFS target to apply the instruction to.
            * **Please change all instances of `"name":` to `"target"` within existing test scripts. Example scripts have been updated as part of the release.**
    
    * No longer validate `cfs_run_dir` on registration. Previously, if the cFS instance was not built (i.e the run directory does not exist), validation would fail.
    * Rename `set_length` to `payload_length` for the `SendInvalidLengthCfsCommand` test instruction.
    
* User IO Plugin (New)
    * Add support for `WaitForUserInput` test instruction (with a prompt message shown to the user). This is useful when testing safety-critical functionality, or need to pause the test until the user confirms to proceed.

* Example Plugin Changes
    * Add an example of loading and utilizing a C shared library within a CTF plugin.

* CTF Editor Changes
    * Improvements to the Run Status View
        * Instructions can now be expanded while/after a test run to inspect instruction arguments and data.
    
    * Updates to support CTF and CCSDS definition changes.

### v0.6
2020-09-14

* CCSDS Plugin Changes
    * Configurable CCSDS Headers
        * Allows users to define CCSDS header structures for Command and Telemetry packets
            * Reference CCSDS Plugin README for documentation on creating custom headers and their associated implementations
        * Migrate CCSDS V1 and V2 definitions to utilize new configurable header functionality
        * Added a new config field `CCSDS_header_path` to set the appropriate python header module for CTF to use

* cFS Plugin Changes
    * Allow "RegisterCfs" instruction to be used without specifying a name. This uses the default `[cfs]` configuration section. 
    * Add new field to "StartCfs" test instruction to support additional command-line arguments when starting the cFS instance.
        * Example
            ```json
                {
                    "command": "StartCfs",
                    "data": {
                        "name": "",
                        "run_args": "-R PO"
                    },
                    "wait": 1
                }
            ```
        * Note: The StartCfs run_args value will append arguments to the `cfs_run_args` field defined in the config
    * Fix "SendInvalidLengthCfsCommand" instruction to send the actual length specified in the instruction as the payload length
        * Note: Total length received by FSW will be equal to the specified `payload_length` + length of the CCSDS header(s)

    * Fix command/telemetry sockets not sending/receiving packets when cFS restarts within a single script
        * CTF to re-initialize command/telemetry sockets after restart
        
    * Write cFS output log files in append mode such that logs are not overwritten when cFS restarts
    
* CTF Editor Changes

    * Fix rendering bug causing last script to be hidden in the file-pane behind sidebar collapse button

### v0.5.1

Disable implicit padding of telemetry and command payload structures (assumes explicit padding in the C data structures, or disabled C compiler implicit padding).

Minor improvements and bug-fixes.

### v0.5
2020-08-06

Major backend updates to improve reliability/maintainability of CTF.

* cFS Plugin Changes
    * Major architecture rework to support multiple and remote cfs instances
    * cFS Plugin
        * Telemetry Reader
            * Add time-tags to telemetry packets for more accurate telemetry verifications.
            * Log begin time of a verification, and clear all packets received for the selected MID prior to verification time.
            * For event messages, the config field `evs_message_clear_after_time` is added to keep events available in CTF telemetry
          up to a specific time. This is needed since EVS messages are only output once.
        * CheckEvent 
            * Now support regular expressions via the `is_regex` parameter.
            * `msg` parameter is now optional. Leaving it blank will only verify the APP and ID fields of EVS messages. 
            * Note: Ensure that the TO subscription table for the FSW project is configured to output a large number of EVS messages in order to
            avoid dropped packets.
    
* Logging
    * Substantially clean up logging when running in INFO or ERROR log level
        * Polling instruction logs should be reduced to only show actual vs. expected and if no packets are received in that poll...
    * cFS plugin will directly write the following to the script log folder
        * cFS Build/Output Logs
        * cFS EVS Logs
        * cFS Telemetry Logs (Experimental, does not output array elements)

* Config INI Changes
    * Reference configs/default_config.ini or config_template.ini for descriptions of fields
    * Core
        * Rename `telem_verify_timeout` to `ctf_verification_timeout`
        * Rename `telem_verify_poll_period` to `ctf_verification_poll_period`
    * CCSDS
        * Remove `CCSDS_reader_script_path`, `CCSDS_reader_class`, `CCSDS_module`
    * cFS
        * Remove `evs_tlm_list_depth`
        * Rename `ip` to `cfs_target_ip`
        * Add `cfs_output_file`, `log_ccsds_imports`, `evs_messages_clear_after_time`

* CTF Editor
    * Update to allow saving commands or function instructions with empty arguments.
        * Empty arguments will be saved to the test script with an empty string value.
        * CTF Backend will zero-out any command argument set to an empty string.
    * Add `is_regex` field to CheckEvent instruction. 
        * Refer to `scripts/example/test_advanced_example.json` for reference.
        
### v0.3.2
2020-08-05

* Log MID values of unknown packets
* Resolve cfs_output file not being written to results when no event messages are received over telemetry
* Add initial support for command array arguments
    
### v0.3.1
2020-07-08

* cFS Plugin Changes
    * Add new instruction "ArchiveCfsFiles", which accepts a FSW artifacts and moves any files created during the test run to the test results directory.
        * Note: Currently, this feature is supported for Linux cFS targets only. SSH and SP0 support for archiving FSW artifacts is planned for a later version.
    * Redesign multi-cfs architecture to be purely configuration based (remove script-specific overrides to allow scripts to be platform independent.) 
        * Each cFS Target should have its own configuration section in the config INI file.
        * RegisterCfs receives a name, and attempts to load target configuration (including protocol) from the loaded configuration.
        * A PASS/FAIL for that instruction will be set after validating the necessary config fields for cFS and the specific protocol (Linux, SSH, SP0)
    * Rework macro replacement logic such that 
        * Macro replacement occurs for command argument values, telemetry field values, and array indices.
        * All macros in a test script should start with the # prefix (example: "#SOME_MACRO_IN_MACRO_MAP").
    * Resolve CheckEvent is a polling instruction, to allow for a timeout/polling (similar to typical CheckTlmValue).
    * Resolve missing "build cfs" implementation for local cfs targets.
    
* General
    * Rework setup_ctf_env.sh and activate_ctf_env.sh such that 
        * Setup only needs to be run once (within the CTF install directory) and will install the anaconda environment to the user's home directory, or a custom path.
        * Activate *can* be placed at the project-specific CTF test directory
        * Multiple projects using CTF on the same platform can share the user-specific anaconda environment.

* CTF Editor
    * Resolve rendering bug when attempting to select an array element within a telemetry field.
    * Ensure arrays are left with "index-placeholders" `[]` where the test author can insert either a hard-coded index, or a macro from the macro map.
        * Note: macros should be preceded with the # token to identify that a replacement needs to take place before evaluating.

* CTF Core
    * Update Test Pass/Fail log message with string-based payload to mirror the data within the test script during test run.
    
### v0.3
2020-05-21

* cFS Plugin Changes
    * Serialize Telemetry Receiving Logic (and accompanying lessons learned about the cFS SCH configuration, and how it should be set up…) -> This resolves the timing issues and dropped packets we were experiencing
    * Continuous Telemetry Verification Capability -> CTF now has the ability to “continually” verify a piece of telemetry against a condition defined in the test script. If the verification fails at any point during the test run, the failure is logged and the test will fail

* CTF Core
    * Configuration/Path improvements to resolve the relative/absolute path issues we were seeing when CTF is configured outside of its repository

* CTF Editor
    * Update editor to support new instruction (continuous verifications)
    * Fixe bug in editor launching backend in pre-defined working directory (as opposed to dynamically).
    
* Other minor bug fixes and improvements

### v0.2
2020-04-24

* cFS Plugin Changes
    * More Generic CCSDS/CCDD Interfaces
        * Add CCSDS Reader Interface (CFE 6.6/CFE 6.7, CCSDS V1/V2)
        * Add CCDD JSON Export Reader
    * Multi/Remote cFS Support
        * Allow the cFS Plugin to execute/manage multiple instances of cFS running on local or remote targets
        * Remote Targets Support: SSH, SP0, Local (linux). More targets can be added as needed.
    * Change command argument structure in test script JSON. Arguments are now encoded in the test script as a JSON dictionary.   

* Initial Plugin Implementations For
    * SSH Plugin
    * SP0 Plugin
    * CCSDS Plugin
           
* Re-haul CTF Editor to support generic CCSDS JSON Exports, and multi/remote cFS.

* Other bug-fixes and improvements
    
### v0.1
2019-11-22

* Initial CTF Release

* Initial Plugin Implementations For
    * cFS Plugin
    * Example Plugin
    * PLATO Plugin (Deprecated)
    * Remote Execution Plugin (Deprecated)
    * Trick cFS (Removed for later release)

* Initial CTF Editor Release

## License

MSC-26646-1, "Core Flight System Test Framework (CTF)"

Copyright (c) 2019-2021 United States Government as represented by the
Administrator of the National Aeronautics and Space Administration. All Rights Reserved.

This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
distributed and modified only pursuant to the terms of that agreement.
See the License for the specific language governing permissions and limitations under the
License at https://software.nasa.gov/.

Unless required by applicable law or agreed to in writing, software distributed under the
License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either expressed or implied.


