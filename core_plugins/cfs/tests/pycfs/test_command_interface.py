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
# Copyright © 2019-2026 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# File: test_command_interface.py
#
# Purpose: This file contains test cases for unit testing of CommandInterface functions.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

import socket
import pytest
from unittest.mock import patch


@pytest.fixture
def ccsdsv2():
    from core_plugins.ccsds_plugin.ccsds_packet_interface import CcsdsHeaderTypes
    from core_plugins.ccsds_plugin.cfe.ccsds_v2.ccsds_v2 import CcsdsPrimaryHeader, CcsdsCommand, CcsdsTelemetry
    return CcsdsHeaderTypes(CcsdsPrimaryHeader, CcsdsCommand, CcsdsTelemetry)


@pytest.fixture(name='cmdif')
def command_interface(ccsdsv2):
    from core_plugins.cfs.pycfs.command_interface import CommandInterface
    from core_plugins.cfs.pycfs.socket_interface import TCPSocketInterface
    tcp_socket_if = TCPSocketInterface("127.0.0.1", 9998, 9999)
    return CommandInterface(tcp_socket_if)


def test_command_interface_init(cmdif):
    assert cmdif.socket_if
    assert cmdif.socket_if.ipaddr == "127.0.0.1"
    assert cmdif.socket_if.src_port == 9998
    assert cmdif.socket_if.dest_port == 9999


def test_command_interface_cleanup(cmdif):
    assert cmdif.cleanup() is None
    assert cmdif.socket_if.cfs_socket is None


def test_command_interface_send_command_packet(cmdif):
    with patch.object(cmdif, 'socket_if') as mock_socket_if:
        mock_socket_if.send_command_packet.return_value = True
        assert cmdif.send_command_packet(b'1234') == True


''' 
def test_command_interface_send_command_packet(cmdif):
    command_packet = 0x12345678.to_bytes(4, "little")
    with patch.object(cmdif, 'command_socket', spec=socket.socket) as mock_sock:
        mock_sock.fileno.return_value = 1
        mock_sock.sendto.return_value = len(command_packet)
        assert cmdif.send_command_packet(command_packet)
        mock_sock.sendto.assert_called_once()


def test_command_interface_send_command_packet_init(cmdif):
    command_packet = 0x12345678.to_bytes(4, "little")
    with patch.object(cmdif, 'command_socket', spec=socket.socket) as mock_sock:
        mock_sock.fileno.return_value = -1
        mock_sock.sendto.return_value = len(command_packet)
        assert cmdif.send_command_packet(command_packet)


def test_command_interface_send_command_packet_error(cmdif):
    command_packet = 0x12345678.to_bytes(4, "little")
    with patch.object(cmdif, 'command_socket', spec=socket.socket) as mock_sock:
        mock_sock.fileno.return_value = 1
        mock_sock.sendto.side_effect = socket.error("mock error")
        assert not cmdif.send_command_packet(command_packet)
        mock_sock.sendto.assert_called_once()
        mock_sock.close.assert_called_once()
        assert mock_sock != cmdif.command_socket, "Socket has been replaced with a new instance"
'''
