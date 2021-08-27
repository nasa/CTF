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
```javascript
{
    "instruction": "SetUserVariable",
    "data": {
         "variable_name": "my_var",
          "operator": "=",
          "value": 0
    }
}
```

### SetUserVariableFromTlm

Set the user defined variable to the latest telemetry value.

- **variable_name**: the user-defined variable name (example: "my_var")
- **mid**: the mid of telemetry packet (example: "TO_HK_TLM_MID")
- **tlm_variable**: the parameter of telemetry packet (example: "usCmdCnt")

Example:
```javascript
{
    "instruction": "SetUserVariableFromTlm",
    "data": {
         "variable_name": "my_var",
          "mid": "TO_HK_TLM_MID",
          "tlm_variable": "usCmdCnt"
    }
}
```

### CheckUserVariable
Compare the user-defined variable with the value using the operator. 
Return the bool outcome of the operation performed on the variables and values.

- **variable_name**: the user-defined variable name (example: "my_var")
- **operator**: the operator applied to variable, including "<", "<=",">", ">=", "==", "!="  (example: "==")
- **value**: numerical number (example: 4)

Example:
```javascript
{
    "instruction": "CheckUserVariable",
    "data": {
         "variable_name": "my_var",
          "operator": "==",
          "value": 4
    }
}
```

### SetLabel

Set the a test-script scope label for control flow instructions. 
- **label_name**: the label name (example: "label_1")
Example:
```javascript
{
    "instruction": "SetLabel",
    "data": {
         "label_name": "label_1"
    }
}
```
