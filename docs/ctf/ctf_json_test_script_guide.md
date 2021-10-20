Table of Contents
=================

   * [cFS Test Framework JSON Input File Format and Description](#cfs-test-framework-json-input-file-format-and-description)
   * [Test Scripts](#test-scripts)
   * [Functions](#functions)
   * [Tests](#tests)
   * [CTF Instructions](#ctf-instructions)
   * [Complete Example](#complete-example)


## cFS Test Framework JSON Input File Format and Description
Integrated tests are described using JSON input files. If you are unfamiliar with JSON,
you can find a great introduction here: https://www.w3schools.com/js/js_json_syntax.asp.

## Test Scripts
The JSON CTF input file, or **Test Script**, is comprised of a number of properties that describe the tests that will be executed. Each **Test Script** can have multiple tests, with each each testing multiple requirements.
Example test scripts can be found at `scripts` folder in the repo.

 The **Test Script** has the following properties:
- **test_number**: Unique identifier for the test script. Format Should be a descriptive test ID that would allow the review to understand what is being tested.
- **test_name**: A short descriptive name for the tests in the file.
- **requirements**: A dictionary where the _key_ is the SRS and the _value_ is a string that states if the test script fully or partially verifies the SRS.
- **description**: Detailed description of the script.  Start with the RTM test for the requirements you are testing.  Then  include the information that would capture what environments the tests can execute within.  The procedures for executing the script, if special steps are needed.  The init point to be used for the tests.  
- **import**: Specify _functions_ (described below) that can be imported from other JSON files.
- **functions**: User-defined functions that can be used by the test script, described below.
- **tests**: an array of objects, where each object describes a single **Test.** The **Test** objects are described below.

Example:
```javascript
{
    "test_number": "Basic-Aspect-Cfs-Plugin-Test",
    "test_name": "Basic Aspect CFS Plugin Test",
    "requirements": {
        "MyRequirement": "N/A"
    },
    "description": "Basic CTF Example Script Showing Simple Commands/Telemetry Verification",
    "owner": "CTF",
    "test_setup": "Script will start ASPECT, execute a verification instruction test and close ASPECT",
    "ctf_options": {
        "verify_timeout": 4
    },
    "import": {},
    "tests": [
        {
            "case_number": "ASPECT-Plugin-Test-001",
            "description": "Start CFS, Send TO NOOP instruction",
            "instructions": [
                {
                    "instruction": "StartCfs",
                    "wait": 1,
                    "data": {}
                },
                {
                    "instruction": "CheckTlmValue",
                    "data": {
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
                },
                {
                    "instruction": "SendCfsCommand",
                    "data": {
                        "mid": "TO_CMD_MID",
                        "cc": "TO_NOOP_CC",
                        "subsysId": 7,
                        "endian": 0,
                        "systemId": 0,
                        "args": []
                    },
                    "wait": 1
                },
                {
                    "instruction": "CheckTlmValue",
                    "data": {
                        "mid": "TO_HK_TLM_MID",
                        "args": [
                            {
                                "compare": "==",
                                "variable": "usCmdCnt",
                                "value": [
                                    2.0
                                ]
                            }
                        ]
                    },
                    "wait": 1
                },
                {
                    "instruction": "ShutdownCfs",
                    "data": {},
                    "wait": 1
                }
            ]
        }
    ]
}
```

## Functions
The **Function** objects are collections of **CTF Instructions** that can be executed by each test case.  These functions can be defined within the same **Test Script** or in a separate file and be imported (see `scripts/cfe_6_7_tests/libs/`).  The object has the following properties:
- **description**: Describe purpose of the function including the steps the function with take and the results the function will provide.  Intended use details should also be included.
- **varlist**: List of arguments required by the function

Example:
```javascript
"functions":{
    "UserDefinedFunction":{
        "description":"<Explain purpose, results, steps of this user-defined functions>",
        "varlist":["_arg1", "_arg2"],
        "instructions":[
        //CTF Instruction objects go here
        ]
    }
}
```

## Tests
The **Test** objects each describe a single test, which can verify any number of requirements. 
Each **Test** contains the requirements verified by the test, a description of the test, and a number of **Instructions** 
objects that define the actions to take during the test.
The object has the following properties:
- **case_number**: Unique identifier of test case in the script.  Use Test name with a unique number.
- **description**: Describes what actions this test is performing.  Include Preconditions, the expected actions/instructions, and the expected results that are going to be observed.
- **instructions**: An array of **Instruction** objects that define the actions taken by the test (described below)

Example:
```javascript
{
    "case_number":"ExampleTest-1",
    "description":"<Explain preconditions, actions, results, steps of test case>",
    "instructions":[
    	//Instruction Objects go here
    ]
}
```

## CTF Instructions
The **CTF Instructions** object defines what action CTF is supposed to take. Each instruction object has the following base structure:
- **instruction:**: The **CTF instruction** to execute. Must be one of the values listed above (string)
- **data:** The arguments for the **CTF Instruction**. Each **Instruction** is going to have a different data object, described below.
- **wait:** The amount of time to wait from the completion of the last instruction before executing the current instruction.
- **timeout:** (Optional) The amount of time for verification instructions to wait for verification to succeed before timing out.

Instructions are implemented in their respective CTF plugin. Refer to the specific plugin's README document for more 
information on instructions supported by each plugin.

## Complete Example
The following example shows the basic CTF test script found in the repo.

```javascript
{
    "test_number": "Basic-CFE-6-7-Cfs-Plugin-Test",
    "test_name": "Basic CFE-6-7 CFS Plugin Test",
    "requirements": {
        "MyRequirement": "N/A"
    },
    "description": "Basic CTF Example Script Showing Simple Commands/Telemetry Verification",
    "owner": "CTF",
    "test_setup": "Script will start CFE-6-7, execute a verification instruction test and close CFE-6-7",
    "ctf_options": {
        "verify_timeout": 4
    },
    "import": {},
    "tests": [
        {
            "case_number": "CFE-6-7-Plugin-Test-001",
            "description": "Start CFS, Send TO NOOP instruction",
            "instructions": [
                {
                    "instruction": "StartCfs",
                    "data": {
                        "name": ""
                    },
                    "wait": 1
                },
                {
                    "instruction": "EnableCfsOutput",
                    "data": {
                        "name": ""
                    },

                    "wait": 1,
                    "comment": "Need this to enable the telemetry thread. Enable Output counts as 1 TO cmd"
                },
                {
                    "instruction": "CheckEvent",
                    "data": {
                        "app": "TO",
                        "id": "3",
                        "msg": "TO - ENABLE_OUTPUT cmd succesful for  routeMask:0x00000001",
                        "msg_args": "",
                        "name": ""
                    },

                    "wait": 1,
                    "comment": "Need this to enable the telemetry thread. Enable Output counts as 1 TO cmd"
                },
                {
                    "instruction": "SendCfsCommand",
                    "data": {
                        "name": "",
                        "mid": "TO_CMD_MID",
                        "cc": "TO_NOOP_CC",
                        "args": {}
                    },
                    "wait": 1
                },
                {
                    "instruction": "CheckTlmContinuous",
                    "comment": "Change 'name' to 'cfs_name' for all instructions",
                    "data": {
                        "name": "",
                        "verification_id": "no_error",
                        "mid": "TO_HK_TLM_MID",
                        "args": [
                            {
                                "compare": "==",
                                "variable": "usCmdErrCnt",
                                "value": [
                                    0.0
                                ]
                            }
                        ]
                    },
                    "wait": 1
                },
                {
                    "instruction": "CheckTlmValue",
                    "data": {
                        "name": "",
                        "mid": "TO_HK_TLM_MID",
                        "args": [
                            {
                                "compare": "==",
                                "variable": "usCmdCnt",
                                "value": [
                                    2.0
                                ]
                            }
                        ]
                    },
                    "wait": 1
                },
                {
                    "instruction": "SendCfsCommand",
                    "data": {
                        "name": "",
                        "mid": "TO_CMD_MID",
                        "cc": "TO_RESET_CC",
                        "args": {}
                    },
                    "wait": 1
                },
                {
                    "instruction": "CheckTlmValue",
                    "data": {
                        "name": "",
                        "mid": "TO_HK_TLM_MID",
                        "args": [
                            {
                                "compare": "==",
                                "variable": "usCmdCnt",
                                "value": [
                                    0.0
                                ]
                            }
                        ]
                    },
                    "wait": 1
                },
                {
                    "instruction": "RemoveCheckTlmContinuous",
                    "data": {
                        "name": "",
                        "verification_id": "no_error"
                    },
                    "wait": 1
                }
            ]
        }
    ]
}
```