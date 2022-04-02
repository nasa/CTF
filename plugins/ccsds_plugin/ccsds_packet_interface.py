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
ccsds_packet_interface.py: Abstract types that provide interfaces for packet and header implementations
"""


import ctypes
import enum
import importlib
import os
import sys
from collections import namedtuple

from lib.ctf_global import Global
from lib.logger import logger as log
from lib.exceptions import CtfTestError
from lib.ctf_utility import expand_path

CcsdsHeaderTypes = namedtuple('CcsdsHeaderTypes', 'CcsdsPrimaryHeader CcsdsCommand CcsdsTelemetry')


class CcsdsVer(enum.IntEnum):
    """
    This class enumerates CCSDS versions as integer values
    """
    Ccsds_ver_1 = 1
    Ccsds_ver_2 = 2
    Ccsds_ver_GW = 3


class CcsdsPacketType(enum.IntEnum):
    """
    This class enumerates CCSDS packet types as integer values
    """
    CommandPacket = 1
    TelemetryPacket = 0


class CcsdsPacketInterface(ctypes.BigEndianStructure):
    """
    This class provides a common interface for CCSDS packets to get and set values in the headers
    without knowing where they are defined

    @note - Classes implementing interface for specific CCSDS packets should inherit from this type
    and override all methods.
    """

    def get_msg_id(self) -> int:
        """Convenience method to get the message ID from the packet"""
        raise NotImplementedError

    def set_msg_id(self, msg_id: int) -> None:
        """
        Convenience method to set the message ID on the packet

        @param msg_id: The message ID value
        """
        raise NotImplementedError

    def has_secondary_header(self) -> bool:
        """Convenience method to check for the presence of a secondary header"""
        raise NotImplementedError

    def get_function_code(self) -> int:
        """Convenience method to get the function code from the packet"""
        raise NotImplementedError

    def set_function_code(self, function_code: int) -> None:
        """
        Convenience method to set the function code on the packet

        @param function_code: The function code value
        """
        raise NotImplementedError


def import_ccsds_header_types():
    """
    Dynamically imports the appropriate CCSDS primary header, command, and telemetry types from the location given
    in the config value 'CCSDS_header_path' and if found, returns them in a tuple.
    """
    headers_path = expand_path(Global.config.get("ccsds", "CCSDS_header_path"))
    if not os.path.exists(headers_path):
        log.error("ccsds:CCSDS_header_path is not a valid path: {}".format(headers_path))
        return None

    log.info("Importing CCSDS header definitions from {}".format(headers_path))
    sys.path.append(os.path.dirname(headers_path))
    try:
        headers_module = importlib.import_module(os.path.basename(headers_path).replace(".py", ""))
    except Exception as exception:
        log.error("Unable to import module {}".format(headers_path))
        raise CtfTestError("Error in import_ccsds_header_types") from exception

    if not hasattr(headers_module, "CcsdsPrimaryHeader"):
        log.error("No definition for CcsdsPrimaryHeader found in {}".format(headers_path))
        return None
    if not hasattr(headers_module, "CcsdsCommand"):
        log.error("No definition for CcsdsCommand found in {}".format(headers_path))
        return None
    if not hasattr(headers_module, "CcsdsTelemetry"):
        log.error("No definition for CcsdsTelemetry found in {}".format(headers_path))
        return None

    ccsds_primary_header = getattr(headers_module, "CcsdsPrimaryHeader")
    if not (issubclass(ccsds_primary_header, ctypes.Structure) and
            callable(getattr(ccsds_primary_header, "get_msg_id", None)) and
            callable(getattr(ccsds_primary_header, "is_command", None))):
        log.error("CcsdsPrimaryHeader definition does not meet interface requirements")
        return None

    ccsds_command = getattr(headers_module, "CcsdsCommand")
    if not (issubclass(ccsds_command, ctypes.Structure) and
            callable(getattr(ccsds_command, "get_msg_id", None)) and
            callable(getattr(ccsds_command, "get_function_code", None))):
        log.error("CcsdsCommand definition does not meet interface requirements")
        return None

    ccsds_telemetry = getattr(headers_module, "CcsdsTelemetry")
    if not (issubclass(ccsds_telemetry, ctypes.Structure) and
            callable(getattr(ccsds_telemetry, "get_msg_id", None))):
        log.error("CcsdsTelemetry definition does not meet interface requirements")
        return None

    return CcsdsHeaderTypes(ccsds_primary_header, ccsds_command, ccsds_telemetry)
