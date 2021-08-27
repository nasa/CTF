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
```javascript
{
    "instruction":"BeginLoop",
    "data": {
       "label": "LOOP_1",
       "conditions": [
                 {"variable": "my_var", "compare": "<", "value": 20},
                 {"variable": "tlm_usCmdCnt", "compare": "<", "value": 7}
       ]
      }
 }
```

### EndLoop

Create a loop exit point. It must match a BeginLoop instruction with the same label. 
If the looping condition in BeginLoop is False, the control flow jumps to the corresponding EndLoop instruction, 
and exits the loop.   

- **label**: a user defined label (example: "LOOP_1")

Example:
```javascript
{
     "instruction": "EndLoop",
     "data": { 
        "label": "LOOP_1" 
     }
}
```
