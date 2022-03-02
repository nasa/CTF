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

import os
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

import lib.logger as logger
from lib.ctf_global import Global


def test_set_logger_options_from_config():
    Global.load_config('./configs/default_config.ini')
    with patch('os.makedirs') as mock_makedir:
        with patch('time.localtime', MagicMock(return_value=time.gmtime(0))):
            logger.set_logger_options_from_config(Global.config)
    assert Global.CTF_log_dir == os.path.abspath('./CTF_Results')
    assert Global.test_log_dir == os.path.abspath('./CTF_Results/Run_01_01_1970_00_00_00')
    assert Global.CTF_log_dir_file == os.path.abspath('./CTF_Results/Run_01_01_1970_00_00_00/CTF_Log_File.log')
    mock_makedir.assert_called_with(Global.test_log_dir)


def test_testformatter(caplog):
    logger.logger.error('test log')
    record = caplog.records[0]
    record.created = datetime(1970, 1, 1).timestamp()
    record.msecs = 12

    # actual format
    assert logger.test_formatter.format(record) == \
           '[00:00:00.012] test_logger                     (36 ) *** ERROR: test log'
    # default format
    assert logger.test_formatter.formatTime(record) == '00:00:00'
    # valid format
    assert logger.test_formatter.formatTime(record, "[%c]") == '[Thu Jan  1 00:00:00 1970]'
    # invalid format
    assert logger.test_formatter.formatTime(record, "invalid") == 'invalid'


def test_logger_change_log_file():
    logger.change_log_file('./temp_log')
    default_handler = logger.logger.handlers[0]
    assert logger.logger.handlers[0].baseFilename == os.path.abspath('./temp_log')
    logger.logger.handlers[0] = default_handler
