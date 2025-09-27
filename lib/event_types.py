"""
@namespace lib.event_types
Instruction class definition for CTF
"""

# =========================================================================================
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
# distributed and modified only pursuant to the terms of that agreement.
# See the License for the specific language governing permissions and limitations under the
# License at https://software.nasa.gov/ .
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either expressed or implied.
#
# Copyright © 2019-2025 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# File: event_types.py
#
# Purpose: This file defines Instruction class for CTF.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================


class Instruction:
    """
    Represents a single CTF Test Instruction.

    @param delay: The time in seconds to wait before executing this instruction
    @param command: The dict containing instruction parameters
    @param test: Integer index of the test that includes this instruction
    @param command_index: Integer index of this instruction within the test
    @param disabled: Whether or not the instruction is disabled

    """
    def __init__(self, delay, command, test, command_index, disabled):
        self.delay = delay
        self.command = command
        self.test = test
        self.command_index = command_index
        self.is_disabled = disabled
