"""
@namespace core_plugins.cfs.pycfs.cfs_interface_utility
CFS interface utility library functions
"""

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
# File: cfs_interface_utility.py
#
# Purpose: This file defines utility library functions for cfs interface.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

from lib.ctf_global import Global
from lib.ctf_utility import resolve_variable, set_nested_attr
from lib.exceptions import CtfParameterError
from lib.logger import logger as log


def build_command_packet_header(ccsds_command, msg_id, function_code, payload, endian, crc,
                                header_args=None, sequence_count=0):
    """
    This function constructs CCSDS command packet header.
    @param ccsds_command: CCSDS command class type.
    @param msg_id: The message ID of the command.
    @param function_code: The app specific function/command code (CC).
    @param payload: A bytearray representing the command packet payload.
    @param endian: The byte order of the packet structure.
    @param crc: The cyclic redundancy check (CRC) flag of the packet header.
    @param header_args: An optional dictionary of additional kwargs for the header constructor.
    @param sequence_count: An optional command sequence_count for the header constructor.
    @return: The constructed CCSDS command packet header.
    """

    updated_header_args = header_args or {}
    command_header = ccsds_command(msg_id, function_code, len(payload), sequence_count=sequence_count,
                                   endian=endian, crc=crc, **updated_header_args)

    for key, value in updated_header_args.items():
        key = resolve_variable(key)
        value = resolve_variable(value)
        set_nested_attr(command_header, key, value)

    return command_header


def resolve_cfs_macro(arg, macro_map):
    """
    Implementation of helper function resolve_macros.
    search macro_map to convert arg to string.
    """
    macro_marker = '#'
    if isinstance(arg, str) and "::" in arg:
        target, arg = arg.split("::", 1)
        log.debug("Referred to the macro defined for target {} as {}".format(target, arg))
        if target in Global.plugins_available['CFS Plugin'].targets:
            cfs_controller = Global.plugins_available['CFS Plugin'].targets[target]
            macro_map = cfs_controller.macro_map
        else:
            raise CtfParameterError("No registered cfs target '{}' in referred macro resolve".format(target), arg)

    while isinstance(arg, str) and arg.count(macro_marker) > 1:
        macro = arg.split(macro_marker, 1)[1].split(macro_marker, 1)[0]
        if macro in macro_map:
            # if arg is '#macro#', don't convert to str, keep its data type
            if macro == arg[1:-1]:
                arg = macro_map[macro]
            else:
                arg = arg.replace("{0}{1}{0}".format(macro_marker, macro), str(macro_map[macro]))
        else:
            raise CtfParameterError("Unknown macro '{}' in arg {}. Use format #MACRO#".format(macro, arg), arg)
    return arg


def update_crc(header, payload):
    """
    This function updates CRC attribute based the header CRC flag and the value of last four bytes of the payload.
    """
    # header.get_crc_flag() == 1 implies the last 4 bytes are crc
    # From CCDD json, the constructed payload should set last 4 bytes to zero by default.
    # If they are not zero, there are 2 possible reasons.
    # 1. test instruction sets 'CRCValue' attribute to nonzero values.
    # 2. SendCfsCommandWithRawPayload specifies hex_buffer.
    # In either case, CTF should not update crc.
    # There is a special case: the header CRC flag is set and 'CRCValue' is set to all zero by test instruction
    # for invalid CRC check. However, the CRC will be calculated/updated, but this may not be intended.

    if header.get_crc_flag() == 1 and not any(payload[-4:]):
        header.set_crc(payload)
