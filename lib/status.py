"""
@namespace lib.status
Defines status messages to be sent out by CTF during a test run
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

from lib.exceptions import CtfTestError


class StatusDefs:
    """
    This class defines enumerations for the status definitions used by CTF to send instruction status.
    """
    # ENHANCE: add additional status to indicate looping
    waiting = 'waiting'
    active = 'active'
    stopped = 'stopped'
    passed = 'passed'
    failed = 'failed'
    error = 'error'
    timeout = 'timeout'
    aborted = 'aborted'
    disabled = 'disabled'


class ObjectFactory:
    """
    This class defines enumerations for the status definitions used by CTF to send instruction status.
    """

    @staticmethod
    def create_object(obj_name: str):
        """
        Static ObjectFactory class method: create objects using factory methods
        """
        if obj_name == 'SuiteStatus':
            return ObjectFactory.__create_suite_status()
        if obj_name == 'TestStatus':
            return ObjectFactory.__create_test_status()
        if obj_name == 'ScriptStatus':
            return ObjectFactory.__create_script_status()
        if obj_name == 'InstructionStatus':
            return ObjectFactory.__create_instruction_status()
        if obj_name == 'PluginInfo':
            return ObjectFactory.__create_plugin_info()
        if obj_name == 'CommandInfo':
            return ObjectFactory.__create_command_info()
        if obj_name == 'ParameterInfo':
            return ObjectFactory.__create_parameter_info()

        raise CtfTestError('Undefined object {}'.format(obj_name))

    @staticmethod
    def __create_suite_status():
        ## Template Dictionary Definition of an Test Status Object. Includes all status fields at the test suite level
        ## (multiple test scripts).
        suite_status = {
            "elapsed_time": 0,
            "status": StatusDefs.waiting,
            "scripts": []
        }
        return suite_status

    @staticmethod
    def __create_test_status():
        ## Template Dictionary Definition of an Test Status Object. Includes all status fields at the test level.
        test_status = {
            "test_number": "",
            "status": StatusDefs.waiting,
            "details": "",
            "instructions": [],
            "comment": "",
            "description": ""
        }
        return test_status

    @staticmethod
    def __create_instruction_status():
        ## Template Dictionary Definition of an Instruction Status Object.
        ## Includes all status fields at the instruction-level.
        instruction_status = {
            "instruction": "",
            "wait": 0,
            "data": {},
            "status": StatusDefs.waiting,
            "details": "",
            "comment": "",
            "description": ""
        }
        return instruction_status

    @staticmethod
    def __create_script_status():
        ## Template Dictionary Definition of an Scripts Status Object. Includes all status fields at the script level.
        script_status = {
            "path": "",
            "test_script_number": "",
            "status": StatusDefs.waiting,
            "details": "",
            "tests": []
        }
        return script_status

    @staticmethod
    def __create_plugin_info():
        plugin_info = {
            "group_name": "",
            "instructions": []
        }
        return plugin_info

    @staticmethod
    def __create_command_info():
        command_info = {
            "name": "",
            "description": "",
            "parameters": []
        }
        return command_info

    @staticmethod
    def __create_parameter_info():
        parameter_info = {
            "name": "",
            "description": "",
            "type": ""
        }
        return parameter_info
