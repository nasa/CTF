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

import pytest
from unittest.mock import Mock, patch

from lib.ctf_global import Global
from lib.plugin_manager import PluginManager
from plugins.validation_plugin.validation_plugin import ValidationPlugin


@pytest.fixture(scope="session", autouse=True)
def init_global():
    Global.load_config("./configs/default_config.ini")
    # Global.plugin_manager is set by PluginManager constructor
    PluginManager(['plugins'])


@pytest.fixture(name="validation_plugin")
def _validation_plugin_instance():
    return ValidationPlugin()


def test_validation_plugin_init(validation_plugin):
    """
    Test Validation initialize method
    """
    assert validation_plugin.initialize()
    assert validation_plugin.description == "CTF Validation Plugin"
    assert validation_plugin.name == "ValidationPlugin"


def test_validation_plugin_commandmap(validation_plugin):
    """
    Test Validation command content
    """
    assert len(validation_plugin.command_map) == 6
    assert "DeleteFiles" in validation_plugin.command_map
    assert "CopyFiles" in validation_plugin.command_map
    assert "SaveFileAsText" in validation_plugin.command_map
    assert "SearchStr" in validation_plugin.command_map
    assert "SearchNoStr" in validation_plugin.command_map
    assert "InsertUserComment" in validation_plugin.command_map


def test_validation_plugin_verify_required_commands(validation_plugin):
    assert len(validation_plugin.verify_required_commands) == 0


def test_validation_plugin_initialize(validation_plugin):
    assert validation_plugin.initialize()


def test_validation_plugin_shutdown(validation_plugin):
    assert validation_plugin.shutdown() is None


def test_validation_plugin_copy_file_fail(validation_plugin, utils):
    utils.clear_log()
    assert not validation_plugin.copy_file('./file_not_exist.py', './copied_file.py')
    assert utils.has_log_level("ERROR")


def test_validation_plugin_copy_file_exception(validation_plugin, utils):
    utils.clear_log()
    with patch('shutil.copytree') as mock_copytree:
        mock_copytree.side_effect = IOError("mock shutil.copytree")
        assert not validation_plugin.copy_file('./configs', './copied_folder')
        assert utils.has_log_level("ERROR")


def test_validation_plugin_copy_file(validation_plugin):
    assert validation_plugin.copy_file('./ctf', './copied_file.py')
    assert validation_plugin.copy_file('./configs', './copied_folder')


def test_validation_plugin_delete_file_exception(validation_plugin, utils):
    utils.clear_log()
    with patch('shutil.rmtree') as mock_rmtree:
        mock_rmtree.side_effect = IOError("mock shutil.rmtree")
        assert not validation_plugin.delete_file('./copied_folder')
        assert utils.has_log_level("ERROR")


def test_validation_plugin_delete_file(validation_plugin):
    assert validation_plugin.delete_file('./copied_file.py')
    assert not validation_plugin.delete_file('./copied_file.py')
    assert validation_plugin.delete_file('./copied_folder')


def test_validation_plugin_sub2microsecs(validation_plugin):
    assert validation_plugin.convert_timestamp(0xffffdf01) == '99999'
    assert validation_plugin.convert_timestamp(2147487943) == '50000'


def test_validation_plugin_save_file_as_text_fail(validation_plugin, utils):
    utils.clear_log()
    assert not validation_plugin.save_file_as_text('file_not_exist.bin', 'file_not_exist.txt', 'EVS')
    assert not validation_plugin.save_file_as_text('./ctf', 'file_not_exist.txt', 'EVS')
    assert utils.has_log_level("ERROR")


def test_validation_plugin_search_txt_file(validation_plugin, utils):
    assert validation_plugin.search_txt_file('./ctf', 'NASA Open Source Agreement')
    utils.clear_log()
    assert not validation_plugin.search_txt_file('file_not_exist.txt', 'NASA Open Source Agreement')
    assert not validation_plugin.search_txt_file('./ctf', 'NO Open Source Agreement')
    assert utils.has_log_level("ERROR")


def test_validation_plugin_search_no_txt_file(validation_plugin, utils):
    assert not validation_plugin.search_no_txt_file('./ctf', 'NASA Open Source Agreement', True)
    utils.clear_log()
    assert not validation_plugin.search_no_txt_file('file_not_exist.txtxxx', 'NASA Open Source Agreement')
    '''
    assert not validation_plugin.search_txt_file('./ctf', 'NO Open Source Agreement')
    assert utils.has_log_level("ERROR")
'''

def test_validation_plugin_save_file_as_text_unknown_type(validation_plugin, utils):
    utils.clear_log()
    assert not validation_plugin.save_file_as_text('./ctf', 'evs.txt', 'EVS')
    assert utils.has_log_level("ERROR")


def test_validation_plugin_save_file_as_text(validation_plugin):
    Global.plugins_available['CFS Plugin'].targets[''] = Mock()
    Global.plugins_available['CFS Plugin'].targets[''].macro_map = {}
    Global.plugins_available['CFS Plugin'].targets[''].config.endianess_of_target = 'little'
    assert validation_plugin.save_file_as_text('plugins/validation_plugin/tests/evs.bin', 'evs.txt', 'EVS', '')


def test_validation_plugin_interpret_event_log(validation_plugin):
    Global.plugins_available['CFS Plugin'].targets.pop('')
    Global.plugins_available['CFS Plugin'].targets['cfs'] = Mock()
    Global.plugins_available['CFS Plugin'].targets['cfs'].macro_map = {}
    Global.plugins_available['CFS Plugin'].targets['cfs'].config.endianess_of_target = 'little'
    assert validation_plugin.interpret_event_log('plugins/validation_plugin/tests/evs.bin', 'evs.txt', '')


def test_validation_plugin_interpret_event_log_no_macro_map(validation_plugin):
    Global.plugins_available['CFS Plugin'].targets.pop('cfs')
    assert validation_plugin.interpret_event_log('plugins/validation_plugin/tests/evs.bin', 'evs.txt', '')


def test_validation_plugin_interpret_binary_data(validation_plugin):
    event_data = b"cFE1\x00\x00\x00\x10\x00\x00\x00@\x00\x00\x00B\x00\x00\x00\x01\x00\x11\x00\x01\x00\x0fF/\t'\xe3tcFE" \
                 b" EVS Log File\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00H\x12\xc0\x00\x00" \
                 b"\xa9\x00\x05\x04\x06\x00\x00\x00\x00\0x00\0x00r\x86\x00\x00CFE_EVS\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
                 b"\x00\x00\x00\x01\x00\x07\x00B\x00\x00\x00\x01\x00\x00" \
                 b"\x00cFE EVS Initialized:  cFE DEVELOPMENT BUILD v6.8.0-rc1+dev1024 (Codename: Bootes), " \
                 b"Last Official Release: cfe v6.7.0\x00\x00\x00\x00\x00\x00\x00\x00H\x12\xc0\x00\x00\xa9\x00\x05\x04"
    validation_plugin.macro_map = {}
    assert validation_plugin.interpret_binary_data(event_data, 1, 0, 'little', 20)


def test_validation_plugin_interpret_event_log_fail(validation_plugin, utils):
    utils.clear_log()
    assert not validation_plugin.interpret_event_log('file_not_exist.txt', 'evs.txt', 'EVS')
    assert utils.has_log_level("ERROR")


def test_validation_plugin_insert_comment(validation_plugin):
    assert validation_plugin.insert_comment("Demo InsertUserComment instruction")