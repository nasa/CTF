"""
@namespace lib.status
Defines status messages to be sent out by CTF during a test run
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


class StatusDefs:
    """
    This class defines enumerations for the status definitions used by CTF to send instruction status.
    """
    waiting = 'waiting'
    active = 'active'
    stopped = 'stopped'
    passed = 'passed'
    failed = 'failed'
    error = 'error'
    timeout = 'timeout'
    aborted = 'aborted'
    disabled = 'disabled'


## Template Dictionary Definition of an Instruction Status Object. Includes all status fields at the instruction-level.
InstructionStatus = {
    "instruction": "",
    "wait": 0,
    "data": {},
    "status": StatusDefs.waiting,
    "details": "",
    "comment": "",
    "description": ""
}

## Template Dictionary Definition of an Test Status Object. Includes all status fields at the test case level.
TestStatus = {
    "case_number": "",
    "status": StatusDefs.waiting,
    "details": "",
    "instructions": [],
    "comment": "",
    "description": ""
}

## Template Dictionary Definition of an Scripts Status Object. Includes all status fields at the script level.
ScriptStatus = {
    "path": "",
    "test_name": "",
    "status": StatusDefs.waiting,
    "details": "",
    "tests": []
}

## Template Dictionary Definition of an Test Status Object. Includes all status fields at the test suite level (multiple
## test scripts.
SuiteStatus = {
    "elapsed_time": 0,
    "status": StatusDefs.waiting,
    "scripts": []
}
