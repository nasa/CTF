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
# File: command_interface.py
#
# Purpose: This file defines the command interface sending commands to a cFS target.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

"""
command_interface.py: Handles sending commands to a cFS target.

- Receives command structure from the cFS interface and sends it over UDP
  to cFS per the configured command port.
"""

import logging as log


class CommandInterface:
    """
    The CommandInterface class provides methods to send CCSDS messages from the CFS test framework to CFS via
    any app that listens on a UDP socket and injects CCSDS packets onto the software bus (TO or DIAG).
    CommandInterface is a misnomer, as it is capable of sending both Command and Telemetry CCSDS packets.
    """

    def __init__(self, socket_if):
        """
        Constructor implementation for CommandInterface Class. It sets up the ip addr, port, ccsds version, etc.
        """
        self.socket_if = socket_if
        self.socket_if.init_socket()

    def cleanup(self):
        """
        Performs requisite cleanup of the class, such as closing the socket.
        @return None
        """
        self.socket_if.cleanup()
        log.info("Clean up command interface")

    def send_command_packet(self, command_packet):
        """
        Send CCSDS command packets to CFS target through the socket.
        @return True if successful, False otherwise
        """
        return self.socket_if.send_command_packet(command_packet)
