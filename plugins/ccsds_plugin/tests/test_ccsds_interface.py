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

from plugins.ccsds_plugin.readers.ccdd_export_reader import CCDDExportReader
from plugins.cfs.cfs_config import CfsConfig


def test_cccsds_interface_init(ccsdsinterface_instance):
    """
    Test CCSDSInterface class constructor
    """
    assert not ccsdsinterface_instance.mids
    assert not ccsdsinterface_instance.mid_map
    assert not ccsdsinterface_instance.enum_map


def test_cccsds_interface_get_ccsds_messages_from_dir(ccsdsinterface_instance):
    """
    Test CCSDSInterface class get_ccsds_messages_from_dir method: Virtual function to be implemented by a reader
    """
    assert ccsdsinterface_instance.get_ccsds_messages_from_dir(directory=None) is None


def test_cccsds_interface_add_enumeration(ccsdsinterface_instance):
    """
    Test CCSDSInterface class add_enumeration method:  Adds an enumeration definition to the internal types
    """
    ccsdsinterface_instance.add_enumeration(key='CS_ENABLE_OS_CC', value=10)
    ccsdsinterface_instance.add_enumeration(key='CS_DISABLE_OS_CC', value=11)
    assert 'CS_ENABLE_OS_CC' in ccsdsinterface_instance.enum_map
    assert 'CS_DISABLE_OS_CC' in ccsdsinterface_instance.enum_map
    assert ccsdsinterface_instance.enum_map['CS_ENABLE_OS_CC'] == 10
    assert ccsdsinterface_instance.enum_map['CS_DISABLE_OS_CC'] == 11

    ccsdsinterface_instance.add_enumeration(key='CS_DISABLE_OS_CC', value=-11)
    assert ccsdsinterface_instance.enum_map['CS_DISABLE_OS_CC'] == -11


def test_cccsds_interface_add_cmd_msg(ccsdsinterface_instance):
    """
    Test CCSDSInterface class add_cmd_msg method: Adds a command message to the internal types
    """

    config = CfsConfig('cfs')
    reader = CCDDExportReader(config)
    cmd_code = {'cc_name': '', 'cc_value': 0, 'args': []}
    [cls, _] = reader._create_parameterized_type(cmd_code, type_id="cc_data_type", arg_id="args")
    command_codes = {cmd_code['cc_name']: {"CODE": 0, "ARG_CLASS": cls}}

    assert 'SCH_TT_SEND_HK_MID' not in ccsdsinterface_instance.enum_map

    assert 'SCH_TT_SEND_HK_MID' not in ccsdsinterface_instance.mid_map

    ccsdsinterface_instance.add_cmd_msg(mid_name='SCH_TT_SEND_HK_MID', mid=10981, command_code_map=command_codes,
                                        command_enums=None)

    assert 'SCH_TT_SEND_HK_MID' in ccsdsinterface_instance.enum_map

    assert ccsdsinterface_instance.enum_map['SCH_TT_SEND_HK_MID'] == 10981

    assert 'SCH_TT_SEND_HK_MID' in ccsdsinterface_instance.mid_map

    assert ccsdsinterface_instance.mid_map['SCH_TT_SEND_HK_MID']['MID'] == 10981


def test_cccsds_interface_add_cmd_msg_with_command_enums(ccsdsinterface_instance):
    """
    Test CCSDSInterface class add_cmd_msg method
    Adds a command message to the internal types,command_enums argument is not None
    """

    config = CfsConfig('cfs')
    reader = CCDDExportReader(config)
    cmd_code = {'cc_name': '', 'cc_value': 0, 'args': []}
    [cls, _] = reader._create_parameterized_type(cmd_code, type_id="cc_data_type", arg_id="args")
    command_codes = {cmd_code['cc_name']: {"CODE": 0, "ARG_CLASS": cls}}

    command_enums = {'FAKE_MID': 98765}
    assert 'SCH_TT_SEND_HK_MID' not in ccsdsinterface_instance.enum_map

    assert 'FAKE_MID' not in ccsdsinterface_instance.enum_map

    ccsdsinterface_instance.add_cmd_msg(mid_name='SCH_TT_SEND_HK_MID', mid=10981, command_code_map=command_codes,
                                        command_enums=command_enums)

    assert 'SCH_TT_SEND_HK_MID' in ccsdsinterface_instance.enum_map

    assert 'FAKE_MID' in ccsdsinterface_instance.enum_map

    assert ccsdsinterface_instance.enum_map['SCH_TT_SEND_HK_MID'] == 10981

    assert ccsdsinterface_instance.enum_map['FAKE_MID'] == 98765


def test_cccsds_interface_add_telem_msg(ccsdsinterface_instance):
    """
    Test CCSDSInterface class add_telem_msg: Adds a telemetry message to the internal types
    """

    config = CfsConfig('cfs')
    reader = CCDDExportReader(config)
    json_dict = {'tlm_mid_name': 'CI_OUT_DATA_MID', 'tlm_description': '', 'tlm_data_type': 'CI_OutData_t',
                 'tlm_parameters': []}

    param_class, _ = reader._create_parameterized_type(json_dict,
                                                                 type_id="tlm_data_type",
                                                                 arg_id="tlm_parameters")
    tlm_enums = {'FAKE_MID': 98765}

    assert 'CI_OUT_DATA_MID' not in ccsdsinterface_instance.enum_map

    assert 'FAKE_MID' not in ccsdsinterface_instance.enum_map

    assert 'CI_OUT_DATA_MID' not in ccsdsinterface_instance.mid_map

    ccsdsinterface_instance.add_telem_msg(mid_name = 'CI_OUT_DATA_MID', mid= 10757, name='CI_OutData_t',
                                          parameters=param_class, parameter_enums=tlm_enums)

    assert 'CI_OUT_DATA_MID' in ccsdsinterface_instance.enum_map

    assert 'FAKE_MID' in ccsdsinterface_instance.enum_map

    assert 'CI_OUT_DATA_MID' in ccsdsinterface_instance.mid_map

    assert ccsdsinterface_instance.enum_map['CI_OUT_DATA_MID'] == 10757

    assert ccsdsinterface_instance.enum_map['FAKE_MID'] == 98765

    assert ccsdsinterface_instance.mid_map['CI_OUT_DATA_MID']['MID'] == 10757


def test_cccsds_interface_add_telem_msg_with_parameter_enums(ccsdsinterface_instance):
    """
    Test CCSDSInterface class add_telem_msg
    Adds a telemetry message to the internal types, parameter_enums argument is not None
    """

    config = CfsConfig('cfs')
    reader = CCDDExportReader(config)
    json_dict = {'tlm_mid_name': 'CI_OUT_DATA_MID', 'tlm_description': '', 'tlm_data_type': 'CI_OutData_t',
                 'tlm_parameters': []}

    param_class, param_enums = reader._create_parameterized_type(json_dict,
                                                                 type_id="tlm_data_type",
                                                                 arg_id="tlm_parameters")

    assert 'CI_OUT_DATA_MID' not in ccsdsinterface_instance.enum_map

    assert 'CI_OUT_DATA_MID' not in ccsdsinterface_instance.mid_map

    ccsdsinterface_instance.add_telem_msg(mid_name = 'CI_OUT_DATA_MID', mid= 10757, name='CI_OutData_t',
                                          parameters=param_class, parameter_enums=param_enums)

    assert 'CI_OUT_DATA_MID' in ccsdsinterface_instance.enum_map

    assert 'CI_OUT_DATA_MID' in ccsdsinterface_instance.mid_map

    assert ccsdsinterface_instance.enum_map['CI_OUT_DATA_MID'] == 10757

    assert ccsdsinterface_instance.mid_map['CI_OUT_DATA_MID']['MID'] == 10757
