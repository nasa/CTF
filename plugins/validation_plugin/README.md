# Validation Plugin

The Validation Plugin provides functionality to interpret a cFE binary event log to a human-readable text file, and search for a text string in a file. 
It also allows the user to delete files/folders and copy files/folders on the local host machine.

### SaveFileAsText

Save the cFE event log file (binary file created via the CFE_EVS_WRITE_LOG_DATA_FILE_CC command) to a human-readable text file

- **input_file**: path of the binary event log file.
- **output_file**: path of the output text file.
- **file_type**: currently only supports 'EVS' file type.
- **target**: cfs target, optional 

Example:
<pre><code>
{
    "instruction":"SaveFileAsText",
    "data":{
        "input_file": "/dev/shm/osal:RAM/event_log.bin",
        "output_file": "./testArtifacts/event_log.txt",
        "file_type": "EVS",
        "target": "cfs"
    }
 }
</code></pre>

### SearchStr

Search a text file for a given text string. If the string is found, return True, otherwise return False.

- **file**: path of the text file.
- **search_str**: text string to be searched for.
- **is_regex**: (Optional) True if `search_str` is to be used for a regex match instead of string search.

Example:
<pre><code>
{
    "instruction":"SearchStr",
     "data":{
         "file": "/testArtifacts/event_log.txt",
         "search_str": "cFE EVS Initial*",
         "is_regex": true                                          
     }        
}
</code></pre>

### SearchNoStr

Search a text file for a given text string. If the string is NOT found, return True, otherwise return False.

- **file**: path of the text file.
- **search_str**: text string to be searched for.
- **is_regex**: (Optional) True if `search_str` is to be used for a regex match instead of string search.

Example:
<pre><code>
{
    "instruction":"SearchNoStr",
     "data":{
         "file": "/testArtifacts/event_log.txt",
         "search_str": "cFE SCH Initial"                                                  
     }        
}
</code></pre>

### CopyFiles

Copy a file or folder on the host file system. The source may point to a file or folder.
If the destination exists, it will be overridden. 
- **source**: path of the file / folder to be copied from on host machine.
- **destination**: path of the file / folder to be copied to on host machine.

Example:
<pre><code>
{
    "instruction":"CopyFiles",
    "data":{
         "source": "./testArtifacts/",
         "destination": "./testArtifacts_2/"                                          
     }        
}
</code></pre>

### DeleteFiles

Delete a file or folder on the host file system.  

- **path**: path of the file / folder to be deleted on host machine.

Example:
<pre><code>
{
     "instruction": "DeleteFiles",
     "data": {
         "path": "./testArtifacts/"                                          
     }             
}
</code></pre>

### InsertUserComment

Insert a comment into test log, which may be used for post-test analysis.  

- **comment**: comment to be inserted into test log.

Example:
<pre><code>
{
     "instruction": "InsertUserComment",
     "data": {
         "comment": "EXPECTED_FAIL_LINUX: system table dump is not implemented in OSAL"
     }             
}
</code></pre>
