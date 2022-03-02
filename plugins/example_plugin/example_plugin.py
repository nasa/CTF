"""
@namespace plugins.example_plugin
The Example Plugin module shows a minimal plugin implementation to be used as a
template for other CTF plugins
"""

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


from ctypes import cdll, CDLL
from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log

# The ExamplePlugin class shows a minimal plugin implementation to be used as a
# template for other CTF plugins.

# The custom plugin class *must* inherit from the Plugin base-class, and define the following
# fields:
#           - name
#           - description
#           - command map: dictionary mapping CTF instructions to a tuple defining the
#                           python function to use for that instruction, and a list of argument types
#           - [optional] verify_required_commands: List of instructions that require verification (i.e polling
#             until verification passes or timeout.
#           - other class variables that can store state, etc...

# A custom CTF plugin can be created to add new CTF instructions that can then be utilized within a JSON test script.

# Note - All plugin functions mapped to a test instruction *must* return true/false to indicate pass/fail of
# that instruction.


class ExamplePlugin(Plugin):
    """
    The Example Plugin Class Definition

    @note The Example Plugin shows a simple CTF plugin that can perform a single test instruction and a single
        verification instruction, in addition to loading a C shared library.

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
        self.name = "ExamplePlugin"

        ## Plugin Description
        self.description = "CTF Example Plugin"

        ## Plugin Command Map
        self.command_map = {
            "TestCommand": (self.test_command, [ArgTypes.string] * 2),
            "TestVerifyCommand": (self.test_verify_command, []),
            "TestSharedLibraryCommand": (self.test_shared_library, [])
        }

        ## List of verification type commands
        self.verify_required_commands = ["TestVerifyCommand"]

        ## Counter to track how many verifications are ran. Other plugin-specific properties can also be defined
        self.example_counter = 0

    def initialize(self):
        """
        Initialize implementation for the example plugin.

        @note The initialize function is called by the CTF plugin manager *after* all plugins have been loaded.

        @note This function may interact with other plugins, since all plugins have been loaded at this stage.

        @return bool: True if successful, False otherwise.
        """
        log.info("Initialized Example Plugin!")
        return True

    @staticmethod
    def test_command(arg1, arg2):
        """
        Simply logs that the test command was executed with the provided arguments.

        @param arg1: any value (example: "Hello")
        @param arg2: any value (example: "World")

        @return bool: True if successful, False otherwise.
        """
        log.info("Test Command Executed with args: {}, {}".format(arg1, arg2))

        # Command implementation goes here...
        foo = arg1 + arg2
        log.info("Example Plugin Test Command: {} + {} = {}".format(arg1, arg2, foo))

        # Return status of that instruction
        status = True
        return status

    def test_verify_command(self):
        """
        Increments the plugin's example_counter value and checks if it is greater than `5`.

        @note Verification instructions will be re-executed by the CTF core until the verification passes, or the
            verification timeout is reached.

        @return bool: True if successful, False otherwise.
        """
        log.info("Test Verify Executed")

        ##############################################
        # Non-blocking verification code goes here...
        ##############################################

        self.example_counter += 1

        # Here, we intentionally wait for example_counter > 5
        # before allowing the verification to pass
        status = bool(self.example_counter > 5)

        ##############################################

        # Return status of verification
        return status

    @staticmethod
    def test_shared_library():
        """
        Uses libc to get the system time and log it to system output.

        @note Verifies that the expected number of bytes were printed.

        @return bool: True if successful, False otherwise.
        """
        log.info("Test Shared Library Executed")
        cdll.LoadLibrary("libc.so.6")
        libc = CDLL("libc.so.6")
        timestamp = libc.time(None)
        length = libc.printf(b"System time is %d\n", timestamp)
        log.debug("{} bytes printed to system out".format(length))
        return length == 26

    def shutdown(self):
        """
        Shutdown implementation for the example plugin.
        @note The shutdown function is called by the CTF plugin manager upon completion of a test run.
        @note The shutdown function can be exposed to test scripts by adding it to the command map.
        """
        log.info("Optional shutdown/cleanup implementation for Example Plugin")
