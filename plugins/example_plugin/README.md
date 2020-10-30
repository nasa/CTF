# Example Plugin

The Example Plugin shows a simple CTF plugin that can perform a single test instruction and a single verification instruction.

### TestCommand

Simply logs that the test command was executed with the provided arguments.

- **arg1**: any value (example: "Hello")
- **arg2**: any value (example: "World")

Example:
```javascript
{
    "command":"TestCommand",
    "data":{
        "arg1": "foo",
        "arg2": 42
    }
 }
```

### TestVerifyCommand

Increments the plugin's example_counter value and checks if it is greater than `5`. CTF will poll run that instructions until the verification is successful, or a timeout occurs.

Example:
```javascript
{
    "command":"TestVerifyCommand",
    "data":{}
}
```

### TestSharedLibraryCommand

Uses libc to get the system time and log it to system output. Verifies that the expected number of bytes were printed.
Example:
```javascript
{
    "command":"TestSharedLibraryCommand",
    "data":{}
}
```
