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
# File: test_socket_interface.py
#
# Purpose: This file contains unit test cases for the SocketInterface functions.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

import pytest
from unittest.mock import patch, MagicMock


from core_plugins.cfs.pycfs.socket_interface import SocketInterface, UDPSocketInterface, TCPSocketInterface, \
    TCPServerSocketInterface


@pytest.fixture
def tlm_listener():
    from core_plugins.cfs.pycfs.tlm_listener import TlmListener
    from core_plugins.cfs.pycfs.socket_interface import UDPSocketInterface
    udp_socket_if = UDPSocketInterface("127.0.0.1", 9998, 9999)
    return TlmListener(udp_socket_if)


@pytest.fixture
def udp_interface():
    return UDPSocketInterface("127.0.0.1", 6011, 6012)


@pytest.fixture
def tcp_interface():
    return TCPSocketInterface("127.0.0.1", 6011, 6012)


@pytest.fixture
def tcp_server_interface():
    return TCPServerSocketInterface("127.0.0.1", 6011, 6012)


def test_socket_interface_not_implement():
    class SocketInterfaceTest(SocketInterface):
        pass

    SocketInterfaceTest.__abstractmethods__ = frozenset()
    interface = SocketInterfaceTest.__new__(SocketInterfaceTest)
    with pytest.raises(NotImplementedError):
        interface.cleanup()
    with pytest.raises(NotImplementedError):
        interface.init_socket()
    with pytest.raises(NotImplementedError):
        interface.read_socket()
    with pytest.raises(NotImplementedError):
        interface.send_command_packet(bytes(10))


def test_udp_interface_get_port(udp_interface):
    assert udp_interface.get_port() == 6012


def test_udp_interface_init_socket(udp_interface, utils):
    assert udp_interface.cfs_socket
    udp_interface.cfs_socket = None
    utils.clear_log()

    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket.bind.side_effect = OSError('bind failed')
        mock_socket_class.return_value = mock_socket
        udp_interface.init_socket()
        assert udp_interface.cfs_socket is None
        assert utils.has_log_level('ERROR')


def test_udp_interface_read_socket(udp_interface, utils):
    assert udp_interface.cfs_socket
    udp_interface.cfs_socket = None
    utils.clear_log()

    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_recd_data = bytes(20)
        mock_socket.recv.return_value = mock_recd_data
        mock_socket_class.return_value = mock_socket
        data = udp_interface.read_socket()
        assert data == mock_recd_data

    mock_socket = MagicMock()
    io_error = OSError(9, "fake error")
    mock_socket.recv.side_effect = io_error
    udp_interface.cfs_socket = mock_socket
    assert udp_interface.read_socket() == 0
    assert utils.has_log('ERROR')


def test_udp_interface_send_command_packet(udp_interface, utils):
    assert udp_interface.cfs_socket
    udp_interface.cfs_socket = None
    utils.clear_log()
    mock_sent_data = bytes(20)

    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket.sendto.return_value = len(mock_sent_data)
        mock_socket_class.return_value = mock_socket
        assert udp_interface.send_command_packet(mock_sent_data)

    mock_socket = MagicMock()
    io_error = OSError(9, "fake error")
    mock_socket.sendto.side_effect = io_error
    udp_interface.cfs_socket = mock_socket
    assert not udp_interface.send_command_packet(mock_sent_data)
    assert utils.has_log('ERROR')


def test_tcp_interface_init_socket(tcp_interface, utils):
    assert tcp_interface.cfs_socket
    tcp_interface.cfs_socket = None
    utils.clear_log()

    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket.bind.side_effect = OSError('bind failed')
        mock_socket_class.return_value = mock_socket
        tcp_interface.init_socket()
        assert tcp_interface.cfs_socket is None
        assert utils.has_log_level('ERROR')


def test_tcp_interface_read_socket(tcp_interface, utils):
    assert tcp_interface.cfs_socket
    tcp_interface.cfs_socket = None
    utils.clear_log()

    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_recd_data = bytes(20)
        mock_socket.recv.return_value = mock_recd_data
        mock_socket_class.return_value = mock_socket
        data = tcp_interface.read_socket()
        assert data == mock_recd_data

    mock_socket = MagicMock()
    io_error = OSError(9, "fake error")
    mock_socket.recv.side_effect = io_error
    tcp_interface.cfs_socket = mock_socket
    assert tcp_interface.read_socket() == 0
    assert utils.has_log('ERROR')

    tcp_interface.connect = MagicMock(return_value="socket could not connect")
    tcp_interface.cfs_socket = None
    assert tcp_interface.read_socket() == 0


def test_tcp_interface_send_command_packet(tcp_interface, utils):
    assert tcp_interface.cfs_socket
    tcp_interface.cfs_socket = None
    utils.clear_log()
    mock_sent_data = bytes(20)

    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket.sendall.return_value = len(mock_sent_data)
        mock_socket_class.return_value = mock_socket
        assert tcp_interface.send_command_packet(mock_sent_data)

    mock_socket = MagicMock()
    io_error = OSError(9, "fake error")
    mock_socket.sendall.side_effect = io_error
    tcp_interface.cfs_socket = mock_socket
    assert not tcp_interface.send_command_packet(mock_sent_data)
    assert utils.has_log('ERROR')

    tcp_interface.connect = MagicMock(return_value="socket could not connect")
    tcp_interface.cfs_socket = None
    assert not tcp_interface.send_command_packet(mock_sent_data)


def test_tcp_interface_connect(tcp_interface, utils):
    assert tcp_interface.cfs_socket
    tcp_interface.connected = False
    utils.clear_log()

    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket.setblocking.side_effect = OSError('setblocking failed')
        mock_socket_class.return_value = mock_socket
        tcp_interface.connect()
        assert not tcp_interface.connected
        assert utils.has_log_level('ERROR')


def test_tcp_server_interface_get_port(tcp_server_interface):
    assert tcp_server_interface.get_port() == 6012


def test_tcp_server_interface_init_socket(tcp_server_interface, utils):
    assert tcp_server_interface.cfs_socket is None
    assert not tcp_server_interface.connected
    tcp_server_interface.listen_socket = None
    utils.clear_log()

    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket.bind.side_effect = OSError('bind failed')
        mock_socket_class.return_value = mock_socket
        tcp_server_interface.init_socket()
        assert tcp_server_interface.listen_socket is None
        assert utils.has_log_level('ERROR')
        assert utils.has_log('Init socket failed')

    tcp_server_interface.cfs_socket = MagicMock()
    assert tcp_server_interface.init_socket() is None
    utils.clear_log()


def test_tcp_server_interface_cleanup(tcp_server_interface, utils):
    assert tcp_server_interface.cfs_socket is None
    assert not tcp_server_interface.connected
    assert tcp_server_interface.listen_socket
    utils.clear_log()
    tcp_server_interface.cleanup()
    assert tcp_server_interface.listen_socket is None
    assert utils.has_log('Closing tcp listen socket')

    tcp_server_interface.cfs_socket = MagicMock()
    utils.clear_log()
    tcp_server_interface.cleanup()
    assert tcp_server_interface.cfs_socket is None
    assert utils.has_log('Closing tcp cfs socket')
    utils.clear_log()


def test_tcp_server_interface_connect(tcp_server_interface, utils):
    assert tcp_server_interface.listen_socket
    assert not tcp_server_interface.connected
    utils.clear_log()
    tcp_server_interface.connect()
    assert utils.has_log('TCP socket no incoming connection')
    assert not tcp_server_interface.connected
    utils.clear_log()

    mock_socket = MagicMock()
    mock_socket.accept.side_effect = OSError('accept failed')
    tcp_server_interface.listen_socket = mock_socket
    tcp_server_interface.connect()
    assert not tcp_server_interface.connected
    assert utils.has_log('TCP socket OS level error occurred')
    utils.clear_log()

    mock_socket = MagicMock()
    mock_socket.accept.return_value = [MagicMock(), 'mock_addr']
    tcp_server_interface.listen_socket = mock_socket
    tcp_server_interface.connect()
    assert tcp_server_interface.connected
    assert utils.has_log('TCP cfs socket connected to mock_addr')
    utils.clear_log()
