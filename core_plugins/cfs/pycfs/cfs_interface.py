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
# File: cfs_interface.py
#
# Purpose: This file defines base-class lower-level interface to communicate with cFS.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

"""
@namespace core_plugins.cfs.pycfs.cfs_interface
cfs_interface.py: Base-class Lower-level interface to communicate with cFS.
"""
import collections
import ctypes
import datetime
import importlib
import os
import re
import socket
import time
import traceback
from collections import namedtuple

# external dependencies
from lib import ctf_utility
from lib.db_manager import DBManager
from lib.ctf_global import Global, CtfVerificationStage
from lib.exceptions import CtfConditionError
from lib.logger import logger as log
from core_plugins.ccsds_plugin.ccsds_packet_interface import CcsdsPacketInterface
from core_plugins.cfs.pycfs.cfs_interface_utility import build_command_packet_header, update_crc, resolve_cfs_macro

# pylint: disable=too-many-lines, too-many-instance-attributes

OPERATION_DIC = {
    "==": float.__eq__,
    "!=": float.__ne__,
    "<=": float.__le__,
    ">=": float.__ge__,
    "<": float.__lt__,
    ">": float.__gt__
}

Packet = namedtuple('Packet', ['mid', 'header', 'payload', 'packetCount', 'timestamp'])
TlmCondition = namedtuple('TlmCondition', ['mid', 'args'])


class InCompletePacket:
    """
    Incomplete Packet class
    """

    def __init__(self, seq, seg_flag, timestamp, buf):
        self.seq = seq
        self.seg_flag = seg_flag
        self.timestamp = timestamp
        self.buf = buf


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

    def __init__(self, config, telemetry, command, mid_map, ccsds, macro_map=None):
        """
        Constructor for CfsInterface class.  Assign config, telemetry, command, mid_map,
        and ccsds arguments to interface attributes
        """
        self.cfs_timestamp = {}
        self.config = config
        self.macro_map = macro_map

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
        self.started_by_ctf = False
        self.command = command
        self.telemetry = telemetry

        self.mid_payload_map = {}
        self.mid_payload_map.update({
            val["MID"]: val["PARAM_CLASS"] for val in mid_map.values() if "PARAM_CLASS" in val
        })
        self.mid_payload_map.update({
            val["MID"]: val["CC"] for val in mid_map.values() if "CC" in val
        })

        self.mid_val_map = {values['MID']: mid for mid, values in mid_map.items()}
        # This call will determine which output app to use and instantiate it
        output_app_interface = importlib.import_module('core_plugins.cfs.pycfs.output_app_interface')
        tlm_app_choice = getattr(output_app_interface, self.config.tlm_app_choice)
        log.debug("Imported CFS Output Interface: {}".format(tlm_app_choice))
        self.output_manager = tlm_app_choice(self.config, self.command, self.mid_payload_map)
        self.cfs_std_out_path = None
        self.evs_log_file = None
        self.tlm_log_file = None
        self.tlm_csv_file = None
        # This flag is used to indicate the tlm is starting to come in from the CFS application being tested
        self.tlm_has_been_received = False

        # List of MIDs for packets that have been received since the last continuous telemetry check
        self.unchecked_packet_mids = []
        self.tlm_verifications_by_mid_and_vid = {}

        self._tlm_payload_set = set()
        self.received_mid_packets_dic = {mid: [] for mid in self.mid_payload_map}

        # These two arrays are used to ensure that the code only prints that it is receiving packets from each specific
        # mid once and not every time a packet is received
        self.has_received_mid = {mid: False for mid in self.mid_payload_map}

        self.ccsds = ccsds
        self.should_skip_header = not self.config.ccsds_header_info_included
        self.tlm_header_offset = ctypes.sizeof(self.ccsds.CcsdsTelemetry)
        self.incomplete_packet_dic = {mid: [] for mid in self.mid_payload_map}

        self.endian = 0 if self.config.endianess_of_target == "big" else 1
        self.crc = self.config.crc

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
        log.info("Disconnecting from CFS target")

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

        for v_ids in self.tlm_verifications_by_mid_and_vid.values():
            for v_id, verification in v_ids.items():
                log.info("Continuous Telemetry Check {} on {}:".format(v_id, self.output_manager.name))
                log.info("Number times Passed:                {}".format(verification.pass_count))
                log.info("Number times Failed:                {}".format(verification.fail_count))

    def __create_tlm_log_file(self):
        try:
            if self.tlm_log_file is None:
                tlm_log_file_path = os.path.join(Global.current_script_log_dir, self.config.name + "_tlm_msgs.log")
                self.tlm_log_file = open(tlm_log_file_path, "a+")
                self.tlm_log_file.write("Time: MID, Data\n")
                log.debug("Create tlm log file {}".format(self.tlm_log_file))
                # update build-in variable for ctf tlm folder
                ctf_utility.set_variable("_CTF_TLM_DIR", "=", os.path.abspath(Global.current_script_log_dir), "string")

            if self.tlm_csv_file is None and self.config.csv_tlm_log and self.config.telemetry_debug:
                tlm_log_csv_path = os.path.join(Global.current_script_log_dir, self.config.name + "_tlm_msgs.csv")
                self.tlm_csv_file = open(tlm_log_csv_path, "a+")
                self.tlm_csv_file.write("MID, Payload Length, Message (in Hex)\n")

        except IOError:
            log.error("Failed to create tlm log file {}")
            log.debug(traceback.format_exc())

    def write_tlm_log(self, payload, buf, header):
        """
        Write payload and mid to telemetry log file. if log file does not exist, create one.
        """
        try:
            if self.tlm_log_file is None:
                self.__create_tlm_log_file()

            mid = header.get_msg_id()
            sequence_count = header.get_sequence_count()
            timestamp_seconds = header.get_timestamp_seconds()
            timestamp_subseconds = header.get_timestamp_subseconds()
            seg_flag = header.pheader.get_segmentation_flags()

            self.tlm_log_file.write(
                "{} - {}: mid:{} seq: {} len: {} seg_flag: {} timestamp_seconds: {} timestamp_subseconds: {}\n\t{}\n".
                format(Global.get_time_manager().exec_time,
                       datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], hex(mid), sequence_count,
                       header.get_msg_size(), seg_flag, timestamp_seconds, timestamp_subseconds,
                       str(payload).replace("\n", "\n\t")))

            if self.config.telemetry_debug:
                self.tlm_log_file.write("        For MID {} Payload length: {} "
                                        "hex values: 0x{}\n".format(hex(mid), len(buf), buf.hex()))
                if self.config.csv_tlm_log:
                    self.tlm_csv_file.write("{}, {}, {}\n".format(hex(mid), len(buf), buf.hex()))

        except (IOError, ValueError):
            log.error("Failed to write telemetry packet received for {}".format(hex(mid)))
            log.debug(traceback.format_exc())

    def write_tlm_error_log(self, mid, description, buf, pkt_size):
        """
        Write telemetry error messages to log file. if log file does not exist, create one.
        """
        try:
            if self.tlm_log_file is None:
                self.__create_tlm_log_file()

            exec_time = Global.get_time_manager().exec_time
            computer_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.tlm_log_file.write("{} - {}: mid:{} \n\t{}\n".
                                    format(exec_time, computer_time, mid, description))
            if self.config.telemetry_debug:
                self.tlm_log_file.write("        For MID {} buf_len:{} msg_size:{} buf hex values:"
                                        " 0x{}\n".format(mid, len(buf), pkt_size, buf.hex()))
                if self.config.csv_tlm_log:
                    self.tlm_csv_file.write("{}, {}, {}\n".format(mid, len(buf), buf.hex()))

        except (IOError, ValueError):
            log.error("Failed to write telemetry packet received for {}".format(mid))
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
            # one option to replace .flush is print(msg, file=self.evs_log_file, flush=True)
            # but it is not consistent with other .write functions.
            self.evs_log_file.flush()
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
        """
        mids_read = []
        pheader_size = ctypes.sizeof(self.ccsds.CcsdsPrimaryHeader())
        msg_recvd = bytearray()
        while True:
            # Read from the socket until no more data available
            try:
                recvd = bytearray(self.telemetry.read_socket())
                if len(recvd) <= 0:
                    break
                msg_recvd.extend(recvd)
            except socket.timeout:
                log.warning("No telemetry received from CFS. Socket timeout...")
                break

        total_recvd_size = len(msg_recvd)
        processed_size = 0
        while processed_size < total_recvd_size:
            if pheader_size > (total_recvd_size - processed_size):
                log.error("Remaining data smaller than CCSDS PrimaryHeader size: {}".format(pheader_size))
                break
            try:
                pheader = self.ccsds.CcsdsPrimaryHeader.from_buffer(
                    msg_recvd[processed_size:(processed_size + pheader_size)])
            except ValueError:
                log.error("Cannot create CCSDS Primary Header")
                break

            pkt_size = pheader.get_msg_size()
            if pkt_size > (total_recvd_size - processed_size):
                log.error("Remaining data smaller than CCSDS packet size: {}".format(pkt_size))
                break

            pkt_bytearray = msg_recvd[processed_size:(processed_size + pkt_size)]
            processed_size += pkt_size
            # If the packet is a command packet it is handled differently
            if pheader.is_command():
                mid = self.parse_command_packet(pkt_bytearray)
            else:
                mid = self.parse_telemetry_packet(pkt_bytearray)

            if mid is not None:
                mids_read.append(mid)

        if processed_size != total_recvd_size:
            log.error("Could not process partial messages, total received bytes: {} "
                      "  processed bytes: {} ".format(total_recvd_size, processed_size))

        if mids_read:
            log.debug("Received {} packets at time {}:".format(len(mids_read), Global.get_time_manager().exec_time))
            mids_read = sorted(collections.Counter(mids_read).items())
            log.debug(", ".join(["{} ({}): {}".format(hex(mid), self.mid_val_map.get(mid, 'UNKNOWN_MID'), count)
                                 for mid, count in mids_read]))

    def parse_command_packet(self, buffer):
        """
        Parse command packets from received buffer.
        """
        cmd_header_offset = ctypes.sizeof(self.ccsds.CcsdsCommand)
        try:
            header = self.ccsds.CcsdsCommand.from_buffer(buffer[0:cmd_header_offset])
            mid = header.get_msg_id()
        except ValueError:
            log.debug("Cannot retrieve command header.")
            return None

        if mid not in self.mid_payload_map:
            self.log_unknown_packet_mid(mid)
            return None

        cmd_dict = self.mid_payload_map[mid]
        cc_class = None
        offset = cmd_header_offset if self.should_skip_header else 0
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
            return None

        self.on_packet_received(mid, header, payload)
        return mid

    def parse_telemetry_packet(self, buffer):
        """
        Parse telemetry packets from received buffer.
        """

        try:
            header = self.ccsds.CcsdsTelemetry.from_buffer(buffer[0:self.tlm_header_offset])
            mid = header.get_msg_id()
            seg_flag = header.pheader.get_segmentation_flags()
            pkt_size = header.get_msg_size()
            if not header.validate(buffer):
                log.debug("Telemetry packet is discarded as CRC check fails.")
                self.write_tlm_error_log(hex(mid), 'CRC check fail', buffer, pkt_size)
                return None
        except ValueError:
            log.debug("Cannot retrieve telemetry header.")
            self.write_tlm_error_log('Unknown', 'Cannot retrieve telemetry header', buffer, 'Unknown')
            return None

        if mid not in self.mid_payload_map:
            self.log_unknown_packet_mid(mid)
            self.write_tlm_error_log(hex(mid), 'Undefined mid, check ccdd json definition files', buffer, pkt_size)
            return None

        if pkt_size != len(buffer):
            log.warning("Received msg size {} does not match with the msg header's attr "
                        "msg_size {} ".format(len(buffer), pkt_size))
            return None

        # If the packet is variable length, CTF needs to reconstruct the payload structure
        key_lst = [mid, self.mid_val_map.get(mid, None)]
        func_lst = [Global.get_variable_length_payload_construct_func(key) for key in key_lst]
        for construct_func in func_lst:
            if construct_func:
                return construct_func(buffer, self, self.mid_val_map.get(mid, None))

        func_lst = [Global.get_tlm_construct_func(key) for key in key_lst]
        # If the packet is segmented(incomplete) and reconstruction func is available, store the packet;
        # Otherwise, it skips the if block and builds the payload object based on CCDD definition.
        if seg_flag != CcsdsPacketInterface.CFE_MSG_SEGFLG_UNSEG and any(func_lst):
            log.debug("Receive incomplete msg: {} seg_flag: {}".format(hex(mid), seg_flag))
            self._append_incomplete_packets(self.incomplete_packet_dic[mid], buffer)
            res = None
            # rebuild the packet if receiving the last incomplete packet
            if seg_flag == CcsdsPacketInterface.CFE_MSG_SEGFLG_LAST:
                # mid if successfully re-construct packet; None with error; otherwise buff
                res = self._build_from_incomplete_packets(mid)
            if res is None or isinstance(res, int):
                return res

            buffer = res
            header = self.ccsds.CcsdsTelemetry.from_buffer(buffer[0:self.tlm_header_offset])

        param_class = self.mid_payload_map[mid]
        offset = self.tlm_header_offset if self.should_skip_header else 0
        try:
            payload = param_class.from_buffer(buffer[offset:])
        except ValueError:
            self.log_invalid_packet(mid)
            self.write_tlm_error_log(hex(mid), 'Could not build payload, check ccdd json definition files',
                                     buffer, pkt_size)
            return None

        # Log to file and DB
        self.write_tlm_log(payload, buffer[offset:], header)
        fsw_timestamp = "{}:{}".format(header.get_timestamp_seconds(), header.get_timestamp_subseconds())
        raw_header = buffer[0:self.tlm_header_offset]
        raw_payload = buffer[offset:]

        if Global.CTF_log_to_db:
            DBManager.log_tlm(
                ctf_timestamp=datetime.datetime.now().strftime("%H:%M:%S.%f")[:-2],
                target=self.config.name,
                fsw_timestamp=fsw_timestamp,
                mid=header.get_msg_id(),
                msghdr=raw_header,
                payload=raw_payload,
                formatted_payload=str(payload))

        self.on_packet_received(mid, header, payload)
        if mid in [self.evs_long_event_msg_mid, self.evs_short_event_msg_mid]:
            # Write this packet to the CFS EVS Log File
            self.write_evs_log(payload)

            if Global.CTF_log_to_db:
                formatted_payload = str(payload)
                payload = payload.Payload
                DBManager.log_event(
                    ctf_timestamp=datetime.datetime.now().strftime("%H:%M:%S.%f")[:-2],
                    target=self.config.name,
                    fsw_timestamp=fsw_timestamp,
                    mid=header.get_msg_id(),
                    msghdr=raw_header,
                    payload=raw_payload,
                    formatted_payload=formatted_payload,
                    app_name=payload.PacketID.AppName.decode(),
                    eventid=payload.PacketID.EventID,
                    event_type=payload.PacketID.EventType,
                    event_message=payload.Message.decode())

        if self.config.command_msg_time_source == 2:
            self.cfs_timestamp = {"sheader.timestamp_seconds": header.get_timestamp_seconds(),
                                  "sheader.timestamp_subseconds": header.get_timestamp_subseconds()}
        elif self.config.command_msg_time_source in (mid, self.mid_val_map[mid]):
            # mid: int > 2; mid_val_map[mid]: str, such as CFE_ES_HK_TLM_MID
            self.cfs_timestamp = {"sheader.timestamp_seconds": header.get_timestamp_seconds(),
                                  "sheader.timestamp_subseconds": header.get_timestamp_subseconds()}
        return mid

    def log_unknown_packet_mid(self, mid):
        """
        If this is the first time receiving a packet with the given mid, log the message.
        """
        msg = "Target {} received message with MID = {}. This MID is not in the CCSDS MID Map. Ignoring..." \
            .format(self.config.name, hex(mid))
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
            log.error("Target:{} cannot retrieve payload from packet with MID {}.".format(self.config.name, hex(mid)))
            self.has_received_mid[mid] = True
            log.debug(traceback.format_exc())

    def on_packet_received(self, mid, header, payload):
        """
        If this is the first time receiving a packet with the given mid then print the value of the mid.
        """
        exec_time = Global.get_time_manager().exec_time
        if not self.has_received_mid[mid]:
            log.info("Target:{} receiving first packet for Data Type: {} with MID: {} at time: {}"
                     .format(self.config.name, type(payload).__name__, hex(mid), exec_time))

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

    def _get_msg_header_timestamp(self):
        """
        This method returns the command header_timestamp based on config attribute.
        Note: ccsds_v1/v2 command header does not have timestamp_seconds, timestamp_subseconds attributes
        """
        header_timestamp = dict()
        if self.config.command_msg_time_source == 0:
            # CCSDS v1/v2 or ini config
            return header_timestamp
        if self.config.command_msg_time_source == 1:
            epoch_timestamp = time.time()
            # Convert the fractional part to 16-bit sub_second
            fraction = epoch_timestamp - int(epoch_timestamp)
            sub_seconds = int(fraction * 65536)
            header_timestamp = {"sheader.timestamp_seconds": int(epoch_timestamp),
                                "sheader.timestamp_subseconds": sub_seconds,
                                "eheader.age_check_flag": 1}
        else:
            header_timestamp = {**{"eheader.age_check_flag": 1}, **self.cfs_timestamp}
        return header_timestamp

    def build_command_packet_header(self, msg_id, function_code, payload, header_args=None):
        """
        This method constructs CCSDS command packet header.
        @param msg_id: The message ID of the command.
        @param function_code: The app specific function/command code (CC).
        @param payload: A bytearray representing the packet payload.
        @param header_args: An optional dictionary of additional kwargs for the header constructor.
        @return: The constructed CCSDS command packet header.
        """

        ccsds_command = self.ccsds.CcsdsCommand

        if isinstance(header_args, dict):
            for key, value in header_args.items():
                value = resolve_cfs_macro(value, self.macro_map)
                if str(value).isnumeric():
                    header_args[key] = int(value)

        updated_header_args = header_args or {}

        updated_header_args = {**self._get_msg_header_timestamp(), **updated_header_args}

        command_packet_header = build_command_packet_header(ccsds_command, msg_id, function_code, payload,
                                                            self.endian, self.crc, updated_header_args)
        return command_packet_header

    def send_command(self, msg_id, function_code, payload, header_args=None):
        """
        Send instruction to CFS instance through command interface.
        """
        command_header = self.build_command_packet_header(msg_id, function_code, payload, header_args)
        to_send = bytearray(command_header) + payload
        update_crc(command_header, to_send)
        status = self.command.send_command_packet(to_send)
        log.debug("Sending bytes: {}".format(to_send.hex()))

        # Log cmd to db
        if Global.CTF_log_to_db:
            DBManager.log_cmd(ctf_timestamp=datetime.datetime.now().strftime("%H:%M:%S.%f")[:-2],
                              target=self.config.name, mid=msg_id, msghdr=bytearray(command_header), payload=payload)

        return status

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
                log.debug('String comparison failed, actual value:%s streq expected value: %s', actual, expected)

        else:  # if there was no string to compare
            log.debug('String comparison failed, actual value:%s streq expected value: %s', actual, expected)
            check_status = False

        return check_status

    @staticmethod
    def _check_str_value(actual, expected, compare):
        """
        Based on the argument compare value, use string comparison methods to compare argument actual and expected
        """
        if compare == "streq":
            return CfsInterface.check_strings(actual, expected, True)
        if compare == "strneq":
            return CfsInterface.check_strings(actual, expected, False)
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

        return False

    @staticmethod
    def check_value(actual, expected, compare, mask, mask_value):
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
            return CfsInterface._check_str_value(actual, expected, compare)

        if compare == "in":
            return actual in expected
        if compare == "not in":
            return actual not in expected

        # strings and lists are processed above, at this point we are processing numbers

        # ENHANCE - Add type and overflow checking based on the ctype of the actual value.
        #           We need to either parse the message type's fields to determine the actual ctype and its size,
        #           or extend the types when they are created to expose the ctype used for primitive fields
        if compare in OPERATION_DIC:

            if isinstance(actual, str):
                log.warning("Type mismatch for comparator '{}'! Actual value '{}' is a string."
                            .format(compare, actual))
            if isinstance(expected, str) and not expected.lower().startswith("0x"):
                log.debug("Type mismatch for comparator '{}'! Expected value '{}' is a string."
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

    def clear_received_msgs_before_verification_start(self, mid, backward=0):
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
            if backward > 0.0:
                start_time = Global.current_verification_start_time - backward
            else:
                start_time = Global.current_verification_start_time
        log.debug(
            "Clearing received packets for MID: {} before time = {} exec_time={} "
            .format(hex(mid), start_time, Global.time_manager.exec_time))
        self.received_mid_packets_dic[mid] = [
            self.received_mid_packets_dic[mid][index]
            for index, i in enumerate(self.received_mid_packets_dic[mid])
            if i.timestamp >= start_time
        ]
        return

    def check_tlm_value(self, mid, args=None, discard_old_packets=True, backward=0.0, inner_mid=None):
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
            self.clear_received_msgs_before_verification_start(mid, backward)
            self._tlm_payload_set.clear()
            self.incomplete_packet_dic[mid].clear()

        if check_tlm_result and len(self.received_mid_packets_dic[mid]) == 0:
            log.debug("No messages received between polling to check. MID = {}".format(hex(mid)))
            check_tlm_result = False

        # If any of the above validation fails, there is no need to proceed into the packets
        # and the instruction will fail.
        if not check_tlm_result:
            return check_tlm_result

        # Traverse packets backwards validating each packet for the selected MID
        log.debug("Check tlmvalue for MID {} in {} messages".format(hex(mid), len(self.received_mid_packets_dic[mid])))
        inner_tlm_payload_type = self.mid_payload_map.get(inner_mid) if inner_mid else None
        if inner_mid and not inner_tlm_payload_type:
            log.error("No telemetry structure defined for MID: {}".format(inner_mid))
            return False

        check_tlm_result = False
        for i in range(len(self.received_mid_packets_dic[mid]) - 1, -1, -1):
            # Get current packet for the selected MID
            payload = self.received_mid_packets_dic[mid][i].payload

            # Check whether the type of the payload matches with the type defined in mid_payload_map,
            # If not, proceed to the next packet (tlm callback func may interpret the payload to other types)
            # pylint: disable=isinstance-second-argument-not-valid-type
            if inner_tlm_payload_type is not None and not isinstance(payload, inner_tlm_payload_type):
                log.debug("Payload type {} doesn't match with {} continue ...".format(type(payload),
                                                                                      inner_tlm_payload_type))
                continue

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

    def get_tlm_value(self, mid, tlm_variable, is_header=False, tlm_args=None):
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
            if tlm_args and not self.check_tlm_packet(packet.payload, tlm_args, False):
                log.debug("Packet {} does not match provided args. Continuing...".format(i))
                continue
            latest_tlm_value = ctf_utility.rgetattr(data, tlm_variable, None)

            if isinstance(latest_tlm_value, bytes):
                log.info("Bytes object {} is decoded to {}".format(latest_tlm_value, latest_tlm_value.decode()))
                latest_tlm_value = latest_tlm_value.decode()

            if latest_tlm_value is not None:
                break

        if len(self.received_mid_packets_dic[mid]) > 0 and latest_tlm_value is None:
            log.debug("Found telemetry packets for MID ({}), but do not match with the provided val/args".
                      format(hex(mid)))

        return latest_tlm_value

    def check_array_value(self, variable_array, expected_value, compare):
        """
        Based on the argument compare value, check array elements in argument variable_array with the expected value.
        """
        result = list()
        for variable in variable_array:
            log.debug("Check array element {} for value {} ".format(variable, expected_value))
            if isinstance(expected_value, dict):
                dic_check_result = list()
                for dict_key, dict_value in expected_value.items():
                    try:
                        dict_var = ctf_utility.rgetattr(variable, dict_key)
                    except (AttributeError, ValueError) as exception:
                        dic_check_result.append(False)
                        log.error("Failed to evaluate variable payload.{}: {}".format(variable, exception))
                        break
                    dic_check_result.append(self.check_value(dict_var, dict_value, compare, None, None))
                result.append(all(dic_check_result))
            else:
                result.append(self.check_value(variable, expected_value, compare, None, None))
        return any(result)

    def check_tlm_packet(self, payload, args, log_result=True):
        """
        Check telemetry message's value based on argument payload and args
        """
        packet_passed = True
        # Compare the current packet to the expected packet using each variable in args.
        for arg in args:
            expected_value = arg.get("value")
            if isinstance(expected_value, list) and len(expected_value) == 1:
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
                log.debug("Bytes object {} is decoded to {}".format(actual, actual.decode()))
                actual = actual.decode()

            # if the actual is an array type, loop through to compare with the expected_value and return the result
            # Note (ctypes.c_char*N) is not ctypes.Array
            if isinstance(actual, ctypes.Array):
                # does not allow tolerance compare
                tol_plus = None
                tol_minus = None
                array_cmp_result = self.check_array_value(actual, expected_value, arg["compare"])
                arg_result = array_cmp_result

            else:  # the actual is a simple type
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

            if log_result and (id(payload) not in self._tlm_payload_set):
                if not arg_result:
                    log.info(
                        "Unsatisfied Intermediate Check - {}: Actual: {}, Expected: {}, Comparison: {}, Tol: +{}, -{}"
                        .format(variable, actual, expected_value, arg["compare"], tol_plus, tol_minus))
                else:
                    log.debug(
                        "Satisfied Intermediate Check - {}: Actual: {}, Expected: {}, Comparison: {}, Tol: +{}, -{}"
                        .format(variable, actual, expected_value, arg["compare"], tol_plus, tol_minus))

            packet_passed = packet_passed and arg_result

        # _tlm_payload_set will be cleared in check_tlm_value method during CtfVerificationStage.first_ver
        # it is to ensure there is only one comparison log message for one tlm message(payload)
        self._tlm_payload_set.add(id(payload))

        return packet_passed

    def enable_output(self):
        """
        Send a command to enable output and check if we receive a response

        This function will first clear the socket before checking for a response
        """
        count = 0
        timeout = 120

        # Flush the socket to ensure we only read fresh packets
        log.debug("EnableCfsOutput: Clearing socket before checking for new packets..")
        self.read_sb_packets()
        self.tlm_has_been_received = False

        while True:
            count += 1
            self.output_manager.enable_output()
            Global.time_manager.wait(1)

            if self.tlm_has_been_received:
                return True
            if count > timeout:
                log.error("Unable to connect to CFS mission")
                return False

    def _append_incomplete_packets(self, buffer_lst, buffer):
        """
        Add the segmented packet to the incomplete_packet_dic for reconstructing the tlm packet later
        """
        header = self.ccsds.CcsdsTelemetry.from_buffer(buffer[0:self.tlm_header_offset])
        seg_flag = header.pheader.get_segmentation_flags()
        sequence_count = header.get_sequence_count()
        cur_exec_time = Global.get_time_manager().exec_time

        # clear incomplete buffer list when receiving the first segmented packet
        if seg_flag == CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST:
            buffer_lst.clear()

        segmented_pkt = InCompletePacket(sequence_count, seg_flag, cur_exec_time, buffer)
        buffer_lst.append(segmented_pkt)

    @staticmethod
    def _sort_incomplete_packets(pkt_lst):
        """
        Sort incomplete packets based on sequence_count
        """
        # sequence_count should increase sequentially. However, it may roll over as it only has 14 bits
        max_seq = 2 ** 14 - 1  # 16383
        pkt_lst.sort(key=lambda pkt: pkt.seq)
        lst_size = len(pkt_lst)
        if pkt_lst[-1].seq == max_seq and (pkt_lst[-1].seq - pkt_lst[0].seq + 1) != lst_size:
            # sequence_count rollover
            for i in range(lst_size - 1):
                original_seq = pkt_lst[i].seq
                pkt_lst[i].seq += (max_seq + 1)
                if original_seq != pkt_lst[i + 1].seq - 1:
                    break

            # sequence_count should be in order, if no missing/duplicated packets
            pkt_lst.sort(key=lambda pkt: pkt.seq)

    def _build_from_incomplete_packets(self, mid):
        """
        Build the telemetry packet from the stored incomplete packets
        """
        pkt_lst = self.incomplete_packet_dic[mid]
        lst_size = len(pkt_lst)
        if lst_size < 2:
            log.warning("Too few incomplete packets for mid: {}".format(hex(mid)))
            return None

        # packets may not come in order, need to sort them based on header sequence_count
        CfsInterface._sort_incomplete_packets(pkt_lst)

        # don't receive all segmented packets
        if ((pkt_lst[-1].seq - pkt_lst[0].seq + 1) != lst_size
                or pkt_lst[0].seg_flag != CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST
                or pkt_lst[-1].seg_flag != CcsdsPacketInterface.CFE_MSG_SEGFLG_LAST):
            log.warning("Not receive all incomplete packets for mid: {}".format(hex(mid)))
            return None

        for i in range(lst_size - 1):
            if pkt_lst[i].seq != (pkt_lst[i + 1].seq - 1):
                log.warning("Incomplete packets not strictly increasing for mid: {}".format(hex(mid)))
                return None

        # mid must be in self.mid_val_map, otherwise parse_telemetry_packet bypass this method
        # plugins could register mid as string or int in tlm_reconstruct_func
        keys_lst = [mid, self.mid_val_map.get(mid, None)]
        func_list = [Global.get_tlm_construct_func(key) for key in keys_lst]
        for construct_func in func_list:
            if construct_func:
                return construct_func(pkt_lst, self)

        return None
