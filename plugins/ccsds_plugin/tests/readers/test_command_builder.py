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

import pytest

from plugins.ccsds_plugin.readers.command_builder import CommandArg, CommandCode, CommandMessage, populate_arg, \
    populate_command_code, populate_message


def test_commandarg_class():
    """
    Test CommandArg class
    """
    arg = CommandArg(None, None)
    arg['name'] = 'Value'
    arg['data_type'] = 'uint8'
    arg.array_size = '0'
    arg.bit_length = '1'

    with pytest.raises(AttributeError):
        type_check = arg.data_type_fake

    assert 'name' in arg
    assert 'data_type' in arg
    assert arg.data_type == 'uint8'

    arg.pop('bit_length')
    del arg['array_size']
    del arg.data_type

    with pytest.raises(AttributeError):
        del arg.data_type_fake

    assert 'array_size' not in arg
    assert 'bit_length' not in arg


def test_commandcode_class():
    """
    Test CommandCode class
    """
    cmd_code = CommandCode(None, None)
    assert not cmd_code.args
    cmd_code['cc_name'] = 'CI_NOOP_CC'
    cmd_code['cc_value'] = '0'
    cmd_code['cc_data_type'] = 'CI_NoArgsCmd_t'

    with pytest.raises(AttributeError):
        type_check = cmd_code.data_type_fake

    assert 'cc_name' in cmd_code
    assert 'cc_value' in cmd_code

    with pytest.raises(AttributeError):
        del cmd_code.data_type_fake

    del cmd_code.cc_name
    assert 'cc_name' not in cmd_code


def test_commandmessage_class():
    """
    Test CommandMessage class
    """
    cmd_msg = CommandMessage()
    cmd_msg['cmd_data_type'] = 'CFE_ES_NoargsCmd_t'
    cmd_msg['cmd_mid_name'] = 'CFE_ES_SEND_HK_MID'
    cmd_msg['cmd_description'] = ''
    cmd_msg['command_codes'].append({'cc_name': '', 'cc_value': 0, 'args': []})

    with pytest.raises(AttributeError):
        type_check = cmd_msg.data_type_fake
    assert cmd_msg.cmd_mid_name == 'CFE_ES_SEND_HK_MID'

    with pytest.raises(AttributeError):
        del cmd_msg.data_type_fake
    del cmd_msg.cmd_mid_name


def test_populate_arg():
    """
    Test populate_arg function: Helper function to construct a CommandArg object
    """
    arg_dict = {'name': 'Param', 'description': '', 'array_size': '16', 'data_type': 'char',
                'bit_length': '0', 'parameters': []}
    cmd_arg = populate_arg(arg_dict)
    assert 'name' in cmd_arg
    assert 'data_type' in cmd_arg
    assert 'description' in cmd_arg
    assert 'array_size' in cmd_arg
    assert 'bit_length' in cmd_arg
    assert 'parameters' in cmd_arg

    assert cmd_arg.name == 'Param'
    assert cmd_arg.data_type == 'char'
    assert cmd_arg.description == ''
    assert cmd_arg.array_size == '16'
    assert cmd_arg.bit_length == '0'
    assert cmd_arg.parameters == []

    cmd_arg = populate_arg({})
    assert cmd_arg.name is None
    assert cmd_arg.data_type is None

    arg_dict = {'name': 'Param', 'description': 'fake args', 'enumeration': ['a', 'b', 'c']}
    cmd_arg = populate_arg(arg_dict)
    assert cmd_arg.name == 'Param'


def test_populate_command_code():
    """
    Test populate_command_code function:  Helper function to construct a CommandCode object
    """
    cmd_code_dict = {'cc_name': 'CTF_TEST_CC', 'cc_value': '11', 'cc_description': '',
                     'cc_data_type': 'CTF_TestParam_t',
                     'cc_parameters': [{'name': 'Param', 'description': '', 'array_size': '16',
                                        'data_type': 'char', 'bit_length': '0',
                                        'parameters': []
                                        }]
                     }
    cmd_code = populate_command_code(cmd_code_dict)

    assert 'cc_name' in cmd_code
    assert 'cc_value' in cmd_code
    assert 'cc_description' in cmd_code
    assert 'cc_data_type' in cmd_code
    assert 'args' in cmd_code

    assert cmd_code['cc_name'] == 'CTF_TEST_CC'
    assert cmd_code['cc_value'] == '11'
    assert cmd_code['cc_description'] == ''
    assert cmd_code['cc_data_type'] == 'CTF_TestParam_t'
    assert cmd_code['args'][0]['name'] == 'Param'


def test_populate_message():
    """
    Test populate_message function:
    Helper function to construct a CommandMessage object, populating the message
    with the respective command codes and arguments.
    """
    msg_dict = {'cmd_mid_name': 'CTF_TEST_CMD_MID', 'cmd_description': '', 'cmd_data_type': 'CTF_TestCmd_t',
                'cmd_parameters': [{"name": "Trans", "description": "", "array_size": "64",
                                    "data_type": "char", "bit_length": "0", "parameters": []
                                    }]}
    msg = populate_message(msg_dict)

    assert 'cmd_mid_name' in msg
    assert 'cmd_description' in msg
    assert 'cmd_data_type' in msg
    assert 'command_codes' in msg

    assert msg['cmd_mid_name'] == 'CTF_TEST_CMD_MID'
    assert msg['cmd_description'] == ''
    assert msg['cmd_data_type'] == 'CTF_TestCmd_t'
    assert msg['command_codes'][0]['args'][0]['name'] == 'Trans'


def test_populate_message_cmd_codes():
    msg_dict = {"cmd_mid_name": "CI_CMD_MID", "cmd_description": "",
                "cmd_codes": [{"cc_name": "CI_NOOP_CC", "cc_value": "0", "cc_description": "",
                               "cc_data_type": "CI_NoArgsCmd_t", "cc_parameters": []
                               }]}

    msg = populate_message(msg_dict)

    assert msg['cmd_mid_name'] == 'CI_CMD_MID'
    assert msg['cmd_description'] == ''
    assert msg['command_codes'][0]['cc_name'] == 'CI_NOOP_CC'
