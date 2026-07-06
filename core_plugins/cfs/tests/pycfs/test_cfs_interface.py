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
# File: test_cfs_interface.py
#
# Purpose: This file contains test cases for unit testing of CfsInterface functions.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

import ctypes
import socket
from unittest.mock import patch, MagicMock, mock_open, seal

import pytest

from core_plugins.ccsds_plugin.cfe.ccsds_v2.ccsds_v2 import CcsdsV2PrimaryHeader
from lib.ctf_global import Global, CtfVerificationStage
from lib.exceptions import CtfConditionError
from core_plugins.cfs.pycfs.cfs_interface import Packet, CfsInterface, InCompletePacket
from core_plugins.ccsds_plugin.ccsds_packet_interface import CcsdsPacketInterface


@pytest.fixture(scope='session', autouse=True)
def init_global():
    Global.load_config('./configs/default_config.ini')
    time_mgr = MagicMock()
    time_mgr.exec_time = 1.0
    Global.time_manager = time_mgr
    Global.current_script_log_dir = '.'


@pytest.fixture(name='cfs')
def cfs_interface(cfs_config, mid_map, ccsdsv2):
    from core_plugins.cfs.pycfs.cfs_interface import CfsInterface
    from core_plugins.cfs.pycfs.command_interface import CommandInterface
    from core_plugins.cfs.pycfs.tlm_listener import TlmListener
    mock_tlm = MagicMock(spec=TlmListener)
    mock_cmd = MagicMock(spec=CommandInterface)
    Global.CTF_log_to_db = True
    with patch('core_plugins.cfs.pycfs.output_app_interface.ToApi', name='mock'):
        return CfsInterface(cfs_config, mock_tlm, mock_cmd, mid_map, ccsdsv2)


def test_cfs_interface_init(cfs):
    assert cfs.config
    assert cfs.evs_long_event_msg_mid == 8198
    assert cfs.evs_short_event_msg_mid == 8199
    assert not cfs.init_passed
    assert cfs.command
    assert cfs.telemetry
    assert [mid in cfs.mid_payload_map for mid in [8198, 10891, 8199, 1337]]
    assert cfs.output_manager
    assert cfs.cfs_std_out_path is None
    assert cfs.evs_log_file is None
    assert cfs.tlm_log_file is None
    assert cfs.tlm_has_been_received is False
    assert cfs.unchecked_packet_mids == []
    assert cfs.tlm_verifications_by_mid_and_vid == {}
    assert cfs.received_mid_packets_dic == {
        8198: [],
        8199: [],
        1337: [],
        10891: []
    }
    assert cfs.has_received_mid == {
        8198: False,
        8199: False,
        1337: False,
        10891: False
    }
    assert cfs.ccsds
    assert cfs.should_skip_header is True
    assert cfs.tlm_header_offset == 16


def test_cfs_interface_init_invalid(cfs_config, mid_map, ccsdsv2, utils):
    from core_plugins.cfs.pycfs.cfs_interface import CfsInterface
    from core_plugins.cfs.pycfs.command_interface import CommandInterface
    from core_plugins.cfs.pycfs.tlm_listener import TlmListener
    mock_tlm = MagicMock(spec=TlmListener)
    mock_cmd = MagicMock(spec=CommandInterface)
    mid_map = {k: v for k, v in mid_map.items() if 'EVS' not in k}
    with patch.object(cfs_config, 'tlm_udp_port', 0):
        with patch('core_plugins.cfs.pycfs.output_app_interface.ToApi', name='mock'):
            cfs = CfsInterface(cfs_config, mock_tlm, mock_cmd, mid_map, ccsdsv2)
            assert utils.has_log_level('ERROR')
            assert cfs.evs_long_event_msg_mid == -1
            assert cfs.evs_short_event_msg_mid == -1


def test_cfs_interface_build_cfs(cfs):
    with pytest.raises(NotImplementedError):
        cfs.build_cfs()


def test_cfs_interface_start_cfs(cfs):
    with pytest.raises(NotImplementedError):
        cfs.start_cfs('run_args')


def test_cfs_interface_stop_cfs_close_file(cfs, mid_map):
    cfs.tlm_log_file = open('temp_tlm_file.txt', "a+")
    cfs.evs_log_file = open('temp_evs_file.txt', "a+")
    cfs.stop_cfs()
    cfs.command.cleanup.assert_called_once()
    cfs.telemetry.cleanup.assert_called_once()


def test_cfs_interface_stop_cfs(cfs, mid_map):
    cfs.add_tlm_condition('v_id1', mid_map['MOCK_TLM_MID'], 'args1')
    cfs.stop_cfs()
    cfs.command.cleanup.assert_called_once()
    cfs.telemetry.cleanup.assert_called_once()


def test_cfs_interface_write_tlm_log(cfs, utils):
    assert cfs.tlm_log_file is None
    assert not utils.has_log_level('ERROR')
    header = cfs.ccsds.CcsdsTelemetry()
    with patch('builtins.open', new_callable=mock_open()) as mock_file:
        cfs.config.telemetry_debug = True
        cfs.config.csv_tlm_log = True
        cfs.write_tlm_log('payload1', bytearray('payload1', 'utf-8'), header)
        assert cfs.tlm_log_file is mock_file.return_value
        assert mock_file.return_value.write.call_count == 5
        mock_file.return_value.write.reset_mock()
        cfs.write_tlm_log('payload2', bytearray('payload2', 'utf-8'), header)
        assert mock_file.return_value.write.call_count == 3
        mock_file.return_value.write.reset_mock()
        mock_file.return_value.write.side_effect = IOError('mock error')
        cfs.write_tlm_log('payload3', bytearray('payload3', 'utf-8'), header)
        assert utils.has_log_level('ERROR')


def test_cfs_interface_write_tlm_error_log_io_error(cfs, utils):
    assert cfs.tlm_log_file is None
    assert not utils.has_log_level('ERROR')
    header = CcsdsV2PrimaryHeader()
    with patch('builtins.open', new_callable=mock_open()) as mock_file:
        cfs.config.telemetry_debug = True
        cfs.config.csv_tlm_log = True
        mock_file.return_value.write.side_effect = IOError('mock error')
        cfs.write_tlm_error_log(hex(100), 'Undefined mid', bytearray('payload1', 'utf-8'), 8)
        assert utils.has_log_level('ERROR')


def test_cfs_interface_write_tlm_error_log(cfs, utils):
    assert cfs.tlm_log_file is None
    assert not utils.has_log_level('ERROR')
    with patch('builtins.open', new_callable=mock_open()) as mock_file:
        header = CcsdsV2PrimaryHeader()
        cfs.config.telemetry_debug = True
        cfs.config.csv_tlm_log = True
        cfs.write_tlm_error_log(hex(100), 'Undefined mid', bytearray('payload1', 'utf-8'), 8)
        assert cfs.tlm_log_file is mock_file.return_value
        mock_file.return_value.write.reset_mock()
        mock_file.return_value.write.side_effect = IOError('mock error')
        cfs.write_tlm_error_log(hex(100), 'Undefined mid', bytearray('payload1', 'utf-8'), 8)
        assert utils.has_log_level('ERROR')


def test_cfs_interface_write_evs_log(cfs, utils):
    assert cfs.evs_log_file is None
    assert not utils.has_log_level('ERROR')
    with patch('builtins.open', new_callable=mock_open()) as mock_file:
        cfs.write_evs_log(MagicMock())
        assert cfs.evs_log_file is mock_file.return_value
        mock_file.assert_called_once_with('./cfs_evs_msgs.log', 'a+')
        assert mock_file.return_value.write.call_count == 1
        cfs.write_evs_log(MagicMock())
        assert mock_file.return_value.write.call_count == 2
        mock_file.return_value.write.side_effect = UnicodeDecodeError('', bytes(), 0, 0, 'mock error')
        cfs.write_evs_log(MagicMock())
        assert utils.has_log_level('ERROR')


def test_cfs_interface_parse_command_packet(cfs, utils):
    buff = bytearray(b'\x8b\xc0\x00\x00\x1d\x00\x00\x1d\x00\x00\x1d\x00\x00\x1d\x00*\x00\x00\x02\x021')
    cfs.md_header_offset = 10
    # mid not in mid_payload_map:
    assert cfs.parse_command_packet(buff) is None
    assert utils.has_log_level('WARNING')


def test_cfs_interface_parse_command_packet_exception(cfs, utils):
    buff = bytearray(b'\x8b\xc0\x00\x00\x1d\x00\x00\x1d\x00\x00\x1d\x00\x00\x1d\x00*\x00\x00\x02\x021')
    with patch.object(cfs, 'ccsds') as mock_ccsds:
        mock_instance = MagicMock()
        mock_instance.from_buffer.side_effect = ValueError('mock error')
        mock_ccsds.CcsdsCommand = mock_instance
        with patch('ctypes.sizeof', return_value=20):
            assert cfs.parse_command_packet(buff) is None
            assert utils.has_log_level('DEBUG')


def test_cfs_interface_parse_command_packet_exception2(cfs, utils):
    buff = bytearray(b'\x8b\xc0\x00\x00\x1d\x00\x00\x1d\x00\x00\x1d\x00\x00\x1d\x00*\x00\x00\x02\x021')
    with patch.object(cfs, 'ccsds') as mock_ccsds:
        mock_header = MagicMock()
        mock_header.get_function_code.side_effect = ValueError('mock error')
        mock_header.get_msg_id.return_value = 1997
        cfs.mid_payload_map[1997] = {}
        cfs.has_received_mid[1997] = True
        mock_command = MagicMock()
        mock_command.from_buffer.return_value = mock_header
        mock_ccsds.CcsdsCommand = mock_command
        with patch('ctypes.sizeof', return_value=20):
            assert cfs.parse_command_packet(buff) is None
            cfs.mid_payload_map.pop(1997)
            cfs.has_received_mid.pop(1997)


def test_cfs_interface_read_sb_packets_exception(cfs, utils):
    recvd = [
        # valid tlm
        b'(\x06\xc0\x08\x00\xa5\x0c \x00B,F\x0f\x00V\xbaTO'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x03\x00\x02\x00B\x00\x00\x00\x01\x00\x00'
        b'\x00TO - ENABLE_OUTPUT cmd succesful for  routeMask:0x00000001'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        0,
    ]
    with patch.object(cfs, 'telemetry') as mock_tlm:
        mock_tlm.read_socket.side_effect = recvd
        with patch.object(cfs.ccsds.CcsdsPrimaryHeader, 'from_buffer') as mock_from_buf:
            mock_from_buf.side_effect = ValueError('mock error')
            utils.clear_log()
            assert cfs.read_sb_packets() is None
            utils.has_log_level('ERROR')
            utils.has_log('Cannot create CCSDS Primary Header')


def test_cfs_interface_read_sb_packets_valid(cfs, utils):
    # alternate data and 0 to break out of read loop after each read
    recvd = [
        # valid tlm
        b'(\x06\xc0\x08\x00\xa5\x0c \x00B,F\x0f\x00V\xbaTO'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x03\x00\x02\x00B\x00\x00\x00\x01\x00\x00'
        b'\x00TO - ENABLE_OUTPUT cmd succesful for  routeMask:0x00000001'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        0,
        # valid cmd
        b':\x8b\xc0\x00\x00\x1d\x00*\x00\x00\x02\x02127.0.0.1'
        b'\x00\x00\x00\x00\x00\x00\x00\x93\x13\x00\x00\x00\x00\x00\x00',
        0
    ]
    with patch.object(cfs, 'telemetry') as mock_tlm:
        mock_tlm.read_socket.side_effect = recvd

        # read valid tlm
        cfs.read_sb_packets()
        assert mock_tlm.read_socket.call_count == 2
        assert cfs.received_mid_packets_dic[8198]
        assert cfs.unchecked_packet_mids == [8198]
        assert not utils.has_log_level('ERROR')

        # read valid cmd
        mock_tlm.reset_mock()
        cfs.read_sb_packets()
        assert mock_tlm.read_socket.call_count == 2
        assert cfs.received_mid_packets_dic[10891]
        assert cfs.unchecked_packet_mids == [8198, 10891]
        assert not utils.has_log_level('ERROR')


def test_cfs_interface_read_sb_packets_invalid_packets(cfs, utils):
    # alternate data and 0 to break out of read loop after each read
    recvd = [
        # unknown mid
        b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a\x06\x07\t'
        b'\x00\x05\x00\x08\x00,\x08\x00\x00\x00\x0c\x00\x00\x1e\x00\x00\x00\x01\x00'
        b'\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x05\x00\x00\x00\x03\x00\x00\x00'
        b'\x0b\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x00'
        b'\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        0,
        # invalid tlm
        b'(\x06\xc0\x08\x00\xa5\x0c \x00B,F\x0f\x00V\xbaTO'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x03\x00\x02\x00B\x00\x00\x00\x01\x00\x00'
        b'\x00TO - ENABLE_OUTPUT cmd succesful for  routeMask:0x00000001',
        0,
        # invalid cmd
        b':\x8b\xc0\x00\x00\x1d\x00*\x00\x00\x02\x02127.0.0.1',
        0
    ]
    with patch.object(cfs, 'telemetry') as mock_tlm:
        mock_tlm.read_socket.side_effect = recvd

        # read unknown mid
        mock_tlm.reset_mock()
        cfs.read_sb_packets()
        assert mock_tlm.read_socket.call_count == 2
        assert not cfs.unchecked_packet_mids
        assert 8193 not in cfs.received_mid_packets_dic
        assert cfs.has_received_mid[8193]
        assert utils.has_log_level('WARNING')
        utils.clear_log()

        # read invalid tlm
        mock_tlm.reset_mock()
        tlm_test_mid = 8198
        cfs.has_received_mid[tlm_test_mid] = False
        cfs.mid_payload_map[tlm_test_mid].from_buffer.side_effect = ValueError('mock error')
        cfs.read_sb_packets()
        assert mock_tlm.read_socket.call_count == 2
        assert not cfs.unchecked_packet_mids
        assert not cfs.received_mid_packets_dic[tlm_test_mid]
        assert not cfs.has_received_mid[tlm_test_mid]
        utils.clear_log()

        # read invalid cmd
        mock_tlm.reset_mock()
        tlm_test_mid = 10891
        cfs.has_received_mid[tlm_test_mid] = False
        cfs.mid_payload_map[tlm_test_mid]['TO_ENABLE_OUTPUT_CC']['ARG_CLASS'].from_buffer.side_effect \
 = ValueError('mock error')
        cfs.read_sb_packets()
        assert mock_tlm.read_socket.call_count == 2
        assert not cfs.unchecked_packet_mids
        assert not cfs.received_mid_packets_dic[tlm_test_mid]
        assert utils.has_log_level('ERROR')
        utils.clear_log()


def test_cfs_interface_read_sb_packets_invalid_headers(cfs, utils):
    # alternate data and 0 to break out of read loop after each read
    recvd = [
        # invalid pheader
        b'\x00\x00',
        0,
        # invalid cmd header
        b':\x8b\xc0\x00\x00\x1d',
        0,
        # invalid tlm header
        b'(\x06\xc0\x08\x00\xa5',
        0
    ]
    with patch.object(cfs, 'telemetry') as mock_tlm:
        mock_tlm.read_socket.side_effect = recvd

        # read invalid pheader
        mock_tlm.reset_mock()
        cfs.read_sb_packets()
        assert mock_tlm.read_socket.call_count == 2
        assert not cfs.unchecked_packet_mids
        assert utils.has_log_level('ERROR')
        utils.clear_log()

        # read invalid cmd header
        mock_tlm.reset_mock()
        cfs.read_sb_packets()
        assert mock_tlm.read_socket.call_count == 2
        assert not cfs.unchecked_packet_mids

        # read invalid tlm header
        mock_tlm.reset_mock()
        cfs.read_sb_packets()
        assert mock_tlm.read_socket.call_count == 2
        assert not cfs.unchecked_packet_mids


def test_cfs_interface_read_sb_packets_timeout(cfs, utils):
    with patch.object(cfs, 'telemetry') as mock_tlm:
        mock_tlm.read_socket.side_effect = socket.timeout
        cfs.read_sb_packets()
        assert not cfs.unchecked_packet_mids
        assert utils.has_log_level('WARNING')


def test_cfs_interface_parse_telemetry_packet_crc_check_fail(cfs, utils):

    buffer = bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a' \
                       b'\x06\x07\t\x00\x05\x00\x08\x00,\x08\x00\x00\x00\x0c\x00\x00\x1e' \
                       b'\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x05' \
                       b'\x00\x00\x00\x03\x00\x00\x00\x0b\x00\x00\x00\x01\x00\x00\x00\x02' \
                       b'\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01' \
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff' \
                       b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00' \
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert not cfs.parse_telemetry_packet(buffer)
    assert utils.has_log_level('DEBUG')


def test_cfs_interface_add_tlm_condition(cfs, mid_map, utils):
    assert not utils.has_log_level('ERROR')
    assert not cfs.tlm_verifications_by_mid_and_vid
    assert cfs.add_tlm_condition('v_id1', mid_map['MOCK_TLM_MID'], 'args1')
    assert 'v_id1' in cfs.tlm_verifications_by_mid_and_vid[1337]
    assert cfs.tlm_verifications_by_mid_and_vid[1337]['v_id1'].verification_id == 'v_id1'
    assert cfs.tlm_verifications_by_mid_and_vid[1337]['v_id1'].condition.args == 'args1'
    assert not cfs.add_tlm_condition('v_id1', mid_map['MOCK_TLM_MID'], 'args2')
    assert utils.has_log_level('ERROR')


def test_cfs_interface_remove_tlm_condition(cfs, mid_map, utils):
    assert not utils.has_log_level('ERROR')
    assert not cfs.tlm_verifications_by_mid_and_vid
    assert not cfs.remove_tlm_condition('v_id1')
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    assert cfs.add_tlm_condition('v_id1', mid_map['MOCK_TLM_MID'], 'args')
    assert cfs.remove_tlm_condition('v_id1')
    assert not cfs.tlm_verifications_by_mid_and_vid[1337]

    cfs.config.remove_continuous_on_fail = False
    assert not cfs.remove_tlm_condition('v_id1')
    assert utils.has_log_level('ERROR')


def test_cfs_check_tlm_conditions(cfs, mid_map):
    # ignore the logic of check_tlm_value for this test, because only pass/fail matters
    with patch.object(cfs, 'check_tlm_value') as mock_check:
        # test no unchecked packets
        assert not cfs.unchecked_packet_mids
        cfs.check_tlm_conditions()
        mock_check.assert_not_called()

        # test no matching verification
        tlm_test_mid = 8198
        cfs.unchecked_packet_mids.append(tlm_test_mid)
        cfs.check_tlm_conditions()
        assert not cfs.unchecked_packet_mids
        mock_check.assert_not_called()

        # test placeholder only
        cfs.unchecked_packet_mids.append(tlm_test_mid)
        cfs.add_tlm_condition('v_id1', mid_map['CFE_EVS_LONG_EVENT_MSG_MID'], 'v_id1 args')
        cfs.received_mid_packets_dic[tlm_test_mid].append(Packet(tlm_test_mid, None, MagicMock(), 1, 0.0))
        cfs.check_tlm_conditions()
        assert not cfs.unchecked_packet_mids
        mock_check.assert_not_called()

        # test check pass
        cfs.unchecked_packet_mids.append(tlm_test_mid)
        cfs.received_mid_packets_dic[tlm_test_mid].append(Packet(tlm_test_mid, None, MagicMock(), 1, 1.0))
        mock_check.return_value = True
        cfs.check_tlm_conditions()
        assert not cfs.unchecked_packet_mids
        mock_check.assert_called_once_with(mid_map['CFE_EVS_LONG_EVENT_MSG_MID'],
                                           'v_id1 args',
                                           discard_old_packets=False)
        mock_check.reset_mock()

        # test other conditions present

        # test check fail
        mock_check.return_value = False
        cfs.unchecked_packet_mids.append(tlm_test_mid)
        cfs.received_mid_packets_dic[tlm_test_mid].append(Packet(tlm_test_mid, None, MagicMock(), 1, 1.0))
        with pytest.raises(CtfConditionError):
            cfs.check_tlm_conditions()


def test_cfs_build_command_packet_header(cfs):
    header = cfs.build_command_packet_header(0x12, 0x34, bytearray(0x1))
    assert header.pheader.app_id == 0x12
    assert header.pheader.sequence_count == 0
    assert header.pheader.version_number == 1

    header = cfs.build_command_packet_header(0x12, 0x34, bytearray(0x1), {"pheader.version_number": 3})
    assert header.pheader.app_id == 0x12
    assert header.pheader.sequence_count == 0
    assert header.pheader.version_number == 3


def test_cfs_send_command(cfs):
    log_flag = Global.CTF_log_to_db
    Global.CTF_log_to_db = True
    assert cfs.send_command(0x12, 0x34, bytearray(0x1))
    Global.CTF_log_to_db = log_flag
    cfs.command.send_command_packet.assert_called_once_with(bytearray(b'(\x12\xc0\x00\x00\n\x04\x00\x00\x0044\x00\x00\x00\x00\x00'))


def test_cfs_check_strings(cfs):
    assert cfs.check_strings('foo', 'foo', True) is True
    assert cfs.check_strings('foo', 'foo', False) is False
    assert cfs.check_strings('foo', 'bar', True) is False
    assert cfs.check_strings('foo', 'bar', False) is True
    assert cfs.check_strings(1, '1', None) is False
    assert cfs.check_strings('1', 1, None) is False
    assert cfs.check_strings(1, 1, None) is False


def test_cfs_check_value_strings(cfs):
    assert cfs.check_value('foo', 'foo', 'streq', None, None) is True
    assert cfs.check_value('foo', 'bar', 'streq', None, None) is False
    assert cfs.check_value('foo', 'foo', 'strneq', None, None) is False
    assert cfs.check_value('foo', 'bar', 'strneq', None, None) is True


def test_cfs_check_value_regex(cfs):
    assert cfs.check_value('foo', r'.', 'regex', None, None) is True
    assert cfs.check_value('foo', r'a', 'regex', None, None) is False
    assert cfs.check_value(1, r'.', 'regex', None, None) is False
    assert cfs.check_value('foo', 1, 'regex', None, None) is False


def test_cfs_check_value_float(cfs, utils):
    utils.clear_log()
    assert cfs.check_value(1.0, 1.0, '==', None, None) is True
    assert cfs.check_value(1.0, 2.0, '==', None, None) is False
    assert not utils.has_log_level('ERROR')
    assert cfs.check_value(1.0, 'foo', '==', None, None) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    assert cfs.check_value(1.0, 1.0, '!=', None, None) is False
    assert cfs.check_value(1.0, 2.0, '!=', None, None) is True
    assert not utils.has_log_level('ERROR')
    assert cfs.check_value(1.0, 'foo', '!=', None, None) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    assert cfs.check_value(1.0, 1.0, '<=', None, None) is True
    assert cfs.check_value(1.0, 2.0, '<=', None, None) is True
    assert not utils.has_log_level('ERROR')
    assert cfs.check_value(1.0, 'foo', '<=', None, None) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    assert cfs.check_value(1.0, 1.0, '>=', None, None) is True
    assert cfs.check_value(1.0, 2.0, '>=', None, None) is False
    assert not utils.has_log_level('ERROR')
    assert cfs.check_value(1.0, 'foo', '>=', None, None) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    assert cfs.check_value(1.0, 1.0, '<', None, None) is False
    assert cfs.check_value(1.0, 2.0, '<', None, None) is True
    assert not utils.has_log_level('ERROR')
    assert cfs.check_value(1.0, 'foo', '<', None, None) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    assert cfs.check_value(2.0, 1.0, '>', None, None) is True
    assert cfs.check_value(1.0, 2.0, '>', None, None) is False
    assert not utils.has_log_level('ERROR')
    assert cfs.check_value(1.0, 'foo', '>', None, None) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    assert cfs.check_value(1.0, 1.0, 'foo', None, None) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()


def test_cfs_check_value_list(cfs):
    assert cfs.check_value(1, [2, 3], 'in', None, None) is False
    assert cfs.check_value(1, [2, 1], 'in', None, None) is True
    assert cfs.check_value(1, [2, 3], 'not in', None, None) is True
    assert cfs.check_value(1, [2, 1], 'not in', None, None) is False


def test_cfs_check_value_mask(cfs, utils):
    # no mask
    utils.clear_log()
    assert cfs.check_value(0x1, 0x9, '==', None, 0x3) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    # no mask value
    assert cfs.check_value(0x1, 0x9, '==', '&', None) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    # & valid
    assert cfs.check_value(0x1, 0x9, '==', '&', 0x3) is False
    assert not utils.has_log_level('ERROR')

    # & invalid expected
    assert cfs.check_value(0x1, '0xv9', '==', '&', 0x3) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    # & invalid actual
    utils.clear_log()
    assert cfs.check_value('0x1', 0x9, '==', '&', 0x3) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    # | valid
    assert cfs.check_value(0xb, 0x9, '==', '|', 0x3) is False
    assert not utils.has_log_level('ERROR')

    # | invalid expected
    assert cfs.check_value(0xb, '0x9', '==', '&', 0x3) is False

    # | invalid actual
    utils.clear_log()
    assert cfs.check_value('0x1', 0x9, '==', '&', 0x3) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    # invalid mask
    assert cfs.check_value(0x0, 0x0, '==', '!', 0x0) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    # invalid mask value
    assert cfs.check_value(0x0, 0x0, '==', '&', 0.0) is False
    assert utils.has_log_level('ERROR')
    utils.clear_log()


def test_clear_received_msgs_before_verification_start(cfs, utils):
    Global.time_manager.exec_time = 10.0
    Global.current_verification_start_time = 3.0
    assert cfs.config.evs_messages_clear_after_time == 5
    assert [not pkt for pkt in cfs.received_mid_packets_dic]

    cfs.clear_received_msgs_before_verification_start(8198)
    assert utils.has_log_level('WARNING')
    utils.clear_log()

    cfs.received_mid_packets_dic[8198].append(Packet(8198, None, MagicMock(), 1, 4.0))
    cfs.received_mid_packets_dic[8198].append(Packet(8198, None, MagicMock(), 2, 5.0))
    cfs.received_mid_packets_dic[8199].append(Packet(8199, None, MagicMock(), 1, 4.0))
    cfs.received_mid_packets_dic[1337].append(Packet(1337, None, MagicMock(), 1, 2.0))
    cfs.received_mid_packets_dic[1337].append(Packet(1337, None, MagicMock(), 2, 3.0))

    cfs.clear_received_msgs_before_verification_start(8198)
    assert len(cfs.received_mid_packets_dic[8198]) == 1
    assert len(cfs.received_mid_packets_dic[8199]) == 1
    assert len(cfs.received_mid_packets_dic[1337]) == 2

    cfs.clear_received_msgs_before_verification_start(8199)
    assert len(cfs.received_mid_packets_dic[8198]) == 1
    assert len(cfs.received_mid_packets_dic[8199]) == 0
    assert len(cfs.received_mid_packets_dic[1337]) == 2

    cfs.clear_received_msgs_before_verification_start(1337)
    assert len(cfs.received_mid_packets_dic[8198]) == 1
    assert len(cfs.received_mid_packets_dic[8199]) == 0
    assert len(cfs.received_mid_packets_dic[1337]) == 1

    cfs.clear_received_msgs_before_verification_start(1337, 1)
    assert len(cfs.received_mid_packets_dic[8198]) == 1
    assert len(cfs.received_mid_packets_dic[8199]) == 0
    assert len(cfs.received_mid_packets_dic[1337]) == 1


def test_cfs_get_tlm_value_invalid_mid(cfs, utils):
    mid = {'INVALID_MID': 8193, 'name': 'CFE_ES_HousekeepingTlm_t', 'PARAM_CLASS': None}
    tlm_variable = 'Payload.CommandCounter'
    utils.clear_log()
    assert cfs.get_tlm_value(mid, tlm_variable) is None
    assert utils.has_log_level('ERROR')

    utils.clear_log()
    mid = {'MID': 8193, 'name': 'CFE_ES_HousekeepingTlm_t', 'PARAM_CLASS': None}
    assert cfs.get_tlm_value(mid, tlm_variable) is None
    assert utils.has_log_level('ERROR')


def test_cfs_get_tlm_value_no_packet(cfs, utils):
    mid = {'MID': 8198, 'name': 'CFE_ES_HousekeepingTlm_t', 'PARAM_CLASS': None}
    tlm_variable = 'Payload.CommandCounter'
    utils.clear_log()
    assert cfs.get_tlm_value(mid, tlm_variable) is None
    assert utils.has_log_level('ERROR')


def test_cfs_get_tlm_value_no_payload(cfs, utils):
    mid = {'MID': 8198, 'name': 'CFE_ES_HousekeepingTlm_t', 'PARAM_CLASS': None}
    tlm_variable = 'Payload.CommandCounter'
    cfs.received_mid_packets_dic[8198].append(Packet(8198, None, None, 1, 4.0))
    utils.clear_log()
    assert cfs.get_tlm_value(mid, tlm_variable) is None
    assert utils.has_log_level('ERROR')


def test_cfs_get_tlm_value(cfs):
    mid = {'MID': 8198, 'name': 'CFE_ES_HousekeepingTlm_t', 'PARAM_CLASS': None}
    tlm_variable = 'Payload.CommandCounter'
    cfs.received_mid_packets_dic[8198].append(Packet(8198, None, MagicMock(), 1, 4.0))
    assert cfs.get_tlm_value(mid, tlm_variable)


def test_cfs_get_tlm_value_bytes(cfs):
    mid = {'MID': 8198, 'name': 'CFE_ES_HousekeepingTlm_t', 'PARAM_CLASS': None}
    tlm_variable = 'Payload.CommandStr'
    mock_tlm = MagicMock()
    mock_tlm.Payload = MagicMock()
    mock_tlm.Payload.CommandStr = b'mock_str'
    cfs.received_mid_packets_dic[8198].append(Packet(8198, None, mock_tlm, 1, 4.0))
    assert cfs.get_tlm_value(mid, tlm_variable) == 'mock_str'


def test_cfs_get_tlm_value_args(cfs, utils):
    mid = {'MID': 8198, 'name': 'CFE_ES_HousekeepingTlm_t', 'PARAM_CLASS': None}
    tlm_variable = 'FieldB'

    # no packet to check
    utils.clear_log()
    assert cfs.get_tlm_value(mid, tlm_variable, False, [{'variable': 'FieldA', 'value': 1, 'compare': '<'}]) is None
    assert not utils.has_log_level('INFO')
    assert not utils.has_log_level('WARNING')
    utils.clear_log()

    mock_tlm1 = MagicMock()
    mock_tlm1.FieldA = 2
    mock_tlm1.FieldB = 123
    cfs.received_mid_packets_dic[8198].append(Packet(8198, None, mock_tlm1, 1, 4.0))
    mock_tlm2 = MagicMock()
    mock_tlm2.FieldA = 1
    cfs.received_mid_packets_dic[8198].append(Packet(8198, None, mock_tlm2, 2, 5.0))

    # match found
    utils.clear_log()
    assert cfs.get_tlm_value(mid, tlm_variable, False, [{'variable': 'FieldA', 'value': 1, 'compare': '>'}]) == 123
    assert not utils.has_log_level('INFO')
    assert not utils.has_log_level('WARNING')
    utils.clear_log()

    # match not found
    utils.clear_log()
    assert cfs.get_tlm_value(mid, tlm_variable, False, [{'variable': 'FieldA', 'value': 1, 'compare': '<'}]) is None
    assert not utils.has_log_level('INFO')
    assert not utils.has_log_level('WARNING')
    utils.clear_log()


def test_cfs_check_tlm_value(cfs, mid_map, utils):
    Global.time_manager.exec_time = 10.0
    Global.current_verification_start_time = 3.0
    mid = mid_map['MOCK_TLM_MID']['MID']
    mock_tlm = mid_map['MOCK_TLM_MID']['PARAM_CLASS']
    mock_tlm.Payload.foo = 42
    seal(mock_tlm)
    assert not cfs.received_mid_packets_dic[mid]

    # first verification check
    Global.current_verification_stage = CtfVerificationStage.first_ver
    cfs.received_mid_packets_dic[mid].append(Packet(mid, None, mock_tlm, 1, 1.0))
    assert not cfs.check_tlm_value(mid_map['MOCK_TLM_MID'],
                                   [{'compare': '==', 'variable': 'foo', 'value': 42}],
                                   discard_old_packets=True)
    assert not cfs.received_mid_packets_dic[mid]

    # polling check
    Global.current_verification_stage = CtfVerificationStage.polling
    cfs.received_mid_packets_dic[mid].append(Packet(mid, None, mock_tlm, 1, 1.0))
    assert cfs.check_tlm_value(mid,
                               [{'compare': '==', 'variable': 'Payload.foo', 'value': 42}],
                               discard_old_packets=True)
    assert not cfs.received_mid_packets_dic[mid]

    # no messages left to check
    assert not cfs.check_tlm_value(mid,
                                   [{'compare': '==', 'variable': 'Payload.foo', 'value': 42}],
                                   discard_old_packets=True)
    assert not utils.has_log_level('ERROR')

    # invalid mid
    assert not cfs.check_tlm_value(0,
                                   [{'compare': '==', 'variable': 'Payload.foo', 'value': 42}],
                                   discard_old_packets=True)
    assert utils.has_log_level('ERROR')
    utils.clear_log()
    assert not cfs.check_tlm_value({'MOCK_TLM_MID': 0},
                                   [{'compare': '==', 'variable': 'Payload.foo', 'value': 42}],
                                   discard_old_packets=True)
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    # invalid payload
    cfs.received_mid_packets_dic[mid] = [Packet(mid, None, mock_tlm, 1, 1.0), (Packet(mid, None, None, 2, 3.0))]
    assert not cfs.check_tlm_value(mid,
                                   [{'compare': '!=', 'variable': 'Payload.foo', 'value': 42}],
                                   discard_old_packets=True)
    assert utils.has_log_level('ERROR')
    utils.clear_log()


def test_cfs_check_tlm_packet(cfs):
    Global.current_verification_stage = CtfVerificationStage.first_ver
    payload = MagicMock()

    class Struct(ctypes.Structure):
        _fields_ = [('field_1', ctypes.c_int),
                    ('field_array', ctypes.c_int * 5)]

    payload.nested.bool = True
    payload.nested.array = [0, 1, 2, 3]
    payload.myint = 42
    payload.myfloat = 3.14
    payload.mynone = None
    payload.mystr = 'hello'
    payload.mybytes = b'0xF00'
    payload.ctypes_int_array = (ctypes.c_int * 10)(0, 1, 2, 3)
    payload.ctypes_struct_array = (Struct * 4)()
    payload.ctypes_struct_array[0].field_1 = 4
    payload.ctypes_struct_array[1].field_1 = 14
    payload.ctypes_struct_array[2].field_1 = 24
    seal(payload)

    # expected is a list
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myint', 'value': [42]}])

    # valid bool, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'nested.bool', 'value': True}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'nested.bool', 'value': 'true'}])

    # valid array, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'nested.array[0]', 'value': 0}])
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'ctypes_int_array', 'value': 1}])
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'ctypes_struct_array',
                                           'value': {'field_1': 4}}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'nested.array[1]', 'value': 2}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'ctypes_int_array', 'value': 11}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'ctypes_struct_array',
                                               'value': {'field_invalid': 4}}])

    # valid int, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myint', 'value': 42}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myint', 'value':-42}])

    # valid float, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myfloat', 'value': 3.14}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myfloat', 'value': 3}])

    # valid string, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': 'streq', 'variable': 'mystr', 'value': 'hello'}])
    assert not cfs.check_tlm_packet(payload, [{'compare': 'streq', 'variable': 'mystr', 'value': 'HELLO'}])

    # valid bytes, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': 'streq', 'variable': 'mybytes', 'value': '0xF00'}])
    assert not cfs.check_tlm_packet(payload, [{'compare': 'streq', 'variable': 'mybytes', 'value': 'F00'}])

    # with tolerance, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myfloat', 'value': 3, 'tolerance': .14}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myfloat', 'value': 4, 'tolerance': .14}])

    # with tol_plus, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myfloat', 'value': 3, 'tolerance_plus': .14}])
    assert not cfs.check_tlm_packet(payload,
                                    [{'compare': '==', 'variable': 'myfloat', 'value': 2, 'tolerance_plus': .14}])

    # with tol_minus, pass and fail
    assert cfs.check_tlm_packet(payload,
                                [{'compare': '==', 'variable': 'myfloat', 'value': 3.2, 'tolerance_minus': .1}])
    assert not cfs.check_tlm_packet(payload,
                                    [{'compare': '==', 'variable': 'myfloat', 'value': 3.1, 'tolerance_minus': .1}])

    # with both, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myfloat', 'value': 3.1,
                                           'tolerance_minus': .1, 'tolerance_plus': .04}])
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myfloat', 'value': 3.2,
                                           'tolerance_minus': .1, 'tolerance_plus': .04}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myfloat', 'value': 3,
                                               'tolerance_minus': 1, 'tolerance_plus': .1}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myfloat', 'value': 3.3,
                                               'tolerance_minus': .1, 'tolerance_plus': 1}])

    # with mask, pass and fail
    assert cfs.check_tlm_packet(payload,
                                [{'compare': '==', 'variable': 'myint', 'value': 10, 'mask': '&', 'maskValue': 0x0F}])
    assert not cfs.check_tlm_packet(payload,
                                    [{'compare': '==', 'variable': 'myint',
                                      'value': 10, 'mask': '|', 'maskValue': 0x0F}])

    # multiple args, pass and fail
    assert cfs.check_tlm_packet(payload,
                                [{'compare': '==', 'variable': 'myint', 'value': 42},
                                 {'compare': '==', 'variable': 'myfloat', 'value': 3.14}])
    assert not cfs.check_tlm_packet(payload,
                                    [{'compare': '==', 'variable': 'myint', 'value':-42},
                                     {'compare': '==', 'variable': 'myfloat', 'value': 3.14}])


def test_cfs_check_tlm_packet_errors(cfs, utils):
    Global.current_verification_stage = CtfVerificationStage.first_ver
    payload = MagicMock()
    payload.__str__.return_value = 'mock payload'
    payload.myint = 42
    seal(payload)

    # no args
    assert cfs.check_tlm_packet(payload, [])

    # no value
    assert not cfs.check_tlm_packet(payload, [{'variable': 'myint', 'compare': '=='}])
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    # no variable
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'value': 42}])
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    # invalid variable
    assert not cfs.check_tlm_packet(payload, [{'variable': 'int', 'compare': '==', 'value': 42}])
    assert utils.has_log_level('ERROR')
    utils.clear_log()


def test_cfs_enable_output(cfs, utils):
    recvd = [
        # valid tlm, valid cmd, and then 0 to break out of read loop
        b'\x18\x12\xc0\x00\x00\x15\x00\x05\x10n\x11\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01!A\x00\x00\x00\x00',
        b'\x18\x12\xc0\x00\x00\x15\x00\x05\x10n\x11\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01!A\x00\x00\x00\x00',
        0
    ]

    cfs.telemetry.read_socket.side_effect = recvd
    receive_calls = 0

    def receive(_):
        cfs.telemetry.reset_mock()
        nonlocal receive_calls
        cfs.tlm_has_been_received = (receive_calls == 2)
        receive_calls += 1

    assert not cfs.tlm_has_been_received
    utils.clear_log()
    with patch.object(Global.time_manager, 'wait') as mock_wait:
        mock_wait.side_effect = receive
        assert cfs.enable_output()
    assert cfs.output_manager.enable_output.call_count == 3
    assert not utils.has_log_level('ERROR')


def test_cfs_interface_get_msg_header_timestamp(cfs):
    assert cfs.config.command_msg_time_source == 0
    timestamp_dic = cfs._get_msg_header_timestamp()
    assert timestamp_dic == {}

    cfs.config.command_msg_time_source = 1
    cfs.cfs_timestamp['sheader.timestamp_seconds'] = 5
    timestamp_dic = cfs._get_msg_header_timestamp()
    assert timestamp_dic['eheader.age_check_flag'] == 1
    assert timestamp_dic['sheader.timestamp_seconds'] != 5

    cfs.config.command_msg_time_source = 2
    cfs.cfs_timestamp['sheader.timestamp_seconds'] = 123
    timestamp_dic = cfs._get_msg_header_timestamp()
    assert timestamp_dic['eheader.age_check_flag'] == 1
    assert timestamp_dic['sheader.timestamp_seconds'] == cfs.cfs_timestamp['sheader.timestamp_seconds']
    # restore config.command_msg_time_source back to 0
    cfs.config.command_msg_time_source = 0


def test_cfs_enable_output_fail(cfs, utils):
    # No tlm received from socket
    cfs.telemetry.read_socket.side_effect = socket.timeout
    
    assert not cfs.tlm_has_been_received
    assert not cfs.enable_output()
    assert cfs.output_manager.enable_output.call_count > 60
    assert utils.has_log_level('ERROR')


def test_cfs_parse_telemetry_packet_segmented_packet_none(cfs, utils):
    def tlm_handler(packet_lst: list, interface):
        pkt_buf = packet_lst[0].buf
        pkt_header = interface.ccsds.CcsdsTelemetry.from_buffer(pkt_buf[0:interface.tlm_header_offset])
        return pkt_header.get_msg_id()

    tlm_test_mid = 8198
    assert tlm_test_mid not in Global.coalesce_funcs
    Global.register_construct_incomplete_tlm_func(tlm_handler, tlm_test_mid)
    assert tlm_test_mid in Global.coalesce_funcs

    # ccsds_v2 telemetry is 16 bytes, the other type telemetry is 20 bytes
    header = cfs.ccsds.CcsdsTelemetry()
    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST)
    header.pheader.set_sequence_count(100)
    header.set_msg_id(tlm_test_mid)
    header.pheader.set_packet_length(36 - 7)
    buffer1 = bytearray(header)+bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    # __append_segmented_packet, __build_from_segmented_packet could not be called directly
    # verify them through its caller parse_telemetry_packet
    assert header.get_msg_id() == tlm_test_mid
    assert header.pheader.get_segmentation_flags() == CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 0
    # The first segmented_packet, parse_telemetry_packet returns None
    assert not cfs.parse_telemetry_packet(buffer1)
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 1

    # Duplicate sequence_count/CFE_MSG_SEGFLG_FIRST, clear buffer list, then add packet
    assert not cfs.parse_telemetry_packet(buffer1)
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 1

    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST)
    header.pheader.set_sequence_count(100)
    buffer2 = bytearray(header) + bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    # Send duplicate CFE_MSG_SEGFLG_FIRST to clear buffer list, then add packet
    assert not cfs.parse_telemetry_packet(buffer2)
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 1

    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_LAST)
    header.pheader.set_sequence_count(110)
    buffer2 = bytearray(header) + bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    # Missing packets between sequence 100 and 110, __build_from_segmented_packet returns None
    assert not cfs.parse_telemetry_packet(buffer2)
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 2

    Global.coalesce_funcs.clear()


def test_cfs_parse_telemetry_packet_segmented_packet_mid(cfs):
    def tlm_handler(packet_lst: list, interface):
        pkt_buf = packet_lst[0].buf
        pkt_header = interface.ccsds.CcsdsTelemetry.from_buffer(pkt_buf[0:interface.tlm_header_offset])
        return pkt_header.get_msg_id()

    tlm_test_mid = 8198
    assert tlm_test_mid not in Global.coalesce_funcs
    # reconstruction func is not registered
    # ccsds_v2 telemetry is 16 bytes, the other type telemetry is 20 bytes
    header = cfs.ccsds.CcsdsTelemetry()
    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST)
    header.pheader.set_sequence_count(100)
    header.set_msg_id(tlm_test_mid)
    header.pheader.set_packet_length(36 - 7)
    buffer1 = bytearray(header) + bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    assert cfs.parse_telemetry_packet(buffer1) == tlm_test_mid
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 0

    Global.register_construct_incomplete_tlm_func(tlm_handler, tlm_test_mid)
    assert tlm_test_mid in Global.coalesce_funcs

    assert cfs.parse_telemetry_packet(buffer1) is None
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 1

    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_CNT)
    header.pheader.set_sequence_count(102)
    buffer2 = bytearray(header) + bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    # not receive CFE_MSG_SEGFLG_LAST packet, will not build
    assert cfs.parse_telemetry_packet(buffer2) is None

    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_CNT)
    header.pheader.set_sequence_count(101)
    buffer3 = bytearray(header) + bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    # not receive CFE_MSG_SEGFLG_LAST packet, will not build
    assert cfs.parse_telemetry_packet(buffer3) is None
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 3

    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_LAST)
    header.pheader.set_sequence_count(103)
    buffer4 = bytearray(header) + bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    # Four segmented_packets, should aggregate the payload; parse_telemetry_packet returns packet MID
    assert cfs.parse_telemetry_packet(buffer4) == tlm_test_mid
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 4

    Global.coalesce_funcs.clear()


def test_cfs_parse_telemetry_packet_segmented_packet_rollover(cfs):
    def tlm_handler(packet_lst: list, interface):
        pkt_buf = packet_lst[0].buf
        pkt_header = interface.ccsds.CcsdsTelemetry.from_buffer(pkt_buf[0:interface.tlm_header_offset])
        return pkt_header.get_msg_id()

    tlm_test_mid = 8198
    cfs.mid_val_map[tlm_test_mid] = 'FM_DIR_TEST_MID'
    assert 'FM_DIR_TEST_MID' not in Global.coalesce_funcs
    Global.register_construct_incomplete_tlm_func(tlm_handler, 'FM_DIR_TEST_MID')
    assert 'FM_DIR_TEST_MID' in Global.coalesce_funcs

    max_seq = 2 ** 14 - 1  # 16383
    # ccsds_v2 telemetry is 16 bytes, the other type telemetry is 20 bytes
    header = cfs.ccsds.CcsdsTelemetry()
    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST)
    header.pheader.set_sequence_count(max_seq - 1)
    header.pheader.set_packet_length(36 - 7)
    header.set_msg_id(tlm_test_mid)
    buffer1 = bytearray(header) + bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    # The first segmented_packet, parse_telemetry_packet returns None
    assert cfs.parse_telemetry_packet(buffer1) is None
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 1

    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_CNT)
    header.pheader.set_sequence_count(0)
    buffer2 = bytearray(header) + bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    # not receive CFE_MSG_SEGFLG_LAST packet, will not build
    assert cfs.parse_telemetry_packet(buffer2) is None

    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_CNT)
    header.pheader.set_sequence_count(max_seq)
    buffer3 = bytearray(header) + bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    # not receive CFE_MSG_SEGFLG_LAST packet, will not build
    assert cfs.parse_telemetry_packet(buffer3) is None
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 3

    header.pheader.set_segmentation_flags(CcsdsPacketInterface.CFE_MSG_SEGFLG_LAST)
    header.pheader.set_sequence_count(1)
    buffer4 = bytearray(header) + bytearray(b'(\x01\xc0\x02\x00\x99\x0c \x00B+F\x0f\x00;\xcd\x00\x00\xfb\x8a')
    # Four segmented_packets, should aggregate the payload; parse_telemetry_packet returns packet MID
    assert cfs.parse_telemetry_packet(buffer4) == tlm_test_mid
    assert len(cfs.incomplete_packet_dic[tlm_test_mid]) == 4

    Global.coalesce_funcs.clear()


def test_cfs_sort_incomplete_packets(cfs):
    buffer_lst = list()
    pkt_1 = InCompletePacket(100, CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST,
                             Global.get_time_manager().exec_time, bytearray(10))
    pkt_2 = InCompletePacket(101, CcsdsPacketInterface.CFE_MSG_SEGFLG_LAST,
                             Global.get_time_manager().exec_time, bytearray(10))
    buffer_lst.append(pkt_2)
    buffer_lst.append(pkt_1)
    CfsInterface._sort_incomplete_packets(buffer_lst)
    assert buffer_lst[0].seq == 100
    assert buffer_lst[1].seq == 101

    max_seq = 2 ** 14 - 1  # 16383
    buffer_lst.clear()
    pkt_1 = InCompletePacket(max_seq - 1, CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST,
                             Global.get_time_manager().exec_time, bytearray(10))
    pkt_2 = InCompletePacket(max_seq, CcsdsPacketInterface.CFE_MSG_SEGFLG_CNT,
                             Global.get_time_manager().exec_time, bytearray(10))
    pkt_3 = InCompletePacket(0, CcsdsPacketInterface.CFE_MSG_SEGFLG_CNT,
                             Global.get_time_manager().exec_time, bytearray(10))
    pkt_4 = InCompletePacket(1, CcsdsPacketInterface.CFE_MSG_SEGFLG_LAST,
                             Global.get_time_manager().exec_time, bytearray(10))
    buffer_lst.append(pkt_2)
    buffer_lst.append(pkt_1)
    buffer_lst.append(pkt_4)
    buffer_lst.append(pkt_3)
    CfsInterface._sort_incomplete_packets(buffer_lst)
    assert buffer_lst[0].seq == max_seq - 1 and buffer_lst[0].seg_flag == CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST
    assert buffer_lst[1].seq == max_seq and buffer_lst[1].seg_flag == CcsdsPacketInterface.CFE_MSG_SEGFLG_CNT
    assert buffer_lst[2].seq == max_seq + 1 and buffer_lst[2].seg_flag == CcsdsPacketInterface.CFE_MSG_SEGFLG_CNT
    assert buffer_lst[3].seq == max_seq + 2 and buffer_lst[3].seg_flag == CcsdsPacketInterface.CFE_MSG_SEGFLG_LAST


def test_cfs_parse_telemetry_packet_variable_len_packet(cfs):
    def tlm_handler(pkt_buf: bytearray, interface, mid_str: str):
        pkt_header = interface.ccsds.CcsdsTelemetry.from_buffer(pkt_buf[0:interface.tlm_header_offset])
        return pkt_header.get_msg_id()

    tml_test_mid = 8199
    assert tml_test_mid not in Global.variable_payload_length_funcs
    Global.register_construct_variable_length_payload_func(tlm_handler, tml_test_mid)

    # ccsds_v2 telemetry is 16 bytes, the other type telemetry is 20 bytes
    header = cfs.ccsds.CcsdsTelemetry()
    header.pheader.set_sequence_count(100)
    header.set_msg_id(tml_test_mid)
    header.pheader.set_packet_length(26-7)
    buffer1 = bytearray(header) + bytearray(10)
    assert cfs.parse_telemetry_packet(buffer1) == tml_test_mid
    Global.variable_payload_length_funcs.pop(tml_test_mid)


def test_cfs_parse_telemetry_packet_exception(cfs, utils):
    buff = bytearray(b'\x8b\xc0\x00\x00\x1d\x00\x00\x1d\x00\x00\x1d\x00\x00\x1d\x00*\x00\x00\x02\x021')
    with patch.object(cfs, 'ccsds') as mock_ccsds:
        mock_header = MagicMock()
        mock_header.get_msg_id.side_effect = ValueError('mock error')
        mock_telemetry = MagicMock()
        mock_telemetry.from_buffer.return_value = mock_header
        mock_ccsds.CcsdsTelemetry = mock_telemetry
        with patch('ctypes.sizeof', return_value=20):
            assert cfs.parse_telemetry_packet(buff) is None
            assert utils.has_log_level('DEBUG')


def test_cfs_parse_telemetry_packet_length_match(cfs, utils):
    buff = bytearray(b'\x8b\xc0\x00\x00\x1d\x00\x00\x1d\x00\x00\x1d\x00\x00\x1d\x00*\x00\x00\x02\x021')
    with patch.object(cfs, 'ccsds') as mock_ccsds:
        mock_header = MagicMock()
        mock_header.get_msg_id.return_value = 8198
        mock_header.get_msg_size.return_value = -2
        mock_telemetry = MagicMock()
        mock_telemetry.from_buffer.return_value = mock_header
        mock_ccsds.CcsdsTelemetry = mock_telemetry
        assert cfs.parse_telemetry_packet(buff) is None
        assert utils.has_log_level('WARNING')


def test_cfs_parse_telemetry_packet_header_validate(cfs, utils):
    # Create the MagicMock that will act as the 'header' object
    mock_header = MagicMock()

    # Configure the behavior of the header
    mock_header.validate.return_value = False
    mock_header.get_msg_id.return_value = 0xABCD
    mock_header.get_msg_size.return_value = 128
    # Nested mock for: header.pheader.get_segmentation_flags()
    mock_header.pheader.get_segmentation_flags.return_value = 1
    utils.clear_log()

    # Patch the 'from_buffer' method on the class
    target_class = cfs.ccsds.CcsdsTelemetry
    with patch.object(target_class, 'from_buffer', return_value=mock_header):
        buffer = bytearray(200)
        result = cfs.parse_telemetry_packet(buffer)
        assert result is None
        assert utils.has_log_level('DEBUG')
        assert utils.has_log('Telemetry packet is discarded as CRC check fails.')


def test_cfs_parse_telemetry_packet_payload_exception(cfs, utils):
    # ccsds_v2 telemetry is 16 bytes, the other type telemetry is 20 bytes
    tlm_test_mid = 18198
    header = cfs.ccsds.CcsdsTelemetry()
    header.pheader.set_sequence_count(100)
    header.set_msg_id(tlm_test_mid)
    header.pheader.set_packet_length(100 - 7)
    buffer = bytearray(header) + bytearray(100-16)

    cfs.has_received_mid[tlm_test_mid] = False
    cfs.mid_payload_map[tlm_test_mid] = MagicMock()
    cfs.mid_payload_map[tlm_test_mid].from_buffer.side_effect = ValueError('mock error')

    utils.clear_log()
    assert cfs.parse_telemetry_packet(buffer) is None
    assert utils.has_log_level('ERROR')
    assert utils.has_log('cannot retrieve payload from packet with MID')


def test_cfs_parse_telemetry_packet_time_source(cfs):
    # ccsds_v2 telemetry is 16 bytes, the other type telemetry is 20 bytes
    tlm_test_mid = 8198
    header = cfs.ccsds.CcsdsTelemetry()
    header.pheader.set_sequence_count(100)
    header.set_msg_id(tlm_test_mid)
    header.pheader.set_packet_length(100 - 7)
    buffer = bytearray(header) + bytearray(100-16)

    cfs.has_received_mid[tlm_test_mid] = False
    cfs.has_received_mid[tlm_test_mid] = 0
    cfs.mid_payload_map[tlm_test_mid] = MagicMock()
    cfs.config.command_msg_time_source = 2
    cfs.cfs_timestamp = {}
    assert cfs.parse_telemetry_packet(buffer) == tlm_test_mid
    assert len(cfs.cfs_timestamp) > 0

    cfs.config.command_msg_time_source = tlm_test_mid
    cfs.cfs_timestamp = {}
    assert cfs.parse_telemetry_packet(buffer) == tlm_test_mid
    assert len(cfs.cfs_timestamp) > 0


def test_check_str_value(cfs):
    assert not cfs._check_str_value('actual', 'expected', 'invalid_compare')
    assert cfs._check_str_value('expected', 'expected', 'streq')
    assert not cfs._check_str_value('expected', 'expected', 'strneq')
    assert not cfs._check_str_value('actual', 'expected', 'streq')
    assert cfs._check_str_value('actual', 'expected', 'strneq')
    assert cfs._check_str_value('expected', 'exp*', 'regex')


def test_cfs_log_invalid_packet(cfs, utils):
    cfs.log_invalid_packet(8198)
    assert utils.has_log_level('ERROR')
    assert cfs.has_received_mid[8198]


def test_cfs_build_from_incomplete_packets_fail(cfs):
    tml_test_mid = 8198
    cfs.incomplete_packet_dic[tml_test_mid].clear()
    pkt_1 = InCompletePacket(100, CcsdsPacketInterface.CFE_MSG_SEGFLG_FIRST,
                             Global.get_time_manager().exec_time, bytearray(10))
    cfs.incomplete_packet_dic[tml_test_mid].append(pkt_1)
    # Too few incomplete packets to build
    assert cfs._build_from_incomplete_packets(tml_test_mid) is None

    pkt_2 = InCompletePacket(100, CcsdsPacketInterface.CFE_MSG_SEGFLG_CNT,
                             Global.get_time_manager().exec_time, bytearray(10))
    pkt_3 = InCompletePacket(102, CcsdsPacketInterface.CFE_MSG_SEGFLG_LAST,
                             Global.get_time_manager().exec_time, bytearray(10))
    cfs.incomplete_packet_dic[tml_test_mid].append(pkt_2)
    cfs.incomplete_packet_dic[tml_test_mid].append(pkt_3)
    # Incomplete packets not strictly increasing
    assert cfs._build_from_incomplete_packets(tml_test_mid) is None

    cfs.incomplete_packet_dic[tml_test_mid].clear()


