# UserIO Plugin

The UserIO Plugin handles user input/output operations, including pausing test for safety critical operations. In such cases, CTF will wait until users confirm whether to continue or to abort the tests. 

### WaitForUserInput 

When CTF executes WaitForUserInput, it will pause and wait for user input from stdin. If a user enters "Y", CTF will continue to execute next test instructions. 
Any other input will abort the test. 

- **prompt**: optional value (example: "safety critical")


Example:
<pre><code>
{
    "instruction":"WaitForUserInput",
    "data":{
     "prompt": "  " 
    }      
 }
</code></pre>

