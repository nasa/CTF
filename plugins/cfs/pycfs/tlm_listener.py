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

""""
tlm_listener.py: Simple telemetry listener class that connects to a given ip/port via UDP and
                 manages that connection. Can call read_socket() to receive the next packet in
                 the telemetry stream.
"""

import errno
import socket

# Set the CCSDS Max Size to maximum theoretical UDP packet size
#   - This value is used during the tlm_socket.recv() to receive *up to*
#     CCSDS_MAX_SIZE bytes
CCSDS_MAX_SIZE = 65535


class TlmListener:
    """
    Simple telemetry listener class that connects to a given ip/port via UDP and manages that connection.
    Can call read_socket() to receive the next packet in telemetry stream.
    """
    def __init__(self, ipaddr, port):
        """
        Constructor of TlmListener class.
        @param ipaddr: IP address of cFS system.
        @param port:   port of cFS system.
        @return None
        """
        self.ipaddr = ipaddr
        # Port = 0 will assign a random available port
        self.port = port
        self.socket = self.create_socket()

    def cleanup(self):
        """
        Close socket connection.

        @return None

        """
        self.socket.close()

    def create_socket(self):
        """
        Create a UDP socket connection to a cFS system.
        @return socket
        """
        tlm_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tlm_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tlm_socket.bind((self.ipaddr, self.port))
        tlm_socket.setblocking(False)
        self.port = tlm_socket.getsockname()[1]
        return tlm_socket

    def get_port(self):
        """
        Return the UDP port to cFS system
        @return UDP port
        """
        return self.port

    def read_socket(self):
        """
        Receive the UDP packet in the telemetry stream.

        @return the number of bytes read from telemetry stream
        """
        received = 0
        if self.socket.fileno() == -1:
            self.socket = self.create_socket()
        try:
            received = self.socket.recv(CCSDS_MAX_SIZE)
        except IOError as exception:  # and here it is handled
            if exception.errno == errno.EWOULDBLOCK:
                pass
        return received
