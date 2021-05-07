# Introduction

CTF Plugins allow developers to extend CTF with new test commands. Each new test command is mapped to its respective implementation in the plugin.

# Types of test commands

There are two types of supported test commands
* Non-verification Commands: Commands that do not require verification at a later time and can be validated right away. Examples include sending data such as sending a CFS Command.

* Verification Commands: Commands that require verification (via polling) until the verification is satisfied, or a timeout is reached. Examples including checking that a piece of telemetry changes at some point in the test. The implementation of those commands must be non-blocking in order to return control to CTF between the verification polls.

# Plugin Creation
To create a new plugin, create a directory with the `plugin-name` under `plugins/`. For example we can create `example_plugin` at the directory `ctf/plugins/example_plugin`.

**Note:** Plugins must conform to a naming convention in order to be loaded by CTF. The module containing the plugin class must end with `_plugin` and **not** contain the word `tests` in its module path. If you provide unit tests for your plugin, place them in a directory named `tests` under `plugin-name`.

In the `example_plugin` directory, we create a new .py file `example_plugin.py`. containing our plugin class, which inherits from the `Plugin` base class. Each plugin is required to define the following properties

*  `name` - plugin name
*  `description` - plugin description
*  `command_map` - python dict object mapping between the command string from the test script, to a python function for the implementation of that command.
*  `verify_required_commands` - python list containing list of command strings that require verification.

Our `example_plugin.py` will look as follows

```python
from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log

class ExamplePlugin(Plugin):
    def __init__(self):
        self.name = "ExamplePlugin"
        self.description = "CTF Example Plugin"
        self.command_map = {
            "TestCommand": (self.test_command, [ArgTypes.string] * 2),
            "TestVerifyCommand": (self.test_verify_command, [])
        }
        self.verify_required_commands = ["TestVerifyCommand"]
        self.example_counter = 0

    def initialize(self):
        #print("Initialize runs before a script is executed")
        return True

    def test_command(self, arg1, arg2):
        log.info("Test Command Executed with args: {}, {}".format(arg1, arg2))

        # Command implementation goes here...

        # Return status of that command
        status = True
        return status

    def test_verify_command(self):
        log.info("Test Verify Executed")

        # Non-blocking verification code goes here...

        # Here, we intentionally wait for example_counter > 5
        # before allowing the verification to pass

        self.example_counter += 1
        if self.example_counter > 5:
            status = True
        else:
            status = False

        # Return status of verification
        return status

    def shutdown(self):
        print("Optional shutdown/cleanup implementation for plugin")
```

With the above plugin definition, the following snippet of a JSON test script shows how the commands are used.

```JSON
{
  "test_number": "Example-Plugin-Test",
  "test_name": "Example Plugin Test",
  "requirements": {
    "MyRequirement": "N/A"
  },
  "description": "Testing Example Plugin",
  "owner": "CTF",
  "test_setup": "Script will execute a single command, and a single verification",
  "ctf_options": {
    "verif_timeout": 2.0
  },
  "telemetry_watch_list": {},
  "command_watch_list": {},
  "tests": [
        {
            "case_number": "Example Plugin Test",
            "description": "No description",
            "commands": [
                {
                    "command": "TestCommand",
                    "data": {
                        "arg1": "foo",
                        "arg2": 42
                    },
                    "wait": 1
                },
                {
                    "command": "TestVerifyCommand",
                    "data": {},
                    "wait": 1
                }
            ]
        }
  ]
}

```

Executing the script produces the following output showing the test command successfully processed, and the test verification command executed 6 times before it the verification was satisfied.

```
[14:13:33.882] test_script                     (85 ) *** INFO: Input file utilized : test_ctf_example_plugin.json
[14:13:33.882] test                            (139) *** INFO: Test Example Plugin Test: Starting
[14:13:34.884] example_plugin                  (22 ) *** INFO: Test Command Executed with args: foo, 42
[14:13:34.884] test                            (56 ) *** TEST_PASS: Event TestCommand: {'arg1': 'foo', 'arg2': 42}
[14:13:35.885] test                            (70 ) *** INFO: Waiting up to 5.0 seconds for verification of TestVerifyCommand: {}
[14:13:35.885] example_plugin                  (31 ) *** INFO: Test Verify Executed
[14:13:36.136] example_plugin                  (31 ) *** INFO: Test Verify Executed
[14:13:36.387] example_plugin                  (31 ) *** INFO: Test Verify Executed
[14:13:36.638] example_plugin                  (31 ) *** INFO: Test Verify Executed
[14:13:36.890] example_plugin                  (31 ) *** INFO: Test Verify Executed
[14:13:37.141] example_plugin                  (31 ) *** INFO: Test Verify Executed
[14:13:37.141] test                            (107) *** TEST_PASS: Verification Passed TestVerifyCommand: {}
[14:13:37.141] test_script                     (78 ) *** INFO: Verification Test Name: Example Plugin Test
[14:13:37.141] test_script                     (79 ) *** INFO: Verification Test Number: Example-Plugin-Test
[14:13:37.142] test_script                     (80 ) *** INFO: Test Conductor: aishehat
[14:13:37.142] test_script                     (81 ) *** INFO: Run Date/Time: 11/07/2019 / 14:13:37
[14:13:37.142] test_script                     (82 ) *** INFO: Platform: #1 SMP Mon Sep 30 14:19:46 UTC 2019
[14:13:37.142] test_script                     (83 ) *** INFO: Requirement Verification Targets: MyRequirement
[14:13:37.142] test_script                     (84 ) *** INFO: Test Description : Testing Example Plugin
[14:13:37.142] test_script                     (85 ) *** INFO: Input file utilized : test_ctf_example_plugin.json
[14:13:37.142] test_script                     (98 ) *** INFO: Number tests Run:                   1
[14:13:37.142] test_script                     (99 ) *** INFO: Number tests Passed:                1
[14:13:37.142] test_script                     (100) *** INFO: Number tests Failed:                0
```