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
# File: test_tlm_listener.py
#
# Purpose: This file contains test cases for unit testing of TlmListener functions.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

from unittest.mock import patch
import pytest


@pytest.fixture
def tlm_listener():
    from core_plugins.cfs.pycfs.tlm_listener import TlmListener
    from core_plugins.cfs.pycfs.socket_interface import UDPSocketInterface
    udp_socket_if = UDPSocketInterface("127.0.0.1", 9998, 9999)
    return TlmListener(udp_socket_if)


def test_tlm_listener_init(tlm_listener):
    assert tlm_listener.socket_if
    assert tlm_listener.socket_if.ipaddr == "127.0.0.1"
    assert tlm_listener.socket_if.src_port == 9998
    assert tlm_listener.socket_if.dest_port == 9999


def test_tlm_listener_cleanup(tlm_listener):
    tlm_listener.cleanup()
    assert tlm_listener.socket_if.cfs_socket is None


def test_tlm_listener_read_socket(tlm_listener):
    with patch.object(tlm_listener, 'socket_if') as mock_socket_if:
        mock_socket_if.read_socket.return_value = "bytes received"
        assert tlm_listener.read_socket() == "bytes received"


'''
def test_tlm_listener_read_socket(tlm_listener):
    with patch.object(tlm_listener, 'socket', spec=socket) as mocksock:
        mocksock.recv.return_value = "bytes received"
        mocksock.fileno.return_value = 1
        assert tlm_listener.read_socket() == "bytes received"
        mocksock.recv.assert_called_once_with(65535)

def test_tlm_listener_read_socket_error(tlm_listener):
    with patch.object(tlm_listener, 'socket', spec=socket) as mocksock:
        mocksock.recv.side_effect = IOError("mock error")
        assert tlm_listener.read_socket() == 0

'''