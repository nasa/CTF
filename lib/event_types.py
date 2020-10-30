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


class Event:
    def __init__(self, time, commands, test):
        self.time = time
        self.commands = commands
        self.test = test

class Command:
    def __init__(self, delay, command, test, command_index):
        self.delay = delay
        self.command = command
        self.test = test
        self.command_index = command_index


class Verify:
    def __init__(self, command, data, start_time, time_expire, test_index, started):
        self.command = command
        self.data = data
        self.start_time = start_time
        self.time_expire = time_expire
        self.test_index = test_index
        self.verified = None
        self.started = started
