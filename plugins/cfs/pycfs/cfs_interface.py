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
@namespace plugins.cfs.pycfs.cfs_interface
cfs_interface.py: Base-class Lower-level interface to communicate with cFS.
"""
import collections
import ctypes
import importlib
import os
import re
import socket
import traceback
from collections import namedtuple

# external dependencies
from lib import ctf_utility
from lib.ctf_global import Global, CtfVerificationStage
from lib.exceptions import CtfConditionError
from lib.logger import logger as log

OPERATION_DIC = {
    "==": float.__eq__,
    "!=": float.__ne__,
    "<=": float.__le__,
    ">=": float.__ge__,
    "<": float.__lt__,
    ">": float.__gt__
}

# This is defining a tuple with 3 fields. mid, payload and packetCount
Packet = namedtuple('Packet', 'mid header payload packetCount timestamp')
TlmCondition = namedtuple('TlmCondition', 'mid args')


class TelemetryVerification:
    """
    Telemetry Verification class
    """

    def __init__(self, v_id, condition):
        """
        Constructor for TelemetryVerification class.  Assign attribute default values.
        """
        self.verification_id = v_id
        self.condition = condition
        self.passed = False
        self.pass_count = 0
        self.fail_count = 0


class CfsInterface:
    """
    CfsInterface: Base-class Lower-level interface to communicate with cFS.
    """

    def __init__(self, config, telemetry, command, mid_map, ccsds):
        """
        Constructor for CfsInterface class.  Assign config, telemetry, command, mid_map,
        and ccsds arguments to interface attributes
        """
        self.config = config
        self.is_running = False

        if self.config.evs_long_event_mid_name in mid_map:
            self.evs_long_event_msg_mid = mid_map[self.config.evs_long_event_mid_name]["MID"]
            log.debug("Capturing EVS long event messages for MID {} ({})"
                      .format(self.config.evs_long_event_mid_name, hex(self.evs_long_event_msg_mid)))
        else:
            self.evs_long_event_msg_mid = -1
            log.error("{} not found in MID map! EVS long event messages will not be captured."
                      .format(self.config.evs_long_event_mid_name))

        if self.config.evs_short_event_mid_name in mid_map:
            self.evs_short_event_msg_mid = mid_map[self.config.evs_short_event_mid_name]["MID"]
            log.debug("Capturing EVS short event messages for MID {} ({})"
                      .format(self.config.evs_short_event_mid_name, hex(self.evs_short_event_msg_mid)))
        else:
            self.evs_short_event_msg_mid = -1
            log.error("{} not found in MID map! EVS short event messages will not be captured."
                      .format(self.config.evs_short_event_mid_name))

        self.init_passed = False

        self.command = command
        self.telemetry = telemetry
        if self.config.tlm_udp_port == 0:
            self.config.tlm_udp_port = self.telemetry.get_port()

        self.mid_payload_map = {}
        self.mid_payload_map.update({
            val["MID"]: val["PARAM_CLASS"] for val in mid_map.values() if "PARAM_CLASS" in val
        })
        self.mid_payload_map.update({
            val["MID"]: val["CC"] for val in mid_map.values() if "CC" in val
        })

        # This call will determine which output app to use and instantiate it
        output_app_interface = importlib.import_module('plugins.cfs.pycfs.output_app_interface')
        tlm_app_choice = getattr(output_app_interface, self.config.tlm_app_choice)
        log.debug("Imported CFS Output Interface: {}".format(tlm_app_choice))

        self.output_manager = tlm_app_choice(self.config.ctf_ip,
                                             self.config.tlm_udp_port,
                                             self.command,
                                             self.config.ccsds_ver,
                                             self.mid_payload_map,
                                             self.config.name)
        self.cfs_std_out_path = None
        self.evs_log_file = None
        self.tlm_log_file = None
        # This flag is used to indicate the tlm is starting to come
        # in from the CFS application being tested
        self.tlm_has_been_received = False

        # List of MIDs for packets that have been received since the last continuous telemetry check
        self.unchecked_packet_mids = []
        self.tlm_verifications_by_mid_and_vid = {}

        self.cmd_packet_list = []
        self.received_mid_packets_dic = {mid: [] for mid in self.mid_payload_map}

        # These two arrays are used to ensure that the code only prints that it is receiving packets from each specific
        # mid once and not every time a packet is received
        self.has_received_mid = {mid: False for mid in self.mid_payload_map}

        self.ccsds = ccsds
        self.pheader_offset = ctypes.sizeof(self.ccsds.CcsdsPrimaryHeader())
        self.should_skip_header = not self.config.ccsds_header_info_included
        self.tlm_header_offset = ctypes.sizeof(self.ccsds.CcsdsTelemetry)
        self.cmd_header_offset = ctypes.sizeof(self.ccsds.CcsdsCommand)

    def build_cfs(self):
        """
        Abstract class method, raise NotImplementedError exception
        """
        raise NotImplementedError

    def start_cfs(self, run_args):
        """
        Abstract class method, raise NotImplementedError exception
        """
        raise NotImplementedError

    def stop_cfs(self):
        """
        Stop CFS executable instance, close command and telemetry sockets.
        """
        log.info("Stopping CFS Executable")

        # Close command and telemetry sockets
        self.command.cleanup()
        self.telemetry.cleanup()

        # Close files
        if self.tlm_log_file is not None and not self.tlm_log_file.closed:
            log.debug("Closing tlm log file {}".format(self.tlm_log_file.name))
            self.tlm_log_file.close()
            self.tlm_log_file = None
        if self.evs_log_file is not None and not self.evs_log_file.closed:
            log.debug("Closing evs log file {}".format(self.evs_log_file.name))
            self.evs_log_file.close()
            self.evs_log_file = None

        self.is_running = False

        for v_ids in self.tlm_verifications_by_mid_and_vid.values():
            for v_id, verification in v_ids.items():
                log.info("Continuous Telemetry Check {} on {}:".format(v_id, self.output_manager.name))
                log.info("Number times Passed:                {}".format(verification.pass_count))
                log.info("Number times Failed:                {}".format(verification.fail_count))

    def write_tlm_log(self, payload, buf, mid):
        """
        Write payload and mid to telemetry log file. if log file does not exist, create one.
        """
        try:
            if self.tlm_log_file is None:
                tlm_log_file_path = os.path.join(Global.current_script_log_dir, self.config.name + "_tlm_msgs.log")
                self.tlm_log_file = open(tlm_log_file_path, "a+")
                self.tlm_log_file.write("Time: MID, Data\n")
                # update build-in variable for ctf tlm folder
                ctf_utility.set_variable("_CTF_TLM_DIR", "=", os.path.abspath(Global.current_script_log_dir), "string")

            self.tlm_log_file.write("{}: {}\n\t{}\n".format(Global.get_time_manager().exec_time, hex(mid),
                                                            str(payload).replace("\n", "\n\t")))
            if self.config.telemetry_debug:
                self.tlm_log_file.write("        For MID {} Payload length: {} hex values: 0x{}\n".format(hex(mid),
                                                                                                          len(buf),
                                                                                                          buf.hex()))
        except (IOError, ValueError):
            log.error("Failed to write telemetry packet received for {}".format(hex(mid)))
            log.debug(traceback.format_exc())

    def write_evs_log(self, payload):
        """
        Write payload and mid to evs log file. if log file does not exist, create one.
        """
        # If this is the first call then the file will need to be opened
        payload = payload.Payload
        try:
            if self.evs_log_file is None:
                evs_log_file_path = os.path.join(Global.current_script_log_dir, self.config.name + "_evs_msgs.log")
                self.evs_log_file = open(evs_log_file_path, "a+")
            self.evs_log_file.write("%s/%s/%s %s: %s\n" %
                                    (payload.PacketID.SpacecraftID,
                                     payload.PacketID.ProcessorID,
                                     payload.PacketID.AppName.decode(),
                                     payload.PacketID.EventID,
                                     payload.Message.decode() if hasattr(payload, "Message") else ""))
        except (UnicodeDecodeError, IOError, ValueError):
            log.error("Failed to write event packet to EVS Log file for Event Payload: {}".format(str(payload)))
            log.debug(traceback.format_exc())

    def read_sb_packets(self):
        """
        read_sb_packets() is responsible for receiving packets coming from the CFS application that is being tested
        and placing them in a dictionary of lists that is ordered by mids as shown below.
        received_mid_packets_dic = {
            "mid1": ["The last packet received with mid1"],
            "mid2": ["The last packet received with mid2"]
         }
         }
        """
        mids_read = []
        while True:
            # Read from the socket until no more data available
            try:
                recvd = bytearray(self.telemetry.read_socket())
                if len(recvd) <= 0:
                    break
                # Pull the primary header from the received data
                try:
                    pheader = self.ccsds.CcsdsPrimaryHeader.from_buffer(recvd[0:self.pheader_offset])
                except ValueError:
                    log.error("Cannot create CCSDS Primary Header")
                    log.debug("Invalid header bytes: {}".format(recvd.hex()))
                    continue

                mids_read.append(pheader.get_msg_id())
                # If the packet is a command packet it is handled differently
                if pheader.is_command():
                    self.parse_command_packet(recvd)
                else:
                    self.parse_telemetry_packet(recvd)
            except socket.timeout:
                log.warning("No telemetry received from CFS. Socket timeout...")
                break
        if mids_read:
            log.debug("Received {} packets at time {}:".format(len(mids_read), Global.get_time_manager().exec_time))
            mids_read = sorted(collections.Counter(mids_read).items())
            log.debug(", ".join(["{}: {}".format(hex(mid), count) for mid, count in mids_read]))

    def parse_command_packet(self, buffer):
        """
        Parse command packets from received buffer.
        """
        try:
            header = self.ccsds.CcsdsCommand.from_buffer(buffer[0:self.cmd_header_offset])
            mid = header.get_msg_id()
        except ValueError:
            log.debug("Cannot retrieve command header.")
            return

        if mid not in self.mid_payload_map:
            self.log_unknown_packet_mid(mid)
            return

        cmd_dict = self.mid_payload_map[mid]
        cc_class = None
        offset = self.cmd_header_offset if self.should_skip_header else 0
        for value in cmd_dict.values():
            if value["CODE"] == header.get_function_code():
                cc_class = value["ARG_CLASS"]

        try:
            payload = {
                "CC": header.get_function_code(),
                "ARGS": cc_class.from_buffer(buffer[offset:]) if cc_class is not None else None
            }
        except (ValueError, IOError):
            self.log_invalid_packet(mid)
            return

        self.on_packet_received(mid, header, payload)

    def parse_telemetry_packet(self, buffer):
        """
        Parse telemetry packets from received buffer.
        """
        try:
            header = self.ccsds.CcsdsTelemetry.from_buffer(buffer[0:self.tlm_header_offset])
            mid = header.get_msg_id()
        except ValueError:
            log.debug("Cannot retrieve telemetry header.")
            return

        if mid not in self.mid_payload_map:
            self.log_unknown_packet_mid(mid)
            return

        param_class = self.mid_payload_map[mid]
        offset = self.tlm_header_offset if self.should_skip_header else 0
        try:
            payload = param_class.from_buffer(buffer[offset:])
        except ValueError:
            self.log_invalid_packet(mid)
            return

        self.write_tlm_log(payload, buffer[offset:], mid)
        self.on_packet_received(mid, header, payload)
        if mid in [self.evs_long_event_msg_mid, self.evs_short_event_msg_mid]:
            # Write this packet to the CFS EVS Log File
            self.write_evs_log(payload)

    def log_unknown_packet_mid(self, mid):
        """
        If this is the first time receiving a packet with the given mid, log the message.
        """
        msg = "Received Message with MID = {}. This MID is not in the CCSDS MID Map. Ignoring..." \
            .format(hex(mid))
        if mid not in self.has_received_mid:
            log.warning(msg)
            self.has_received_mid[mid] = True
        # Always print error in debug to indicate to user that an MID is missing
        log.debug(msg)

    def log_invalid_packet(self, mid):
        """
        If this is the first time receiving a packet with the given mid, log the packet.
        """
        if not self.has_received_mid[mid]:
            log.error("Cannot retrieve payload from packet with MID {}.".format(hex(mid)))
            self.has_received_mid[mid] = True
            log.debug(traceback.format_exc())

    def on_packet_received(self, mid: int, header: any, payload: any) -> None:
        """
        If this is the first time receiving a packet with the given mid then print the value of the mid.
        """
        exec_time = Global.get_time_manager().exec_time
        if not self.has_received_mid[mid]:
            log.info("Receiving first packet for Data Type: {} with MID: {} at time: {}"
                     .format(type(payload).__name__, hex(mid), exec_time))

            # Update the array so that the message is not printed again
            self.has_received_mid[mid] = True

        payload_count = len(self.received_mid_packets_dic[mid]) + 1
        # Add the received packet to the dictionary under the correct mid
        packet = Packet(mid, header, payload, payload_count, exec_time)
        self.received_mid_packets_dic[mid].append(packet)
        self.tlm_has_been_received = True
        self.unchecked_packet_mids.append(mid)

    def add_tlm_condition(self, v_id, mid, args):
        """
        Add verification condition (with ID) to telemetry verification dictionary and do verification based on id
        """
        if [v_ids for v_ids in self.tlm_verifications_by_mid_and_vid.values() if v_id in v_ids]:
            log.error("Condition with id {} is already registered! Check your test instructions".format(v_id))
            return False

        mid_val = mid["MID"]
        if mid_val not in self.tlm_verifications_by_mid_and_vid:
            self.tlm_verifications_by_mid_and_vid[mid_val] = {}

        self.tlm_verifications_by_mid_and_vid[mid_val][v_id] = \
            TelemetryVerification(v_id, TlmCondition(mid, args))
        return True

    def remove_tlm_condition(self, v_id):
        """
        Remove verification condition (with ID) from telemetry verification dictionary.
        """
        verification = next((ids[v_id] for ids in self.tlm_verifications_by_mid_and_vid.values() if v_id in ids), None)
        if not verification:
            if self.config.remove_continuous_on_fail:
                log.error(
                    "Condition with id {} is not registered! It may have failed earlier in the test.".format(v_id))
            else:
                log.error("Condition with id {} is not registered! Check your test instructions.".format(v_id))
            return False

        log.info("Continuous Telemetry Check {} on {}:".format(v_id, self.output_manager.name))
        log.info("Number times Passed:                {}".format(verification.pass_count))
        log.info("Number times Failed:                {}".format(verification.fail_count))

        self.tlm_verifications_by_mid_and_vid[verification.condition.mid['MID']].pop(v_id)
        return True

    def check_tlm_conditions(self):
        """
        Check all unchecked telemetry message by mid and vid.
        If verification fails, raise CtfConditionError exception.
        """
        for mid in self.unchecked_packet_mids:
            if mid in self.tlm_verifications_by_mid_and_vid:
                for v_id, verification in self.tlm_verifications_by_mid_and_vid[mid].items():
                    # If there is only one packet for this MID it will be the placeholder
                    if len(self.received_mid_packets_dic[mid]) == 1:
                        continue

                    if not self.check_tlm_value(*verification.condition,
                                                discard_old_packets=False):
                        if self.config.remove_continuous_on_fail:
                            self.remove_tlm_condition(v_id)
                        verification.fail_count += 1
                        raise CtfConditionError("Continuous Telemetry Check {} Failed.".format(v_id), verification)
                    verification.passed = True
                    verification.pass_count += 1
        self.unchecked_packet_mids.clear()

    def send_command(self, msg_id, function_code, data, header_args=None):
        """
        Send instruction to CFS instance through command interface.
        """
        sent_bytes = self.command.send_command(msg_id, function_code, data, header_args)
        return sent_bytes

    @staticmethod
    def check_strings(actual, expected, equal):
        """
        Check whether string argument actual == string argument expected,
        if yes, return argument equal, otherwise return not equal
        """
        check_status = not equal
        if isinstance(actual, str) and isinstance(expected, str):
            if actual == expected:
                check_status = equal
            else:
                log.warning('String comparison failed, actual value:%s streq expected value: %s', actual, expected)

        else:  # if there was no string to compare
            log.warning('String comparison failed, actual value:%s streq expected value: %s', actual, expected)
            check_status = False

        return check_status

    def check_value(self, actual, expected, compare, mask, mask_value):
        """
        Based on the argument compare value, use different method to compare argument actual and expected
        """
        if compare in ['streq', 'strneq', 'regex']:
            if not isinstance(actual, str):
                log.warning("Type mismatch for comparator '{}'! Actual value {} is not a string."
                            .format(compare, actual))
            if not isinstance(expected, str):
                log.warning("Type mismatch for comparator '{}'! Expected value {} is not a string."
                            .format(compare, expected))

        if compare == "streq":
            return self.check_strings(actual, expected, True)
        if compare == "strneq":
            return self.check_strings(actual, expected, False)
        if compare == "regex":
            regex_cmpstatus = False
            if isinstance(actual, str) and isinstance(expected, str):
                if re.search(expected, actual):
                    regex_cmpstatus = True
                else:
                    log.warning('Regex match failed, actual value:%s regex value: %s', actual, expected)
            else:
                log.warning('Regex match failed, actual value:%s regex value: %s', actual, expected)

            return regex_cmpstatus

        # Strings are processed above, at this point we are processing numbers

        # ENHANCE - Add type and overflow checking based on the ctype of the actual value.
        #           We need to either parse the message type's fields to determine the actual ctype and its size,
        #           or extend the types when they are created to expose the ctype used for primitive fields
        if compare in OPERATION_DIC:

            if isinstance(actual, str):
                log.warning("Type mismatch for comparator '{}'! Actual value '{}' is a string."
                            .format(compare, actual))
            if isinstance(expected, str) and not expected.lower().startswith("0x"):
                log.warning("Type mismatch for comparator '{}'! Expected value '{}' is a string."
                            .format(compare, expected))

            try:
                actual = float(actual)
                # the expected is a numerical type. However, if it is a hex string like 0x12' or '0X12',
                # need to convert it to int first, before converting to float
                if isinstance(expected, str) and expected.lower().startswith("0x"):
                    expected = int(expected, 0)
                expected = float(expected)
            except ValueError as exception:
                log.error("Failed to convert args: {}".format(exception))
                return False

            if mask is not None and mask_value is not None:
                try:
                    if mask == "&":
                        masked = int(actual) & mask_value
                        result = OPERATION_DIC[compare](float(masked), expected)
                    elif mask == "|":
                        masked = int(actual) | mask_value
                        result = OPERATION_DIC[compare](float(masked), expected)
                    else:
                        log.error("Invalid Mask Value: {}".format(mask))
                        result = False
                except (TypeError, ValueError) as exception:
                    log.error("Failed to apply mask: {}".format(exception))
                    result = False
            elif mask is not None:
                log.error("Invalid comparison: mask provided without maskValue")
                result = False
            elif mask_value is not None:
                log.error("Invalid comparison: maskValue provided without mask")
                result = False
            else:
                result = OPERATION_DIC[compare](actual, expected)
        else:
            log.error('Invalid Comparison Value: {}'.format(compare))
            result = False

        return result

    def clear_received_msgs_before_verification_start(self, mid):
        """
        Given a mid argument, iterate over all received packets.
        If packets' received time expires, clear the packets with matching mid.
        """
        if not self.received_mid_packets_dic.get(mid):
            log.warning("No messages received for MID: {} to clear.".format(hex(mid)))
            return
        if mid in [self.evs_long_event_msg_mid, self.evs_short_event_msg_mid]:
            start_time = Global.time_manager.exec_time - self.config.evs_messages_clear_after_time
        else:
            start_time = Global.current_verification_start_time
        log.debug("Clearing received packets for MID: {} before time = {}"
                  .format(hex(mid), start_time))
        self.received_mid_packets_dic[mid] = [
            self.received_mid_packets_dic[mid][index]
            for index, i in enumerate(self.received_mid_packets_dic[mid])
            if i.timestamp >= start_time
        ]
        return

    def check_tlm_value(self, mid, args=None, discard_old_packets=True):
        """
         Given a mid and a arguments, iterate over all received packets since the start of the verification.
         Validate each packet until a success is seen, or there are no more packets to check.
        """
        # Flag indicating result of current CheckTlmValue
        check_tlm_result = True
        if isinstance(mid, dict):
            mid_name = mid
            mid = mid.get("MID")
            if mid is None:
                log.error("No MID Value found in: {}".format(mid_name))
                check_tlm_result = False
        if mid not in self.received_mid_packets_dic:
            log.error("Unknown MID value {}".format(mid))
            check_tlm_result = False

        if Global.current_verification_stage == CtfVerificationStage.first_ver:
            self.clear_received_msgs_before_verification_start(mid)

        if check_tlm_result and len(self.received_mid_packets_dic[mid]) == 0:
            log.debug("No messages received between polling to check. MID = {}".format(hex(mid)))
            check_tlm_result = False

        # If any of the above validation fails, there is no need to proceed into the packets
        # and the instruction will fail.
        if not check_tlm_result:
            return check_tlm_result

        # Traverse packets backwards validating each packet for the selected MID
        for i in range(len(self.received_mid_packets_dic[mid]) - 1, -1, -1):
            # Get current packet for the selected MID
            payload = self.received_mid_packets_dic[mid][i].payload

            # Check that a payload exists, otherwise proceed to the next packet
            if payload is None:
                log.error("Failed to extract packet from received MID: {}. Continuing...".format(hex(mid)))
                continue
            # Check the current packet against provided args, if any. If successful,
            # the check_tlm_value will pass and discard packets if needed.
            check_tlm_result = (not args) or self.check_tlm_packet(payload, args)
            if check_tlm_result:
                break

        if discard_old_packets:
            self.received_mid_packets_dic[mid] = []
        return check_tlm_result

    def get_tlm_value(self, mid: dict, tlm_variable: str, is_header: bool = False):
        """
        Given a mid and a tlm_variable, iterate over all received packets, and return the latest tlm value.
        """
        latest_tlm_value = None
        if isinstance(mid, dict):
            mid_name = mid
            mid = mid.get("MID")
            if mid is None:
                log.error("No MID Value found in: {}".format(mid_name))
                return None
        if mid not in self.received_mid_packets_dic:
            log.error("Unknown MID value {}".format(mid))
            return None

        if len(self.received_mid_packets_dic[mid]) == 0:
            log.error("No messages received for MID = {}".format(hex(mid)))
            return None

        # Traverse packets backwards validating each packet for the selected MID
        log.debug("There are {} packets with mid {}".format(len(self.received_mid_packets_dic[mid]), hex(mid)))
        for i in range(len(self.received_mid_packets_dic[mid]) - 1, -1, -1):
            # Get current packet for the selected MID
            packet = self.received_mid_packets_dic[mid][i]
            data = packet.header if is_header else packet.payload
            log.debug("packet data = {} ".format(data))
            # Check that a payload exists, otherwise proceed to the next packet
            if data is None:
                log.error("Failed to extract packet from received MID: {}. Continuing...".format(hex(mid)))
                continue
            latest_tlm_value = ctf_utility.rgetattr(data, tlm_variable, None)

            if isinstance(latest_tlm_value, bytes):
                log.info("Bytes object {} is decoded to {}".format(latest_tlm_value, latest_tlm_value.decode()))
                latest_tlm_value = latest_tlm_value.decode()

            if latest_tlm_value is not None:
                break

        return latest_tlm_value

    def check_tlm_packet(self, payload, args):
        """
        Check telemetry message's value based on argument payload and args
        """
        packet_passed = True
        # Compare the current packet to the expected packet using each variable in args.
        for arg in args:
            expected_value = arg.get("value")
            if isinstance(expected_value, list):
                expected_value = expected_value[0]
            variable = arg.get("variable")
            mask = arg.get("mask")
            mask_value = arg.get("maskValue")
            tol = arg.get("tolerance")
            tol_plus = arg.get("tolerance_plus")
            tol_minus = arg.get("tolerance_minus")

            if expected_value is None:
                # If there is no expected value provided, check_tlm_value will fail before
                # checking packets since there is no value to compare to.
                if Global.current_verification_stage == CtfVerificationStage.first_ver:
                    log.error("No expected 'value' provided in arg: {}. with payload {}".format(arg, payload))
                packet_passed = False

            if variable is None:
                # If there is no variable provided, check_tlm_value will fail before
                # checking packets since there is no value to compare to.
                if Global.current_verification_stage == CtfVerificationStage.first_ver:
                    log.error("No variable provided in arg: {}".format(arg))
                packet_passed = False

            if not packet_passed:
                return packet_passed

            if tol is not None:
                tol_plus = tol
                tol_minus = tol
            if tol_plus is None:
                tol_plus = 0
            if tol_minus is None:
                tol_minus = 0
            try:
                actual = ctf_utility.rgetattr(payload, variable)
            except (AttributeError, ValueError) as exception:
                log.error("Failed to evaluate variable payload.{}: {}".format(variable, exception))
                log.debug(traceback.format_exc())
                packet_passed = False
                break

            if isinstance(actual, bytes):
                log.info("Bytes object {} is decoded to {}".format(actual, actual.decode()))
                actual = actual.decode()

            initial_result = self.check_value(actual, expected_value, arg["compare"], mask, mask_value)
            arg_result = initial_result

            if tol_plus:
                tol_plus_value = expected_value + tol_plus
                tol_plus_result = self.check_value(actual, tol_plus_value, "<=", mask, mask_value)
                tol_plus_result &= self.check_value(actual, expected_value, ">=", mask, mask_value)
                arg_result |= tol_plus_result

            if tol_minus:
                tol_minus_value = expected_value - tol_minus
                tol_minus_result = self.check_value(actual, tol_minus_value, ">=", mask, mask_value)
                tol_minus_result &= self.check_value(actual, expected_value, "<=", mask, mask_value)
                arg_result |= tol_minus_result

            if not arg_result:
                log.warning(
                    'FAILED Intermediate Check - {}: Actual: {}, Expected: {}, Comparison: {}, Tol: +{}, -{}'.format(
                        variable, actual, expected_value, arg["compare"], tol_plus, tol_minus))
            else:
                log.info(
                    'PASSED Intermediate Check - {}: Actual: {}, Expected: {}, Comparison: {}, Tol: +{}, -{}'.format(
                        variable, actual, expected_value, arg["compare"], tol_plus, tol_minus))
            packet_passed = packet_passed and arg_result

        return packet_passed

    def enable_output(self):
        """
        Send a command to enable output and check if we receive a response
        """
        count = 0
        while True:
            count += 1
            self.output_manager.enable_output()
            Global.time_manager.wait(1)

            if self.tlm_has_been_received:
                return True
            if count > 60:
                log.error("Unable to connect to CFS mission")
                return False
