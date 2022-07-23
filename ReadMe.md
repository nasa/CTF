# Table of Contents
   * [cFS Test Framework](#cfs-test-framework)
      * [Getting Started](#getting-started)
      * [Release Notes](#release-notes)
      * [License](#license)

# cFS Test Framework

The cFS Test Framework (CTF) provides cFS projects with the capability to develop and run automated test and verification scripts. The CTF tool parses and executes JSON-based test scripts containing test instructions, while logging and reporting the results. CTF utilizes a plugin-based architecture to allow developers to extend CTF with new test instructions, external interfaces, and custom functionality.

CTF is currently in active development, and is available under the NASA Open Source Agreement license (NOSA). See the [license](#license) section for more information.

## Getting Started

To get started, clone the CTF repository using the following:

`git clone https://github.com/nasa/CTF`

For more detailed information on CTF usage, see the CTF Software User's Guide (CTF_SUG.pdf) 
in the `CTF Documentation` directory of the CTF releases' Assets (https://github.com/nasa/CTF/releases).
 
## Release Notes

### v1.6 
07/20/2022

* CTF Core Changes
    * Update test script naming conventions and log formatting to be consistent.  
    
    * Various logging improvements. 
    
    * Update source code for the new sample cFS workspace.

    * Minor improvements and bug fixes.

* CTF Plugins Changes
    * Updates to Validation Plugin 
        * Add a new instruction InsertUserComment to allow testers to insert comments into test logs for post-test analysis.

        * Modify SearchStr and SearchNoStr instructions to support regex search.

    * Updates to Variable Plugin
        * Add target as an argument to SetUserVariableFromTlm and SetUserVariableFromTlmHeader instructions. 

        * Add an optional argument variable_type to SetUserVariable instruction for explicit type conversion. 
        
        * Minor improvements and bug fixes: convert bytes array to string in SetUserVariableFromTlm; allow variable to be array index in instruction arguments. 
    
    * Updates to CFS Plugin
        * Allow SendCfsCommandWithRawPayload to work with any MID and command code.

        * Minor improvements and bug fixes. 
    
 * CTF Tool and Scripts Changes
    * Update setup_ctf_env.sh to fix the issue of incompatible packages for Anaconda3 installation.

    * Update CTF Editor (GUI) to highlight invalid json scripts.
    
    * Improve documents and test scripts to certify CTF.

    * Modify the upgrade script in ctf/tools to automatically update CTF config files and test scripts for v1.6 compatibility.
   

### v1.5 
03/31/2022

* CTF Core Changes
    * Consolidate `CheckEvent` verification timeout configuration using the name `verify_timeout` in test scripts.  

    * Minor improvements and bug fixes.
    
* CTF Plugins Changes
    * Add a new plugin: Validation Plugin. 
        * Provide instructions to allow CTF users to copy / delete files / folders, search a string in a text file, 
        and save CFS evs binary file to a text file. See plugin docs for more information.
    
    * Updates to CFS Plugin
        * Fix a bug that caused missing logs and telemetry after the first test cases of a run. 

        * Support hex value arguments (of the form `"0x1F"`) in `SendCfsCommand`, `CheckTlmValue`, `CheckEvent` instructions. 
    
        * Change `SendCfsCommand` to use the configured target's endianness for bitfield values.

    * Add new instruction `SetUserVariableFromTlmHeader` to Variable Plugin.

    * Add support in CCSDS Plugin for data structures defined in their own files independently of MIDs.

    * Remove the outdated instruction `SetLabel`. 
  
    * Minor improvements and bug fixes.
 
 * CTF Tool and Scripts Changes
    * Integrate jsonlint tool to scan json test scripts before executing tests.
    
    * Modify the upgrade script in `ctf/tools` to automatically update CTF config files and test scripts for v1.4 / v1.5 compatibility.

    * Update CTF documents and FAQ.
    
    * Update CTF unit tests.
      
    
### v1.4
02/28/2022
* CTF Core Changes
    * Support local variable evaluation in test instruction arguments with the format `$variable$`.

    * Update additional_plugins_path attribute in INI file to accept a list of (multiple) plugin paths.  

    * Remove instruction's default 1 second wait time. 

    * Minor improvements and bug fixes.
    
* CTF Plugins Changes
     * Update CFS plugin.
        * Add new instruction `SendCfsCommandWithRawPayload`, which specifies a variable length payload in the form of a hex string.
        * Rename `SendInvalidLengthCfsCommand` to `SendCfsCommandWithPayloadLength`.
        * `SendCfsCommandWithPayloadLength` now includes any serialized `args` in the payload, up to the length specified.
        * Change the syntax of `CheckEvent` and `CheckNoEvent` to allow a list of events to be checked simultaneously.
        * Add support for bitfield values in `SendCfsCommand` instruction.
        * CFS Plugin instructions handle MID and CC values as names, decimal or hexadecimal integers, stringified integers, or macros. 
       
    * Add conditional branching if and else instructions in Control-Flow Plugin. See plugin README for more information.  
       
    * Clear ram drive on Linux target if cFS instance is starting without `-RPR` argument.
    
    * Minor improvements and bug fixes.

 * CTF Editor Changes
    * Fix bug of SetUserVariableFromTlm instruction for child element. 
    
    * Fix bug of saving instruction argument 0 as string type instead of int type.  
    
    * Remove backward-compatibility fields such as `telemetry_watch_list`, `command_watch_list`. 
        
    * Fix bug of editor failing to save the modified script in some corner cases.  
     
    * Support multiple plugin infor folders for editor.
    
    * Support new CheckEvent syntax. 
 
 * CTF Tool and Scripts Changes
    * Add new test scripts for CTF certification test cases.
        
    * Minor improvements to unit test coverage, logging, and example scripts. 

    * Add an upgrade script in `ctf/tools` to automatically update CTF config files and test scripts for v1.4 compatibility.

    * Update CTF documents and FAQ.


### v1.3.1
10/19/2021

* CTF Plugins Changes

    * CFS shutdown on Linux logs an error, but does not fail, if no such process is found.
     
    * CFS Plugin macros now require the format `#MACRO#` instead of `#MACRO`.
       
    * Fix the 'disable' attribute in function definition.

* CTF Documentation Changes
    * Updated JSON Test Script Guide
    
    * Add Troubleshooting & FAQ Guide section.


### v1.3 
08/26/2021

* CTF Core Changes
    * Logging improvements
        * No longer create temporary logging directory during test execution
        * Use the same log format with colors if `colorlog` is installed. Use `pip install colorlog` to enable.

    * Allow test scripts' import paths to include environment variables, including the configured `workspace_dir`

    * Allow FTP upload to a directory that already exists.

    * Minor improvements and bug fixes.
    
* CTF Plugins Changes
    * Add two new plugins: Variable Plugin and Control-Flow Plugin. 
        * These provide new instructions to allow CTF users to do looping and conditional statements. See plugin docs for more information.

    * Sort CCDD files before parsing so the files are always processed in alphabetical order.

    * Allow CCDD macros for non-numeric string literals.

    * Support custom field arguments for CCSDS headers in `SendCfsCommand`.
    
    * Support the default fill value of arrays in `SendCfsCommand` args, if the array name is given instead of an index.

    * Add two new instructions `CheckTlmPacket` and `CheckNoTlmPacket` in cFS plugin.

    * Allow `CheckTlmValue` to check elements in arrays.

    * Remove `start_cfs_on_init` and `auto_run` configuration options for cFS targets.

    * Improve the mechanism to shut down cFS.
        * Note - on some distros you may need to install the `sysvinit-tools` package to enable the `pidof` command.

    * Minor improvements and bug fixes.

 * CTF Editor Changes
    * Add Editor support for new Control Flow instructions.
    
    * Improve Editor response while running 2 cFS instances. 
    
    * Improve handling of large arrays such as in `MM_LOAD_MEM_WID_CC` by truncating inputs.
      
    * Minor improvements and bug fixes.   
 
 * CTF Tool and Scripts Changes
    * Expand unit test coverage.
    
    * Purge test scripts from `sample_cfs_workspace`. 
    
    * Purge `start_cfs_on_init` and `auto_run` from INI files.
    
    * Purge command & telemetry watch lists from CTF test scripts.
    
    
### v1.2.1
05/20/2021

* Fixed the type conversion of args for object arrays in `SendCfsCommand`.

### v1.2
05/06/2021

* CTF Core Changes
    * Minor improvements and bug fixes.

* CFS Plugin Changes
    
    * Fix the use of CCDD macros in test scripts.
    
    * Improve argument type checking in `SendCfsCommand` instruction.
    
    * Improve validation of Remote CFS configs. `RegisterCfs` will fail if any errors are found.
    
    * Change `ValidateCcsdsData` parameter from `name` to `target` to match CFS instructions. 
   
    * Minor improvements and bug fixes.
    
* CTF Editor Changes
    * Fix the bug of deleting arguments for `CheckTlmValue` and `CheckTlmContinuous` instructions. 
      
    * Minor improvements and bug fixes.
    
* CTF Documentation and Tool Changes
    * Add document generation by doxygen tool.
    
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
        * Note: Currently, this feature is supported for Linux cFS targets only. SSH support for archiving FSW artifacts is planned for a later version.
    * Redesign multi-cfs architecture to be purely configuration based (remove script-specific overrides to allow scripts to be platform independent.) 
        * Each cFS Target should have its own configuration section in the config INI file.
        * RegisterCfs receives a name, and attempts to load target configuration (including protocol) from the loaded configuration.
        * A PASS/FAIL for that instruction will be set after validating the necessary config fields for cFS and the specific protocol (Linux, SSH)
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
        * Remote Targets Support: SSH, Local (linux). More targets can be added as needed.
    * Change command argument structure in test script JSON. Arguments are now encoded in the test script as a JSON dictionary.   

* Initial Plugin Implementations For
    * SSH Plugin
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

Copyright (c) 2019-2022 United States Government as represented by the
Administrator of the National Aeronautics and Space Administration. All Rights Reserved.

This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
distributed and modified only pursuant to the terms of that agreement.
See the License for the specific language governing permissions and limitations under the
License at https://software.nasa.gov/.

Unless required by applicable law or agreed to in writing, software distributed under the
License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either expressed or implied.


