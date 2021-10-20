# Troubleshooting & FAQ

[[_TOC_]]

## What platforms does CTF support?

CTF is developed and tested on CentOS 7 Linux. It may work with other Linux distributions or Docker containers, but is not officially supported.

---
## What version of CTF am I running?

Check the first line in the terminal output, or of `CTF_Log_File.log` in your log output directory, for `*** INFO: cFS Test Framework (vX.X) Starting...` where X.X is the version number. For the latest version, see https://github.com/nasa/CTF/releases

---
## I see an error "pidof: command not found" in CTF output, and/or cFS does not shut down
The `pidof` command is used to stop cFS processes on Linux. You may need to install the `sysvinit-tools` package in your environment to enable `pidof`.

---
## I'm having trouble with a config (.ini) file. What properties should I look out for?
## How do I configure a cFS target?

*TBD: complete this section*

Configuration of the CFS Plugin is based around targets and registration. A target is a cFS instance represented by a corresponding section of the config file, and referred to by name in the test script. Registration reads a section, associates it with the name, and initializes a connection to the target.
Registration may be done explicitly via the `RegisterCfs` instruction with a target name; automatically if `BuildCfs` or `StartCfs` are used first, or if `RegisterCfs` is used without a target name. Automatic registration takes only those sections beginning with `cfs_`, or the `cfs` section only if no others are found.

cFS targets are defined entirely within the config file by their respectively named sections. The test script only refers to targets by name, which must match a section in the config file.
The section `cfs` provides default values for other targets, and should be included even if you are not explicitly registering it. This section is only used to register a target if no other sections beginning with `cfs_` are found. Other target names do not necessarily have to begin with `cfs_`, but such targets must be registered explicitly using `RegisterCfs`.
`cfs` is not required to include all properties if it is not registered directly, but may provide values that are common to all targets. Other targets may then only define properties that differ. Any properties missing from a target section will be taken from the `cfs` section. If it is not defined in either section, an error will be reported and registration will fail. During automatic registration, 

There are several properties in `cfs` that you will likely need to customize for each target and/or project:

`cfs_protocol`
Must be one of "local", "ssh", or "sp0". Determines the type of connection made, and which additional config properties are needed. SSH targets require `destination`. SP0 targets require `reboot`, `cfs_exe_path`, `cfs_entry_point`, `cfs_startup_time`, `log_stdout`, and `stop_command`.  

`workspace_dir`
Not read by CTF directly, but is provided in the example configs as a convenient way to map paths relative to the root working directory. You may use `${cfs:workspace_dir}` (or another key) to append relative paths such as `cfs_build_dir` or `CCSDS_data_dir`. If you're seeing errors such as file not found or unexpected paths on startup, check `workspace_dir`.

`cfs_run_in_xterm`
Only applies to targets using the "local" protocol. If true, and xterm is found, each target's stdout will be displayed in a separate xterm window that opens when cFS starts and closes when it stops. Otherwise, all cFS output will be printed inline on the console. It is recommended to set this to false for tests run in CI, via a script, or otherwise headless.

Other properties that may be commonly changed, or could cause unexpected behavior:

`core:reset_plugins_between_scripts`

`logging:log_level` and `cfs:log_ccsds_imports`

`ccsds:CCSDS_header_path`
This is a path to the file containing the CCSDS header definitions to be used by CTF. This must be a Python file that conforms to the CCSDS packet interface found in `ctf/plugins/ccsds_plugin/ccsds_packet_interface.py`


---
## I have unexpected or missing telemetry, or EnableCfsOutput is failing.

An instance of flight software may still be running in the background and holding onto resources. Run `ps -aux | grep core` (or the name of your cFS exe) before and/or after a test run to check for any persisting processes. Rebooting the host computer may also help, if some other process is using a required port.

Also, check the `cmd_udp_port` and `tlm_udp_port` in the `[cfs]` or target section of your config file. The command port will be determined by cFS and is where CTF sends commands; the telemetry port is determined by CTF and is where it informs cFS to send telemetry by the enable output command.

---
## CheckEvent or CheckTlmValue is failing, but I see the events in CTF logs.

Your checks may be happening too early or too late. For event checks, CTF will only check events that arrive between the start of the check and the verification timeout. Compare the execution times in `cfs_tlm_msgs.log` with the timestamps of the checks in the CTF test output file. (Note that execution time is the offset in seconds from the start of the test.) We recommend using a "wait" of 0 for all checks, unless you know that the packet will be delayed:
```

                {
                    "instruction": "EnableCfsOutput",
                    "data": {},
                    "wait": 2,
                },
                {
                    "instruction": "CheckEvent",
                    "data": {
                        "app": "TO",
                        "id": "3",
                        "msg": "TO - ENABLE_OUTPUT cmd succesful for  routeMask:0x00000001"
                    },
                    "wait": 0
                }, 
```

---
## My first telemetry check for a given packet passes, but others fail.

Checking any value in a packet clears that packet from memory, to avoid checking stale data again later in the test. If you need to check multiple values from the same packet, combine the conditions in one instruction using a list:
```
"args": [
  {
    "compare": "==",
    "variable": "cmdCount",
    "value": 1
  },
  {
    "compare": "==",
    "variable": "errCount",
    "value": 0
  },
]
```

---
## How do I run multiple test scripts at once?

When executing CTF, you may provide any number of directory and/or file paths to be executed in order. For directories, all .json files will be executed in indeterminate order.

Example: `./ctf --config_file=./configs/default_config.ini test_scripts script1.json script2.json script3.json`
This will execute all .json files in test_scripts, followed by script1, script2, and finally script3.

If the tests are designed to be executed in sequence, you may wish to set `reset_plugins_between_scripts` to False in your config file to allow the plugin state, and potentially the flight software process(es), to be preserved across all test scripts - similarly to multiple test cases in one script. This allows you to avoid registering and starting cFS targets in each test script. Note that when doing so, cFS will not be stopped until the end of the final test, unless `ShutdownCfs` is used.

---
## When should I use RegisterCfs, or use a target name vs an empty string?
## Why do some of the example tests not specify a cFS target name?
## How do I write test scripts so that they can be reused with different configurations?

Using `RegisterCfs` to declare your cFS target(s) is optional. The CFS Plugin will automatically register and use CFS targets as defined in the config file if no target name is explicitly provided. Automatic registration occurs at the first occurrence of `BuildCfs` or `StartCfs` if no target has yet been registered. During automatic registration, any section in the config file beginning with `cfs_` will be treated as a CFS target, such as `[cfs_lx1]`. The required section `[cfs]` will be used to register a default target if no others are provided. When explicitly registering a target with RegisterCfs, the name must match a section in the config file, but it is not required to begin with `cfs_`. In other words, `[cfs_lx1]` may be registered automatically or with `RegisterCfs` but `[lx1]` can only be registered with `RegisterCfs`.

Likewise in your test script, you may or may not provide a target name for any CFS Plugin instruction. If a target name is provided, it must match a section name in the config file, whether it was registered explicitly or automatically. If no target is provided (an empty string `""`, or omitting `"target"` altogether), the instruction will apply to **any and all** registered targets sequentially. Thus omission of target names allows a test script to be trivially reused with different config files, but is most practical when configured with a single target.

These features allow you to mix and match test scripts with different configurations by relying on automatic registration of targets. If the test script does not name or register any targets, its instructions will apply to any one or more targets as defined in the config file. Alternatively, you may use `RegisterCfs` to specify only those targets from your config file that you want to register for the test, even if there are others defined.

---
## I'm getting unusual Python errors relating to my instruction arguments.
##When do I use certain types and comparison operators in instruction arguments?

Instructions that evaluate expressions, like `CheckTlmValue`, support different operators for comparing values. Standard logical operators like ==, !=, <=, etc are allowed for numeric comparisons. When comparing strings, use `streq` for equality or `strneq` for inequality. You cannot use string comparison for numbers or vice versa.

*TBD: correct and incorrect example of comparison operators*

Types used in JSON should match the corresponding data as closely as possible. Use whole numbers for integers, decimals for floats or doubles, and strings for strings or characters. Do not put a numeric value in quotes unless it is to be handled as a string.

*TBD: correct and incorrect example of type matching*

For complex types, such as "args" for `SendCfsCommand`, use nested JSON objects with key-value pairs to represent the structure. Within an object, you may use an ordered list for values that are arrays (ie, those having a nonzero `array_size` attribute in their data definition). Do not use lists to represent multiple fields in an object.

*TBD: correct and incorrect example of nested args*

To specify a single value in an array, you may use the indexed name of the element (eg `"myArray[3]" = 1`). You may also provide a single value to an array name to fill the array with that value (eg `"myArray" = 1` sets ALL elements in `myArray` to 1). Both methods can be used in combination.

*TBD: example of default and indexed values for an array*

For examples of correct usage of these and other instruction arguments, see the test scripts in `scripts\example_tests`.

---
## Can I check for a partial string match on an event?
## How do I use macros, regular expressions, or string arguments?

*TBD: complete this section*

*TBD: example of macro usage*
*TBD: example of event msg_args*
*TBD: example of event regex match*

---
## How do I get color-coded log output?

Simply install the Python package `colorlog`: `(pip install colorlog)`. The package is not installed by default since many users run CTF via the editor or scripts and do not inspect the output directly at runtime. Colors only apply to the command line output.

---
## I am seeing some other odd behavior not described here.

Make sure you are using the latest CTF and flight software. Pull from the git repo(s), check out the latest release branch/tag, reinstall your Anaconda environment, and rebuild everything. Try running CTF directly without the editor or intermediate scripts. If the problem persists, contact a developer or open an issue at https://github.com/nasa/CTF/issues
