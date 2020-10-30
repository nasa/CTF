# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2020 United States Government as represented by the
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
    def __init__(self):
        super().__init__()
        self.name = "UserIOPlugin"
        self.description = "CTF UserIO Plugin"
        self.command_map = {
            "WaitForUserInput": (self.waituserinput_command, [ArgTypes.string])
        }
        self.end_test_on_fail_commands = ["WaitForUserInput"]


    def initialize(self):
        # FIXME remove commented out code
        #print("Initialize runs before a script is executed")
        return True

    def waituserinput_command(self, prompt = ""):
        # FIXME remove commented out code
        # arg1 = data["arg1"]
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
        log.info("userio plugin shutdown")
