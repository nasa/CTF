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

import os
import ctypes
from unittest.mock import patch
import pytest

import lib
from lib.exceptions import CtfTestError
from plugins.ccsds_plugin.readers.ccdd_export_reader import CCDDExportReader, ctypes_name, \
    dynamic_init, create_type_class, to_string
from plugins.cfs.cfs_config import CfsConfig


@pytest.fixture(name="ccdd_export_reader")
def _ccdd_export_reader_instance():
    config = CfsConfig("cfs")
    return CCDDExportReader(config)


def test_func_ctypes_name():
    """
    Test function: ctypes_name
    Converts a Python type name to an equivalent ctypes type name by prepending 'c_' and stripping '_t'
    """
    assert ctypes_name('int') == 'c_int'
    assert ctypes_name('double') == 'c_double'
    assert ctypes_name('byte') == 'c_byte'


def test_func_create_type_class(utils):
    """
    Test function: create_type_class
    Dynamically creates types of a given name, supertype,
    and attributes with essential fields for the metaclass used by ctypes.
    """
    ctype_structure = ctypes.Structure
    data_type_name = 'CTF_TestCmd_t'
    data_type = create_type_class(data_type_name, ctype_structure, [])
    assert data_type.__str__ is to_string
    assert data_type.__init__ is dynamic_init
    type_1 = data_type()
    assert 'CTF_TestCmd_t' in str(type_1)
    utils.clear_log()

    with pytest.raises(Exception):
        create_type_class(data_type_name, "", [])
        assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_init(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class constructor
    """
    assert not ccdd_export_reader.type_dict
    assert ccdd_export_reader.current_file_name is None
    assert ccdd_export_reader.ctype_structure is ctypes.LittleEndianStructure

    config = CfsConfig("cfs")
    config.endianess_of_target = 'big'
    reader = CCDDExportReader(config)
    assert reader.ctype_structure is ctypes.BigEndianStructure

    utils.clear_log()
    config.endianess_of_target = 'none'
    reader = CCDDExportReader(config)
    assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_validate_json_schema(utils):
    """
    Test CCDDExportReader class static method: validate_json_schema
    Validates a dictionary of JSON data against a schema file
    """
    utils.clear_log()
    CCDDExportReader.validate_json_schema({}, "./schema")
    assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_process_command_invalid_file(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_command -- input is invalid json file
    Parses the contents of a JSON dictionary for a CCSDS command message to dynamically create a new type for each
    command code which is added to the type dictionary. Defines a command message with the MID and command codes,
    and an enumeration for each command code by name.
    """
    utils.clear_log()
    # json file has No cmd_mid_name
    json_dict = {'cmd_mid_nameXYZ': 'CTF_TEST_MID', 'cmd_description': '', 'cmd_data_type': 'CTF_NoArgsCmd_t',
                 'cmd_parameters': []}
    enum_map_len = len(ccdd_export_reader.enum_map)
    mid_map_len = len(ccdd_export_reader.mid_map)
    ccdd_export_reader.process_command(json_dict)
    assert utils.has_log_level("ERROR")
    # no new type is added
    assert enum_map_len == len(ccdd_export_reader.enum_map)
    assert mid_map_len == len(ccdd_export_reader.mid_map)


def test_ccdd_export_reader_process_command_exception(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_command -- raise exception
    Parses the contents of a JSON dictionary for a CCSDS command message to dynamically create a new type for each
    command code which is added to the type dictionary. Defines a command message with the MID and command codes,
    and an enumeration for each command code by name.
    """
    # json file has No cmd_mid_name
    json_dict = {'cmd_mid_name': 'CTF_TEST_MID', 'cmd_description': '', 'cmd_data_type': 'CTF_NoArgsCmd_t',
                 'cmd_parameters': []}

    utils.clear_log()
    with patch('plugins.ccsds_plugin.readers.ccdd_export_reader.CCDDExportReader._create_parameterized_type') \
            as mock_create:
        mock_create.side_effect = CtfTestError('Mock _create_parameterized_type')
        with pytest.raises(CtfTestError):
            enum_map_len = len(ccdd_export_reader.enum_map)
            mid_map_len = len(ccdd_export_reader.mid_map)
            ccdd_export_reader.process_command(json_dict)
        assert utils.has_log_level("ERROR")
        # no new type is added
        assert enum_map_len == len(ccdd_export_reader.enum_map)
        assert mid_map_len == len(ccdd_export_reader.mid_map)

        json_dict = {
            "cmd_mid_name": "INVALID_CMD_MID", "cmd_codes":
            [{"cc_name": "INVALID", "cc_value": "0", "cc_data_type": "INVALID", "cc_parameters": []}]
        }
        utils.clear_log()
        with pytest.raises(CtfTestError):
            enum_map_len = len(ccdd_export_reader.enum_map)
            mid_map_len = len(ccdd_export_reader.mid_map)
            ccdd_export_reader.process_command(json_dict)
        assert utils.has_log_level("ERROR")
        # no new type is added
        assert enum_map_len == len(ccdd_export_reader.enum_map)
        assert mid_map_len == len(ccdd_export_reader.mid_map)


def test_ccdd_export_reader_process_command(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_command
    Parses the contents of a JSON dictionary for a CCSDS command message to dynamically create a new type for each
    command code which is added to the type dictionary. Defines a command message with the MID and command codes,
    and an enumeration for each command code by name.
    """
    # json file has No cmd_mid_name
    json_dict = {'cmd_mid_name': 'CFE_SB_SUB_RPT_CTRL_MID', 'cmd_description': '',
                 'cmd_codes': [{'cc_name': 'CFE_SB_ENABLE_SUB_REPORTING_CC', 'cc_value': '9', 'cc_description': '',
                                'cc_data_type': 'CFE_SB_CmdHdr_t',
                                'cc_parameters': []},
                               {'cc_name': 'CFE_SB_DISABLE_SUB_REPORTING_CC', 'cc_value': '10', 'cc_description': '',
                                'cc_data_type': 'CFE_SB_CmdHdr_t', 'cc_parameters': []},
                               {'cc_name': 'CFE_SB_SEND_PREV_SUBS_CC', 'cc_value': '11', 'cc_description': '',
                                'cc_data_type': 'CFE_SB_CmdHdr_t', 'cc_parameters': []}
                               ]
                 }
    # process command without mids code
    utils.clear_log()
    assert 'CFE_SB_SUB_RPT_CTRL_MID' not in ccdd_export_reader.enum_map
    ccdd_export_reader.process_command(json_dict)
    assert utils.has_log_level("WARNING")
    assert 'CFE_SB_SUB_RPT_CTRL_MID' not in ccdd_export_reader.enum_map

    # process command with mids code
    ccdd_export_reader.mids['CFE_SB_SUB_RPT_CTRL_MID'] = 8327
    assert 'CFE_SB_SUB_RPT_CTRL_MID' not in ccdd_export_reader.enum_map
    ccdd_export_reader.process_command(json_dict)
    assert 'CFE_SB_SUB_RPT_CTRL_MID' in ccdd_export_reader.enum_map


def test_ccdd_export_reader_process_command_no_cc(ccdd_export_reader, utils):
    json_dict = {
        "cmd_mid_name": "HK_SEND_COMBINED_PKT_MID",
        "cmd_description": "",
        "cmd_data_type": "HK_Send_Out_Msg_t",
        "cmd_parameters": [
            {
                "name": "OutMsgToSend",
                "description": "MsgId #CFE_SB_MsgId_t of combined tlm pkt to send",
                "array_size": "0",
                "data_type": "CFE_SB_MsgId_t",
                "bit_length": "0",
                "parameters": []
            }
        ]
    }
    assert "HK_SEND_COMBINED_PKT_MID" not in ccdd_export_reader.enum_map
    ccdd_export_reader.mids['HK_SEND_COMBINED_PKT_MID'] = 1234
    ccdd_export_reader.process_command(json_dict)
    assert "HK_SEND_COMBINED_PKT_MID" in ccdd_export_reader.enum_map
    assert ccdd_export_reader.mid_map["HK_SEND_COMBINED_PKT_MID"]["CC"][""]["CODE"] == 0


def test_ccdd_export_reader_build_data_type_and_field_existing_type(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: _build_data_type_and_field -- with existing type
    Builds a field, containing a simple data type, for a custom type. Returns the data type and appends it to fields.
    """
    param = {'name': 'Value', 'data_type': 'uint8', 'description': '0=all, 1=cmd, 2=fault 3=up 4=down',
             'array_size': '0', 'bit_length': '0', 'parameters': []}
    fields = []
    ccdd_export_reader.type_dict['Value'] = 'Mock'
    utils.clear_log()
    assert ccdd_export_reader._build_data_type_and_field(param, fields) is None
    assert utils.has_log_level("WARNING")


def test_ccdd_export_reader_build_data_type_and_field_multiply(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: _build_data_type_and_field
    Builds a field, containing a simple data type, for a custom type. Returns the data type and appends it to fields.
    """
    param = {'name': 'Value', 'data_type': 'uint8', 'description': '0=all, 1=cmd, 2=fault 3=up 4=down',
             'array_size': 'TRUE', 'bit_length': '0', 'parameters': []}
    fields = []
    ccdd_export_reader.type_dict = {'int32': ctypes.c_int32, 'int64': ctypes.c_int64,
                                    'uint8': ctypes.c_ubyte, 'TRUE': 1}
    assert ccdd_export_reader._build_data_type_and_field(param, fields)  is ctypes.c_ubyte * 1


def test_ccdd_export_reader_build_data_type_and_field_type_in_subtype(ccdd_export_reader):
    """
    Test CCDDExportReader class method: _build_data_type_and_field -- data type is already in subtype
    Builds a field, containing a simple data type, for a custom type. Returns the data type and appends it to fields.
    """
    param = {'name': 'Payload', 'data_type': 'CFE_ES_RestartCmd_Payload_t', 'description': '', 'array_size': '0',
             'bit_length': '0',
             'parameters': [{'name': 'RestartType',
                             'description': '#CFE_ES_PROCESSOR_RESET=Processor Reset ',
                             'array_size': '0', 'data_type': 'uint16', 'bit_length': '0', 'parameters': []
                             }
                            ]
             }
    fields = []
    subtypes = {'Payload': 'Mock_class'}
    assert ccdd_export_reader._build_data_type_and_field(param, fields, subtypes) == 'Mock_class'


def test_ccdd_export_reader_build_data_type_and_field_type_in_type_dict(ccdd_export_reader):
    """
    Test CCDDExportReader class method: _build_data_type_and_field -- data type is already in type_dict
    Builds a field, containing a simple data type, for a custom type. Returns the data type and appends it to fields.
    """
    param = {'name': 'ChildCurrentCC', 'description': 'Command code currently executing', 'array_size': '2',
             'data_type': 'uint8', 'bit_length': '2', 'parameters': []}
    fields = []
    subtypes = {}
    ccdd_export_reader.type_dict = {'int32': ctypes.c_int32, 'int64': ctypes.c_int64,
                                    'uint8': ctypes.c_ubyte}
    assert ccdd_export_reader._build_data_type_and_field(param, fields, subtypes) is ctypes.c_ubyte * 2


def test_ccdd_export_reader_build_data_type_and_field_error(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: _build_data_type_and_field -- array_size is invalid
    Builds a field, containing a simple data type, for a custom type. Returns the data type and appends it to fields.
    """
    param = {'name': 'ChildCurrentCC', 'description': 'Command code currently executing', 'array_size': 'error',
             'data_type': 'uint8', 'bit_length': '2', 'parameters': []}
    fields = []
    subtypes = {}
    ccdd_export_reader.type_dict = {'int32': ctypes.c_int32, 'int64': ctypes.c_int64,
                                    'uint8': ctypes.c_ubyte}
    utils.clear_log()
    assert ccdd_export_reader._build_data_type_and_field(param, fields, subtypes)
    assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_create_parameterized_type(ccdd_export_reader):
    """
    Test CCDDExportReader class method: _create_parameterized_type
    Recursively creates custom type definitions from JSON data and any known subtypes,
    and adds them to the type dictionary. Returns the top-level type and a dictionary of any enumerations.
    """
    type_dict = {'cc_name': 'CI_RESET_CC', 'cc_value': '1',
                 'args': [{'name': 'Byte', 'data_type': 'uint8', 'description': '0=all, 1=cmd, 2=fault 3=up 4=down',
                           'array_size': '0', 'bit_length': '0',
                           'parameters': []},
                          {'name': 'Spare', 'data_type': 'uint8', 'description': '', 'array_size': '3',
                           'enumeration': [{'label': 'mock_label', 'value': 'mock_value'}],
                           'bit_length': '0', 'parameters': []}],
                 'cc_description': '', 'cc_data_type': 'uint8'}
    type_id = 'cc_data_type'
    arg_id = 'args'
    subtypes = {}
    ccdd_export_reader.type_dict = {'uint8': ctypes.c_ubyte}
    parameterized_type = ccdd_export_reader._create_parameterized_type(type_dict, type_id, arg_id, subtypes)
    assert parameterized_type[0].__name__ == 'uint8'


def test_ccdd_export_reader_create_parameterized_type_exception(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: _create_parameterized_type -- corner cases (raise exception)
    Recursively creates custom type definitions from JSON data and any known subtypes,
    and adds them to the type dictionary. Returns the top-level type and a dictionary of any enumerations.
    """
    type_dict = {'cc_name': 'CI_RESET_CC', 'cc_value': '1',
                 'args': [{'name': 'Byte', 'data_type': 'uint8', 'description': '0=all, 1=cmd, 2=fault 3=up 4=down',
                           'array_size': '0', 'bit_length': '0',
                           'parameters': []},
                          {'name': 'Spare', 'data_type': 'uint8', 'description': '', 'array_size': '3',
                           'enumeration': [{'label': 'mock_label', 'value': 'mock_value'}],
                           'bit_length': '0', 'parameters': []}],
                 'cc_description': '', 'cc_data_type': 'CI_ResetCtrsCmd_t'}
    type_id = 'cc_data_type'
    arg_id = 'args'
    subtypes = {}
    utils.clear_log()

    # test case : create_type_class method raise the first exception
    with patch('plugins.ccsds_plugin.readers.ccdd_export_reader.create_type_class') as mock_create:
        mock_create.side_effect = CtfTestError('Mock create_type_class')
        with pytest.raises(CtfTestError):
            ccdd_export_reader._create_parameterized_type(type_dict, type_id, arg_id, subtypes)


def test_ccdd_export_reader_create_process_telemetry_exception(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_telemetry: corner case - raise exception
    Parses the contents of a JSON dictionary for a CCSDS telemetry message to dynamically create a new type
    which is added to the type dictionary. Defines a telemetry message with the MID, name, and type.
    """
    json_dict = {'tlm_mid_name_X': 'CFE_ES_SHELL_TLM_MID', 'tlm_description': '',
                 'tlm_data_type_X': 'CFE_ES_ShellTlm_t',
                 'tlm_parameters': [{'name': 'Payload', 'description': '', 'array_size': '0',
                                     'data_type': 'CFE_ES_ShellPacket_Payload_t', 'bit_length': '0',
                                     'parameters': [{'name': 'ShellOutput', 'description': 'ASCII text string contain',
                                                     'array_size': '64', 'data_type': 'char', 'bit_length': '0',
                                                     'parameters': []
                                                     }]
                                     }]
                 }
    utils.clear_log()
    with pytest.raises(CtfTestError):
        ccdd_export_reader.process_telemetry(json_dict)
        assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_create_process_telemetry_warning(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_telemetry: corner case - tlm_mid_name warning
    Parses the contents of a JSON dictionary for a CCSDS telemetry message to dynamically create a new type
    which is added to the type dictionary. Defines a telemetry message with the MID, name, and type.
    """
    utils.clear_log()
    json_dict = {'tlm_mid_name': 'CFE_ES_SHELL_TLM_MID', 'tlm_description': '', 'tlm_data_type': 'CFE_ES_ShellTlm_t',
                 'tlm_parameters': [{'name': 'Payload', 'description': '', 'array_size': '0',
                                     'data_type': 'CFE_ES_ShellPacket_Payload_t', 'bit_length': '0',
                                     'parameters': [{'name': 'ShellOutput', 'description': 'ASCII text string contain',
                                                     'array_size': '64', 'data_type': 'char', 'bit_length': '0',
                                                     'parameters': []
                                                     }]
                                     }]
                 }
    ccdd_export_reader.process_telemetry(json_dict)

    json_dict = {'tlm_mid_name_X': 'CFE_ES_SHELL_TLM_MID', 'tlm_description': '', 'tlm_data_type': 'CFE_ES_ShellTlm_t',
                 'tlm_parameters': [{'name': 'Payload', 'description': '', 'array_size': '0',
                                     'data_type': 'CFE_ES_ShellPacket_Payload_t', 'bit_length': '0',
                                     'parameters': [{'name': 'ShellOutput', 'description': 'ASCII text string contain',
                                                     'array_size': '64', 'data_type': 'char', 'bit_length': '0',
                                                     'parameters': []
                                                     }]
                                     }]
                 }
    ccdd_export_reader.process_telemetry(json_dict)
    assert utils.has_log_level("WARNING")


def test_ccdd_export_reader_process_types(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_types
    Parses the contents of a JSON dictionary for type macros, and inserts any aliases, constants, or MID
    mapping into the appropriate dictionaries.
    """
    utils.clear_log()
    assert len(ccdd_export_reader.type_dict) == 0
    json_list = [{'alias_name': 'int8', 'actual_name': 'c_int8'}, {'alias_name': 'int16', 'actual_name': 'c_int16'},
                 {'alias_name': 'int32', 'actual_name': 'c_int32'}, {'alias_name': 'int64', 'actual_name': 'c_int64'},
                 {'alias_name': 'uint8', 'actual_name': 'c_uint8'}, {'alias_name': 'uint16', 'actual_name': 'c_uint16'},
                 {'alias_name': 'uint32', 'actual_name': 'c_uint32'},
                 {'alias_name': 'uint64', 'actual_name': 'c_uint64'}, {'alias_name': 'float', 'actual_name': 'c_float'},
                 {'alias_name': 'double', 'actual_name': 'c_double'}, {'alias_name': 'char', 'actual_name': 'c_char'},
                 {'alias_name': 'string', 'actual_name': 'c_char'}, {'alias_name': 'bool', 'actual_name': 'c_uint8'},
                 {'alias_name': 'boolean', 'actual_name': 'c_uint8'},
                 {'alias_name': 'address', 'actual_name': 'c_voidp'},
                 {'alias_name': 'cpuaddr', 'actual_name': 'c_uint32'},
                 {'alias_name': 'CFE_SB_PipeId_t', 'actual_name': 'c_uint8'},
                 {'alias_name': 'CFE_SB_MsgId_t', 'actual_name': 'c_uint32'},
                 {'alias_name': 'CFE_SB_MsgId_Atom_t', 'actual_name': 'c_uint32'},
                 {'alias_name': 'CFE_SB_MsgRouteIdx_Atom_t', 'actual_name': 'c_uint16'},
                 {'alias_name': 'CFE_ES_MemHandle_t', 'actual_name': 'c_uint32'},
                 {'alias_name': 'CFE_EVS_LogMode_Enum_t', 'actual_name': 'c_uint8'},
                 {'alias_name': 'CFE_EVS_MsgFormat_Enum_t', 'actual_name': 'c_uint8'},
                 {'alias_name': 'CFE_TBL_Handle_t', 'actual_name': 'c_int16'},
                 {'alias_name': '_tblref_', 'actual_name': 'c_char'},
                 {'constant_name': 'TRUE', 'constant_value': '1'},
                 {'constant_name': 'FALSE', 'constant_value': 'abc1#'},
                 {'constant_name': 'CCSDS_TIME_SIZE', 'constant_value': '6'}]
    assert ccdd_export_reader.process_types(json_list) is None
    assert len(ccdd_export_reader.type_dict) == 28

    json_list.append({'alias_name_error': 'CFE_EVS_MsgFormat_Enum_t', 'actual_name': 'c_uint8'})
    ccdd_export_reader.process_types(json_list)
    assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_process_types_debug(ccdd_export_reader):
    """
    Test CCDDExportReader class method: process_types
    Parses the contents of a JSON dictionary for type macros, and inserts any aliases, constants, or MID
    mapping into the appropriate dictionaries.
    """
    assert len(ccdd_export_reader.type_dict) == 0
    json_list = [{'alias_name': 'mock_name', 'actual_name': 'mock'}, {'alias_name': 'int16', 'actual_name': 'c_int16'},
                 {'alias_name': 'int32', 'actual_name': 'c_int32'}, {'alias_name': 'int64', 'actual_name': 'c_int64'},
                 {'alias_name': 'FM_FreeSpaceTblPtr', 'actual_name': 'c_voidp'}]
    assert ccdd_export_reader.process_types(json_list) is None
    assert len(ccdd_export_reader.type_dict) == 4


def test_ccdd_export_reader_process_types_duplicated_mid_name(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_types
    Parses the contents of a JSON dictionary for type macros, and inserts any aliases, constants, or MID
    mapping into the appropriate dictionaries.
    """
    assert len(ccdd_export_reader.type_dict) == 0
    json_list = [{'target': 'set1', 'mids': [{'mid_name': 'CFE_ES_CMD_MID', 'mid_value': '0x2081'},
                                             {'mid_name': 'CFE_ES_SEND_HK_MID', 'mid_value': '0x2082'},
                                             {'mid_name': 'CFE_EVS_CMD_MID', 'mid_value': '0x2083'},
                                             {'mid_name': 'CFE_EVS_SEND_HK_MID', 'mid_value': '0x2084'},
                                             {'mid_name': 'CFE_SB_CMD_MID', 'mid_value': '0x2085'},
                                             {'mid_name': 'CFE_SB_CMD_MID', 'mid_value': '0x20859'},
                                             {'mid_name': 'CFE_ES_SHELL_TLM_MID', 'mid_value': '0x2002'},
                                             {'mid_name': 'CFE_ES_MEMSTATS_TLM_MID', 'mid_value': '0x2003'},
                                             ]}]
    utils.clear_log()
    ccdd_export_reader.process_types(json_list)
    assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_process_types_duplicated_mid_value(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_types
    Parses the contents of a JSON dictionary for type macros, and inserts any aliases, constants, or MID
    mapping into the appropriate dictionaries.
    """
    assert len(ccdd_export_reader.type_dict) == 0
    json_list = [{'target': 'set1', 'mids': [{'mid_name': 'CFE_ES_CMD_MID', 'mid_value': '0x2081'},
                                             {'mid_name': 'CFE_ES_SEND_HK_MID', 'mid_value': '0x2082'},
                                             {'mid_name': 'CFE_EVS_CMD_MID', 'mid_value': '0x2083'},
                                             {'mid_name': 'CFE_EVS_SEND_HK_MID', 'mid_value': '0x2084'},
                                             {'mid_name': 'CFE_SB_CMD_MID', 'mid_value': '0x2085'},
                                             {'mid_name': 'CFE_ES_SHELL_TLM_MID', 'mid_value': '0x2085'},
                                             {'mid_name': 'CFE_ES_MEMSTATS_TLM_MID', 'mid_value': '0x2003'},
                                             ]}]
    utils.clear_log()
    ccdd_export_reader.process_types(json_list)
    assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_process_types_exception(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_types  corner test case- raise exception
    Parses the contents of a JSON dictionary for type macros, and inserts any aliases, constants, or MID
    mapping into the appropriate dictionaries.
    """
    utils.clear_log()
    json_list = [{'alias_name': 'mock_name', 'actual_name': 'mock'}, {'alias_name': 'int16', 'actual_name': 'c_int16'},
                 {'alias_name': 'int32', 'actual_name': 'c_int32'}, {'alias_name': 'int64', 'actual_name': 'c_int64'},
                 {'alias_name': 'FM_FreeSpaceTblPtr', 'actual_name': 'c_voidp'}]

    with patch('lib.logger.logger.debug') as mock_exception:
        mock_exception.side_effect = CtfTestError('Mock function call')
        with pytest.raises(CtfTestError):
            ccdd_export_reader.process_types(json_list)
            assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_process_types_second_pass_exception(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_types_second_pass corner test case - raise exception
    Parses the contents of a JSON dictionary for type aliases only, and adds them to the type dictionary if they
    are not already defined.
    """
    utils.clear_log()
    json_list = [{'alias_name': 'int32', 'actual_name': 'c_int32'},
                 {'constant_name': 'TRUE', 'constant_value': '1'},
                 {'constant_name': 'FALSE', 'constant_value': '0'},
                 {'constant_name': 'CCSDS_TIME_SIZE', 'constant_value': '6'},
                 {'constant_name': 'CFE_ES_CDS_MAX_FULL_NAME_LEN', 'constant_value': '38'},
                 {'constant_name': 'CFE_ES_MAX_APPLICATIONS', 'constant_value': '32'},
                 {'constant_name': 'CFE_ES_MAX_MEMPOOL_BLOCK_SIZES', 'constant_value': '17'},
                 {'constant_name': 'CFE_ES_MAX_SHELL_CMD', 'constant_value': '64'},
                 {'constant_name': 'CFE_MISSION_ES_MAX_APPLICATIONS', 'constant_value': '16'},
                 {'constant_name': 'CFE_MISSION_EVS_MAX_MESSAGE_LENGTH', 'constant_value': '122'},
                 {'constant_name': 'CFE_MISSION_MAX_API_LEN', 'constant_value': '20'},
                 {'constant_name': 'CFE_MISSION_MAX_PATH_LEN', 'constant_value': '64'},
                 {'constant_name': 'CFE_MISSION_SB_MAX_PIPES', 'constant_value': '64'},
                 {'constant_name': 'CFE_SB_MAX_PIPES', 'constant_value': '64'},
                 {'constant_name': 'CFE_SB_TLM_HDR_SIZE', 'constant_value': '24'},
                 {'constant_name': 'CFE_TBL_MAX_FULL_NAME_LEN', 'constant_value': '40'}]

    with patch('lib.logger.logger.error') as mock_exception:
        mock_exception.side_effect = [CtfTestError('Mock function call'), lib.logger.logger.error]
        with pytest.raises(CtfTestError):
            ccdd_export_reader.process_types_second_pass(json_list)
            assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_process_types_second_pass_warnings(ccdd_export_reader):
    """
    Test CCDDExportReader class method: process_types_second_pass
    Parses the contents of a JSON dictionary for type aliases only, and adds them to the type dictionary if they
    are not already defined.
    """
    json_list = [{'alias_name': 'int32', 'actual_name': 'c_int32'},
                 {'constant_name': 'TRUE', 'constant_value': '1'}
                 ]
    ccdd_export_reader.type_dict['int32'] = 'c_int32'
    ccdd_export_reader.process_types_second_pass(json_list)

    ccdd_export_reader.type_dict.clear()
    ccdd_export_reader.type_dict['c_int32'] = ' '
    ccdd_export_reader.process_types_second_pass(json_list)


def test_ccdd_export_reader_process_custom_types(ccdd_export_reader):
    json_dict = {
        "data_type": "my_custom_type",
        "parameters": [{"name": "myArg", "data_type": "char", "parameters": []}]
    }
    ccdd_export_reader.process_custom_types(json_dict)
    assert "my_custom_type" in ccdd_export_reader.type_dict


def test_ccdd_export_reader_process_custom_types_errors(ccdd_export_reader):
    # invalid name key
    json_dict = {
        "cc_data_type": "my_custom_type",
        "parameters": [{"name": "myArg", "data_type": "char", "parameters": []}]
    }
    with pytest.raises(CtfTestError):
        ccdd_export_reader.process_custom_types(json_dict)
    assert "my_custom_type" not in ccdd_export_reader.type_dict

    # invalid parameter key
    json_dict = {
        "data_type": "my_custom_type",
        "cc_parameters": [{"name": "myArg", "data_type": "char", "parameters": []}]
    }
    with pytest.raises(CtfTestError):
        ccdd_export_reader.process_custom_types(json_dict)
    assert "my_custom_type" not in ccdd_export_reader.type_dict

    # exception during creation
    json_dict = {
        "data_type": "my_custom_type",
        "parameters": [{"name": "myArg", "data_type": "char", "parameters": []}]
    }
    with patch('plugins.ccsds_plugin.readers.ccdd_export_reader.CCDDExportReader._build_data_type_and_field') as mock:
        mock.side_effect = CtfTestError('Mock _build_data_type_and_field')
        with pytest.raises(CtfTestError):
            ccdd_export_reader.process_custom_types(json_dict)
        assert "my_custom_type" not in ccdd_export_reader.type_dict


def test_ccdd_export_reader_process_ccsds_json_file_invalid_file(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_ccsds_json_file  process invalid file
    Reads JSON from a single file and, if it matches the filter, parses the contents
    """
    utils.clear_log()
    config = CfsConfig('cfs')
    directory = config.ccsds_data_dir
    json_file = directory + '/auto_cfe_es_CMD.json'
    ccdd_export_reader.process_ccsds_json_file(json_file)
    json_file = directory + '/auto_ci_CMD.json'
    ccdd_export_reader.process_ccsds_json_file(json_file)
    invalid_file = directory + '/invalid.json'
    echo_cmd = "echo 'invalid file' >> {}".format(invalid_file)
    rm_cmd = "rm {}".format(invalid_file)
    os.system(echo_cmd)
    ccdd_export_reader.process_ccsds_json_file(invalid_file)
    os.system(rm_cmd)
    assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_process_ccsds_json_file_custom_types(ccdd_export_reader):
    """
    Test CCDDExportReader class method: process_ccsds_json_file  process custom_types json file
    Reads JSON from a single file and, if it matches the filter, parses the contents
    """
    config = CfsConfig('cfs')
    directory = config.ccsds_data_dir
    custom_types_file = directory + '/custom_types.json'
    with open(custom_types_file, 'w') as f:
        f.write(' {"data_type": 100} ')
    rm_cmd = "rm {}".format(custom_types_file)
    ccdd_export_reader.process_ccsds_json_file(custom_types_file)
    os.system(rm_cmd)


def test_ccdd_export_reader_process_ccsds_json_file_exception(ccdd_export_reader, utils):
    """
    Test CCDDExportReader class method: process_ccsds_json_file  raise exception
    Reads JSON from a single file and, if it matches the filter, parses the contents
    """
    utils.clear_log()
    config = CfsConfig('cfs')
    directory = config.ccsds_data_dir
    json_file = directory + '/auto_cfe_es_CMD.json'
    ccdd_export_reader.process_ccsds_json_file(json_file)

    with patch('plugins.ccsds_plugin.readers.ccdd_export_reader.CCDDExportReader.process_command') as mock_command:
        mock_command.side_effect = CtfTestError('Mock process_command')
        ccdd_export_reader.process_ccsds_json_file(json_file)
        assert utils.has_log_level("ERROR")


def test_ccdd_export_reader_process_ccsds_get_ccsds_messages_from_dir(ccdd_export_reader):
    """
    Test CCDDExportReader class method: get_ccsds_messages_from_dir
    Walks through a directory and parses CCSDS command and telemetry messages and type macros
    from the JSON, as appropriate. Creates and returns dictionaries mapping names to these constructs.
    """
    config = CfsConfig('cfs')
    directory = config.ccsds_data_dir
    mid_map, macro_map = ccdd_export_reader.get_ccsds_messages_from_dir(directory)
    assert len(mid_map) > 0
    assert len(macro_map) > 0
