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

from lib.event_types import Instruction


def test_command():
    cmd = Instruction(1.0, "Command", "Test", 0, True)
    assert cmd.delay == 1.0
    assert cmd.command == "Command"
    assert cmd.test == "Test"
    assert cmd.command_index == 0
    assert cmd.is_disabled is True
