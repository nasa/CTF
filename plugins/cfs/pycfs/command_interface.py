"""
command_interface.py: Handles sending commands to a cFS target.

- Receives command structure from the cFS interface and sends it over UDP
  to cFS per the configured command port.
"""

import socket


class CommandInterface(object):
    """
    The CommandInterface class provides methods to send CCSDS messages from the CFS test framework to CFS via
    any app that listens on a UDP socket and injects CCSDS packets onto the software bus (TO or DIAG).
    CommandInterface is a misnomer, as it is capable of sending both Command and Telemetry CCSDS packets.
    """

    def __init__(self, ccsds, port=1234, ip="127.0.0.1", endianness="little"):
        self.ccsds = ccsds
        self.ip_address = ip
        self.port = port
        self.command_socket = None
        self.init_socket()
        self.endianness = 1 if endianness == "big" else 0
        self.debug = False

    def init_socket(self):
        self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def cleanup(self):
        """
        Performs requisite cleanup of the class, such as closing the socket.
        :return: None
        """
        self.command_socket.close()

    def send_command(self, msg_id, function_code, data, ccsds_ver=1):
        """
        This method constructs a CCSDS command packet and sends it
         to the ip:port defined when creating the class via UDP

        :param msg_id: The message ID of the command to send
        :param function_code: The app specific function/command code (CC)
        :param ccsds_ver: What version of the CCSDS protocol to use
        :param data: A bytearray representing the packed message payload. This is specific to the message, so for now
        the bytearray needs to be contructed by hand using struct.pack or the included BytePacker class
        :param subsysId: If using CCSDS V2 you can use this parameter to specify which subsystem to target
        :param endian: If using CCSDS V2 you can use this parameter to specify what endianess to use
        :param systemId: If using CCSDS V2 you can use this paramater to specify which system to target
        :return: The number of bytes that were sent over the socket. UDP is connectionless, so there is no way for the
        socket to know that a packet was received by the destination
        """
        sequence_counter = 0
        command = self.ccsds.CcsdsCommand(msg_id, function_code, len(data), sequence_count=sequence_counter,
                                          endian=self.endianness)
        to_send = memoryview(bytearray(command)).obj[:] + data
        # Check if socket is closed, and if so, reinitialize command socket.
        if self.command_socket.fileno() == -1:
            self.init_socket()
        try:
            # Send command bytes.
            # Note - command bytes are logged by the send_cfs_command in DEBUG
            bytessent = self.command_socket.sendto(to_send, (self.ip_address, self.port))
        except socket.error as msg:
            print(msg)
            self.command_socket.close()
            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            bytessent = 0
        return bytessent == len(to_send)

    # TODO - Move the function below to a TelemetryInterface that opens its own socket
    #               and sends CCSDS telemetry packets to the selected port/ip. May be used for playback.
    def send_telemetry(self, msg_id, data):
        """
        This method constructs a CCSDS telemetry packet and sends it
         to the ip:port defined when creating the class via UDP

        :param msg_id: The message ID of the telemetry to send
        :param data: A bytearray representing the packed message payload. This is specific to the message, so for now
        the bytearray needs to be contructed by hand using struct.pack or the included BytePacker class
        :return: The number of bytes that were sent over the socket. UDP is connectionless, so there is no way for the
        socket to know that a packet was received by the destination
        """
        telemetry = self.ccsds.CcsdsTelemetry(msg_id, data)
        to_send = bytearray(memoryview(telemetry)) + data
        try:
            bytessent = self.command_socket.sendto(to_send, (self.ip_address, self.port))
        except socket.error as msg:
            print(msg)
            self.command_socket.close()
            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            bytessent = 0
        return bytessent
