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
# File: socket_interface.py
#
# Purpose: This file defines TCPSocketInterface and UDPSocketInterface classes that initialize socket,
#          send and receive data to cFS.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

""""
socket_interface.py: TCPSocketInterface and UDPSocketInterface classes that connects to a given ip/port
                      via TCP/UDP and manages that connection. Can call read_socket() to receive telemetry packets
                      and send_command_packet() to send CCSDS commands to cFS.
"""

import errno
import socket
from abc import ABC, abstractmethod

import logging as log

# Set the CCSDS Max Size to maximum theoretical UDP packet size
#   - This value is used during the tlm_socket.recv() to receive *up to*
#     CCSDS_MAX_SIZE bytes
CCSDS_MAX_SIZE = 65535


class SocketInterface(ABC):
    """
    Abstract base class defining the interface for socket communication
    with a Core Flight System (cFS) target.

    Subclasses should implement the required socket operations such as
    initialization, sending, receiving, and cleanup.
    """

    def __init__(self, ipaddr, src_port, dest_port):
        """
        Initialize the SocketInterface object.

        @param    ipaddr (str): IP address of the cFS target system.
        @param    src_port (int): Source port for the local socket (0 for any available port).
        @param    dest_port (int): Destination port of the cFS system.
        """
        # ipaddr is assigned by OS, through which CTF can reach cfs_target_ip
        self.ipaddr = ipaddr
        # Port = 0 will assign a random available port
        self.src_port = src_port
        self.dest_port = dest_port
        self.cfs_socket = None

    def get_port(self):
        """
        Get the destination port used to communicate with the cFS system.
        Returns:
            int: The destination port number.
        """
        return self.dest_port

    @abstractmethod
    def cleanup(self):
        """
        Clean up and close the socket connection.
        This method must be implemented by a subclass.
        """
        raise NotImplementedError('Subclasses must implement cleanup method')

    @abstractmethod
    def init_socket(self):
        """
        Initialize and configure the socket.
        This method must be implemented by a subclass.
        """
        raise NotImplementedError('Subclasses must implement init_socket method')

    @abstractmethod
    def read_socket(self):
        """
        Read data from the socket.
        This method must be implemented by a subclass.
        """
        raise NotImplementedError('Subclasses must implement read_socket method')

    @abstractmethod
    def send_command_packet(self, command_packet):
        """
        Send a command packet to the cFS system over the socket.
        @param  command_packet (bytes): The command packet to be sent.
        This method must be implemented by a subclass.
        """
        raise NotImplementedError('Subclasses must implement send_command_packet method')


class UDPSocketInterface(SocketInterface):
    """
    Concrete implementation of a UDP-based socket interface for sending command packets
    and receiving telemetry packets from cFS using non-blocking sockets.
    """

    def __init__(self, ipaddr, src_port, dest_port):
        """
        Initialize the UDP socket interface.

        @param    ipaddr (str): IP address of the cFS target system.
        @param    src_port (int): Source port for the local socket (0 for any available port).
        @param    dest_port (int): Destination port of the cFS system.
        """
        super().__init__(ipaddr, src_port, dest_port)
        self.init_socket()

    def init_socket(self):
        """
        Initializes the UDP socket.
        - Creates a new socket if one doesn't already exist.
        - Binds it to the specified source port (if provided).
        - Sets it to non-blocking mode for asynchronous operation.
        """
        if self.cfs_socket:
            return
        log.info("Init udp socket with src_port:{} dest_port:{}".format(self.src_port, self.dest_port))
        try:
            cfs_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cfs_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if self.src_port:
                # listen on self.src_port (tlm_udp_port), regardless of the network interfaces the traffic comes from
                cfs_socket.bind(('', self.src_port))
            cfs_socket.setblocking(False)
            port = cfs_socket.getsockname()
            log.info("Successfully create udp socket and bind with port: {}".format(port))
        except OSError as exception:
            log.error("Init socket failed: {}".format(exception))
            cfs_socket = None

        self.cfs_socket = cfs_socket

    def read_socket(self):
        """
        Attempts to receive a telemetry UDP packet from the socket.

        @return The received data as a bytes object, or 0 if no data is available.
        """
        received = 0
        if not self.cfs_socket:
            self.init_socket()
        try:
            received = self.cfs_socket.recv(CCSDS_MAX_SIZE)
        except IOError as exception:
            if exception.errno != errno.EWOULDBLOCK:
                log.error("Socket receive failed: {}".format(exception))
        return received

    def cleanup(self):
        """
        Closes and cleans up the socket.
        Ensures the resource is properly released.
        """
        if self.cfs_socket:
            socket_name = self.cfs_socket.getsockname()
            self.cfs_socket.close()
            self.cfs_socket = None
            log.debug("Closing udp socket {}".format(socket_name))

    def send_command_packet(self, command_packet):
        """
        Sends a CCSDS command packet via the UDP socket.

        @param command_packet: Bytes object representing the CCSDS command to send.
        @return True if the entire packet was sent successfully, False otherwise.
        """
        if not self.cfs_socket:
            self.init_socket()
        try:
            # Note - command bytes are logged by the send_command function in DEBUG log
            bytes_sent = self.cfs_socket.sendto(command_packet, (self.ipaddr, self.dest_port))
        except OSError as exception:
            log.error("Command socket exception {}: close and re-init socket".format(exception))
            self.cfs_socket.close()
            self.init_socket()
            bytes_sent = 0
        return bytes_sent == len(command_packet)


class TCPSocketInterface(SocketInterface):
    """
    TCP socket implementation of the SocketInterface.

    Used for sending command packets and receiving telemetry data over a TCP connection.
    This implementation handles lazy connection, error recovery, and non-blocking I/O as TCP client.
    """

    def __init__(self, ipaddr, src_port, dest_port):
        """
        Initialize the TCP socket interface.

        @param    ipaddr (str): IP address of the cFS target system.
        @param    src_port (int): Source port for the local socket (0 for any available port).
        @param    dest_port (int): Destination port of the cFS system.
        """
        super().__init__(ipaddr, src_port, dest_port)
        self.connected = False
        self.init_socket()

    def init_socket(self):
        """
        Initialize the TCP socket:
        - Creates a TCP socket object.
        - Sets socket options for address reuse.
        - Optionally binds to a local source port.
        - Does not connect immediately as cFS may not start.
        """
        if self.cfs_socket:
            return
        log.info("Init tcp socket with src_port:{} dest_port:{}".format(self.src_port, self.dest_port))
        self.connected = False
        try:
            cfs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cfs_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if self.src_port:
                # listen on self.src_port (tlm_udp_port), regardless of the network interfaces the traffic comes from
                # Should not call socket.connect, as cFS may not start yet
                cfs_socket.bind(('', self.src_port))
            assigned_port = cfs_socket.getsockname()
            log.info("Successfully created tcp socket on {}".format(assigned_port))
        except OSError as exception:
            log.error("Init socket failed: {}".format(exception))
            cfs_socket = None

        self.cfs_socket = cfs_socket

    def read_socket(self):
        """
        Read telemetry data from the TCP socket.
        Ensures the socket is connected before attempting to read. Uses non-blocking I/O.
        @return: Bytes received from the TCP socket, or 0 if no data was available or an error occurred.
        """
        received = 0
        if not self.cfs_socket:
            self.init_socket()

        self.connect()

        if not self.cfs_socket or not self.connected:
            return received

        try:
            received = self.cfs_socket.recv(CCSDS_MAX_SIZE)
        except OSError as exception:
            if exception.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                # not the exception: [Errno 11] Resource temporarily unavailable
                log.error("Socket recv failed: {} self.connected={}".format(exception, self.connected))
                self.cfs_socket = None
        return received

    def cleanup(self):
        """
        Cleanly close the TCP socket.
        Releases any system resources associated with the socket.
        """
        if self.cfs_socket:
            self.cfs_socket.close()
            self.cfs_socket = None
            log.debug("Closing tcp socket")

    def connect(self):
        """
        Attempt to establish a TCP connection to the remote host.

        This method is only called when needed and skips reconnecting if already connected.
        It uses blocking connect followed by switching to non-blocking mode for I/O.
        """
        if self.cfs_socket and not self.connected:
            try:
                self.cfs_socket.connect((self.ipaddr, self.dest_port))
                self.connected = True
                # Blocking connect, non-blocking I/O afterward to simplify connect logic
                self.cfs_socket.setblocking(False)
                log.info("TCP socket connected to {}:{}".format(self.ipaddr, self.dest_port))
            except OSError as exception:
                self.connected = False
                log.error("Connecting socket failed: {}".format(exception))

    def send_command_packet(self, command_packet):
        """
        Send a CCSDS command packet to the remote server via the TCP socket.
        Ensures the socket is connected before sending. Uses `sendall()` to ensure all bytes are sent.

        @param command_packet: Bytes object containing the full command packet.
        @return: True if the packet was sent successfully, False otherwise.
        """
        if not self.cfs_socket:
            self.init_socket()

        self.connect()

        if not self.cfs_socket or not self.connected:
            return False

        try:
            # Note - command bytes are logged by the send_command function in DEBUG log
            self.cfs_socket.sendall(command_packet)
            status = True
        except OSError as exception:
            log.error("socket sendall exception {}: close and re-init socket".format(exception))
            self.cfs_socket.close()
            self.init_socket()
            status = False
        return status


class TCPServerSocketInterface(TCPSocketInterface):
    """
    TCP server socket implementation of the SocketInterface.

    Used for sending command packets and receiving telemetry data over a TCP connection.
    This implementation handles lazy connection, error recovery, and non-blocking I/O as TCP server.
    """

    def __init__(self, ipaddr, src_port, dest_port):
        """
        Initialize the TCP socket interface.

        @param    ipaddr (str): IP address of the cFS target system.
        @param    src_port (int): Source port for the local socket (0 for any available port).
        @param    dest_port (int): Destination port of the cFS system.
        """
        self.listen_socket = None
        super().__init__(ipaddr, src_port, dest_port)
        self.connected = False
        self.init_socket()

    def init_socket(self):
        """
        Initialize the TCP socket:
        - Creates a TCP listen socket object.
        - Sets socket options for address reuse, non-blocking and binds to source port.
        - Does not connect immediately as cFS may not start.
        """
        if self.cfs_socket:
            return

        if not self.listen_socket:
            log.info("Init tcp listen socket with src_port:{} dest_port:{}".format(self.src_port, self.dest_port))
            self.connected = False
            try:
                listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listen_socket.bind(('', self.src_port))
                listen_socket.listen()
                listen_socket.setblocking(False)  # Non-blocking
                assigned_port = listen_socket.getsockname()
                log.info("Successfully created tcp listen socket on {}".format(assigned_port))
                self.listen_socket = listen_socket
            except OSError as exception:
                log.error("Init socket failed: {}".format(exception))

    def cleanup(self):
        """
        Cleanly close the TCP sockets.
        Releases any system resources associated with the sockets.
        """
        if self.cfs_socket:
            self.cfs_socket.close()
            self.cfs_socket = None
            log.debug("Closing tcp cfs socket")
        if self.listen_socket:
            self.listen_socket.close()
            self.listen_socket = None
            log.debug("Closing tcp listen socket")

    def connect(self):
        """
        Attempt to establish a TCP connection to the remote host.

        This method is only called when needed and skips reconnecting if already connected.
        It sets the new connected socket as non-blocking mode for I/O.
        """
        if self.listen_socket and not self.connected:
            try:
                conn, addr = self.listen_socket.accept()
                conn.setblocking(False)
                self.cfs_socket = conn
                self.connected = True
                log.info("TCP cfs socket connected to {}".format(addr))
            except BlockingIOError:
                log.debug("TCP socket no incoming connection right now (non-blocking)")
            except OSError as exception:
                log.error("TCP socket OS level error occurred: {}".format(exception))
