"""
cfs_interface.py: Base-class Lower-level interface to communicate with cFS.
"""

import os
import re
import sys
import ctypes
import socket
import traceback
from collections import namedtuple

# external dependencies
from lib.Global import Global, CtfVerificationStage
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
Packet = namedtuple('Packet', 'mid payload packetCount timestamp')
TlmCondition = namedtuple('TlmCondition', 'mid args')


class TelemetryVerification(object):
    def __init__(self, v_id, condition):
        self.verification_id = v_id
        self.condition = condition
        self.passed = False
        self.pass_count = 0
        self.fail_count = 0


class CfsInterface(object):

    def __init__(self, config, telemetry, command, mid_map, ccsds):
        self.config = config

        if self.config.evs_event_mid_name in mid_map:
            self.evs_event_msg_mid = mid_map[self.config.evs_event_mid_name]["MID"]
        else:
            self.evs_event_msg_mid = -1
            log.error("{} not found in MID map! EVS event messages will not be captured.")

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
        log.debug("Imported CFS Output Interface")
        tlm_app_choice = getattr(sys.modules['plugins.cfs.pycfs.output_app_interface'], self.config.tlm_app_choice)
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
        self.received_mid_packets_dic = {mid: [] for mid in self.mid_payload_map.keys()}

        # These two arrays are used to ensure that the code only prints that it is receiving packets from each specific
        # mid once and not every time a packet is received
        self.has_received_mid = {mid: False for mid in self.mid_payload_map.keys()}

        self.ccsds = ccsds
        self.pheader_offset = ctypes.sizeof(self.ccsds.CcsdsPrimaryHeader())
        self.should_skip_header = not self.config.CCSDS_header_info_included
        self.tlm_header_offset = ctypes.sizeof(self.ccsds.CcsdsTelemetry)
        self.cmd_header_offset = ctypes.sizeof(self.ccsds.CcsdsCommand)

    def build_cfs(self):
        raise NotImplementedError

    def start_cfs(self, run_args):
        raise NotImplementedError

    def stop_cfs(self):
        log.info("Stopping CFS Executable")

        # Close command and telemetry sockets
        self.command.cleanup()
        self.telemetry.cleanup()

        for v_ids in self.tlm_verifications_by_mid_and_vid.values():
            for v_id, verification in v_ids.items():
                log.info("Continuous Telemetry Check {} on {}:".format(v_id, self.output_manager.name))
                log.info("Number times Passed:                {}".format(verification.pass_count))
                log.info("Number times Failed:                {}".format(verification.fail_count))

    def write_tlm_log(self, payload, mid):
        if self.tlm_log_file is None:
            tlm_log_file_path = os.path.join(Global.current_script_log_dir, self.config.name + "_tlm_msgs.log")
            self.tlm_log_file = open(tlm_log_file_path, "w+")
            self.tlm_log_file.write("Time: MID, Data\n")
        try:
            self.tlm_log_file.write("{}: {}\n\t{}\n".format(Global.get_time_manager().exec_time, hex(mid),
                                                            str(payload).replace("\n", "\n\t")))
        except (IOError, Exception):
            log.error("Failed to write telemetry packet received for {}".format(hex(mid)))
            traceback.format_exc()

    def write_evs_log(self, payload):
        # If this is the first call then the file will need to be opened
        payload = payload.Payload
        if self.evs_log_file is None:
            evs_log_file_path = os.path.join(Global.current_script_log_dir, self.config.name + "_evs_msgs.log")
            self.evs_log_file = open(evs_log_file_path, "w")
        try:
            self.evs_log_file.write("%s/%s/%s %s: %s\n" %
                                    (payload.PacketID.SpacecraftID,
                                     payload.PacketID.ProcessorID,
                                     payload.PacketID.AppName,
                                     payload.PacketID.EventID,
                                     payload.Message))
        except UnicodeDecodeError:
            log.error("Failed to write event packet to EVS Log file for Event Payload: {}".format(str(payload)))
            traceback.format_exc()

    # read_sb_packets() is responsible for receiving packets coming from the CFS application that is being tested
    # and placing them in a dictionary of lists that is ordered by mids as shown below.
    # received_mid_packets_dic = {
    #   "mid1": ["The last packet received with mid1"],
    #   "mid2": ["The last packet received with mid2"]
    # }
    def read_sb_packets(self):
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
                    continue

                # If the packet is a command packet it is handled differently
                if pheader.is_command():
                    # Pull the command header from the received data
                    try:
                        header = self.ccsds.CcsdsCommand.from_buffer(recvd[0:self.cmd_header_offset])
                        mid = header.get_msg_id()
                    except ValueError:
                        log.debug("Cannot retrieve command header.")
                        continue

                    cmd_dict = self.mid_payload_map[mid]
                    cc_class = None
                    for value in cmd_dict.values():
                        if value["CODE"] == header.get_function_code():
                            cc_class = value["ARG_CLASS"]

                    payload = {
                        "CC": header.get_function_code(),
                        "ARGS": cc_class.from_buffer(
                            recvd[self.cmd_header_offset:]) if cc_class is not None else None
                    }
                    if not self.has_received_mid[mid]:
                        log.info("Receiving command packets for MID: %s", hex(mid))
                        self.has_received_mid[mid] = True
                    packet_count = len(self.received_mid_packets_dic[mid]) + 1
                    # Add the received packet to the dictionary under the correct mid
                    self.received_mid_packets_dic[mid].append(Packet(mid, payload, packet_count,
                                                                     Global.get_time_manager().exec_time))
                    self.tlm_has_been_received = True
                    self.unchecked_packet_mids.append(mid)
                else:
                    try:
                        header = self.ccsds.CcsdsTelemetry.from_buffer(recvd[0:self.tlm_header_offset])
                        mid = header.get_msg_id()
                    except ValueError:
                        log.debug("Cannot retrieve command header.")
                        continue
                    # The received packet is a telemetry packet and its mid must be in the telemetry_watch
                    # list of the test script being executed
                    if mid not in self.mid_payload_map:
                        msg = "Received Message with MID = {}. This MID is not in the CCSDS MID Map. Ignoring..."\
                            .format(hex(mid))
                        if mid not in self.has_received_mid:
                            log.warn(msg)
                            self.has_received_mid[mid] = True
                        # Always print error in debug to indicate to user that an MID is missing
                        log.debug(msg)
                        continue
                    # Retrieve the payload from the received packet
                    try:
                        payload = self.mid_payload_map[mid].from_buffer(
                            recvd[self.tlm_header_offset if self.should_skip_header else 0:])
                        self.write_tlm_log(payload, mid)
                    except (ValueError, Exception):
                        if not self.has_received_mid[mid]:
                            log.error("Cannot retrieve payload from TLM packet with MID {}.".format(hex(mid)))
                            self.has_received_mid[mid] = True
                            log.debug(traceback.format_exc())
                        continue

                    # If this is the first time receiving a packet with the given mid than print
                    # the value of the mid.
                    if not self.has_received_mid[mid]:
                        log.info("Receiving Telemetry Packets for Data Type: {} with MID: {}"
                                 .format(self.mid_payload_map[mid].__name__, hex(mid)))

                        # Update the print_once_tlm array so that the message is not printed again
                        self.has_received_mid[mid] = True

                    payload_count = len(self.received_mid_packets_dic[mid]) + 1
                    # Add the received packet to the dictionary under the correct mid
                    self.received_mid_packets_dic[mid].append(Packet(mid, payload, payload_count,
                                                                     Global.get_time_manager().exec_time))
                    self.tlm_has_been_received = True
                    self.unchecked_packet_mids.append(mid)
                    if mid == self.evs_event_msg_mid:
                        # Write this packet to the CFS EVS Log File
                        self.write_evs_log(payload)
            except socket.timeout:
                log.warn("No telemetry received from CFS. Socket timeout...")
                break
        return

    def add_tlm_condition(self, v_id, mid, args):
        if [v_ids for v_ids in self.tlm_verifications_by_mid_and_vid if v_id in v_ids]:
            log.error("Condition with id {} is already registered! Check your test instructions".format(v_id))
            return False

        mid_val = mid["MID"]
        if mid_val not in self.tlm_verifications_by_mid_and_vid:
            self.tlm_verifications_by_mid_and_vid[mid_val] = {}

        self.tlm_verifications_by_mid_and_vid[mid_val][v_id] = \
            TelemetryVerification(v_id, TlmCondition(mid, args))
        return True

    def remove_tlm_condition(self, v_id):
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

    def send_command(self, msg_id, function_code, data):
        sent_bytes = self.command.send_command(msg_id, function_code, data, self.config.ccsds_ver)
        return sent_bytes

    def send_telemetry(self, msg_id, data):
        sent_bytes = self.command.send_telemetry(msg_id, data)
        return sent_bytes

    @staticmethod
    def check_strings(actual, expected, equal):
        if isinstance(actual, str):  # if there is a string to compare
            if actual == expected:
                return equal
            else:
                log.warn('String comparison failed, actual value:%s streq expected value: %s', actual, expected)
                return not equal

        else:  # if there was no string to compare
            log.warn('String comparison failed, actual value:%s streq expected value: %s', actual, expected)
            return False

    def check_value(self, actual, expected, compare, mask, mask_value):
        if isinstance(actual, bytes):
            actual = actual.decode()

        if compare == "streq":
            return self.check_strings(actual, expected, True)
        if compare == "strneq":
            return self.check_strings(actual, expected, False)
        if compare == "regex":
            if isinstance(actual, str):
                if re.search(expected, actual):
                    return True
                else:
                    log.warn('Regex match failed, actual value:%s regex value: %s', actual, expected)
                    return False
            else:
                log.warn('Regex match failed, actual value:%s regex value: %s', actual, expected)
                return False

        # Strings are processed above, at this point we are processing numbers

        # TODO - Add type and overflow checking based on the ctype of the actual value.
        #           We need to either parse the message type's fields to determine the actual ctype and its size,
        #           or extend the types when they are created to expose the ctype used for primitive fields
        if compare in OPERATION_DIC:
            try:
                actual = float(actual)
                expected = float(expected)
            except ValueError as e:
                log.error("Failed to convert args: {}".format(e))
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
                except ValueError as e:
                    log.error("Failed to apply mask: {}".format(e))
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
        if mid not in self.received_mid_packets_dic:
            log.error("No messages received for MID: {} to clear.".format(hex(mid)))
            return
        time_offset = 0
        if mid == self.evs_event_msg_mid:
            time_offset += self.config.evs_messages_clear_after_time
        start_time = Global.current_verification_start_time - time_offset
        log.debug("Clearing received packets for MID: {} before time = {}"
                  .format(hex(mid), start_time))
        self.received_mid_packets_dic[mid] = [
            self.received_mid_packets_dic[mid][index]
            for index, i in enumerate(self.received_mid_packets_dic[mid])
            if i.timestamp >= start_time
        ]
        return

    # Given an MID to check and arguments, iterate over all received packets
    # since the start of the verification. Validate each packet until a success
    # is seen, or there are no more packets to check.
    def check_tlm_value(self, mid, args, discard_old_packets=True):
        # Flag indicating result of current CheckTlmValue
        check_tlm_result = True
        if isinstance(mid, dict):
            mid_name = mid
            mid = mid.get("MID")
            if mid is None:
                log.error("Failed to get MID Value for MID Name: {}".format(mid_name))
                check_tlm_result = False

        if Global.current_verification_stage == CtfVerificationStage.first_ver:
            self.clear_received_msgs_before_verification_start(mid)

        if len(self.received_mid_packets_dic[mid]) == 0:
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
            # Check the current packet against provided args. If successful,
            # the check_tlm_value will pass and discard packets if needed.
            check_tlm_result = self.check_tlm_packet(payload, args)
            if check_tlm_result:
                break

        if discard_old_packets:
            self.received_mid_packets_dic[mid] = []
        return check_tlm_result

    def check_tlm_packet(self, payload, args):
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
            tol_plus_result = None
            tol_minus = arg.get("tolerance_minus")
            tol_minus_result = None

            if expected_value is None:
                # If there is no expected value provided, check_tlm_value will fail before
                # checking packets since there is no value to compare to.
                if Global.current_verification_stage == CtfVerificationStage.first_ver:
                    log.error("No expected 'value' provided in arg: {}.".format(arg))
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
            eval_string = ""
            try:
                eval_string = "payload.{}".format(variable)
                actual = eval(eval_string)
            except (SyntaxError, AttributeError) as e:
                log.error("Failed to Evaluate: {}".format(eval_string))
                log.debug(traceback.format_exc())
                continue

            initial_result = self.check_value(actual, expected_value, arg["compare"], mask, mask_value)

            if tol_plus:
                tol_plus_value = expected_value + tol_plus
                tol_plus_result = self.check_value(actual, tol_plus_value, "<=", mask, mask_value)

            if tol_minus:
                tol_minus_value = expected_value - tol_minus
                tol_minus_result = self.check_value(actual, tol_minus_value, ">=", mask, mask_value)

            arg_result = initial_result
            if tol_plus_result and tol_minus_result:
                arg_result = arg_result or (tol_plus_result and tol_minus_result)

            if not arg_result:
                log.warn(
                    'FAILED Intermediate Check - {}: Actual: {}, Expected: {}, Comparison: {}, Tol: +{}, -{}'.format(
                        variable, actual, expected_value, arg["compare"], tol_plus, tol_minus))
            else:
                log.info(
                    'PASSED Intermediate Check - {}: Actual: {}, Expected: {}, Comparison: {}, Tol: +{}, -{}'.format(
                        variable, actual, expected_value, arg["compare"], tol_plus, tol_minus))
            packet_passed = packet_passed and arg_result

        return packet_passed
