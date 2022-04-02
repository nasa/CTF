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

from unittest.mock import patch

from lib.ctf_global import Global


def test_ccsds_plugin_init(ccsds_plugin_instance):
    """
    Test CCSDS plugin constructor
    """
    assert ccsds_plugin_instance.name == "CCSDS Plugin"
    assert ccsds_plugin_instance.description == "CTF CCSDS Plugin"
    assert ccsds_plugin_instance.cfs_plugin


def test_ccsds_plugin_commandmap(ccsds_plugin_instance):
    """
    Test CCSDS plugin command content
    """
    assert "ValidateCfsCcsdsData" in ccsds_plugin_instance.command_map


def test_ccsds_plugin_get_cfs_plugin(ccsds_plugin_instance):
    """
    Test CCSDS plugin get_cfs_plugin method
    """
    ccsds_plugin_instance.get_cfs_plugin()
    # plugin manager is not initialized yet
    if not Global.plugins_available:
        assert ccsds_plugin_instance.cfs_plugin is None


def test_ccsds_plugin_initialize(ccsds_plugin_instance):
    """
    Test CCSDS plugin initialize method: this method only log a message
    """
    assert ccsds_plugin_instance.initialize() is None


def test_ccsds_plugin_shutdown(ccsds_plugin_instance):
    """
    Test CCSDS plugin shutdown method: this method does not do actual work
    """
    assert ccsds_plugin_instance.shutdown() is None


def test_ccsds_plugin_validate_cfs_ccsds_data_fail(ccsds_plugin_instance, utils, cfs_plugin_instance):
    """
    Test CCSDS plugin validate_cfs_ccsds_data method: failed cases
    Validates the CCSDS data types by sending an empty instance of each command code found in the MID map to CFS.
    """
    utils.clear_log()
    # plugin manager is not initialized yet
    with patch("plugins.ccsds_plugin.ccsds_plugin.CCSDSPlugin.get_cfs_plugin", return_value=None):
        ccsds_plugin_instance.cfs_plugin = None
        assert not ccsds_plugin_instance.validate_cfs_ccsds_data()
        assert utils.has_log_level("ERROR")

    # another error case: cfs plugin not registered
    utils.clear_log()
    Global.plugins_available = {"CFS Plugin": cfs_plugin_instance}
    assert not ccsds_plugin_instance.validate_cfs_ccsds_data()
    assert utils.has_log_level("ERROR")

    # cfs target is not defined
    utils.clear_log()
    cfs_plugin_instance.initialize()
    assert not ccsds_plugin_instance.validate_cfs_ccsds_data("target1")
    assert utils.has_log_level("ERROR")


def test_ccsds_plugin_validate_cfs_ccsds_data(ccsds_plugin_instance, cfs_plugin_instance):
    """
    Test CCSDS plugin validate_cfs_ccsds_data method:
    Validates the CCSDS data types by sending an empty instance of each command code found in the MID map to CFS.
    """
    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface'):
        if Global.get_time_manager() is None:
            print("Global.get_time_manager() is None:")
            cfs_plugin_instance.initialize()

        Global.plugins_available = {"CFS Plugin": cfs_plugin_instance}
        cfs_plugin_instance.register_cfs('cfs')

    with patch('plugins.cfs.cfs_plugin.CfsPlugin.send_cfs_command', return_value=True), \
         patch('lib.ctf_global.Global.time_manager.wait', return_value=True):
        ccsds_plugin_instance.validate_cfs_ccsds_data('cfs')
