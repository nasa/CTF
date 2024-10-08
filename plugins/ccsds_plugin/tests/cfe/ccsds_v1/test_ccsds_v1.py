# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2024 United States Government as represented by the
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

from plugins.ccsds_plugin.cfe.ccsds_v1.ccsds_v1 import CcsdsV1Packet, CcsdsV1CmdPacket, CcsdsV1TlmPacket


@pytest.fixture(name="ccsds_v1_packet")
def _ccsds_v1_packet_instance():
    return CcsdsV1Packet()


@pytest.fixture(name="ccsds_v1_cmd_packet")
def _ccsds_v1_cmd_packet_instance():
    return CcsdsV1CmdPacket(mid=10, command_code=1, payload_length=20)


@pytest.fixture(name="ccsds_v1_tel_packet")
def _ccsds_v1_tel_packet_instance():
    return CcsdsV1TlmPacket()


def test_ccsds_v1_packet_constructor(ccsds_v1_packet):
    """
    Test CcsdsV1Packet constructor
    """
    assert ccsds_v1_packet.pheader.segmentation_flags == 0
    assert ccsds_v1_packet.pheader.secondary_header_flag == 0
    assert ccsds_v1_packet.pheader.sequence_count == 0
    assert ccsds_v1_packet.pheader.length == 0


def test_ccsds_v1_packet_get_sequence_count(ccsds_v1_packet):
    """
    Test CcsdsV1Packet method: get_sequence_count
    Convenience method to get sequence_count from the packet header
    """
    assert ccsds_v1_packet.get_sequence_count() == 0


def test_ccsds_v1_packet_set_msg_id(ccsds_v1_packet):
    """
    Test CcsdsV1Packet method: set_msg_id
    Convenience method to set the message ID on the packet
    """
    ccsds_v1_packet.set_msg_id(98)
    assert ccsds_v1_packet.pheader.version_number == 0


def test_ccsds_v1_packet_get_msg_id(ccsds_v1_packet):
    """
    Test CcsdsV1Packet method: get_msg_id
    Convenience method to get the message ID from the packet
    """
    # maybe a bug here  packet_type = (msg_id & CFE_SB_CMD_MESSAGE_TYPE) >> 7
    # check default msg id constructed from pheader
    assert ccsds_v1_packet.get_msg_id() == 0
    ccsds_v1_packet.set_msg_id(58)
    assert ccsds_v1_packet.get_msg_id() == 58


def test_ccsds_v1_packet_has_secondary_header(ccsds_v1_packet):
    """
    Test CcsdsV1Packet method: has_secondary_header
    Convenience method to check for the presence of a secondary header
     """
    assert not ccsds_v1_packet.has_secondary_header()
    ccsds_v1_packet.pheader.set_secondary_header_flag(1)
    assert ccsds_v1_packet.has_secondary_header()


def test_ccsds_v1_cmd_packet_set_function_code(ccsds_v1_cmd_packet):
    """
    Test CcsdsV1CmdPacket method: set_function_code
    Convenience method to set the function code on the packet
    """
    assert ccsds_v1_cmd_packet.set_function_code(10) is None


def test_ccsds_v1_cmd_packet_get_function_code(ccsds_v1_cmd_packet):
    """
    Test CcsdsV1CmdPacket method: get_function_code
    Convenience method to get the function code from the packet
    """
    ccsds_v1_cmd_packet.set_function_code(16)
    assert ccsds_v1_cmd_packet.get_function_code() == 16
    ccsds_v1_cmd_packet.set_function_code(10)
    assert ccsds_v1_cmd_packet.get_function_code() == 10
    assert ccsds_v1_cmd_packet.validate(bytearray([1, 2, 3, 4]))


def test_ccsds_v1_cmd_packet_validate(ccsds_v1_cmd_packet):
    """
    Test CcsdsV1CmdPacket method: get_function_code
    Packet validation is not supported in open source release
    """
    assert ccsds_v1_cmd_packet.validate(None)


def test_ccsds_v1_cmd_packet_get_crc_flag(ccsds_v1_cmd_packet):
    """
    Test CcsdsV1CmdPacket method: get_function_code
    Get the header crc flag: CRC is not supported in open source release CcsdsV1Packet
    """
    assert ccsds_v1_cmd_packet.get_crc_flag() == 0


def test_ccsds_v1_tel_get_timestamp_seconds(ccsds_v1_tel_packet):
    """
    Test CcsdsV1TlmPacket method: get_timestamp_seconds
    """
    assert ccsds_v1_tel_packet.sheader.timestamp_seconds == 0
    ccsds_v1_tel_packet.sheader.timestamp_seconds = 4294967295
    assert ccsds_v1_tel_packet.get_timestamp_seconds() == 4294967295
    ccsds_v1_tel_packet.sheader.timestamp_seconds = 65535
    assert ccsds_v1_tel_packet.get_timestamp_seconds() == 65535


def test_ccsds_v1_tel_get_timestamp_subseconds(ccsds_v1_tel_packet):
    """
    Test CcsdsV1TlmPacket method: get_timestamp_subseconds
    """
    assert ccsds_v1_tel_packet.sheader.timestamp_subseconds == 0
    ccsds_v1_tel_packet.sheader.timestamp_subseconds = 65535
    assert ccsds_v1_tel_packet.get_timestamp_subseconds() == 65535
    ccsds_v1_tel_packet.sheader.timestamp_subseconds = 255
    assert ccsds_v1_tel_packet.get_timestamp_subseconds() == 255
