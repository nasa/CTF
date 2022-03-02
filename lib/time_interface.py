"""
@namespace lib.time_interface
Interface definition for time managers to implement
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


import time


class TimeInterface:
    """
    Virtual class definition for custom plugins to implement their own time managers.

    @note A custom plugin must set the global time manager used by CTF using Global.set_time_manager(time_manager)
    """
    def __init__(self):
        """
        Constructor of TimeInterface Class: Initiate instance properties
        """
        ## Execution time since the time manager was initialized
        self.exec_time = 0

        ## Execution time when the last instruction was completed
        self.last_command_completion_time = 0

        ## How much time has passed since the last instruction was completed.
        self.time_since_last_command = 0

    @staticmethod
    def wait_seconds(seconds):
        """
        Helper utility to wait in seconds (OS Time)
        """
        time.sleep(seconds)

    def wait(self, seconds):
        """
        Virtual method to wait an amount of time.

        @note - May include special logic to interface with external time sources
        """
        raise NotImplementedError()

    @staticmethod
    def pre_command():
        """
        Optional implementation of logic to be executed *before* a CTF instruction is invoked.

        @note - This is useful when pausing/resuming of frames on an external time source is needed.
        """
        return

    @staticmethod
    def post_command():
        """
        Optional implementation of logic to be executed *after* a CTF instruction is invoked.

        @note - This is useful when pausing/resuming of frames on an external time source is needed.
        """
        return
