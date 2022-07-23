# CFS Plugin

The CFS Plugin provides CFS command/telemetry support for CTF. The following test instructions are available.

### Configuration
The CFS plugin draws many default values from the CTF config file. The section `[cfs]` defines defaults for all CFS targets and is always required.

If multiple CFS targets are to be registered, for each target name, the plugin will load values from a correspondingly named section.

If no targets are explicitly registered by name by the time `StartCfs` is first executed, the plugin will automatically configure targets for each config section beginning with `cfs_`. If no such sections are found, the plugin will configure a single
target using the `[cfs]` config section. Note that if the `cfs_protocol` field is not found in the `cfs` section, a local target will be registered.

The precedence of values is first the named config section, if any, and then the `[cfs]` config section. A target cannot be registered, 
explicitly nor automatically, without a correspondingly named config section.

#### Example
```
#################################
# Base settings for cfs
#################################
[cfs]
...
#################################
# Override settings for cfs_LX1
#################################
[cfs_LX1]
...
#################################
# Override settings for cfs_workstation
#################################
[cfs_workstation]
...
#################################
# Override settings for remote_cfs
#################################
[remote_cfs]
```

In this case, the test script may explicitly register target(s) named any of `cfs`, `cfs_LX1`, `cfs_workstation`, or `remote_cfs`.
If no targets are explicitly registered, the plugin will configure targets `cfs_LX1` and `cfs_workstation` automatically because
they match the naming convention, but not `remote_cfs`: it must be explicitly registered. The following examples assume 
that a target `cfs_workstation` has been registered.

A number of configuration fields relate to the CCDD files and formats, which will likely vary by project:

* `cfs:CCSDS_data_dir` provides the path to the directory containing CCDD JSON files for this target.
* `cfs:CCSDS_target` provides the target name found in the CCDD JSON files to identify MID values for this target.
* `cfs:log_ccsds_imports` will log details of CCDD JSON parsing for this target.
* `cfs:evs_event_mid_name` provides the name of the EVS event MID which must match the name given in CCDD JSON.
* `ccsds:CCSDS_header_path` provides the path to the module implementing CCSDS header definitions for all targets.

### Test Script Considerations

CTF supports resolving macros from the `ccsds_data_dir` and replacing macros in the test script with the actual value.
Macros are defined as constant values in CCDD json files. An example of macro definition is `sample_cfs_workspace/ccdd/json/auto_cfs_grp1_CONSTANTS.json`.
Macros are used in instruction parameters by wrapping the name in `#` like this `#macro_name#`. Ensure a `#` before and after the macro name in the instruction argument.  

Macros can be used in the arguments of `SendCfsCommand`, `CheckTlmValue`, `CheckEvent`, and their related CFS Plugin instructions.
Macros are target (flight software) specific. In other words, for different targets, their evaluated values may be different.

CTF also supports definition and evaluation of user variables. These work similarly to macros, but variables are defined in test scripts, not CCDD files. 
Refer to [Variable Plugin README](../variable_plugin/README.md) for details. 

###### Macro Example 
<pre><code>               
{
        "instruction": "CheckTlmValue",
        "data": {
                "mid": "CFE_EVS_HK_TLM_MID",
                "args": [
                        {
                            "variable": "Payload.AppData[#MY_APPDATA_INDEX#].AppID",
                            "value": 0
                            "compare": "=="
                        }
                        ],
                "target": ""
                },
        "wait": 1
}
</code></pre>

### RegisterCfs
Declares a CFS target to be loaded according to the config file section of the same name. Any fields not provided in the named
section will fall back to the CFS default values. The named section must contain, at minimum, a value for `cfs_protocol`, and may
override any value specified in the `[cfs]` section.
- **target:** (string) A unique name to identify the target in later instructions. The name must match a section name in the config file.

Example:
<pre><code>
{
    "instruction": "RegisterCfs",
    "data": {
        "target": "cfs_workstation"
    },
    "wait": 1,
}
</code></pre>

Config:
<pre><code>
[cfs_workstation]
cfs_protocol="local"
...
</code></pre>

### BuildCfs
Builds a CFS target.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.

Example:
<pre><code>
{
    "instruction": "BuildCfs",
    "data": {
        "target": "cfs_workstation"
    },
    "wait": 1,
}
</code></pre>

### StartCfs
Starts a CFS target.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **run_args:** (Optional) Specify command line arguments to start CFS with. The value is appended to the `cfs_run_args`
                defined in the configuration INI file.
                
Example:
<pre><code>
{
    "instruction": "StartCfs",
    "data": {
        "target": "cfs_workstation",
        "run_args": "-R PO"
    },
    "wait": 1
}
</code></pre>

### EnableCfsOutput
Enables CFS output. No parameters.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered target.

Example:
<pre><code>
{
    "instruction": "EnableCfsOutput",
    "data": {
        "target": "cfs_workstation"
    },
    "wait": 1,
}
</code></pre>

### SendCfsCommand & SendCfsCommandWithPayloadLength
Constructs and sends a command message to CFS with the specified MID, command code, and payload arguments.
**Note:** `SendCfsCommandWithPayloadLength` was named `SendInvalidLengthCfsCommand` prior to CTF v1.4
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **mid:** The message ID of the command (i.e. "BEX_CMD_MID") (string)
- **cc:** The command code for the command (i.e. "BEX_NOOP_CC") (string)
- **payload_length:** (Optional) The size of the payload in bytes for a manually sized command. Do not specify for valid fixed-size commands. The actual length of the message will include the header size.
- **args:** An object where the key is the argument name, and the value is the argument value.
  Because `args` is a dictionary, the order does not matter. (i.e. `{"field_b": 1, "field_a": 0}` is equivalent to `{"field_a": 0, "field_b": 1}`)
- **header:** (Optional) An object where the key is the header field name, and the value is the field value.
  This object is passed into to the `CcsdsCommand` type (as determined by the config field [`ccsds:CCSDS_header_path`](../ccsds_plugin/README.md)) and is not handled by CTF directly. It is made available for custom CCSDS header implementations to allow specification of the packet header.

Example:
<pre><code>
{
    "instruction":"SendCfsCommand",
    "data":{
        "target": "cfs_workstation",
        "mid":"TO_CMD_MID",
        "cc": TO_ENABLE_OUTPUT,
        "args": {
            "cDestIp": "127.0.0.1", 
            "usDestPort": "5011"
            }
        },
    "wait": 1
}
</code></pre>


### SendCfsCommandWithRawPayload
Constructs and sends a command message to CFS with the specified MID, command code, and payload bytes.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **mid:** The message ID of the command (i.e. "BEX_CMD_MID") (string)
- **cc:** The command code for the command (i.e. "BEX_NOOP_CC") (string)
- **hex_buffer:** A hexadecimal string representing the command payload. The string must be an even length (2 characters per byte) and contain only hex numerals 0-F. The payload will be sized to fit the bytes given.
- **header:** (Optional) An object where the key is the header field name, and the value is the field value.
  This object is passed into to the `CcsdsCommand` type (as determined by the config field [`ccsds:CCSDS_header_path`](../ccsds_plugin/README.md)) and is not handled by CTF directly. It is made available for custom CCSDS header implementations to allow specification of the packet header.

Example:
<pre><code>
{
    "instruction": "SendCfsCommandWithRawPayload",
    "data":{
        "target": "cfs_workstation",
        "mid": "DUMMY_IO_CMD_MID",
        "cc": "DUMMY_IO_RAW_BYTE_CC",
        "hex_buffer": "0123456789ABCDEF"
    },
    "wait": 1
}
</code></pre>

### CheckEvent
Checks that an event message matching the given parameters has been received from the CFS target.
**Note:** This instruction's syntax changed in CTF v1.4
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **args**: an array of argument objects that describe the events to be checked. Multiple arguments 
can be listed here to check multiple events at once.
    - **app_name**: The app that sent the event message.
    - **event_id**: The Event ID, taken from an EVS enum, to represent the criticality level of a message.  13 is information, 14 is error, and anything else should be updated into this wiki as you find it.
    - **event_str**: (Optional) The expected message of the event. If blank, the event_str field is not verified.
    - **is_regex**: (Optional) True if `event_str` is to be used for a regex match instead of string comparison
    - **event_str_args**: (optional) arguments that will be inserted into `event_str`, similar to printf() functions

Example:
<pre><code>
{
    "instruction":"CheckEvent",
    "data":{
        "target": "cfs_workstation",
        "args": [
          {
            "app_name":"BEX",
            "event_id":13,
            "event_str":"Processed MODE(%d) Command Successfully Received",
            "is_regex": false,
            "event_str_args":"(1,)"
          },
          {
            "app_name": "TO",
            "event_id": "3",
            "event_str": "TO - ENABLE_OUTPUT cmd succesful for routeMask:0x00000001"
           },
        ]
    },
    "wait": 1
}
</code></pre>

### CheckNoEvent
Checks that an event message matching the given parameters is no longer valid in received messages from the CFS target.
**Note:** This instruction's syntax changed in CTF v1.4
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **args**: an array of argument objects that describe the events to be checked. Multiple arguments 
can be listed here to check multiple events at once.
    - **app_name**: The app that sent the event message.
    - **event_id**: The Event ID, taken from an EVS enum, to represent the criticality level of a message.  13 is information, 14 is error, and anything else should be updated into this wiki as you find it.
    - **event_str**: (Optional) The expected message of the event. If blank, the event_str field is not verified.
    - **is_regex**: (Optional) True if `event_str` is to be used for a regex match instead of string comparison
    - **event_str_args**: (optional) arguments that will be inserted into `event_str`, similar to printf() functions

Example:
<pre><code>
{
  "instruction": "CheckNoEvent",
  "data": {
          "target": "cfs_workstation",
          "args": [
            {
              "app_name": "TO",
              "event_id": "3",
              "event_str": "TO - ENABLE_OUTPUT cmd succesful for routeMask:0x00000001",
              "event_str_args": "",
             }
           ]
   },
  "wait": 4,
  "description": "ENABLE_OUTPUT cmd message is no longer valid in received messages"
}
</code></pre>

### CheckTlmValue
Checks that a telemetry message matching the given parameters has been received from the CFS target.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **mid**: The telemetry message ID to check.
- **args**: an array of argument objects that describe the values to be checked. Multiple arguments
can be listed here to check multiple attributes of a given packet at once.
    - **compare**: How to compare the telemetry value with the test value.
    Must be one of: `==`, `<=`, `<`, `>`, `>=`, `!=`, `streq` (string equal), `strneq` (string not equal), `regex` (any regex match on a string).
    - **variable**: The attribute in the telemetry packet to check against.
    - **expected_mid** (optional): The telemetry message ID where the expected value can be found. Only needed if the check will be performed between two variables.
    This must match a name that was defined for this MID in the CCDD. (string)
    - **value**: The value to compare against. (number, string, bool) Note that the single value must be contained in a list: **"value":[0]**, not **"value":0**. Also if the command is called within a function and the value is a function parameter, put the parameter name as a string: **"value":["myParamName"]**. If **expected_mid** is set, this field should contain the variable path to be checked.
    - **tolerance**: floating point tolerance.
    - **tolerance_plus/tolerance_minus**: non-symmetric floating point tolerance.


Example:
<pre><code>
{
    "instruction": "CheckTlmValue",
    "data": {
        "target": "cfs_workstation",
        "mid": "TO_HK_TLM_MID",
        "args": [
            {
                "compare": "==",
                "variable": "usCmdErrCnt",
                "value": [
                    1
                ]
            },
            {
                "compare": "==",
                "variable": "usCmdCnt",
                "value": [
                    3.05
                ],
                "tolerance_plus": 0.1,
                "tolerance_minus": 0.1
            }
        ]
    },
    "wait": 1
}
</code></pre>

### CheckTlmPacket
Checks that a telemetry message with the given MID has been received from the CFS target. This is equivalent to
`CheckTlmValue` without comparing args.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **mid**: The telemetry message ID to check.

Example:
<pre><code>
{
    "instruction": "CheckTlmPacket",
    "data": {
        "target": "cfs_workstation",
        "mid": "TO_HK_TLM_MID"
    },
    "wait": 1
}
</code></pre>

### CheckNoTlmPacket
Checks that a telemetry message with the given MID is no longer valid in received messages from the CFS target.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **mid**: The telemetry message ID to check.

Example:
<pre><code>
{
    "instruction": "CheckNoTlmPacket",
    "data": {
        "target": "cfs_workstation",
        "mid": "TO_HK_TLM_MID"
    },
    "wait": 1
}
</code></pre>

### CheckTlmContinuous
Similar to `CheckTlmValue` except the check is performed each time telemetry is received, until the test ends or the check is removed by `RemoveCheckTlmContinuous`.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **verification_id**: A unique string to identify this check within the test.
- **mid**: The telemetry message ID to check.
- **args**: an array of argument objects that describe the values to be checked. Multiple arguments
can be listed here to check multiple attributes of a given packet at once.
    - **compare**: How to compare the telemetry value with the test value.
    Must be one of: `==`, `<=`, `<`, `>`, `>=`, `!=`, `streq` (string equal), `strneq` (string not equal), `regex` (any regex match on a string).
    - **variable**: The attribute in the telemetry packet to check against.
    - **expected_mid** (optional): The telemetry message ID where the expected value can be found. Only needed if the check will be performed between two variables.
    This must match a name that was defined for this MID in the CCDD. (string)
    - **value**: The value to compare against. (number, string, bool) Note that the single value must be contained in a list: **"value":[0]**, not **"value":0**. Also if the command is called within a function and the value is a function parameter, put the parameter name as a string: **"value":["myParamName"]**. If **expected_mid** is set, this field should contain the variable path to be checked.
    - **tolerance**: floating point tolerance.
    - **tolerance_plus/tolerance_minus**: non-symmetric floating point tolerance.


Example:
<pre><code>
{
    "instruction": "CheckTlmContinuous",
    "data": {
        "target": "cfs_workstation",
        "verification_id": "TO_no_errors",
        "mid": "TO_HK_TLM_MID",
        "args": [
            {
                "compare": "==",
                "variable": "usCmdErrCnt",
                "value": [
                    0
                ]
            }
        ]
    },
    "wait": 1
}
</code></pre>

### RemoveCheckTlmContinuous
Cancels a continuous telemetry check by ID so that it is no longer performed.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
Note that the target must match with the target specified in `CheckTlmContinuous`, otherwise the instruction will fail
 as it tries to remove the ID on the wrong target. 
- **verification_id:** The ID of a check previously added by `CheckTlmContinuous`

Example:
<pre><code>
{
    "instruction": "RemoveCheckTlmContinuous",
    "data": {
        "target": "cfs_workstation",
        "verification_id": "TO_no_errors"
    },
    "wait": 1,
}
</code></pre>

### ArchiveCfsFiles
Copies files from a directory that have been modified during the current test run into the test run's log directory.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **source_path:** A directory path, absolute or relative to the location of CTF, from which to copy files

Example:
<pre><code>
{
    "instruction": "ArchiveCfsFiles",
    "data":{
        "target": "cfs_workstation",
        "source_path": "../../build/exe/lx1/cf/"
    },
    "wait": 1
}
</code></pre>

### ShutdownCfs
Shuts down a CFS target explicitly within the test script. 
Note, the CFS plugin will automatically shutdown all CFS targets on test completion. 

- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.

Example:
<pre><code>
{
    "instruction": "ShutdownCfs",
    "data": {
        "target": "cfs_workstation"
    },
    "wait": 1,
}
</code></pre>
