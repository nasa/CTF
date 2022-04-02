# Variable Plugin

The Variable Plugin provides CTF users with the capability to Set / Check / Update user-defined variables
from json test scripts. The defined variables can be used in control flow instructions,
such as "BeginLoop" and "EndLoop". The following instructions are available.

### SetUserVariable

Set / update the value of user defined variable.

- **variable_name**: the user-defined variable name (example: "my_var")
- **operator**: the operator applied to variable, including "=", "+", "-", "*", "/"  (example: "=")
- **value**: numerical number (example: 0)

Example:
<pre><code>
{
    "instruction": "SetUserVariable",
    "data": {
         "variable_name": "my_var",
          "operator": "=",
          "value": 0
    }
}
</code></pre>

### SetUserVariableFromTlm

Set the user defined variable to the latest telemetry value.

- **variable_name**: the user-defined variable name (example: "my_var")
- **mid**: the mid of telemetry packet (example: "TO_HK_TLM_MID")
- **tlm_variable**: the parameter of telemetry packet (example: "usCmdCnt")

Example:
<pre><code>
{
    "instruction": "SetUserVariableFromTlm",
    "data": {
         "variable_name": "my_var",
          "mid": "TO_HK_TLM_MID",
          "tlm_variable": "usCmdCnt"
    }
}
</code></pre>

### SetUserVariableFromTlmHeader

Same as `SetUserVariableFromTlm` except the variable references the packet header.

- **variable_name**: the user-defined variable name (example: "my_var")
- **mid**: the mid of telemetry packet (example: "TO_HK_TLM_MID")
- **header_variable**: the parameter of telemetry packet (example: "pheader.length")

Example:
<pre><code> 
{
    "instruction": "SetUserVariableFromTlmHeader",
    "data": {
         "variable_name": "my_var",
          "mid": "TO_HK_TLM_MID",
          "tlm_variable": "pheader.length"
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


