# Trick Plugin

The Trick Plugin provides an interface to a Trick simulation. The following test instructions are available.
In these instructions, the parameters `variable_name` and `value` may contain [user-defined variables](../variable_plugin/README.md).

For information on Trick simulations, see the documentation at https://nasa.github.io/trick/

### Configuration

The Trick Plugin uses the `[trick]` section of the CTF config file for its configuration parameters.
This section is required if and only if any Trick Plugin instructions are used in the test.

#### Example
```
#################################
# Trick plugin configuration
#################################
[trick]

# The hostname or IP address of the machine where the Trick simulation is running
hostname = localhost

# The port number of the Trick simulation
port = 7000
```

### FreezeTrickSim
Freezes or un-freezes the Trick simulation.
- **freeze**: `true` to freeze or `false` to un-freeze

Example:
<pre><code>
{
    "instruction": "FreezeTrickSim",
    "data": {
        "freeze": true
    }
},
</code></pre>

### SetTrickVariable
Sets the value of a variable.
- **variable_name**: The name of the variable to be set. (string)
- **value**: The value to be set.
- **variable_type**: (Optional) The type to which to convert `value` before setting. Must be one of `("int", "float", "string", "boolean")` (string)
- **units**: (Optional) The units in which to set the variable (string)

Example:
<pre><code>
{
    "instruction": "SetTrickVariable",
    "data": {
        "variable_name": "dyn.cannon.impactTime",
        "value": 5,
        "variable_type": "int",
        "units": "s"
    }
},
</code></pre>

### CheckTrickVariable
Checks that the value of the specified variable meets a condition.
- **variable_name**: The name of the variable to be checked. (string)
- **operator**: The logical operator with which to compare the variable and `value`. Must be one of: `==`, `<=`, `<`, `>`, `>=`, `!=`
- **value**: The value to compare against.
- **variable_type**: (Optional) The type to which to convert `value` **and** the variable before checking. Must be one of: `"int"`, `"float"`, `"string"`, `"boolean"`
- **units**: (Optional) The units in which to get the variable (string)

Example:
<pre><code>
{
    "instruction": "CheckTrickVariable",
    "data": {
        "variable_name": "dyn.cannon.impactTime",
        "value": 5,
        "operator": "=="
    },
}
</code></pre>