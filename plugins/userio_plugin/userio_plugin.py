# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2022 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
# distributed and modified only pursuant to the terms of that agreement.
# See the License for the specific language governing permissions and limitations under the
# License at https://software.nasa.gov/ .
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either expressed or implied.

"""
userio_plugin.py: User IO Plugin Implementation for CTF.

- Defines the Plugin commands to allow user to pause the testing. User must confirm to continue testing
  for safety critical tasks.
- The CTF will wait until a user instructs to continue or abort the testing. If aborting the testing,
  the tests after the instruction will not be executed.
- The plugin adds a new command in end_test_on_fail_commands for test.py to check the command
"""

from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log


class UserIOPlugin(Plugin):
    """
    The UserIO Plugin Class Definition

    @note The UserIO Plugin define a command to allow user to pause the testing. User must confirm to continue testing
           for safety critical tasks.

    @note The CTF will wait until a user instructs to continue or abort the testing. If aborting the testing,
          the tests after the instruction will not be executed.

    @note The plugin adds a new command in end_test_on_fail_commands for test.py to check the user input.

    @note The custom plugin class *must* inherit from the Plugin base-class.

    @note A custom CTF plugin can be created to add new CTF instructions that can then be utilized within a JSON test
        script.

    @note All plugin functions mapped to a test instruction *must* return true/false to indicate pass/fail of
        that instruction.
    """

    def __init__(self):
        """
         Constructor implementation for example plugin.

         @note The __init__ function is called once a plugin is loaded.

         @note The __init__ function should not reference/interact with any other plugin since the other plugin may not
             be loaded at this stage.

         @note The constructor of a plugin must define the following fields:
             - name
             - description
             - command map: dictionary mapping CTF instructions to a tuple defining the
                           python function to use for that instruction, and a list of argument types
             - [optional] verify_required_commands: List of instructions that require verification (i.e polling
             until verification passes or timeout.
             - other class variables that can store state, etc...
         """

        super().__init__()

        ## Plugin Name
        self.name = "UserIOPlugin"

        ## Plugin Description
        self.description = "CTF UserIO Plugin"

        ## Plugin Command Map
        self.command_map = {
            "WaitForUserInput": (self.waituserinput_command, [ArgTypes.string])
        }

        ## List of end_test_on_fail_commands commands
        self.end_test_on_fail_commands = ["WaitForUserInput"]

    def initialize(self):
        """
         Initialize implementation for the UserIO plugin.

         @note The initialize function is called by the CTF plugin manager *after* all plugins have been loaded.

         @note This function may interact with other plugins, since all plugins have been loaded at this stage.

         @return bool: True if successful, False otherwise.
         """
        log.info("Initialized UserIO Plugin!")
        return True

    @staticmethod
    def waituserinput_command(prompt=""):
        """
        Wait for user input:  if there is no user input, wait forever;
        if user input is 'Y' or 'y', continue the test;
        if user input is anything else, abort the test

        @param prompt: any value (example: "user input")

        @return bool: True if successful, False otherwise.
        """
        promptmsg = prompt
        log.info("Test Command Executed with args: {}".format(promptmsg))
        log.info("Wait for user input: ")
        userinput = input("\nPlease Enter 'Y' to continue... \n")
        log.info("User Entered: {}".format(userinput))

        # Command implementation goes here...
        if userinput.upper() == "Y":
            status = True
            log.info("User confirms to continue the test ")
        else:
            status = False
            log.error("User aborts the test ! ")

        # Return status of that command
        return status

    def shutdown(self):
        """
        Shutdown implementation for the userio plugin.
        @note The shutdown function is called by the CTF plugin manager upon completion of a test run.
        @note The shutdown function can be exposed to test scripts by adding it to the command map.
        """
        log.info("userio plugin shutdown")
