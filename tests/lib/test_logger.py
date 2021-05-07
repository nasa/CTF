# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2021 United States Government as represented by the
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
from datetime import datetime

import lib.logger as logger
from lib.ctf_global import Global


def test_set_logger_options_from_config():
    Global.load_config('./configs/default_config.ini')
    logger.set_logger_options_from_config(Global.config)
    assert Global.CTF_log_dir == os.path.abspath('./script_outputs')
    assert Global.CTF_log_dir_file == os.path.abspath('./script_outputs/CTF_Log_File.log')
    assert os.path.exists(Global.CTF_log_dir)
    assert logger.logger.handlers[0].baseFilename == Global.CTF_log_dir_file


def test_testformatter(caplog):
    formatter = logger.TestFormatter()
    logger.logger.info('test log')
    record = caplog.records[0]
    record.created = datetime(1970, 1, 1).timestamp()
    record.msecs = 12

    # default format
    assert formatter.formatTime(record) == '00:00:00.012'
    # valid format
    assert formatter.formatTime(record, "[%c]") == '[Thu Jan  1 00:00:00 1970]'
    # invalid format
    assert formatter.formatTime(record, "invalid") == 'invalid'


def test_logger_change_log_file():
    logger.change_log_file('./temp_log')
    assert logger.logger.handlers[0].baseFilename == os.path.abspath('./temp_log')
    logger.change_log_file(Global.CTF_log_dir_file)
