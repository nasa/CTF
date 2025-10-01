# =========================================================================================
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
# distributed and modified only pursuant to the terms of that agreement.
# See the License for the specific language governing permissions and limitations under the
# License at https://software.nasa.gov/ .
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either expressed or implied.
#
# Copyright © 2019-2025 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# File: test_cfs_interface_utility.py
#
# Purpose: This file contains test cases for cfs interface utility functions.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================


import pytest

from core_plugins.cfs.pycfs.cfs_interface_utility import build_command_packet_header, update_crc


@pytest.fixture
def ccsds_command(workspace):
    if workspace['type'] == 'open_source':
        from core_plugins.ccsds_plugin.cfe.ccsds_v2.ccsds_v2 import CcsdsCommand
    ccsds_command = CcsdsCommand
    return ccsds_command


def test_build_command_packet_header(workspace, ccsds_command):
    msg_id = 10891
    if workspace['type'] != 'open_source':
        msg_id = 210047086

    header = build_command_packet_header(ccsds_command, msg_id, 0x2, bytearray(0x20), 1, 1,
                                         header_args=None, sequence_count=7)
    # pheader.type is part of msg_id
    assert header.pheader.type == 1
    assert header.pheader.sequence_count == 7
    if workspace['type'] != 'open_source':
        assert header.sheader.timestamp_seconds == 0
        assert header.sheader.timestamp_subseconds == 0
        # open_source CcsdsSecondaryCmdHeader has no attribute 'source_id'
        assert header.sheader.source_id == 0

    header_args = {"sheader.timestamp_seconds": 100, "sheader.timestamp_subseconds": 200}
    header = build_command_packet_header(ccsds_command, msg_id, 0x2, bytearray(0x20), 1, 1,
                                         header_args=header_args, sequence_count=15)
    assert header.pheader.type == 1
    assert header.pheader.sequence_count == 15
    if workspace['type'] != 'open_source':
        assert header.sheader.timestamp_seconds == 100
        assert header.sheader.timestamp_subseconds == 200


def test_update_crc(workspace, ccsds_command):
    if workspace['type'] != 'open_source':
        header = build_command_packet_header(ccsds_command, 210047086, 0x2, bytearray(0x20), 1, 1,
                                             header_args=None, sequence_count=7)
        payload = bytearray(0x20)
        assert update_crc(header, payload) is None
        assert payload[-1] == 187

        header = build_command_packet_header(ccsds_command, 210047086, 0x2, bytearray(0x20), 1, 0,
                                             header_args=None, sequence_count=7)
        payload = bytearray(0x20)
        assert update_crc(header, payload) is None
        assert payload[-1] == 0




