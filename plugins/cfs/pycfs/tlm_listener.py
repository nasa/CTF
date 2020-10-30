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


class TlmListener(object):
    def __init__(self, ip, port):
        self.ip = ip
        # Port = 0 will assign a random available port
        self.port = port
        self.socket = self.create_socket()

    def cleanup(self):
        self.socket.close()

    def create_socket(self):
        tlm_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tlm_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tlm_socket.bind((self.ip, self.port))
        tlm_socket.setblocking(False)
        self.port = tlm_socket.getsockname()[1]
        return tlm_socket

    def get_port(self):
        return self.port

    def read_socket(self):
        received = 0
        if self.socket.fileno() == -1:
            self.socket = self.create_socket()
        try:
            received = self.socket.recv(CCSDS_MAX_SIZE)
        except IOError as e:  # and here it is handeled
            if e.errno == errno.EWOULDBLOCK:
                pass
        return received
