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
command_interface.py: Handles sending commands to a cFS target.

- Receives command structure from the cFS interface and sends it over UDP
  to cFS per the configured command port.
"""

import socket


class CommandInterface:
    """
    The CommandInterface class provides methods to send CCSDS messages from the CFS test framework to CFS via
    any app that listens on a UDP socket and injects CCSDS packets onto the software bus (TO or DIAG).
    CommandInterface is a misnomer, as it is capable of sending both Command and Telemetry CCSDS packets.
    """

    def __init__(self, ccsds, port=1234, ip="127.0.0.1", endianness="little"):
        """
        Constructor implementation for CommandInterface Class. It sets up the ip addr, port, ccsds version, etc.
        """
        self.ccsds = ccsds
        self.ip_address = ip
        self.port = port
        self.command_socket = None
        self.init_socket()
        self.endianness = 1 if endianness == "big" else 0
        self.debug = False

    def init_socket(self):
        """
        Initialize socket connection.
        @return None
        """
        self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def cleanup(self):
        """
        Performs requisite cleanup of the class, such as closing the socket.
        @return None
        """
        self.command_socket.close()

    def send_command(self, msg_id, function_code, data, header_args=None):
        """
        This method constructs a CCSDS command packet and sends it
         to the ip:port defined when creating the class via UDP

        @param msg_id: The message ID of the command to send
        @param function_code: The app specific function/command code (CC)
        @param data: A bytearray representing the packed message payload. This is specific to the message, so for now
        the bytearray needs to be constructed by hand using struct.pack or the included BytePacker class
        @param header_args: An optional dictionary of additional kwargs for the header constructor
         @return  The number of bytes that were sent over the socket. UDP is connectionless, so there is no way for the
        socket to know that a packet was received by the destination
        """
        sequence_counter = 0
        command = self.ccsds.CcsdsCommand(msg_id, function_code, len(data), sequence_count=sequence_counter,
                                          endian=self.endianness, **(header_args or {}))
        to_send = bytearray(command) + data
        # Check if socket is closed, and if so, reinitialize command socket.
        if self.command_socket.fileno() == -1:
            self.init_socket()
        try:
            # Note - command bytes are logged by the send_cfs_command in DEBUG
            bytessent = self.command_socket.sendto(to_send, (self.ip_address, self.port))
        except socket.error as msg:
            print(msg)
            self.command_socket.close()
            self.init_socket()
            bytessent = 0
        return bytessent == len(to_send)
