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

"""
ccsds_v1.py: Implementation of the CCSDS v1 message types used by CFE.
"""


import ctypes

from plugins.ccsds_plugin.ccsds_packet_interface import CcsdsPacketInterface
from plugins.ccsds_plugin.ccsds_primary_header import CcsdsPrimaryHeaderBase
from plugins.ccsds_plugin.cfe.ccsds_secondary_header import CcsdsSecondaryCmdHeader, CcsdsSecondaryTlmHeader

APP_ID_MASK = 0x07FF
CFE_SB_CMD_MESSAGE_TYPE = 0x00000080


class CcsdsV1PrimaryHeader(CcsdsPrimaryHeaderBase):
    pass


class CcsdsV1Packet(CcsdsPacketInterface):
    def set_msg_id(self, msg_id: int) -> None:
        self.pheader.set_ccsds_version(0)

        packet_type = (msg_id & CFE_SB_CMD_MESSAGE_TYPE) >> 7
        self.pheader.set_packet_type(packet_type)

        app_id = ctypes.c_uint16(msg_id).value & APP_ID_MASK
        self.pheader.set_app_id(app_id)

    def get_msg_id(self) -> int:
        return (self.pheader.version_number << 15) + (self.pheader.type << 12) + \
               (self.pheader.secondary_header_flag << 11) + self.pheader.app_id

    def has_secondary_header(self) -> bool:
        return self.pheader.secondary_header_flag

    def get_function_code(self) -> int:
        if isinstance(self, CcsdsV1CmdPacket):
            return self.sheader.get_function_code()
        raise TypeError("Function code is only supported in a command packet")

    def set_function_code(self, function_code: int) -> None:
        if isinstance(self, CcsdsV1CmdPacket):
            self.sheader.set_function_code(function_code)
        else:
            raise TypeError("Function code is only supported in a command packet")

    def set_checksum(self, checksum: int) -> None:
        self.sheader.set_checksum(checksum)


class CcsdsV1CmdPacket(CcsdsV1Packet):
    _pack_ = 1
    _fields_ = [
        ("pheader", CcsdsV1PrimaryHeader),
        ("sheader", CcsdsSecondaryCmdHeader)
    ]

    def __init__(self, mid, command_code, payload_length, endian=0, sequence_count=0):
        super().__init__()
        # Packet Length = Complete Packet Length - 7 (Per CCSDS Definition)
        packet_length = payload_length + ctypes.sizeof(self) - 7

        # Set Msg Id
        self.set_msg_id(mid)

        # Set Additional Primary Header Properties
        self.pheader.set_segmentation_flags(3)
        self.pheader.set_secondary_header_flag(1)
        self.pheader.set_sequence_count(sequence_count)
        self.pheader.set_packet_length(packet_length)

        # Set Secondary Header Properties
        self.set_function_code(command_code)
        self.set_checksum(command_code)


class CcsdsV1TlmPacket(CcsdsV1Packet):
    _pack_ = 1
    _fields_ = [
        ("pheader", CcsdsV1PrimaryHeader),
        ("sheader", CcsdsSecondaryTlmHeader)
    ]


CcsdsPrimaryHeader = CcsdsV1PrimaryHeader
CcsdsCommand = CcsdsV1CmdPacket
CcsdsTelemetry = CcsdsV1TlmPacket
