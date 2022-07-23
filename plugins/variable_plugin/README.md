# Variable Plugin

The Variable Plugin provides CTF users with the capability to Set / Check / Update user-defined variables
from json test scripts. The defined variables can be evaluated in other CTF instructions,
such as "BeginLoop" and "EndLoop".  

In addition, CTF provides four 'built-in' variables: `_CTF_EXE_DIR`, `_CTF_LOG_DIR`, `_CTF_TLM_DIR`, `_CTF_CFS_NAME_CFS_OUTPUT_FILE`. 
An example of using these variables is shown in `example_scripts/config_required/lx1_lx2_basic_example.json`.  
`_CTF_EXE_DIR` is CTF runtime directory.  
`_CTF_LOG_DIR` is the test log folder during CTF execution, the value will change when CTF executes different test json scripts.  
`_CTF_TLM_DIR` is the telemetry log folder during CTF execution, the value will change when CTF restarts flight SW.   
`_CTF_CFS_NAME_CFS_OUTPUT_FILE` is the flight SW's standard output file, the value will change when CTF restarts flight SW.
`CFS_NAME` is the CFS section name defined in INI config file.  


### SetUserVariable

Set / update the value of user defined variable.

- **variable_name**: the user-defined variable name (example: "my_var")
- **operator**: the operator applied to variable, including "=", "+", "-", "*", "/"  (example: "=")
- **value**: value to be applied to the operation (example: 0)
- **variable_type**: (Optional) One of "int", "float", "string", or "boolean" indicating the type of `value` to be set. If not specified, `value` will be stored as-is. Only valid when used with the "=" operator.

Example:
<pre><code>
{
    "instruction": "SetUserVariable",
    "data": {
         "variable_name": "my_var",
          "operator": "=",
          "value": 0,
          "variable_type": "int"
    }
}
</code></pre>

Another way to define a variable is to define it in INI config file's [test_variable] section. 
For example, below define variable_1 to be 10, and variable_2 to be false. 
Variables defined in INI file can be used in the same way as SetUserVariable and the related instructions. 
<pre><code>
[test_variables]
variable_1 = 10
variable_2 = false
</code></pre>

### SetUserVariableFromTlm

Set the user defined variable to the latest telemetry value.

- **variable_name**: the user-defined variable name (example: "my_var")
- **mid**: the mid of telemetry packet (example: "TO_HK_TLM_MID")
- **tlm_variable**: the parameter of telemetry packet (example: "usCmdCnt")
- **target:** (Optional) A previously registered target name. If no name is given, will use the first registered target.

Example:
<pre><code>
{
    "instruction": "SetUserVariableFromTlm",
    "data": {
         "variable_name": "my_var",
          "mid": "TO_HK_TLM_MID",
          "tlm_variable": "usCmdCnt",
          "target": "cfs_workstation"
    }
}
</code></pre>

### SetUserVariableFromTlmHeader

Same as `SetUserVariableFromTlm` except the variable references the packet header.

- **variable_name**: the user-defined variable name (example: "my_var")
- **mid**: the mid of telemetry packet (example: "TO_HK_TLM_MID")
- **header_variable**: the parameter of telemetry packet (example: "pheader.length")
- **target:** (Optional) A previously registered target name. If no name is given, will use the first registered target.

Example:
<pre><code> 
{
    "instruction": "SetUserVariableFromTlmHeader",
    "data": {
         "variable_name": "my_var",
          "mid": "TO_HK_TLM_MID",
          "header_variable": "pheader.length",
          "target": "cfs_workstation"
    }
}
</code></pre>

### CheckUserVariable
Compare the user-defined variable with the value using the operator. 
Return the bool outcome of the operation performed on the variables and values.

- **variable_name**: the user-defined variable name (example: "my_var")
- **operator**: the operator applied to variable, including "<", "<=",">", ">=", "==", "!="  (example: "==")
- **value**: numerical number (example: 4)

Example:
<pre><code>
{
    "instruction": "CheckUserVariable",
    "data": {
         "variable_name": "my_var",
          "operator": "==",
          "value": 4
    }
}
</code></pre>


### Referring to Variables

After variables are defined by the instructions `SetUserVariable`, `SetUserVariableFromTlm` or `SetUserVariableFromTlmHeader`, 
they can be evaluated in other instruction parameters during run-time by wrapping a defined variable name in `$` like this: `$my_var$`.

**Note**: User variables must be defined using one of the above instructions before they can be referenced using the `$` syntax. Built-in variables may be referenced in the same way at any time.

###### Example 
<pre><code>               
{
    "instruction": "BeginLoop",
    "data": {
            "label": "LOOP_1",
             "conditions": [
                    {
                        "variable": "loop_cnt",
                        "value": "$max_loop_cnt$",
                        "compare": "<="
                     }
                    ]
            }
}
</code></pre>



Variable usage examples can be found in the directory `functional_tests/plugin_tests`:

- Test_CTF_Basic_Example.json: Using variables as values to be checked
- Test_CTF_Control_Flow_Loop.json: Using variables as a loop index and command args
- Test_CTF_Loop_Tlmvalue.json: Using variables to check different telemetry fields in a loop