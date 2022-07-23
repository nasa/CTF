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
ccsds_v2.py: Implementation of the CCSDS v2 message types used by CFE.
"""

import ctypes

from plugins.ccsds_plugin.ccsds_packet_interface import CcsdsPacketInterface
from plugins.ccsds_plugin.ccsds_primary_header import CcsdsPrimaryHeaderBase
from plugins.ccsds_plugin.cfe.ccsds_secondary_header import CcsdsSecondaryCmdHeader, CcsdsSecondaryTlmHeader

APP_ID_MASK = 0x07FF
CFE_SB_CMD_MESSAGE_TYPE = 0x00000080


class CcsdsV2ExtendedHeader(ctypes.BigEndianStructure):
    """
    This class implements a CCSDS V2 extended header as represented by a ctypes BigEndianStructure
    """

    _pack_ = 1
    _fields_ = [
        ("eds_version", ctypes.c_uint16, 5),  # EDS Version for packet definition used
        ("endian", ctypes.c_uint16, 1),  # Endian: Big = 0, Little = 1
        ("playback_flag", ctypes.c_uint16, 1),  # Playback flag 0 = original, 1 = playback
        ("subsystem_id", ctypes.c_uint16, 9),  # Subsystem ID (mission defined)
        ("system_id", ctypes.c_uint16, 16),  # System ID (mission defined)
    ]

    def __init__(self):
        """
        class CcsdsV2ExtendedHeader constructor: assign attributes default values
        """
        super().__init__()
        self.eds_version = 0
        self.endian = 0
        self.playback_flag = 0
        self.subsystem_id = 0
        self.system_id = 0

    def set_eds_version(self, version: int) -> None:
        """
        Convenience method to set the EDS version on the packet

        @param version: The EDS version
        """
        self.eds_version = version

    def set_endian(self, endian: int) -> None:
        """
        Convenience method to set the endianness on the packet

        @param endian: The endianness value, 0 for Big or 1 for Little
        """
        self.endian = endian

    def set_playback_flag(self, flag: int) -> None:
        """
        Convenience method to set the playback flag on the packet

        @param flag: The playback flag value
        """
        self.playback_flag = flag

    def set_subsystem_id(self, subsystem_id: int) -> None:
        """
        Convenience method to set the subsystem ID on the packet

        @param subsystem_id: The subsystem ID
        """
        self.subsystem_id = subsystem_id

    def set_system_id(self, system_id: int) -> None:
        """
        Convenience method to set the system ID on the packet

        @param system_id: The system ID
        """
        self.system_id = system_id


class CcsdsV2PrimaryHeader(CcsdsPrimaryHeaderBase):
    """
    This class provides an interface to a CCSDS V2 primary header

    @note - This is a sample implementation showing how custom headers can extend CcsdsPrimaryHeaderBase as needed.
            The implementation of is_command is redundant with CcsdsPrimaryHeaderBase.
    """

    def is_command(self) -> int:
        return self.type


class CcsdsV2Packet(CcsdsPacketInterface):
    """
    This class provides an interface to a CCSDS V2 packet
    """
    _pack_ = 1
    _fields_ = [
        ("pheader", CcsdsV2PrimaryHeader),
        ("eheader", CcsdsV2ExtendedHeader)
    ]

    def set_msg_id(self, msg_id: int) -> None:
        """
        Sets the message ID on the packet
        Python implementation of CFE_SB_SetMsgId(CFE_SB_MsgPtr_t MsgPtr, CFE_SB_MsgId_t MsgId)

        @param msg_id: The message ID
        """
        self.pheader.set_ccsds_version(1)

        app_id = ctypes.c_uint16(msg_id).value & APP_ID_MASK
        self.pheader.set_app_id(app_id)

        packet_type = (msg_id & CFE_SB_CMD_MESSAGE_TYPE) >> 7
        self.pheader.set_packet_type(packet_type)

        # Set CCSDS v2 Extended Header Properties
        subsystem_id = (ctypes.c_uint16(msg_id).value & 0x0000FF00) >> 8
        system_id = 0
        self.eheader.set_eds_version(0)
        self.eheader.set_playback_flag(0)
        self.eheader.set_subsystem_id(subsystem_id)
        self.eheader.set_system_id(system_id)

    def get_msg_id(self) -> int:
        """
        Returns the message ID derived from the header fields
        Python implementation of CFE_SB_GetMsgId(CFE_SB_MsgPtr_t MsgPtr)
        """
        msg_id = self.pheader.app_id
        if self.pheader.is_command():
            msg_id = msg_id | CFE_SB_CMD_MESSAGE_TYPE
        msg_id = msg_id | (self.eheader.subsystem_id << 8)
        return msg_id

    def has_secondary_header(self) -> bool:
        return self.pheader.secondary_header_flag

    def get_function_code(self) -> int:
        raise TypeError("Function code is only supported in a command packet")

    def set_function_code(self, function_code: int) -> None:
        raise TypeError("Function code is only supported in a command packet")


class CcsdsV2CmdPacket(CcsdsV2Packet):
    """
    This class implements a CCSDS V2 command packet as represented by a ctypes BigEndianStructure
    """

    _pack_ = 1
    _fields_ = [
        ("sheader", CcsdsSecondaryCmdHeader),
        ("spare", ctypes.c_uint32)
    ]

    def __init__(self, mid, command_code, payload_length, endian=0, sequence_count=0, **_: dict):
        super().__init__()
        # Packet Length = Complete Packet Length - 7 (Per CCSDS Definition)
        packet_length = payload_length + ctypes.sizeof(self) - 7

        # Set Msg Id (also sets extended header properties for CCSDS v2)
        self.set_msg_id(mid)

        # Set additional primary header properties
        self.pheader.set_segmentation_flags(3)
        self.pheader.set_secondary_header_flag(1)
        self.pheader.set_sequence_count(sequence_count)
        self.pheader.set_packet_length(packet_length)

        # Set additional extender header properties
        self.eheader.set_endian(endian)

        # Set Secondary Header Properties
        self.sheader.set_function_code(command_code)
        self.sheader.set_checksum(command_code)

    def get_function_code(self) -> int:
        return self.sheader.get_function_code()

    def set_function_code(self, function_code: int) -> None:
        self.sheader.set_function_code(function_code)


class CcsdsV2TlmPacket(CcsdsV2Packet):
    """
    This class implements a CCSDS V2 telemetry packet as represented by a ctypes BigEndianStructure
    """

    _pack_ = 1
    _fields_ = [
        ("sheader", CcsdsSecondaryTlmHeader)
    ]


CcsdsPrimaryHeader = CcsdsV2PrimaryHeader
CcsdsCommand = CcsdsV2CmdPacket
CcsdsTelemetry = CcsdsV2TlmPacket
