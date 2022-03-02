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

import ctypes
from unittest.mock import MagicMock, patch

import pytest

from lib.ctf_global import Global
from plugins.cfs.cfs_config import CfsConfig
from plugins.cfs.cfs_plugin import CfsPlugin


@pytest.fixture(scope="session", autouse=True)
def init_global():
    from lib.ctf_global import Global
    from lib.logger import set_logger_options_from_config
    Global.load_config("./configs/default_config.ini")
    with patch('os.makedirs'):
        set_logger_options_from_config(Global.config)


@pytest.fixture
@patch('plugins.cfs.cfs_plugin.RemoteCfsController')
@patch('plugins.cfs.cfs_plugin.CfsController')
def cfs_plugin(mock_local, mock_remote):
    """
    CFS interfaces are patched here to avoid attempts to build or start CFS when a target is registered with the plugin
    """
    mock_local.return_value.name = "CfsController"
    mock_remote.return_value.name = "RemoteCfsController"
    return CfsPlugin()


@pytest.fixture
def cfs_config():
    Global.load_config("./configs/default_config.ini")
    return CfsConfig("cfs")


@pytest.fixture(name='utils')
def ctf_test_utils(caplog):
    class CtfTestUtils:
        @staticmethod
        def clear_log():
            caplog.clear()

        @staticmethod
        def has_log_level(level):
            return any([rec for rec in caplog.records if rec.levelname == level])

    return CtfTestUtils


class EvsLongStruct(ctypes.Structure):
    # need Payload field
    _fields_ = [('x', ctypes.c_uint8, 8)]


class EvsShortStruct(ctypes.Structure):
    _fields_ = [('y', ctypes.c_uint8, 2)]


class MockStruct(ctypes.Structure):
    _fields_ = [('foo', ctypes.c_uint16, 16)]


@pytest.fixture
def mid_map():
    mock_evs_long = MagicMock()
    mock_evs_long.__name__ = 'Mock EVS Long Event Msg'
    mock_tlm = MagicMock()
    mock_tlm.__name__ = 'Mock Tlm Msg'
    return {
        'CFE_EVS_LONG_EVENT_MSG_MID': {
            'MID': 8198,
            'PARAM_CLASS': mock_evs_long
        },
        'CFE_EVS_SHORT_EVENT_MSG_MID': {
            'MID': 8199,
            'PARAM_CLASS': MagicMock()
        },
        'TO_COMMAND_MID': {
            'MID': 10891,
            'CC': {
                'TO_ENABLE_OUTPUT_CC': {
                    'CODE': 2,
                    'ARG_CLASS': MagicMock()
                }
            }
        },
        'MOCK_TLM_MID': {
            'MID': 1337,
            'PARAM_CLASS': mock_tlm
        }
    }


@pytest.fixture
def ccsdsv2():
    from plugins.ccsds_plugin.ccsds_packet_interface import CcsdsHeaderTypes
    from plugins.ccsds_plugin.cfe.ccsds_v2.ccsds_v2 import CcsdsPrimaryHeader, CcsdsCommand, CcsdsTelemetry
    return CcsdsHeaderTypes(CcsdsPrimaryHeader, CcsdsCommand, CcsdsTelemetry)
