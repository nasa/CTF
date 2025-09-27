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
# File: conftest.py
#
# Purpose: This file contains pytest fixture for ccsds plugin unit tests.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

import pytest

from lib.plugin_manager import PluginManager
from core_plugins.ccsds_plugin.ccsds_plugin import CCSDSPlugin
from core_plugins.ccsds_plugin.ccsds_interface import CCSDSInterface
from core_plugins.cfs.cfs_config import CfsConfig
from lib.ctf_global import Global
from lib.logger import set_logger_options_from_config
from core_plugins.cfs.cfs_plugin import CfsPlugin


@pytest.fixture(scope="session", autouse=True)
def init_global():
    Global.load_config("./configs/default_config.ini")
    # Global.plugin_manager is set by PluginManager constructor
    PluginManager(['core_plugins'])


@pytest.fixture(name="ccsds_plugin_instance")
def _ccsds_plugin_instance():
    return CCSDSPlugin()


@pytest.fixture(name="cfs_plugin_instance")
def _cfs_plugin_instance():
    return CfsPlugin()


@pytest.fixture(name="ccsdsinterface_instance")
def _ccsdsinterface_instance():
    # need to pass CfsController.config to config argument self.ccsds_reader = CCDDExportReader(self.config)
    config = CfsConfig("cfs")
    return CCSDSInterface(config=config)
