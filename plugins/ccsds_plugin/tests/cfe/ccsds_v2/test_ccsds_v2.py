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

from plugins.ccsds_plugin.cfe.ccsds_v2.ccsds_v2 import CcsdsV2Packet, CcsdsV2CmdPacket, CcsdsV2ExtendedHeader


@pytest.fixture(name="ccsds_v2_packet")
def _ccsds_v2_packet_instance():
    return CcsdsV2Packet()


@pytest.fixture(name="ccsds_v2_cmd_packet")
def _ccsds_v2_cmd_packet_instance():
    return CcsdsV2CmdPacket(mid=10891, command_code=2, payload_length=24)


@pytest.fixture(name="ccsds_v2_extended_header")
def _ccsds_v2_extended_header_instance():
    return CcsdsV2ExtendedHeader()


def test_v2_extended_header(ccsds_v2_extended_header):
    """
    Test  CcsdsV2ExtendedHeader class constructor: assign attributes default values
    """
    assert ccsds_v2_extended_header.eds_version == 0
    assert ccsds_v2_extended_header.endian == 0
    assert ccsds_v2_extended_header.playback_flag == 0
    assert ccsds_v2_extended_header.playback_flag == 0
    assert ccsds_v2_extended_header.subsystem_id == 0
    assert ccsds_v2_extended_header.system_id == 0


def test_v2_extended_header_set_eds_version(ccsds_v2_extended_header):
    """
    Test  CcsdsV2ExtendedHeader class method: set_eds_version
    Convenience method to set the EDS version on the packet
    """
    ccsds_v2_extended_header.set_eds_version(23)
    assert ccsds_v2_extended_header.eds_version == 23

    with pytest.raises(TypeError):
        ccsds_v2_extended_header.set_eds_version(0.1)
    with pytest.raises(TypeError):
        ccsds_v2_extended_header.set_eds_version('0')
    # test ("eds_version", ctypes.c_uint16, 5) overflow
    ccsds_v2_extended_header.set_eds_version(33)
    assert ccsds_v2_extended_header.eds_version != 33


def test_v2_extended_header_set_endian(ccsds_v2_extended_header):
    """
    Test  CcsdsV2ExtendedHeader class method: set_endian
    Convenience method to set the endianness on the packet
    """
    ccsds_v2_extended_header.set_endian(1)
    assert ccsds_v2_extended_header.endian == 1

    with pytest.raises(TypeError):
        ccsds_v2_extended_header.set_endian(0.2)
    with pytest.raises(TypeError):
        ccsds_v2_extended_header.set_endian('0')
    # test ("endian", ctypes.c_uint16, 1) overflow
    ccsds_v2_extended_header.set_endian(3)
    assert ccsds_v2_extended_header.endian != 3


def test_v2_extended_header_set_playback_flag(ccsds_v2_extended_header):
    """
    Test  CcsdsV2ExtendedHeader class method: set_playback_flag
    Convenience method to set the playback flag on the packet
    """
    ccsds_v2_extended_header.set_playback_flag(1)
    assert ccsds_v2_extended_header.playback_flag == 1

    with pytest.raises(TypeError):
        ccsds_v2_extended_header.set_playback_flag(0.2)
    with pytest.raises(TypeError):
        ccsds_v2_extended_header.set_playback_flag('0')
    # test ("playback_flag", ctypes.c_uint16, 1) overflow
    ccsds_v2_extended_header.set_playback_flag(2)
    assert ccsds_v2_extended_header.playback_flag != 2


def test_v2_extended_header_set_subsystem_id(ccsds_v2_extended_header):
    """
    Test CcsdsV2ExtendedHeader class method: set_subsystem_id
    Convenience method to set the subsystem ID on the packet
    """
    ccsds_v2_extended_header.set_subsystem_id(1)
    assert ccsds_v2_extended_header.subsystem_id == 1

    with pytest.raises(TypeError):
        ccsds_v2_extended_header.set_subsystem_id(0.2)
    with pytest.raises(TypeError):
        ccsds_v2_extended_header.set_subsystem_id('0')
    # test ("subsystem_id", ctypes.c_uint16, 9) overflow
    ccsds_v2_extended_header.set_subsystem_id(1000)
    assert ccsds_v2_extended_header.subsystem_id != 1000


def test_v2_extended_header_set_system_id(ccsds_v2_extended_header):
    """
    Test CcsdsV2ExtendedHeader class method: set_system_id
    Convenience method to set the playback flag on the packet
    """
    ccsds_v2_extended_header.set_system_id(1)
    assert ccsds_v2_extended_header.system_id == 1

    with pytest.raises(TypeError):
        ccsds_v2_extended_header.set_system_id(0.2)
    with pytest.raises(TypeError):
        ccsds_v2_extended_header.set_system_id('0')

    ccsds_v2_extended_header.set_system_id(65535)
    assert ccsds_v2_extended_header.system_id == 65535

    # test ("system_id", ctypes.c_uint16, 16) overflow
    ccsds_v2_extended_header.set_system_id(65536)
    assert ccsds_v2_extended_header.system_id != 65536


def test_ccsds_v2_packet_set_msg_id(ccsds_v2_packet):
    """
    Test CcsdsV2Packet class method: set_msg_id
    Sets the message ID on the packet
    """
    # check the default msg id
    assert ccsds_v2_packet.get_msg_id() == 0

    ccsds_v2_packet.set_msg_id(8321)
    assert ccsds_v2_packet.pheader.app_id == 129
    assert ccsds_v2_packet.get_msg_id() == 8321


def test_ccsds_v2_packet_has_secondary_header(ccsds_v2_packet):
    """
    Test CcsdsV2Packet class method: has_secondary_header
    """
    assert ccsds_v2_packet.has_secondary_header() == 0
    ccsds_v2_packet.pheader.set_secondary_header_flag(1)
    assert ccsds_v2_packet.has_secondary_header() == 1


def test_ccsds_v2_packet_get_function_code(ccsds_v2_packet, utils):
    """
    Test CcsdsV2Packet class method: get_function_code
    """
    utils.clear_log()
    with pytest.raises(TypeError):
        ccsds_v2_packet.get_function_code()
        assert utils.has_log_level("ERROR")


def test_ccsds_v2_packet_set_function_code(ccsds_v2_packet, utils):
    """
    Test CcsdsV2Packet class method: set_function_code
    """
    utils.clear_log()
    with pytest.raises(TypeError):
        ccsds_v2_packet.set_function_code(100)
        assert utils.has_log_level("ERROR")


def test_ccsds_v2_cmd_packet_constructor(ccsds_v2_cmd_packet):
    """
    Test CcsdsV2CmdPacket class constructor
    """
    assert ccsds_v2_cmd_packet.pheader.segmentation_flags == 3
    assert ccsds_v2_cmd_packet.pheader.secondary_header_flag == 1
    assert ccsds_v2_cmd_packet.pheader.sequence_count == 0
    assert ccsds_v2_cmd_packet.pheader.length == 33
    assert ccsds_v2_cmd_packet.sheader.get_function_code() == 2
    assert ccsds_v2_cmd_packet.sheader.get_checksum() == 2


def test_ccsds_v2_cmd_packet_get_function_code(ccsds_v2_cmd_packet):
    """
    Test CcsdsV2CmdPacket class method: get_function_code & set_function_code
    """
    ccsds_v2_cmd_packet.get_function_code()
    ccsds_v2_cmd_packet.set_function_code(100)
