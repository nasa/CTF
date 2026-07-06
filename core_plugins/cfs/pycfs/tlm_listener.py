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
# File: tlm_listener.py
#
# Purpose: This file defines telemetry listener class that connects to a given port and
#          manages the connection.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

""""
tlm_listener.py: Simple telemetry listener class that connects to a given ip/port and
                 manages that connection. Can call read_socket() to receive the next packets in
                 the telemetry stream.
"""

import logging as log

# Set the CCSDS Max Size to maximum theoretical UDP packet size
#   - This value is used during the tlm_socket.recv() to receive *up to*
#     CCSDS_MAX_SIZE bytes
CCSDS_MAX_SIZE = 65535


class TlmListener:
    """
    Simple telemetry listener class that connects to a given ip/port and manages that connection.
    Can call read_socket() to receive the next packets in telemetry stream.
    """
    def __init__(self, socket_if):
        """
        Constructor of TlmListener class.
        @param socket_if: socket instance to receive telemetry packets from cFS.
        @return None
        """
        self.socket_if = socket_if
        self.socket_if.init_socket()

    def cleanup(self):
        """
        Close socket connection.
        @return None
        """
        self.socket_if.cleanup()
        log.info("Cleaning up tlm_listener")

    def read_socket(self):
        """
        Receive telemetry packets from cFS.

        @return the number of bytes read from telemetry stream
        """
        return self.socket_if.read_socket()
