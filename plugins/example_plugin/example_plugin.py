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

from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log
from ctypes import cdll, CDLL

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
    def __init__(self):
        super().__init__()
        self.name = "ExamplePlugin"
        self.description = "CTF Example Plugin"
        self.command_map = {
            "TestCommand": (self.test_command, [ArgTypes.string] * 2),
            "TestVerifyCommand": (self.test_verify_command, []),
            "TestSharedLibraryCommand": (self.test_shared_library, [])
        }
        self.verify_required_commands = ["TestVerifyCommand"]
        self.example_counter = 0

    def initialize(self):
        log.info("Initialized Example Plugin!")
        return True

    def test_command(self, arg1, arg2):
        log.info("Test Command Executed with args: {}, {}".format(arg1, arg2))
        # Command implementation goes here...

        foo = arg1 + arg2
        log.info("Example Plugin Test Command: {} + {} = {}".format(arg1, arg2, foo))

        # Return status of that command
        status = True
        return status

    def test_verify_command(self):
        log.info("Test Verify Executed")

        # Non-blocking verification code goes here...

        self.example_counter += 1
        # Here, we intentionally wait for example_counter > 5
        # before allowing the verification to pass
        if self.example_counter > 5:
            status = True
        else:
            status = False

        # Return status of verification
        return status

    def test_shared_library(self):
        log.info("Test Shared Library Executed")

        cdll.LoadLibrary("libc.so.6")
        libc = CDLL("libc.so.6")
        timestamp = libc.time(None)
        length = libc.printf(b"System time is %d\n", timestamp)
        log.debug("{} bytes printed to system out".format(length))

        return length == 26

    def shutdown(self):
        log.info("Optional shutdown/cleanup implementation for Example Plugin")
