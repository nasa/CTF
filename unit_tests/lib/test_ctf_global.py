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
import sys
from unittest.mock import patch, Mock

import pytest

from lib.ctf_global import Global, CtfVerificationStage


# TODO move to top conftest, pass to init_global
@pytest.fixture(scope='function', autouse=True)
def global_reinit():
    Global.config = None
    Global.plugins_available = dict()
    Global.plugin_manager = None
    Global.current_script_log_dir = ""
    Global.test_log_dir = ""
    Global.CTF_log_dir = ""
    Global.CTF_log_dir_file = None
    Global.time_manager = None
    Global.test_start_time = None
    Global.current_verification_start_time = None
    Global.current_verification_stage = CtfVerificationStage.none


def test_ctf_global_init():
    assert not Global.config
    assert not Global.plugins_available
    assert not Global.plugin_manager
    assert not Global.current_script_log_dir
    assert not Global.test_log_dir
    assert not Global.CTF_log_dir
    assert not Global.CTF_log_dir_file
    assert not Global.time_manager
    assert not Global.test_start_time
    assert not Global.current_verification_start_time
    assert Global.current_verification_stage == CtfVerificationStage.none


def test_ctf_global_create_arg_parser():
    with patch.object(sys, 'argv', ['ctf',
                                    '--port=1234',
                                    '--pluginInfo=./plugins/info',
                                    '--config_file=./configs/ci_config.ini'
                                    ]):
        args = Global.create_arg_parser().parse_args()
    assert not args.scripts
    assert args.port == 1234
    assert args.pluginInfo == './plugins/info'
    assert args.config_file == './configs/ci_config.ini'

    with patch.object(sys, 'argv', ['ctf',
                                    './functional_tests/plugin_tests/Test-CTF-Basic-Example.json',
                                    './functional_tests/plugin_tests/Test-CTF-Intermediate-Example.json',
                                    './functional_tests/plugin_tests/Test-CTF-Advanced-Example.json']):
        args = Global.create_arg_parser().parse_args()
    assert len(args.scripts) == 3
    assert not args.port
    assert not args.pluginInfo
    assert args.config_file == 'configs/default_config.ini'


def test_ctf_global_load_config():
    status = Global.load_config("configs/default_config.ini")
    assert status
    assert Global.config
    assert os.environ['workspace_dir'] == '~/sample_cfs_workspace'


def test_ctf_global_load_config_invalid():
    # trigger exit call if config files do not exist
    with patch('lib.ctf_global.sys.exit', side_effect=Exception('mock exit')):
        with pytest.raises(Exception):
            Global.load_config('')
    assert not Global.config


def test_ctf_global_time_manager():
    assert Global.get_time_manager() is None
    Global.set_time_manager(Mock())
    assert Global.get_time_manager() == Global.time_manager
