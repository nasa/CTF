# CFS Plugin

The CFS Plugin provides CFS command/telemetry support for CTF. The following test instructions are available.

### Configuration
The CFS plugin draws many default values from the CTF config file. The section `[cfs]` defines defaults for all CFS targets and is always required.

If multiple CFS targets are to be registered, for each target name, the plugin will load values from a correspondingly named section.

If no targets are explicitly registered by name by the time `StartCfs` is first executed, the plugin will automatically configure targets for each config section beginning with `cfs_`. If no such sections are found, the plugin will configure a single *local*
target using the `[cfs]` config section.

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

CTF supports resolving macros from the ccsds_data_dir and replacing macros in the test script with the actual "c_value". Ensure a `#` precedes the macro in the test script in order for CTF to do macro replacement.

###### Example 
```                
{
                    "command": "CheckTlmValue",
                    "data": {
                        "mid": "CFE_EVS_HK_TLM_MID",
                        "args": [
                            {
                                "variable": "Payload.AppData[#MY_APPDATA_INDEX].AppID",
                                "value": [
                                    "0"
                                ],
                                "compare": "=="
                            }
                        ],
                        "target": ""
                    },
                    "wait": 1
                }
```

### RegisterCfs
Declares a CFS target to be loaded according to the config file section of the same name. Any fields not provided in the named
section will fall back to the CFS default values. The named section must contain, at minimum, a value for `cfs_protocol`, and may
override any value specified in the `[cfs]` section.
- **target:** (string) A unique name to identify the target in later instructions. The name must match a section name in the config file.

Example:
```javascript
{
    "command": "RegisterCfs",
    "data": {
        "target": "cfs_workstation"
    }
    "wait": 1,
},
```
Config:
```
[cfs_workstation]
cfs_protocol="local"
...
```

### BuildCfs
Builds a CFS target.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.

Example:
```javascript
{
    "command": "BuildCfs",
    "data": {
        "target": "cfs_workstation"
    }
    "wait": 1,
},
```

### StartCfs
Starts a CFS target.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **run_args:** (Optional) Specify command line arguments to start CFS with. The value is appended to the `cfs_run_args`
                defined in the configuration INI file.
                
Example:
```javascript
{
    "command": "StartCfs",
    "data": {
        "target": "cfs_workstation",
        "run_args": "-R PO"
    }
    "wait": 1
},
```

### EnableCfsOutput
Enables CFS output. No parameters.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered target.

Example:
```javascript
{
    "command": "EnableCfsOutput",
    "data": {
        "target": "cfs_workstation"
    }
    "wait": 1,
},
```

### SendCfsCommand & SendInvalidLengthCfsCommand

- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **mid:** The message ID of the command (i.e. "BEX_CMD_MID") (string)
- **cc:** The command code for the command (i.e. "BEX_NOOP_CC") (string)
- **payload_length:** (Optional) The size of the payload in bytes for an invalid length command. Do not specify for valid commands. The actual length of the sent message will be plus the header size.
- **args:** An object where the key is the argument name,
  and the value is the argument value.
  Because args is a dictionary, the order does not matter. (i.e. {, "field_b": 1, "field_a": 0})

Example:
```javascript
{
    "command":"SendCfsCommand",
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
```

### CheckEvent
Checks that an event message matching the given parameters has been received from the CFS target.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **app**: The app that sent the event message.
- **id**: The Event ID, taken from an EVS enum, to represent the criticality level of a message.  13 is information, 14 is error, and anything else should be updated into this wiki as you find it.
- **msg**: (Optional) The expected message of the event. If blank, the msg field is not verified.
- **is_regex**: (Optional) True if `msg` is to be used for a regex match instead of string comparison
- **msg_args**: (optional) arguments that will be inserted into `msg`, similar to printf() functions

Example:
```javascript
{
    "command":"CheckEvent",
    "data":{
        "target": "cfs_workstation",
        "app":"BEX",
        "id":13,
        "msg":"Processed MODE(%d) Command Successfully Received",
        "is_regex": false,
        "msg_args":"(1,)"
    },
    "wait": 1
}
```

### CheckTlmValue
Checks that a telemetry message matching the given parameters has been received from the CFS target.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **mid**: The telemetry message ID to check. **NOTE**: this message ID MUST be listed in the
 `telemetry_watch_list` attribute of the **Test Script** object.
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
```javascript
{
    "command": "CheckTlmValue",
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
```

### CheckTlmContinuous
Similar to `CheckTlmValue` except the check is performed each time telemetry is received, until the test ends or the check is removed by `RemoveCheckTlmContinuous`.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **verification_id**: A unique string to identify this check within the test.
- **mid**: The telemetry message ID to check. **NOTE**: this message ID MUST be listed in the
 `telemetry_watch_list` attribute of the **Test Script** object.
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
```javascript
{
    "command": "CheckTlmContinuous",
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
```

### RemoveCheckTlmContinuous
Cancels a continuous telemetry check by ID so that it is no longer performed.
- **verification_id:** The ID of a check previously added by `CheckTlmContinuous`

Example:
```javascript
{
    "command": "RemoveCheckTlmContinuous",
    "data": {
        "verification_id": "TO_no_errors"
    }
    "wait": 1,
},
```

### ArchiveCfsFiles
Copies files from a directory that have been modified during the current test run into the test run's log directory.
- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.
- **source_path:** A directory path, absolute or relative to the location of CTF, from which to copy files

Example:
```javascript
{
    "command": "ArchiveCfsFiles",
    "data":{
        "target": "cfs_workstation",
        "source_path": "../../build/exe/lx1/cf/"
    },
    "wait": 1
}
```

### ShutdownCfs
Shuts down a CFS target explicitly within the test script. 
Note, the CFS plugin will automatically shutdown all CFS targets on test completion. 

- **target:** (Optional) A previously registered target name. If no name is given, applies to all registered targets.

Example:
```javascript
{
    "command": "ShutdownCfs",
    "data": {
        "target": "cfs_workstation"
    }
    "wait": 1,
},
```
