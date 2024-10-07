# Validation Plugin

The Validation Plugin provides the functionality to copy, delete the files/folders on the host file system, check file/folder existence, and search a file for text string. 


### SearchStr

Search a file for a given text string. If the string is found, return True, otherwise return False.

- **file**: path of the file.
- **search_str**: text string to be searched for.
- **variable_name**: (Optional) user-defined variable name. If variable_name is provided, assign the count of the text string in the file to the variable. It does not apply to regex match. 
- **is_regex**: (Optional) True if `search_str` is to be used for a regex match instead of string search. default is False.
- **target**: (Optional) the section name in the config file, if `search_str` includes macros defined in the section's CCSDS Data Directory json files. 

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

Search a file for a given text string. If the string is NOT found, return True, otherwise return False.

- **file**: path of the file.
- **search_str**: text string to be searched for.
- **is_regex**: (Optional) True if `search_str` is to be used for a regex match instead of string search. default is False.
- **target**: (Optional) the section name in the config file, if `search_str` includes macros defined in the section's CCSDS Data Directory json files. 

Example:
<pre><code>
{
    "instruction":"SearchNoStr",
     "data":{
         "target":"cfs",
         "file": "/testArtifacts/event_log.txt",
         "search_str": "cFE SCH #SCH_ENA_GRP_CMD_ERR_EID# Initial"                                                  
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

### CheckFileExists

Check whether a file or folder exists on the host file system.  

- **file**: path of the file.

Example:
<pre><code>
{
     "instruction": "CheckFileExists",
     "data": {
         "file": "/testArtifacts/event_log.txt"
     }             
}
</code></pre>

