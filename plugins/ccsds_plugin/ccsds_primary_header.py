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
ccsds_primary_header.py: Implementation of the CCSDS primary header structure that is standard for all CCSDS messaging
"""


import ctypes


class CcsdsPrimaryHeaderBase(ctypes.BigEndianStructure):
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

    def set_ccsds_version(self, version) -> None:
        self.version_number = version

    def set_app_id(self, app_id: int) -> None:
        self.app_id = app_id

    def set_secondary_header_flag(self, flag) -> None:
        self.secondary_header_flag = flag

    def set_segmentation_flags(self, flags: int) -> None:
        self.segmentation_flags = flags

    def set_sequence_count(self, count: int) -> None:
        self.sequence_count = count

    def set_packet_length(self, length: int) -> None:
        self.length = length

    def set_packet_type(self, packet_type: int) -> None:
        self.type = packet_type

    def is_command(self) -> int:
        return self.type

    def get_msg_id(self) -> int:
        msg_id = (self.version_number << 15) + (self.type << 12) + (
                self.secondary_header_flag << 11) + self.app_id
        return msg_id
