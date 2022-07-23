# Control Flow Plugin

The Control-Flow Plugin provides the functionality of CTF control flow statement at instruction level. 
It includes looping and conditional statements. 

### BeginLoop

Create a loop entry point. The loop is identified by a unique label. 
The BeginLoop must be in pairs with EndLoop instruction. The loop condition is defined in parameter "conditions" 
as a list of variables and the associated comparison operations. The condition is True, only 
if all comparison operations are True.
    
- **label**: a user defined label (example: "LOOP_1")
- **conditions**: a list of comparison conditions. Each includes "name", "operator" and "value".
- **variable**: either a variable defined by user or a variable from telemetry.
- **compare**: the operator applied to variable, including "<", "<=",">", ">=", "==", "!="  (example: "<")
- **value**: numerical number (example: 20)

Example:
<pre><code>
{
    "instruction":"BeginLoop",
    "data": {
       "label": "LOOP_1",
       "conditions": [
                 {"variable": "my_var", "compare": "<=", "value": 20},
                 {"variable": "tlm_usCmdCnt", "compare": "<=", "value": 7}
       ]
      }
 }
</code></pre>

### EndLoop

Create a loop exit point. It must match a BeginLoop instruction with the same label. 
If the looping condition in BeginLoop is False, the control flow jumps to the corresponding EndLoop instruction, 
and exits the loop.   

- **label**: a user defined label (example: "LOOP_1")

Example:
<pre><code>
{
     "instruction": "EndLoop",
     "data": { 
        "label": "LOOP_1" 
     }
}
</code></pre>

### IfCondition

Create an entry point for if conditional branch block. It is identified by a unique label per test script.
The IfCondition must be in pairs with EndCondition instruction. ElseCondition instruction is optional.
The condition is defined in parameter "conditions" as a list of variables and the associated comparison operations. 
The condition is True, only if all comparison operations are True.   

- **label**: a user defined label (example: "If_Label_1")
- **conditions**: a list of comparison conditions. Each includes "name", "operator" and "value".
- **variable**: either a variable defined by user or a variable from telemetry.
- **compare**: the operator applied to variable, including "<", "<=",">", ">=", "==", "!="  (example: "<")
- **value**: numerical number (example: 7)

Example:
<pre><code>
{
    "instruction":"IfCondition",
    "data": {
       "label": "If_Label_1",
       "conditions": [
                 {"variable": "my_var", "compare": "<=", "value": 10},
                 {"variable": "tlm_usCmdCnt", "compare": "!=", "value": 7}
       ]
      }
}
</code></pre>

### ElseCondition

Create an entry point for else conditional branch block. The instruction is optional. But if defined, 
it must match a IfCondition and a EndCondition instruction with the same label. 
If the condition of IfCondition instruction is False, the control flow skips the 'if' branch block,
only executes the 'else' branch block. If ElseCondition instruction is not defined,
the control flow jumps to the end of conditional branch block defined by a EndCondition instruction.

- **label**: a user defined label (example: "If_Label_1")

Example:
<pre><code>
{
     "instruction": "ElseCondition",
     "data": { 
        "label": "If_Label_1" 
     }
}
</code></pre>

### EndCondition

Create an exit point for if conditional branch block. It must match a IfCondition instruction with the same label. 
When the control flow reaches EndCondition instruction, it exits the conditional branch block.   

- **label**: a user defined label (example: "If_Label_1")

Example:
<pre><code>
{
     "instruction": "EndCondition",
     "data": { 
        "label": "If_Label_1" 
     }
}
</code></pre>
