"""
@namespace lib.time_manager
Default implementation for a minimal OS time manager
"""

# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2021 United States Government as represented by the
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

from lib.time_interface import TimeInterface


class TimeManager(TimeInterface):
    """
    Default implementation for the CTF time manager. This TimeManager is set as the active time manager on CTF start-up.

    @note - Custom plugin may define their own TimeManager and set it as the CTF TimeManager
            using Global.set_time_manager(time_manager)

    @note - This minimal implementation uses python's time.sleep() method. Other time manager implementations can
            perform logic while waiting.
    """
    def __init__(self):
        TimeInterface.__init__(self)

    def wait(self, seconds):
        """
        Wait the specified number of seconds

        @param seconds: How many seconds the TimeManager should sleep before returning control to CTF
        """
        time.sleep(seconds)

    def pre_command(self):
        """
        Optional implementation of logic to be executed *before* a CTF instruction is invoked.

        @note - This is useful when pausing/resuming of frames on an external time source is needed.
        """
        return

    def post_command(self):
        """
        Optional implementation of logic to be executed *after* a CTF instruction is invoked.

        @note - This is useful when pausing/resuming of frames on an external time source is needed.
        """
        return
