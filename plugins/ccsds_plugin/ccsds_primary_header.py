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
ccsds_primary_header.py: Implementation of the CCSDS primary header structure that is standard for all CCSDS messaging
"""

import ctypes


class CcsdsPrimaryHeaderBase(ctypes.BigEndianStructure):
    """
    This class implements the CCSDS primary header as represented by a ctypes BigEndianStructure
    """

    _pack_ = 1
    _fields_ = [
        ("version_number", ctypes.c_uint16, 3),  # CCSDS version
        ("type", ctypes.c_uint16, 1),  # Packet type:      0 = TLM, 1 = CMD
        ("secondary_header_flag", ctypes.c_uint16, 1),  # Secondary header: 0 = absent, 1 = present
        ("app_id", ctypes.c_uint16, 11),  # Application ID
        ("segmentation_flags", ctypes.c_uint16, 2),  # Segmentation flags:  3 = complete packet
        ("sequence_count", ctypes.c_uint16, 14),  # Sequence count
        ("length", ctypes.c_uint16, 16)  # (total packet length) - 7
    ]

    def __init__(self):
        """
        class CcsdsPrimaryHeaderBase constructor: assign attributes default values
        """
        super().__init__()
        self.version_number = 0
        self.app_id = 0
        self.secondary_header_flag = 0
        self.segmentation_flags = 0
        self.sequence_count = 0
        self.length = 0
        self.type = 0

    def set_ccsds_version(self, version: int) -> None:
        """
        Sets the CCSDS version number

        @param version: The version number
        """
        self.version_number = version

    def set_app_id(self, app_id: int) -> None:
        """
        Sets the app ID field

        @param app_id: The app ID value
        """
        self.app_id = app_id

    def set_secondary_header_flag(self, flag: int) -> None:
        """
        Sets the secondary header flag field

        @param flag: The flag value
        """
        self.secondary_header_flag = flag

    def set_segmentation_flags(self, flags: int) -> None:
        """
        Sets the segmentation flags field

        @param flags: The flags value
        """
        self.segmentation_flags = flags

    def set_sequence_count(self, count: int) -> None:
        """
        Sets the sequence count field

        @param count: The sequence count value
        """
        self.sequence_count = count

    def set_packet_length(self, length: int) -> None:
        """
        Sets the packet length field

        @param length: The packet length value
        """
        self.length = length

    def set_packet_type(self, packet_type: int) -> None:
        """
        Sets the packet type field

        @param packet_type: The packet type value
        """
        self.type = packet_type

    def is_command(self) -> int:
        """Returns true if the packet represents a command, indicated by the type field"""
        return self.type

    def get_msg_id(self) -> int:
        """Returns the message ID value derived from the header fields"""
        msg_id = (self.version_number << 15) + (self.type << 12) + (
                self.secondary_header_flag << 11) + self.app_id
        return msg_id
