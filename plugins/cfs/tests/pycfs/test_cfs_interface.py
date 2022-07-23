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

import socket
from unittest.mock import patch, MagicMock, mock_open, seal

import pytest

from lib.ctf_global import Global, CtfVerificationStage
from lib.exceptions import CtfConditionError
from plugins.cfs.pycfs.cfs_interface import Packet


@pytest.fixture(scope='session', autouse=True)
def init_global():
    Global.load_config('./configs/default_config.ini')
    time_mgr = MagicMock()
    time_mgr.exec_time = 1.0
    Global.time_manager = time_mgr
    Global.current_script_log_dir = '.'


@pytest.fixture(name='cfs')
def cfs_interface(cfs_config, mid_map, ccsdsv2):
    from plugins.cfs.pycfs.cfs_interface import CfsInterface
    from plugins.cfs.pycfs.command_interface import CommandInterface
    from plugins.cfs.pycfs.tlm_listener import TlmListener
    mock_tlm = MagicMock(spec=TlmListener)
    mock_cmd = MagicMock(spec=CommandInterface)
    with patch('plugins.cfs.pycfs.output_app_interface.ToApi', name='mock'):
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
    assert cfs.cmd_packet_list == []
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
    assert cfs.pheader_offset == 6
    assert cfs.should_skip_header is True
    assert cfs.tlm_header_offset == 16
    assert cfs.cmd_header_offset == 16


def test_cfs_interface_init_invalid(cfs_config, mid_map, ccsdsv2, utils):
    from plugins.cfs.pycfs.cfs_interface import CfsInterface
    from plugins.cfs.pycfs.command_interface import CommandInterface
    from plugins.cfs.pycfs.tlm_listener import TlmListener
    mock_tlm = MagicMock(spec=TlmListener)
    mock_cmd = MagicMock(spec=CommandInterface)
    mid_map = {k: v for k, v in mid_map.items() if 'EVS' not in k}
    with patch.object(cfs_config, 'tlm_udp_port', 0):
        with patch('plugins.cfs.pycfs.output_app_interface.ToApi', name='mock'):
            cfs = CfsInterface(cfs_config, mock_tlm, mock_cmd, mid_map, ccsdsv2)
            assert utils.has_log_level('ERROR')
            assert cfs.evs_long_event_msg_mid == -1
            assert cfs.evs_short_event_msg_mid == -1
            assert cfs.config.tlm_udp_port != 0


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
    with patch('builtins.open', new_callable=mock_open()) as mock_file:
        cfs.config.telemetry_debug = True
        cfs.write_tlm_log('payload1', bytearray('payload1', 'utf-8'), 100)
        assert cfs.tlm_log_file is mock_file.return_value
        mock_file.assert_called_once_with('./cfs_tlm_msgs.log', 'a+')
        assert mock_file.return_value.write.call_count == 3
        mock_file.return_value.write.reset_mock()
        cfs.write_tlm_log('payload2', bytearray('payload2', 'utf-8'), 200)
        assert mock_file.return_value.write.call_count == 2
        mock_file.return_value.write.reset_mock()
        mock_file.return_value.write.side_effect = IOError('mock error')
        cfs.write_tlm_log('payload3', bytearray('payload3', 'utf-8'), 300)
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
        cfs.has_received_mid[8198] = False
        cfs.mid_payload_map[8198].from_buffer.side_effect = ValueError('mock error')
        cfs.read_sb_packets()
        assert mock_tlm.read_socket.call_count == 2
        assert not cfs.unchecked_packet_mids
        assert not cfs.received_mid_packets_dic[8198]
        assert cfs.has_received_mid[8198]
        assert utils.has_log_level('ERROR')
        utils.clear_log()

        # read invalid cmd
        mock_tlm.reset_mock()
        cfs.has_received_mid[10891] = False
        cfs.mid_payload_map[10891]['TO_ENABLE_OUTPUT_CC']['ARG_CLASS'].from_buffer.side_effect \
            = ValueError('mock error')
        cfs.read_sb_packets()
        assert mock_tlm.read_socket.call_count == 2
        assert not cfs.unchecked_packet_mids
        assert not cfs.received_mid_packets_dic[10891]
        assert cfs.has_received_mid[10891]
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
        cfs.unchecked_packet_mids.append(8198)
        cfs.check_tlm_conditions()
        assert not cfs.unchecked_packet_mids
        mock_check.assert_not_called()

        # test placeholder only
        cfs.unchecked_packet_mids.append(8198)
        cfs.add_tlm_condition('v_id1', mid_map['CFE_EVS_LONG_EVENT_MSG_MID'], 'v_id1 args')
        cfs.received_mid_packets_dic[8198].append(Packet(8198, None, MagicMock(), 1, 0.0))
        cfs.check_tlm_conditions()
        assert not cfs.unchecked_packet_mids
        mock_check.assert_not_called()

        # test check pass
        cfs.unchecked_packet_mids.append(8198)
        cfs.received_mid_packets_dic[8198].append(Packet(8198, None, MagicMock(), 1, 1.0))
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
        cfs.unchecked_packet_mids.append(8198)
        cfs.received_mid_packets_dic[8198].append(Packet(8198, None, MagicMock(), 1, 1.0))
        with pytest.raises(CtfConditionError):
            cfs.check_tlm_conditions()
        # assert condition was removed
        # assert not verification.passed
        # assert not verification.pass_count


def test_cfs_send_command(cfs):
    cfs.command.send_command.return_value = 1
    assert cfs.send_command('mid', 'cc', bytearray(0x1)) == 1
    cfs.command.send_command.assert_called_once_with('mid', 'cc', bytearray(0x1), None)


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
                                   [{'compare': '==', 'variable': 'foo', 'value': '42'}],
                                   discard_old_packets=True)
    assert not cfs.received_mid_packets_dic[mid]

    # polling check
    Global.current_verification_stage = CtfVerificationStage.polling
    cfs.received_mid_packets_dic[mid].append(Packet(mid, None, mock_tlm, 1, 1.0))
    assert cfs.check_tlm_value(mid,
                               [{'compare': '==', 'variable': 'Payload.foo', 'value': '42'}],
                               discard_old_packets=True)
    assert not cfs.received_mid_packets_dic[mid]

    # no messages left to check
    assert not cfs.check_tlm_value(mid,
                                   [{'compare': '==', 'variable': 'Payload.foo', 'value': '42'}],
                                   discard_old_packets=True)
    assert not utils.has_log_level('ERROR')

    # invalid mid
    assert not cfs.check_tlm_value(0,
                                   [{'compare': '==', 'variable': 'Payload.foo', 'value': '42'}],
                                   discard_old_packets=True)
    assert utils.has_log_level('ERROR')
    utils.clear_log()
    assert not cfs.check_tlm_value({'MOCK_TLM_MID': 0},
                                   [{'compare': '==', 'variable': 'Payload.foo', 'value': '42'}],
                                   discard_old_packets=True)
    assert utils.has_log_level('ERROR')
    utils.clear_log()

    # invalid payload
    cfs.received_mid_packets_dic[mid] = [Packet(mid, None, mock_tlm, 1, 1.0), (Packet(mid, None, None, 2, 3.0))]
    assert not cfs.check_tlm_value(mid,
                                   [{'compare': '!=', 'variable': 'Payload.foo', 'value': '42'}],
                                   discard_old_packets=True)
    assert utils.has_log_level('ERROR')
    utils.clear_log()


def test_cfs_check_tlm_packet(cfs):
    Global.current_verification_stage = CtfVerificationStage.first_ver
    payload = MagicMock()
    payload.nested.bool = True
    payload.nested.array = [0, 1, 2, 3]
    payload.myint = 42
    payload.myfloat = 3.14
    payload.mynone = None
    payload.mystr = 'hello'
    payload.mybytes = b'0xF00'
    seal(payload)

    # expected is a list
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myint', 'value': [42, None]}])

    # valid bool, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'nested.bool', 'value': True}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'nested.bool', 'value': 'true'}])

    # valid array, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'nested.array[0]', 'value': 0}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'nested.array[1]', 'value': 2}])

    # valid int, pass and fail
    assert cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myint', 'value': 42}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myint', 'value': -42}])

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
                                               'tolerance_minus': 1,  'tolerance_plus': .1}])
    assert not cfs.check_tlm_packet(payload, [{'compare': '==', 'variable': 'myfloat', 'value': 3.3,
                                               'tolerance_minus': .1,  'tolerance_plus': 1}])

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
                                    [{'compare': '==', 'variable': 'myint', 'value': -42},
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
    receive_calls = 0

    def receive(_):
        nonlocal receive_calls
        cfs.tlm_has_been_received = (receive_calls == 2)
        receive_calls += 1

    assert not cfs.tlm_has_been_received
    with patch.object(Global.time_manager, 'wait') as mock_wait:
        mock_wait.side_effect = receive
        assert cfs.enable_output()
    assert cfs.output_manager.enable_output.call_count == 3
    assert not utils.has_log_level('ERROR')


def test_cfs_enable_output_fail(cfs, utils):
    assert not cfs.tlm_has_been_received
    assert not cfs.enable_output()
    assert cfs.output_manager.enable_output.call_count > 60
    assert utils.has_log_level('ERROR')
