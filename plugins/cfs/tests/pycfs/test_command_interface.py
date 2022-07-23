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

import socket
from unittest.mock import patch

import pytest


@pytest.fixture
def ccsdsv2():
    from plugins.ccsds_plugin.ccsds_packet_interface import CcsdsHeaderTypes
    from plugins.ccsds_plugin.cfe.ccsds_v2.ccsds_v2 import CcsdsPrimaryHeader, CcsdsCommand, CcsdsTelemetry
    return CcsdsHeaderTypes(CcsdsPrimaryHeader, CcsdsCommand, CcsdsTelemetry)


@pytest.fixture(name='cmdif')
def command_interface(ccsdsv2):
    from plugins.cfs.pycfs.command_interface import CommandInterface
    return CommandInterface(ccsdsv2)


def test_command_interface_init(cmdif):
    assert isinstance(cmdif.ccsds, tuple)
    assert cmdif.ip_address == "127.0.0.1"
    assert cmdif.port == 1234
    assert cmdif.command_socket
    assert cmdif.endianness == 0
    assert cmdif.debug is False


def test_command_interface_init_socket(cmdif):
    assert not cmdif.command_socket._closed
    assert cmdif.command_socket.getblocking()


def test_command_interface_cleanup(cmdif):
    cmdif.cleanup()
    assert cmdif.command_socket._closed


def test_command_interface_send_command(cmdif):
    mid = 0xABC
    cc = 3
    data = 0x12345678.to_bytes(4, "little")
    with patch.object(cmdif, 'command_socket', spec=socket.socket) as mocksock:
        mocksock.fileno.return_value = 1
        mocksock.sendto.return_value = len(data) + 16
        assert cmdif.send_command(mid, cc, data)
        # TODO compute actual byte array and check called
        mocksock.sendto.assert_called_once()


def test_command_interface_send_command_init(cmdif):
    mid = 0xABC
    cc = 3
    data = 0x12345678.to_bytes(4, "little")
    with patch.object(cmdif, 'command_socket', spec=socket.socket) as mocksock:
        mocksock.fileno.return_value = -1
        mocksock.sendto.return_value = len(data) + 12
        assert cmdif.send_command(mid, cc, data)


def test_command_interface_send_command_error(cmdif):
    mid = 0xABCD
    cc = 3
    data = 0x12345678.to_bytes(4, "little")
    with patch.object(cmdif, 'command_socket', spec=socket.socket) as mocksock:
        mocksock.fileno.return_value = 1
        mocksock.sendto.side_effect = socket.error("mock error")
        assert not cmdif.send_command(mid, cc, data)
        mocksock.sendto.assert_called_once()
        mocksock.close.assert_called_once()
        assert mocksock != cmdif.command_socket, "Socket has been replaced with a new instance"
