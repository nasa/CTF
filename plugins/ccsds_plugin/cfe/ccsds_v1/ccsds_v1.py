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

"""
ccsds_v1.py: Implementation of the CCSDS v1 message types used by CFE.
"""


import ctypes

from plugins.ccsds_plugin.ccsds_packet_interface import CcsdsPacketInterface
from plugins.ccsds_plugin.cfe.ccsds_secondary_header import CcsdsSecondaryCmdHeader, CcsdsSecondaryTlmHeader
from plugins.ccsds_plugin.ccsds_primary_header import CcsdsPrimaryHeaderBase

APP_ID_MASK = 0x07FF
CFE_SB_CMD_MESSAGE_TYPE = 0x00000080


class CcsdsV1PrimaryHeader(CcsdsPrimaryHeaderBase):
    """This is a marker interface to indicate a CCSDS V1 primary header"""


class CcsdsV1Packet(CcsdsPacketInterface):
    """
    This class provides an interface to a CCSDS V1 packet
    """
    # pylint: disable=abstract-method
    _pack_ = 1
    _fields_ = [
        ("pheader", CcsdsV1PrimaryHeader)
    ]

    def set_msg_id(self, msg_id: int) -> None:
        """
        Convenience method to set the message ID on the packet

        @param msg_id: The message ID value
        """
        self.pheader.set_ccsds_version(0)

        packet_type = (msg_id & CFE_SB_CMD_MESSAGE_TYPE) >> 7
        self.pheader.set_packet_type(packet_type)

        app_id = ctypes.c_uint16(msg_id).value & APP_ID_MASK
        self.pheader.set_app_id(app_id)

    def get_msg_id(self) -> int:
        """Convenience method to get the message ID from the packet"""
        return (self.pheader.version_number << 15) + (self.pheader.type << 12) + \
               (self.pheader.secondary_header_flag << 11) + self.pheader.app_id

    def has_secondary_header(self) -> bool:
        """Convenience method to check for the presence of a secondary header"""
        return self.pheader.secondary_header_flag


class CcsdsV1CmdPacket(CcsdsV1Packet):
    """
    This class implements a CCSDS V1 command packet as represented by a ctypes BigEndianStructure
    """

    _pack_ = 1
    _fields_ = [
        ("sheader", CcsdsSecondaryCmdHeader)
    ]

    def __init__(self, mid, command_code, payload_length, sequence_count=0, **_: dict):
        super().__init__()
        # Packet Length = Complete Packet Length - 7 (Per CCSDS Definition)
        packet_length = payload_length + ctypes.sizeof(self) - 7

        # Set Msg Id
        self.set_msg_id(mid)

        # Set Additional Primary Header Properties
        self.pheader.set_secondary_header_flag(1)
        self.pheader.set_segmentation_flags(3)
        self.pheader.set_sequence_count(sequence_count)
        self.pheader.set_packet_length(packet_length)

        # Set Secondary Header Properties
        self.set_function_code(command_code)
        self.set_checksum(command_code)

    def get_function_code(self) -> int:
        """Convenience method to get the function code from the packet"""
        return self.sheader.get_function_code()

    def set_function_code(self, function_code: int) -> None:
        """
        Convenience method to set the function code on the packet

        @param function_code: The function code value
        """
        self.sheader.set_function_code(function_code)

    def set_checksum(self, checksum: int) -> None:
        """
        Convenience method to set the checksum on the packet

        @param checksum: The checksum value
        """
        self.sheader.set_checksum(checksum)


class CcsdsV1TlmPacket(CcsdsV1Packet):
    """
    This class implements a CCSDS V1 telemetry packet as represented by a ctypes BigEndianStructure
    """
    # pylint: disable=abstract-method

    _pack_ = 1
    _fields_ = [
        ("sheader", CcsdsSecondaryTlmHeader)
    ]


CcsdsPrimaryHeader = CcsdsV1PrimaryHeader
CcsdsCommand = CcsdsV1CmdPacket
CcsdsTelemetry = CcsdsV1TlmPacket
