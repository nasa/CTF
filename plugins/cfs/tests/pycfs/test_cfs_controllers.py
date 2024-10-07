# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2024 United States Government as represented by the
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
import os
import shutil
from unittest.mock import Mock, patch, mock_open, call
import tempfile

import pytest

from lib.ctf_global import Global, CtfVerificationStage
from lib.exceptions import CtfTestError, CtfParameterError
from plugins.cfs.cfs_config import CfsConfig, RemoteCfsConfig
from plugins.cfs.pycfs.cfs_controllers import CfsController, RemoteCfsController, merge_ccsds_dictionaries


@pytest.fixture(scope="session", autouse=True)
def init_global():
    Global.load_config("./configs/default_config.ini")
    Global.set_time_manager(Mock())


# TODO patch start and build without breaking anything else

@pytest.fixture(name="cfs_controller")
def _cfs_controller_instance():
    config = CfsConfig("cfs")
    # give the interface something harmless to do
    config.cfs_build_cmd = 'echo "building"'
    config.cfs_run_cmd = 'tail -f /dev/null'
    return CfsController(config)


@pytest.fixture(name="cfs_controller_inited")
def _cfs_controller_instance_inited():
    config = CfsConfig("cfs")
    # give the interface something harmless to do
    config.cfs_build_cmd = 'echo "building"'
    config.cfs_run_cmd = 'tail -f /dev/null'
    controller = CfsController(config)
    controller.initialize()
    controller.cfs.started_by_ctf = True
    controller.cfs_pid = 42
    return controller


@pytest.fixture(name="remote_controller")
def _remote_controller_instance():
    config = RemoteCfsConfig("local_ssh")
    config.build_cfs = True
    return RemoteCfsController(config)


@pytest.fixture(name="remote_controller_inited")
def _remote_controller_instance_inited():
    config = RemoteCfsConfig("local_ssh")
    controller = RemoteCfsController(config)
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        controller.initialize()
        controller.cfs_pid = 42
    return controller


def test_cfs_controller_init(cfs_controller):
    """
    Test CfsController class constructor
    """
    assert cfs_controller.cfs is None
    assert cfs_controller.ccsds_reader is None
    assert cfs_controller.mid_map is None
    assert cfs_controller.macro_map is None
    assert cfs_controller.first_call_flag
    assert cfs_controller.mid_pkt_count is None


def test_cfs_controller_process_ccsds_files(cfs_controller):
    """
    Test CfsController class process_ccsds_files method
    """
    assert cfs_controller.mid_map is None
    assert cfs_controller.process_ccsds_files()
    assert cfs_controller.mid_map
    assert cfs_controller.ccsds

    # After calling process_ccsds_files, mid_map is not None, call process_ccsds_files again will output debug log.
    assert cfs_controller.mid_map
    assert cfs_controller.process_ccsds_files()


def test_cfs_controller_process_ccsds_files_merge_error_mid(cfs_controller, workspace):
    """
    Test CfsController class process_ccsds_files method. Merging dictionary fails due to a
    duplicate MID definition with non-matching values
    """
    if workspace['type'] == 'open_source':
        return

    # Create a temporary directory to contain the test files
    with tempfile.TemporaryDirectory() as tmpDir:

        # Create a test SEDS XML file in the temporary directory defining a constant
        with tempfile.NamedTemporaryFile(mode='w', dir=tmpDir, suffix='.xml', encoding='utf-8', delete=False) as tmp:
            tmp.write('<seds:PackageFile xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns="http://www.ccsds.org/schema/sois/seds">\n')
            tmp.write('  <Package name="name">\n')
            tmp.write('    <DataTypeSet>\n')
            tmp.write('      <IntegerDataType name="CommonContainers_Uint32_Type" AliasType="uint32">\n')
            tmp.write('        <IntegerDataEncoding byteOrder="bigEndian" encoding="unsigned" sizeInBits="32" />\n')
            tmp.write('        <Range>\n')
            tmp.write('          <MinMaxRange max="4294967295" min="0" rangeType="inclusiveMinInclusiveMax" />\n')
            tmp.write('        </Range>\n')
            tmp.write('      </IntegerDataType>\n')
            tmp.write('      <ContainerDataType abstract="false" name="CFE_ES_NoArgsCmd_Struct_Type" AliasType="CFE_ES_NoArgsCmd_t">\n')
            tmp.write('        <EntryList>\n')
            tmp.write('          <Entry name="CRCValue" type="CommonContainers_Uint32_Type" />\n')
            tmp.write('        </EntryList>\n')
            tmp.write('      </ContainerDataType>\n')
            tmp.write('    </DataTypeSet>\n')
            tmp.write('    <DeclaredInterfaceSet>\n')
            tmp.write('      <Interface level="application" name="CMD_ES_Interface">\n')
            tmp.write('        <CommandSet>\n')
            tmp.write('          <Command commandCode="0" msgid="2081" AliasMID="CFE_ES_CMD_MID" name="CMD_CFEES_NoOpCmd" AliasCC="CFE_ES_NOOP_CC">\n')
            tmp.write('            <Argument defaultValue="" name="BufPtr" type="CFE_ES_NoArgsCmd_Struct_Type" />\n')
            tmp.write('          </Command>\n')
            tmp.write('        </CommandSet>\n')
            tmp.write('      </Interface>\n')
            tmp.write('    </DeclaredInterfaceSet>\n')
            tmp.write('  </Package>\n')
            tmp.write('</seds:PackageFile>')
            tmp.close()

            # Create a test JSON file in the temporary directory defining the same constant as in the
            # XML file, but with a different value
            with tempfile.NamedTemporaryFile(mode='w', dir=tmpDir, suffix='_CMD.json', encoding='utf-8', delete=False) as tmp2:
                tmp2.write('{\n')
                tmp2.write('  "cmd_mid_name": "CFE_ES_CMD_MID",\n')
                tmp2.write('  "cmd_description": "",\n')
                tmp2.write('  "cmd_codes": [\n')
                tmp2.write('    {\n')
                tmp2.write('      "cc_name": "CFE_ES_NOOP_CC",\n')
                tmp2.write('      "cc_value": "0",\n')
                tmp2.write('      "cc_description": "",\n')
                tmp2.write('      "cc_data_type": "CFE_ES_NoArgsCmd_t",\n')
                tmp2.write('      "cc_parameters": [\n')
                tmp2.write('        {\n')
                tmp2.write('          "name": "CRCValue",\n')
                tmp2.write('          "description": "",\n')
                tmp2.write('          "array_size": "0",\n')
                tmp2.write('          "data_type": "uint32",\n')
                tmp2.write('          "bit_length": "0",\n')
                tmp2.write('          "parameters": []\n')
                tmp2.write('        }\n')
                tmp2.write('      ]\n')
                tmp2.write('    }\n')
                tmp2.write('  ]\n')
                tmp2.write('}')
                tmp2.close()

                # Create a test JSON file in the temporary directory defining the same constant as in the
                # XML file, but with a different value
                with tempfile.NamedTemporaryFile(mode='w', dir=tmpDir, suffix='_MIDS.json', encoding='utf-8', delete=False) as tmp3:
                    tmp3.write('[\n')
                    tmp3.write('  {\n')
                    tmp3.write('    "target": "set1",\n')
                    tmp3.write('    "mids": [\n')
                    tmp3.write('      {\n')
                    tmp3.write('        "mid_name": "CFE_ES_CMD_MID",\n')
                    tmp3.write('        "mid_value": "0xC850401"\n')
                    tmp3.write('      }\n')
                    tmp3.write('    ]\n')
                    tmp3.write('  }\n')
                    tmp3.write(']')
                    tmp3.close()

                    cfs_controller.config.ccsds_data_dir = tmpDir
                    assert not cfs_controller.process_ccsds_files()

        os.remove(tmp.name)
        os.remove(tmp2.name)
        os.remove(tmp3.name)


def test_cfs_controller_process_ccsds_files_merge_error_macro(cfs_controller, workspace):
    """
    Test CfsController class process_ccsds_files method. Merging dictionary fails due to a
    duplicate macro definition with non-matching values
    """
    if workspace['type'] == 'open_source':
        return

    # Create a temporary directory to contain the test files
    with tempfile.TemporaryDirectory() as tmpDir:

        # Create a test SEDS XML file in the temporary directory defining a macro
        with tempfile.NamedTemporaryFile(mode='w', dir=tmpDir, suffix='.xml', encoding='utf-8', delete=False) as tmp:
            tmp.write('<seds:PackageFile xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns="http://www.ccsds.org/schema/sois/seds">\n')
            tmp.write('  <Metadata>\n')
            tmp.write('     <Category name="ConfigurationValues">>\n')
            tmp.write('        <Category name="MissionConfigurations">\n')
            tmp.write('           <MetadataValueSet>\n')
            tmp.write('              <IntegerValue name="new_constant" value="1234"/>\n')
            tmp.write('           </MetadataValueSet>\n')
            tmp.write('        </Category>\n')
            tmp.write('     </Category>\n')
            tmp.write('  </Metadata>\n')
            tmp.write('  <Package name="name">\n')
            tmp.write('    <DataTypeSet>\n')
            tmp.write('    </DataTypeSet>\n')
            tmp.write('    <DeclaredInterfaceSet>\n')
            tmp.write('    </DeclaredInterfaceSet>\n')
            tmp.write('  </Package>\n')
            tmp.write('</seds:PackageFile>')
            tmp.close()

            # Create a test JSON file in the temporary directory defining the same macro as in the XML
            # file, but with a different value
            with tempfile.NamedTemporaryFile(mode='w', dir=tmpDir, suffix='.json', encoding='utf-8', delete=False) as tmp2:
                tmp2.write('[\n')
                tmp2.write('  {\n')
                tmp2.write('    "constant_name": "new_constant",\n')
                tmp2.write('    "constant_value": "5678"\n')
                tmp2.write('  }\n')
                tmp2.write(']')
                tmp2.close()

                cfs_controller.config.ccsds_data_dir = tmpDir
                assert not cfs_controller.process_ccsds_files()

        os.remove(tmp.name)
        os.remove(tmp2.name)


def test_cfs_controller_process_ccsds_files_merge_error_type(cfs_controller, workspace):
    """
    Test CfsController class process_ccsds_files method. Merging dictionary fails due to a
    duplicate type definition with non-matching values
    """
    if workspace['type'] == 'open_source':
        return

    # Create a temporary directory to contain the test files
    with tempfile.TemporaryDirectory() as tmpDir:

        # Create a test SEDS XML file in the temporary directory defining a constant
        with tempfile.NamedTemporaryFile(mode='w', dir=tmpDir, suffix='.xml', encoding='utf-8', delete=False) as tmp:
            tmp.write('<seds:PackageFile xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns="http://www.ccsds.org/schema/sois/seds">\n')
            tmp.write('  <Package name="name">\n')
            tmp.write('    <DataTypeSet>\n')
            tmp.write('      <IntegerDataType name="CommonContainers_Uint32_Type" AliasType="uint32">\n')
            tmp.write('        <IntegerDataEncoding byteOrder="bigEndian" encoding="unsigned" sizeInBits="32" />\n')
            tmp.write('        <Range>\n')
            tmp.write('          <MinMaxRange max="4294967295" min="0" rangeType="inclusiveMinInclusiveMax" />\n')
            tmp.write('        </Range>\n')
            tmp.write('      </IntegerDataType>\n')
            tmp.write('      <ContainerDataType abstract="false" name="CFE_ES_NoArgsCmd_Struct_Type" AliasType="CFE_ES_NoArgsCmd_t">\n')
            tmp.write('        <EntryList>\n')
            tmp.write('          <Entry name="CRCValue" type="CommonContainers_Uint32_Type" />\n')
            tmp.write('        </EntryList>\n')
            tmp.write('      </ContainerDataType>\n')
            tmp.write('    </DataTypeSet>\n')
            tmp.write('    <DeclaredInterfaceSet>\n')
            tmp.write('      <Interface level="application" name="CMD_ES_Interface">\n')
            tmp.write('        <CommandSet>\n')
            tmp.write('          <Command commandCode="0" msgid="2081" AliasMID="CFE_ES_CMD_MID" name="CMD_CFEES_NoOpCmd" AliasCC="CFE_ES_NOOP_CC">\n')
            tmp.write('            <Argument defaultValue="" name="BufPtr" type="CFE_ES_NoArgsCmd_Struct_Type" />\n')
            tmp.write('          </Command>\n')
            tmp.write('        </CommandSet>\n')
            tmp.write('      </Interface>\n')
            tmp.write('    </DeclaredInterfaceSet>\n')
            tmp.write('  </Package>\n')
            tmp.write('</seds:PackageFile>')
            tmp.close()

            # Create a test JSON file in the temporary directory defining the same constant as in the
            # XML file, but with a different value
            with tempfile.NamedTemporaryFile(mode='w', dir=tmpDir, suffix='_CMD.json', encoding='utf-8', delete=False) as tmp2:
                tmp2.write('{\n')
                tmp2.write('  "cmd_mid_name": "CFE_ES_CMD_MID",\n')
                tmp2.write('  "cmd_description": "",\n')
                tmp2.write('  "cmd_codes": [\n')
                tmp2.write('    {\n')
                tmp2.write('      "cc_name": "DIFFERENT_CC",\n')
                tmp2.write('      "cc_value": "0",\n')
                tmp2.write('      "cc_description": "",\n')
                tmp2.write('      "cc_data_type": "CFE_ES_NoArgsCmd_t",\n')
                tmp2.write('      "cc_parameters": [\n')
                tmp2.write('        {\n')
                tmp2.write('          "name": "CRCValue",\n')
                tmp2.write('          "description": "",\n')
                tmp2.write('          "array_size": "0",\n')
                tmp2.write('          "data_type": "uint32",\n')
                tmp2.write('          "bit_length": "0",\n')
                tmp2.write('          "parameters": []\n')
                tmp2.write('        }\n')
                tmp2.write('      ]\n')
                tmp2.write('    }\n')
                tmp2.write('  ]\n')
                tmp2.write('}')
                tmp2.close()

                # Create a test JSON file in the temporary directory defining the same constant as in the
                # XML file, but with a different value
                with tempfile.NamedTemporaryFile(mode='w', dir=tmpDir, suffix='_MIDS.json', encoding='utf-8', delete=False) as tmp3:
                    tmp3.write('[\n')
                    tmp3.write('  {\n')
                    tmp3.write('    "target": "set1",\n')
                    tmp3.write('    "mids": [\n')
                    tmp3.write('      {\n')
                    tmp3.write('        "mid_name": "CFE_ES_CMD_MID",\n')
                    tmp3.write('        "mid_value": "0x2081"\n')
                    tmp3.write('      }\n')
                    tmp3.write('    ]\n')
                    tmp3.write('  }\n')
                    tmp3.write(']')
                    tmp3.close()

                    cfs_controller.config.ccsds_data_dir = tmpDir
                    assert not cfs_controller.process_ccsds_files()

        os.remove(tmp.name)
        os.remove(tmp2.name)
        os.remove(tmp3.name)


def test_cfs_controller_merge_ccsds_dictionaries(cfs_controller):
    """
    Test CfsController class merge_ccsds_dictionaries method
    """
    # Merge two dictionaries: second is empty
    pri_dict = {'a':1, 'b':2, 'd':4}
    sec_dict = {}
    assert not merge_ccsds_dictionaries('test_dict', pri_dict, sec_dict)
    assert pri_dict == {'a':1, 'b':2, 'd':4}

    # Merge two dictionaries: first is empty
    sec_dict = {}
    pri_dict = {'a':1, 'b':2, 'd':4}
    assert not merge_ccsds_dictionaries('test_dict', pri_dict, sec_dict)
    assert pri_dict == {'a':1, 'b':2, 'd':4}

    # Merge two dictionaries: no duplicate keys
    pri_dict = {'a':1, 'b':2, 'd':4}
    sec_dict = {'c':3}
    assert not merge_ccsds_dictionaries('test_dict', pri_dict, sec_dict)
    assert pri_dict == {'a':1, 'b':2, 'c':3, 'd':4}

    # Merge two dictionaries: duplicate keys
    pri_dict = {'a':1, 'b':2, 'd':4}
    sec_dict = {'a':1, 'c':3, 'd':4}
    assert not merge_ccsds_dictionaries('test_dict', pri_dict, sec_dict)
    assert pri_dict == {'a':1, 'b':2, 'c':3, 'd':4}

    # Merge two dictionaries: duplicate keys with different values
    pri_dict = {'a':1, 'b':2, 'd':4}
    sec_dict = {'a':1, 'b':3, 'd':4}
    assert merge_ccsds_dictionaries('test_dict', pri_dict, sec_dict)


def test_cfs_controller_initialize_pass(cfs_controller):
    """
    Test CfsController class initialize method
    Initialize CfsController instance, including the followings: create mid map; import ccsds header;
    create command interface; create telemetry interface; create local CFS interface
    """
    assert cfs_controller.cfs is None
    with patch('builtins.open', mock_open()):
        assert cfs_controller.initialize()
    assert cfs_controller.cfs is not None
    assert cfs_controller.mid_map is not None
    assert cfs_controller.macro_map is not None
    assert cfs_controller.ccsds is not None
    assert cfs_controller.ccsds.CcsdsPrimaryHeader is not None
    assert cfs_controller.ccsds.CcsdsCommand is not None
    assert cfs_controller.ccsds.CcsdsTelemetry is not None
    assert cfs_controller.cfs.command.command_socket.getsockname() == ('0.0.0.0', 5011)


def test_cfs_controller_initialize_fail(cfs_controller, utils):
    """
    Test CfsController class initialize method
    Initialize CfsController instance, including the followings: create mid map; import ccsds header;
    create command interface; create telemetry interface; create local CFS interface
    """
    # cfs init fails
    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface') as mock_localcfsinterface:
        mock_localcfsinterface.return_value.init_passed = False
        utils.clear_log()
        assert not cfs_controller.initialize()
        assert utils.has_log_level("ERROR")


def test_cfs_controller_initialize_exception(cfs_controller, utils):
    """
    Test CfsController class initialize method: raise exception
    Initialize CfsController instance, including the followings: create mid map; import ccsds header;
    create command interface; create telemetry interface; create local CFS interface
    """
    with patch('plugins.cfs.pycfs.cfs_controllers.import_ccsds_header_types') as mock_import:
        mock_import.side_effect = CtfTestError("Raise Exception for import_ccsds_header_types")
        utils.clear_log()
        assert not cfs_controller.initialize()
        mock_import.assert_called_once()
        assert utils.has_log_level("ERROR")

    with patch("plugins.cfs.pycfs.local_cfs_interface.LocalCfsInterface.start_cfs") as mock_start_cfs:
        mock_start_cfs.side_effect = CtfTestError('Mock start_cfs')
        cfs_controller.initialize()
        assert utils.has_log_level("ERROR")


def test_cfs_controller_build_cfs(cfs_controller):
    """
    Test CfsController class build_cfs method:
    Implementation of CFS plugin instructions build_cfs. When CFS plugin instructions (build_cfs) is executed,
    it calls CfsController instance's build_cfs function.
    """
    with patch('plugins.cfs.pycfs.local_cfs_interface.LocalCfsInterface.build_cfs', return_value=True) as mock_build:
        assert cfs_controller.initialize()
        assert cfs_controller.build_cfs()
        mock_build.assert_called()


def test_cfs_controller_start_cfs_exception(cfs_controller_inited, utils):
    """
    Test CfsController class start_cfs method: raise exception
    Implementation of CFS plugin instructions start_cfs. When CFS plugin instructions (start_cfs) is executed,
    it calls CfsController instance's start_cfs function.
    """
    with patch("plugins.cfs.pycfs.local_cfs_interface.LocalCfsInterface.start_cfs") as mock_start_cfs:
        mock_start_cfs.side_effect = CtfTestError('Mock start_cfs')
        utils.clear_log()
        cfs_controller_inited.start_cfs('')
        assert utils.has_log_level("ERROR")


def test_cfs_controller_start_cfs(cfs_controller_inited):
    """
    Test CfsController class start_cfs method:
    Implementation of CFS plugin instructions start_cfs. When CFS plugin instructions (start_cfs) is executed,
    it calls CfsController instance's start_cfs function.
    """
    with patch("plugins.cfs.pycfs.local_cfs_interface.LocalCfsInterface.start_cfs") as mock_start_cfs, \
            patch('plugins.cfs.pycfs.local_cfs_interface.LocalCfsInterface.enable_output'):
        mock_start_cfs.return_value = {'result': True, 'pid':-1}
        cfs_controller_inited.start_cfs('')
        assert cfs_controller_inited.cfs_pid == -1


def test_cfs_controller_start_cfs_restart(cfs_controller_inited):
    """
    Test CfsController class start_cfs method: create a new CFS interface
    Implementation of CFS plugin instructions start_cfs. When CFS plugin instructions (start_cfs) is executed,
    it calls CfsController instance's start_cfs function.
    """
    with patch("plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface") as mock_cfs:
        mock_cfs.return_value.init_passed = True
        mock_cfs.return_value.start_cfs.return_value = {'result': True, 'pid':-1}
        cfs_controller_inited.shutdown_cfs()
        assert cfs_controller_inited.cfs is None
        assert cfs_controller_inited.start_cfs('') is True
        assert cfs_controller_inited.cfs


def test_cfs_controller_start_cfs_restart_error(cfs_controller_inited):
    """
    Test CfsController class start_cfs method: fail to create a new CFS interface
    Implementation of CFS plugin instructions start_cfs. When CFS plugin instructions (start_cfs) is executed,
    it calls CfsController instance's start_cfs function.
    """
    with patch("plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface") as mock_cfs:
        mock_cfs.return_value.init_passed = False
        cfs_controller_inited.shutdown_cfs()
        assert cfs_controller_inited.cfs is None
        assert cfs_controller_inited.start_cfs('') is False
        assert cfs_controller_inited.cfs
        cfs_controller_inited.cfs.start_cfs.assert_not_called()


def test_cfs_controller_enable_cfs_output(cfs_controller):
    """
    Test CfsController class enable_cfs_output method:
    Implementation of CFS plugin instructions enable_cfs_output.  When CFS plugin instructions
    (enable_cfs_output) is executed, it calls CfsController instance's enable_cfs_output function.
    """
    with patch('plugins.cfs.pycfs.local_cfs_interface.LocalCfsInterface.enable_output'), \
            patch('plugins.cfs.pycfs.local_cfs_interface.LocalCfsInterface.build_cfs', return_value=True) as mock_build:
        assert cfs_controller.initialize()
        cfs_controller.enable_cfs_output()
        cfs_controller.cfs.enable_output.assert_called_once()
        mock_build.assert_called()


def test_cfs_controller_send_cfs_command(cfs_controller, workspace):
    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface'):
        cfs_controller.initialize()
        bytes_TO = b'127.0.0.1\x00\x00\x00\x00\x00\x00\x00\x93\x13\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        bytes_ES = b'hostname\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                   b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                   b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                   b'\x00\x00\x00\x00/cf/test_output.txt\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                   b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                   b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

        TO_CMD_MID = workspace['TO_CMD_MID']
        CFE_ES_CMD_MID = workspace['CFE_ES_CMD_MID']

        # simple case
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('TO_CMD_MID',
                                               'TO_ENABLE_OUTPUT_CC',
                                               {'cDestIp': '127.0.0.1', 'usDestPort': 5011})
        cfs_controller.cfs.send_command.assert_called_once_with(TO_CMD_MID, 2, bytes_TO, None)

        # nested payload
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('CFE_ES_CMD_MID',
                                               'CFE_ES_SHELL_CC',
                                               {"Payload": {
                                                   "CmdString": "hostname", "OutputFilename": "/cf/test_output.txt"
                                               }})
        cfs_controller.cfs.send_command.assert_called_once_with(CFE_ES_CMD_MID, 3, bytes_ES, None)

        # ctype args
        assert cfs_controller.send_cfs_command(TO_CMD_MID,
                                               'TO_ENABLE_OUTPUT_CC',
                                               cfs_controller.mid_map
                                               ['TO_CMD_MID']['CC']['TO_ENABLE_OUTPUT_CC']['ARG_CLASS'](),
                                               ctype_args=True)
        cfs_controller.cfs.send_command.assert_called_with(TO_CMD_MID, 2, bytearray(28), None)

        # specify length shorter
        assert cfs_controller.send_cfs_command('TO_CMD_MID',
                                               'TO_ENABLE_OUTPUT_CC',
                                               {'cDestIp': '127.0.0.1', 'usDestPort': 5011},
                                               payload_length=8)
        cfs_controller.cfs.send_command.assert_called_with(TO_CMD_MID, 2, bytes_TO[0:8], None)

        # specify length longer
        assert cfs_controller.send_cfs_command('TO_CMD_MID', 'TO_NOOP_CC', {}, payload_length=6)
        cfs_controller.cfs.send_command.assert_called_with(TO_CMD_MID, 0, bytearray(6), None)

        # no args provided
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command(TO_CMD_MID, 'TO_ENABLE_OUTPUT_CC', [])
        cfs_controller.cfs.send_command.assert_called_once_with(TO_CMD_MID, 2, bytearray(28), None)

        # noop with empty args
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('TO_CMD_MID', 0, {})
        cfs_controller.cfs.send_command.assert_called_once_with(TO_CMD_MID, 0, bytearray(4), None)

        # int mid and cc
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command(TO_CMD_MID, 2, {'cDestIp': '127.0.0.1', 'usDestPort': 5011})
        cfs_controller.cfs.send_command.assert_called_once_with(TO_CMD_MID, 2, bytes_TO, None)

        # stringified mid and cc
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command(TO_CMD_MID, '2', {'cDestIp': '127.0.0.1', 'usDestPort': 5011})

        cfs_controller.cfs.send_command.assert_called_once_with(TO_CMD_MID, 2, bytes_TO, None)

        # noop with non-dictionary header args
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('TO_CMD_MID', 0, {}, [])
        cfs_controller.cfs.send_command.assert_called_once_with(TO_CMD_MID, 0, bytearray(4), [])

        # noop with empty header args dictionary
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('TO_CMD_MID', 0, {}, {})
        cfs_controller.cfs.send_command.assert_called_once_with(TO_CMD_MID, 0, bytearray(4), {})

        # noop with header args dictionary; non-numeric value
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('TO_CMD_MID', 0, {}, {'key': 'value'})
        cfs_controller.cfs.send_command.assert_called_once_with(TO_CMD_MID, 0, bytearray(4), {'key': 'value'})

        # noop with header args dictionary; numeric value
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('TO_CMD_MID', 0, {}, {'key': '123'})
        cfs_controller.cfs.send_command.assert_called_once_with(TO_CMD_MID, 0, bytearray(4), {'key': 123})


def test_cfs_controller_send_cfs_command_args_indexed_struct(cfs_controller, workspace):
    DUMMY_IO_CMD_MID = workspace['DUMMY_IO_CMD_MID']

    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface'):
        cfs_controller.initialize()

        # myData populated
        bytes_io = b'*\x00\x00\x04m\xda\x03\x00\xea\x16\xb0L\x02\x00\x00\x00' \
                   b'D\x17AT\xfb!\t@\x00\x00`@a\x01\x00\x00\x00\x00\x00\x00' \
                   b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('DUMMY_IO_CMD_MID',
                                               'DUMMY_IO_SEND_MULTI_TYPES_CC',
                                               {
                                                   "args[0]": {
                                                       "myByte": 42,
                                                       "myShort": 1024,
                                                       "myInt": 252525,
                                                       "myLong": 9876543210,
                                                       "myFloat": 3.50,
                                                       "myDouble": 3.1415926535,
                                                       "myChar": "a",
                                                       "myBool": 1
                                                   }})
        cfs_controller.cfs.send_command.assert_called_once_with(DUMMY_IO_CMD_MID, 2, bytes_io, None)

        # myArray populated
        bytes_io = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                   b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x00' \
                   b'\x00\x00\x00\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('DUMMY_IO_CMD_MID',
                                               'DUMMY_IO_SEND_MULTI_TYPES_CC',
                                               {
                                                   "args[0]": {
                                                       "myArray[0]": 0,
                                                       "myArray[1]": 1,
                                                       "myArray[7]": 7,
                                                       "myArray[2]": 2
                                                   }})
        cfs_controller.cfs.send_command.assert_called_once_with(DUMMY_IO_CMD_MID, 2, bytes_io, None)

        # myArray default value
        bytes_io = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                   b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02' \
                   b'\x02\x02\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('DUMMY_IO_CMD_MID',
                                               'DUMMY_IO_SEND_MULTI_TYPES_CC',
                                               {
                                                   "args[0]": {
                                                       "myArray": 2
                                                   }})
        cfs_controller.cfs.send_command.assert_called_once_with(DUMMY_IO_CMD_MID, 2, bytes_io, None)

        # no args provided
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('DUMMY_IO_CMD_MID', 'DUMMY_IO_SEND_MULTI_TYPES_CC', [])
        cfs_controller.cfs.send_command.assert_called_once_with(DUMMY_IO_CMD_MID, 2, bytearray(60), None)


def test_cfs_controller_send_cfs_command_args_nested_chars(cfs_controller, workspace):
    DUMMY_IO_CMD_MID = workspace['DUMMY_IO_CMD_MID']

    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface'):
        cfs_controller.initialize()

        # myString nominal case
        bytes_io = bytes(40) + b'a string\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('DUMMY_IO_CMD_MID',
                                               'DUMMY_IO_SEND_MULTI_TYPES_CC',
                                               {
                                                   "args[0]": {
                                                       "myString": "a string"
                                                   }})
        cfs_controller.cfs.send_command.assert_called_once_with(DUMMY_IO_CMD_MID, 2, bytes_io, None)

        # myString with special characters
        bytes_io = bytes(40) + b'../../\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('DUMMY_IO_CMD_MID',
                                               'DUMMY_IO_SEND_MULTI_TYPES_CC',
                                               {
                                                   "args[0]": {
                                                       "myString": "../../"
                                                   }})
        cfs_controller.cfs.send_command.assert_called_once_with(DUMMY_IO_CMD_MID, 2, bytes_io, None)

        # myString with a number
        bytes_io = bytes(40) + b'12345\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('DUMMY_IO_CMD_MID',
                                               'DUMMY_IO_SEND_MULTI_TYPES_CC',
                                               {
                                                   "args[0]": {
                                                       "myString": "12345"
                                                   }})
        cfs_controller.cfs.send_command.assert_called_once_with(DUMMY_IO_CMD_MID, 2, bytes_io, None)


def test_cfs_controller_send_cfs_command_args_bitfield(cfs_controller, workspace):
    # define SET1_CFS_GRP1_DUMMY_IO_CMD_MID                 0x2A8E
    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface'):
        cfs_controller.initialize()

        # bitfields populated
        bytes_io = bytes(46) + b'\x00\x00\x11\x00\x00\x00\x21\x80\x00\x00\x00\x00\x00\x00'
        cfs_controller.cfs.send_command.reset_mock()
        assert cfs_controller.send_cfs_command('DUMMY_IO_CMD_MID',
                                               'DUMMY_IO_SEND_MULTI_TYPES_CC',
                                               {
                                                   "args[0]": {
                                                       "myBitfield8a": 1,
                                                       "myBitfield8b": 1,
                                                       "myBitfield16a": 1,
                                                       "myBitfield16b": 1,
                                                       "myBitfield16c": 1
                                                   }})
        DUMMY_IO_CMD_MID = workspace['DUMMY_IO_CMD_MID']
        cfs_controller.cfs.send_command.assert_called_once_with(DUMMY_IO_CMD_MID, 2, bytes_io, None)


def test_cfs_controller_send_cfs_command_errors(cfs_controller, workspace):
    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface'):
        cfs_controller.initialize()

        # invalid mid
        cfs_controller.cfs.send_command.reset_mock()
        assert not cfs_controller.send_cfs_command(0, 'TO_ENABLE_OUTPUT_CC', {})
        cfs_controller.cfs.send_command.assert_not_called()

        # send error
        cfs_controller.cfs.send_command.return_value = False
        assert not cfs_controller.send_cfs_command('TO_CMD_MID',
                                                   'TO_ENABLE_OUTPUT_CC',
                                                   {'cDestIp': '127.0.0.1', 'usDestPort': 5011})

        # invalid cc
        cfs_controller.cfs.send_command.reset_mock()
        assert not cfs_controller.send_cfs_command('TO_CMD_MID', 'INVALID_CC', {})
        cfs_controller.cfs.send_command.assert_not_called()

        # invalid args
        cfs_controller.cfs.send_command.reset_mock()

        TO_CMD_MID = workspace['TO_CMD_MID']

        with pytest.raises(CtfTestError):
            cfs_controller.send_cfs_command(TO_CMD_MID,
                                            'TO_ENABLE_OUTPUT_CC',
                                            {'DestIp': '127.0.0.1', 'DestPort': 5011})
        cfs_controller.cfs.send_command.assert_not_called()

        # primitive arg (invalid)
        cfs_controller.cfs.send_command.reset_mock()
        with pytest.raises(CtfTestError):
            cfs_controller.send_cfs_command('TO_CMD_MID', 'TO_ENABLE_OUTPUT_CC', "")
        cfs_controller.cfs.send_command.assert_not_called()


def test_send_cfs_raw_command(cfs_controller, workspace):
    TO_CMD_MID = workspace['TO_CMD_MID']

    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface'):
        cfs_controller.initialize()

        # base case
        assert cfs_controller.send_raw_cfs_command(
            "TO_CMD_MID",
            "TO_ENABLE_OUTPUT_CC",
            "3132372e302e302e31000000000000009313000000000000",
            {})
        cfs_controller.cfs.send_command.assert_called_once_with(
            TO_CMD_MID,
            2,
            b'127.0.0.1\x00\x00\x00\x00\x00\x00\x00\x93\x13\x00\x00\x00\x00\x00\x00',
            {})

        # int mid
        assert cfs_controller.send_raw_cfs_command(TO_CMD_MID, "TO_ENABLE_OUTPUT_CC", "ABCDEF", {}, 1)
        cfs_controller.cfs.send_command.assert_called_with(TO_CMD_MID, 2, b'\xab', {})

        # int cc
        assert cfs_controller.send_raw_cfs_command("TO_CMD_MID", 2, "ABCDEF")
        cfs_controller.cfs.send_command.assert_called_with(TO_CMD_MID, 2, b'\xab\xcd\xef', None)

        # both int
        assert cfs_controller.send_raw_cfs_command(TO_CMD_MID, 2, "ABCDEF")
        cfs_controller.cfs.send_command.assert_called_with(TO_CMD_MID, 2, b'\xab\xcd\xef', None)

        # empty payload
        assert cfs_controller.send_raw_cfs_command(TO_CMD_MID, 12, "")
        cfs_controller.cfs.send_command.assert_called_with(TO_CMD_MID, 12, b'', None)

        # leading 0x
        assert cfs_controller.send_raw_cfs_command(TO_CMD_MID, 2, "0xABCDEF")
        cfs_controller.cfs.send_command.assert_called_with(TO_CMD_MID, 2, b'\xab\xcd\xef', None)


def test_send_cfs_raw_command_errors(cfs_controller, utils):
    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface'):
        cfs_controller.initialize()

        # invalid mid
        utils.clear_log()
        assert not cfs_controller.send_raw_cfs_command("", "TO_ENABLE_OUTPUT_CC", "ABCDEF")
        cfs_controller.cfs.send_command.assert_not_called()
        assert utils.has_log_level("ERROR")

        # invalid cc
        utils.clear_log()
        assert not cfs_controller.send_raw_cfs_command("TO_CMD_MID", "", "ABCDEF")
        cfs_controller.cfs.send_command.assert_not_called()
        assert utils.has_log_level("ERROR")

        # invalid payload
        utils.clear_log()
        assert not cfs_controller.send_raw_cfs_command("TO_CMD_MID", "TO_ENABLE_OUTPUT_CC", "INVALID")
        cfs_controller.cfs.send_command.assert_not_called()
        assert utils.has_log_level("ERROR")

        # send error
        utils.clear_log()
        cfs_controller.cfs.send_command.return_value = False
        assert not cfs_controller.send_raw_cfs_command("TO_CMD_MID", "TO_ENABLE_OUTPUT_CC", "ABCDEF")
        cfs_controller.cfs.send_command.assert_called_once()
        assert utils.has_log_level("ERROR")

        # invalid cc and mid as int, send invalid cfs_command intended
        utils.clear_log()
        assert not cfs_controller.send_raw_cfs_command(-5, 11, "ABCDEF")
        assert utils.has_log_level("ERROR")


def test_cfs_controller_convert_args_to_ctypes(cfs_controller_inited):
    # arg_class is a list
    cmd_message = cfs_controller_inited.mid_map['TO_CMD_MID']
    code_dict = cmd_message["CC"]['TO_ENABLE_OUTPUT_CC']
    arg_class = [code_dict["ARG_CLASS"]]
    args = {'cDestIp': '127.0.0.1', 'usDestPort': 5011}
    cfs_controller_inited.convert_args_to_ctypes(args, arg_class)

    # args is a non-empty list
    cmd_message = cfs_controller_inited.mid_map['TO_CMD_MID']
    code_dict = cmd_message["CC"]['TO_ENABLE_OUTPUT_CC']
    arg_class = code_dict["ARG_CLASS"]
    arg_class._fields_.clear()
    arg_class._fields_.append(('a', ctypes.c_char))
    args = [{'cDestIp': '127.0.0.1', 'usDestPort': 5011}]
    cfs_controller_inited.convert_args_to_ctypes(args, arg_class)


def test_cfs_controller_encode_ctypes_to_bytes_array(cfs_controller, workspace):
    from plugins.ccsds_plugin.readers.ccdd_export_reader import create_type_class
    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface'):
        cfs_controller.initialize()
        arr16_type = (ctypes.c_uint16 * 4)
        struct_type = create_type_class("arr16type", cfs_controller.ccsds_reader.ctype_structure,
                                        [("arr16", arr16_type)])
        struct = struct_type(arr16_type(64, 128, 256, 512))
        buf = cfs_controller.encode_ctypes_to_bytes(struct)
        assert buf == bytearray(b'\x40\x00\x80\x00\x00\x01\x00\x02')

    if workspace['type'] == 'open_source':
        return

    from plugins.ccsds_plugin.readers.seds_reader import create_type_class
    with patch('plugins.cfs.pycfs.cfs_controllers.LocalCfsInterface'):
        cfs_controller.initialize()
        arr16_type = (ctypes.c_uint16 * 4)
        struct_type = create_type_class("uint16 * 4 type", "arr16type", cfs_controller.ccsds_reader.ctype_structure,
                                        [("arr16", arr16_type)])
        struct = struct_type(arr16_type(64, 128, 256, 512))
        buf = cfs_controller.encode_ctypes_to_bytes(struct)
        assert buf == bytearray(b'\x40\x00\x80\x00\x00\x01\x00\x02')


def test_cfs_controller_resolve_macros(cfs_controller_inited):
    """
    Test CfsController class resolve_macros method:
     Implementation of helper function resolve_macros, search macro_map to convert arg to string.
    """
    # nominal case
    assert cfs_controller_inited.resolve_macros('cfs::#CI_RESET_CC#') == '1'

    # embedded macro
    assert cfs_controller_inited.resolve_macros('1 == #CI_RESET_CC#') == '1 == 1'

    # no macro
    assert cfs_controller_inited.resolve_macros('#CI_RESET_CC') == '#CI_RESET_CC'

    # invalid macro
    with pytest.raises(CtfParameterError):
        cfs_controller_inited.resolve_macros('#CI_RESET_CC_X#')

    with pytest.raises(CtfParameterError):
        cfs_controller_inited.resolve_macros('invalid_cfs::#CI_RESET_CC#')


def test_cfs_controller_resolve_simple_type(cfs_controller_inited):
    """
    Test CfsController class resolve_simple_type method:
    Implementation of helper function resolve_simple_type, if arg is macro, call resolve_macros to convert args
    """
    args_class = cfs_controller_inited.mid_map['TO_CMD_MID']["CC"]['TO_ENABLE_OUTPUT_CC']["ARG_CLASS"]
    # string type
    arg_type = args_class._fields_[0][1]._type_
    assert cfs_controller_inited.resolve_simple_type('127.0.0.1', arg_type) == b'127.0.0.1'
    assert cfs_controller_inited.resolve_simple_type('pwd', arg_type) == b'pwd'
    assert cfs_controller_inited.resolve_simple_type(101010, arg_type) == b'101010'

    # int type
    arg_type = args_class._fields_[1][1]._type_
    assert cfs_controller_inited.resolve_simple_type(5011, arg_type) == 5011
    assert cfs_controller_inited.resolve_simple_type('5011', arg_type) == 5011
    assert cfs_controller_inited.resolve_simple_type('0x1393', arg_type) == 5011
    assert cfs_controller_inited.resolve_simple_type('5011', ctypes.Structure) == 5011
    with pytest.raises(ValueError):
        cfs_controller_inited.resolve_simple_type(5011.0, arg_type)

    # float type
    arg_type = ctypes.c_float
    assert cfs_controller_inited.resolve_simple_type(1.23, arg_type) == 1.23
    assert cfs_controller_inited.resolve_simple_type('1.23', arg_type) == 1.23
    assert cfs_controller_inited.resolve_simple_type(0, arg_type) == 0.0
    arg_type = ctypes.c_float.__ctype_be__
    assert cfs_controller_inited.resolve_simple_type(1.23, arg_type) == 1.23
    assert cfs_controller_inited.resolve_simple_type('1.23', arg_type) == 1.23
    assert cfs_controller_inited.resolve_simple_type(0, arg_type) == 0.0

    # bool type
    arg_type = ctypes.c_bool
    assert cfs_controller_inited.resolve_simple_type('TRUE', arg_type) is True
    assert cfs_controller_inited.resolve_simple_type('true', arg_type) is True
    assert cfs_controller_inited.resolve_simple_type('False', arg_type) is False
    assert cfs_controller_inited.resolve_simple_type(1, arg_type) is True
    assert cfs_controller_inited.resolve_simple_type(0, arg_type) is False
    with pytest.raises(CtfParameterError):
        cfs_controller_inited.resolve_simple_type('tru', arg_type)
    with pytest.raises(CtfParameterError):
        cfs_controller_inited.resolve_simple_type(None, arg_type)


def test_cfs_controller_resolve_simple_type_exception(cfs_controller_inited, utils):
    """
    Test CfsController class resolve_simple_type method:
    Implementation of helper function resolve_simple_type, if arg is macro, call resolve_macros to convert args
    """
    arg_type = ctypes.c_int * 2
    with pytest.raises(CtfParameterError):
        utils.clear_log()
        cfs_controller_inited.resolve_simple_type('4', arg_type)
        assert utils.has_log_level("ERROR")


def test_cfs_controller_resolve_args_from_dict(cfs_controller_inited):
    """
    Test CfsController class resolve_args_from_dict method:
    Implementation of helper function resolve_args_from_dict. Convert argument args to args_class
    """
    cmd_message = cfs_controller_inited.mid_map['TO_CMD_MID']
    code_dict = cmd_message["CC"]['TO_ENABLE_OUTPUT_CC']
    arg_class = code_dict["ARG_CLASS"]
    args = {'cDestIp': '127.0.0.1', 'usDestPort': 5011}
    cfs_controller_inited.resolve_args_from_dict(args, arg_class)

    cmd_message = cfs_controller_inited.mid_map['CFE_ES_CMD_MID']
    code_dict = cmd_message["CC"]['CFE_ES_SHELL_CC']
    arg_class = code_dict["ARG_CLASS"]
    args = {'Payload': {'CmdString': 'hostname', 'OutputFilename': '/cf/test_output.txt'}}
    cfs_controller_inited.resolve_args_from_dict(args, arg_class)

    # invalid format
    with pytest.raises(CtfParameterError):
        args = {'Payload': ['hostname', '/cf/test_output.txt']}
        cfs_controller_inited.resolve_args_from_dict(args, arg_class)


def test_cfs_controller_field_class_by_name(cfs_controller_inited):
    """
    Test CfsController class field_class_by_name method:
    Implementation of helper function field_class_by_name. Return a field with matching name.
    """
    cmd_message = cfs_controller_inited.mid_map['TO_CMD_MID']
    code_dict = cmd_message["CC"]['TO_ENABLE_OUTPUT_CC']
    arg_class = code_dict["ARG_CLASS"]
    cfs_controller_inited.field_class_by_name('cDestIp', arg_class)

    # raise exception
    with pytest.raises(CtfParameterError):
        cfs_controller_inited.field_class_by_name('cDestIp_mock', arg_class)


def test_cfs_controller_check_tlm_continuous(cfs_controller_inited):
    """
    Test CfsController class check_tlm_continuous method:
    Implementation of CFS plugin instructions check_tlm_continuous. When CFS plugin instructions
    (check_tlm_continuous) is executed, it calls CfsController instance's check_tlm_continuous function.
    """
    v_id = 'no_error'
    mid = 'TO_HK_TLM_MID'
    args = [{'compare': '==', 'variable': 'usCmdErrCnt', 'value': [0.0]}]

    assert cfs_controller_inited.check_tlm_continuous(v_id, mid, args)


def test_cfs_controller_check_tlm_continuous_no_mid(cfs_controller_inited, utils):
    """
    Test CfsController class check_tlm_continuous method:
    Implementation of CFS plugin instructions check_tlm_continuous. When CFS plugin instructions
    (check_tlm_continuous) is executed, it calls CfsController instance's check_tlm_continuous function.
    """
    v_id = 'no_error'
    mid = 'TO_HK_TLM_MID_invalid'
    args = [{'compare': '==', 'variable': 'usCmdErrCnt', 'value': [0.0]}]
    # with invalid mid
    utils.clear_log()
    assert not cfs_controller_inited.check_tlm_continuous(v_id, mid, args)
    assert utils.has_log_level("ERROR")


def test_cfs_controller_check_tlm_continuous_not_in_packet(cfs_controller_inited, utils, workspace):
    """
        Test CfsController class check_tlm_continuous method:
        Implementation of CFS plugin instructions check_tlm_continuous. When CFS plugin instructions
        (check_tlm_continuous) is executed, it calls CfsController instance's check_tlm_continuous function.
        #define SET1_CFS_GRP1_TO_HK_TLM_MID                    0x2A0D
    """
    v_id = 'no_error'
    mid = 'TO_HK_TLM_MID'
    args = [{'compare': '==', 'variable': 'usCmdErrCnt', 'value': [0.0]}]
    to_mid = workspace['TO_HK_TLM_MID']

    # remove messages into received_mid_packets_dic. should return False
    utils.clear_log()
    cfs_controller_inited.cfs.received_mid_packets_dic.pop(to_mid)
    assert not cfs_controller_inited.check_tlm_continuous(v_id, mid, args)
    assert utils.has_log_level("ERROR")


def test_cfs_controller_check_tlm_value_no_mid(cfs_controller_inited, utils):
    """
    Test CfsController class check_tlm_value method: mid not available
    Implementation of CFS plugin instructions check_tlm_value. When CFS plugin instructions (check_tlm_value)
    is executed, it calls CfsController instance's check_tlm_value function.
    """
    mid = 'CFE_ES_HK_TLM_MID_INVALID'
    args = [{'variable': 'Payload.CommandCounter', 'value': [1], 'compare': '=='},
            {'variable': 'Payload.CommandErrorCounter', 'value': [0], 'compare': '=='}]

    # mid not available
    with patch.object(Global, 'current_verification_stage', CtfVerificationStage.first_ver):
        utils.clear_log()
        assert not cfs_controller_inited.check_tlm_value(mid, args)
        assert utils.has_log_level("ERROR")


def test_cfs_controller_check_tlm_value(cfs_controller_inited, utils, workspace):
    """
    Test CfsController class check_tlm_value method:
    Implementation of CFS plugin instructions check_tlm_value. When CFS plugin instructions (check_tlm_value)
    is executed, it calls CfsController instance's check_tlm_value function.
    """
    mid = 'CFE_ES_HK_TLM_MID'
    args = [{'variable': 'Payload.CommandCounter', 'value': [1], 'compare': '=='},
            {'variable': 'Payload.CommandErrorCounter', 'value': [0], 'compare': '=='}]
    ES_HK_TLM_MID = workspace['ES_HK_TLM_MID']

    # should not receive message
    assert not cfs_controller_inited.check_tlm_value(mid, args)

    # remove messages into received_mid_packets_dic. should return False
    with patch.object(Global, 'current_verification_stage', CtfVerificationStage.first_ver):
        utils.clear_log()
        cfs_controller_inited.cfs.received_mid_packets_dic.pop(ES_HK_TLM_MID)
        assert not cfs_controller_inited.check_tlm_value(mid, args)
        assert utils.has_log_level("ERROR")


def test_cfs_controller_check_tlm_value_pass(cfs_controller_inited):
    """
    Test CfsController class check_tlm_value method:
    Implementation of CFS plugin instructions check_tlm_value. When CFS plugin instructions (check_tlm_value)
    is executed, it calls CfsController instance's check_tlm_value function.
    """
    mid = 'CFE_ES_HK_TLM_MID'
    args = [{'variable': 'Payload.CommandCounter', 'value': [1], 'compare': '=='},
            {'variable': 'Payload.CommandErrorCounter', 'value': [0], 'compare': '=='}]

    with patch("plugins.cfs.pycfs.local_cfs_interface.LocalCfsInterface.check_tlm_value", return_value=True):
        assert cfs_controller_inited.check_tlm_value(mid, args)


def test_cfs_controller_clear_tlm_packet(cfs_controller_inited):
    """
    Test CfsController clear_tlm_packet method:
    Implementation of CFS plugin instruction ClearTlmPacket. When CFS plugin instruction (ClearTlmPacket)
    is executed, it calls CfsController instance's clear_tlm_packet function.
    """
    assert not cfs_controller_inited.clear_tlm_packet("INVALID_MID")
    # 8193 is 'CFE_ES_HK_TLM_MID'
    assert cfs_controller_inited.clear_tlm_packet("CFE_ES_HK_TLM_MID")
    mid = 75826177
    cfs_controller_inited.cfs.received_mid_packets_dic.pop(mid, None)
    assert not cfs_controller_inited.clear_tlm_packet(mid)



def test_cfs_controller_get_tlm_value(cfs_controller_inited):
    """
    Test CfsController class get_tlm_value method:
    Implementation of CFS plugin instructions get_tlm_value. When CFS plugin method (get_tlm_value)
    is executed, it calls CfsController instance's get_tlm_value function.
    """
    mid = 'CFE_ES_HK_TLM_MID'
    tlm_variable = 'Payload.CommandCounter'
    with patch("plugins.cfs.pycfs.local_cfs_interface.LocalCfsInterface.get_tlm_value", return_value=True):
        assert cfs_controller_inited.get_tlm_value(mid, tlm_variable)


def test_cfs_controller_get_tlm_value_fail(cfs_controller_inited):
    """
    Test CfsController class get_tlm_value method: no received packages matching MID
    Implementation of CFS plugin instructions get_tlm_value. When CFS plugin method (get_tlm_value)
    is executed, it calls CfsController instance's get_tlm_value function.
    """
    mid = 'CFE_ES_HK_TLM_MID'
    tlm_variable = 'Payload.CommandCounter'

    cfs_controller_inited.mid_map = {'CFE_ES_HK_TLM_MID': {'MID': 9999, 'name': 'CFE_ES_OneAppTlm_t'}}
    assert cfs_controller_inited.get_tlm_value(mid, tlm_variable) is None


def test_cfs_controller_get_tlm_value_invalid_mid(cfs_controller_inited):
    """
    Test CfsController class get_tlm_value method: invalid mid
    Implementation of CFS plugin instructions get_tlm_value. When CFS plugin method (get_tlm_value)
    is executed, it calls CfsController instance's get_tlm_value function.
    """
    mid = 'INVALID_MID'
    tlm_variable = 'Payload.CommandCounter'
    assert cfs_controller_inited.get_tlm_value(mid, tlm_variable) is None


def test_cfs_controller_convert_check_tlm_args(cfs_controller_inited):
    """
    Test CfsController class convert_check_tlm_args method:
    Implementation of helper function convert_check_tlm_args. Convert telemetry data args with "value" to a list
    """
    # nominal case, value is array
    args = [{'variable': 'Payload.CommandCounter', 'value': [1], 'compare': '=='},
            {'variable': 'Payload.CommandErrorCounter', 'value': [0], 'compare': '=='}]
    assert cfs_controller_inited.convert_check_tlm_args(args) == args

    # value is macro
    args = [{'variable': 'Payload.CommandErrorCounter', 'value': '#FALSE#', 'compare': '=='}]
    assert cfs_controller_inited.convert_check_tlm_args(args)[0]['value'] == '0'


def test_cfs_controller_check_event_exception(cfs_controller_inited, utils):
    """
    Test CfsController class check_event method: raise exception
    Checks for an EVS event message in the telemetry packet history,
    assuming a particular structure for CFE_EVS_LongEventTlm_t.
    This can be generified in the future to determine the structure from the MID map.
    """
    app = 'TO'
    event_id = 3
    is_regex = False

    utils.clear_log()
    assert not cfs_controller_inited.check_event(app, event_id, None, is_regex, 'exception')
    assert utils.has_log_level("ERROR")


def test_cfs_controller_check_event(cfs_controller_inited, workspace):
    """
    Test CfsController class check_event method:
    Checks for an EVS event message in the telemetry packet history,
    assuming a particular structure for CFE_EVS_LongEventTlm_t.
    This can be generified in the future to determine the structure from the MID map.
    #define SET1_CFE_EVS_LONG_EVENT_MSG_MID                0x2006
    #define SET1_CFE_EVS_SHORT_EVENT_MSG_MID               0x2007
    """
    app = 'TO'
    event_id = 3
    msg = 'TO - ENABLE_OUTPUT cmd successful for  routeMask:0x0000000{}}'
    is_regex = False
    event_str_args = 1
    msg_2 = '%s - ENABLE_OUTPUT cmd successful for  routeMask:0x00000001}'
    event_str_args_2 = 'TO'
    MACRO_MARKER = '#'

    # no received events
    assert not cfs_controller_inited.check_event(app, event_id, msg, is_regex, event_str_args)
    assert not cfs_controller_inited.check_event(app, event_id, None, is_regex)
    assert not cfs_controller_inited.check_event(app, event_id, msg_2, False, event_str_args_2)
    # macro ID
    cfs_controller_inited.macro_map["MY_ID"] = event_id
    event_id_macro = MACRO_MARKER + "MY_ID" + MACRO_MARKER
    assert not cfs_controller_inited.check_event(app, event_id_macro, msg, is_regex)

    EVS_LONG_EVENT_MSG_MID = workspace['EVS_LONG_EVENT_MSG_MID']
    EVS_SHORT_EVENT_MSG_MID = workspace['EVS_SHORT_EVENT_MSG_MID']

    with patch.object(cfs_controller_inited.cfs, 'check_tlm_value') as mock_check:
        # pass with long event
        mock_check.side_effect = [False, True]
        args = [
            {"compare": "streq", "variable": "Payload.PacketID.AppName", "value": app},
            {"compare": "==", "variable": "Payload.PacketID.EventID", "value": event_id},
            {"compare": "streq", "variable": "Payload.Message", "value": msg}
        ]
        assert cfs_controller_inited.check_event(app, event_id, msg, is_regex)
        mock_check.assert_called_with(EVS_LONG_EVENT_MSG_MID, args, discard_old_packets=False)
        mock_check.reset_mock()
        # pass with short event
        mock_check.side_effect = None
        mock_check.return_value = True
        assert cfs_controller_inited.check_event(app, event_id, msg, is_regex)
        mock_check.assert_called_once_with(EVS_SHORT_EVENT_MSG_MID, args[:2], discard_old_packets=False)


def test_cfs_controller_convert_archive_cfs_files_exception(cfs_controller_inited, utils):
    """
    Test CfsController class archive_cfs_files method:  exception raised
    Implementation of CFS plugin instructions archive_cfs_files. When CFS plugin instructions
    (archive_cfs_files) is executed, it calls CfsController instance's archive_cfs_files function.
    """
    source_path = '~/sample_cfs_workspace/ctf_tests/test_scripts/sample_test_suite/app_tests'
    utils.clear_log()
    assert not cfs_controller_inited.archive_cfs_files(source_path)
    assert utils.has_log_level("ERROR")


def test_cfs_controller_convert_archive_cfs_files(cfs_controller_inited):
    """
    Test CfsController class archive_cfs_files method:
    Implementation of CFS plugin instructions archive_cfs_files. When CFS plugin instructions
    (archive_cfs_files) is executed, it calls CfsController instance's archive_cfs_files function.
    """
    source_path = 'temp_archive'
    if not os.path.exists(source_path):
        os.mkdir(source_path)
    if os.path.exists('artifacts'):
        shutil.rmtree('artifacts')
    shutil.copy('functional_tests/plugin_tests/Test_CTF_Basic_Example.json', source_path)

    # mock Global.test_start_time to year 2016 to move files
    with patch('time.mktime', return_value=1455511418.00):
        assert cfs_controller_inited.archive_cfs_files(source_path)

    shutil.rmtree('temp_archive')


def test_cfs_controller_remove_check_tlm_continuous(cfs_controller_inited):
    """
    Test CfsController class remove_check_tlm_continuous method:
    Implementation of CFS plugin instructions remove_check_tlm_continuous. When CFS plugin instructions
    (remove_check_tlm_continuous) is executed, it calls CfsController instance's function.
    """
    assert not cfs_controller_inited.remove_check_tlm_continuous('no_error')


def test_cfs_controller_shutdown_cfs(cfs_controller_inited):
    """
    Test CfsController class shutdown_cfs method:
    Implementation of CFS plugin instructions shutdown_cfs. When CFS plugin instructions
    (shutdown_cfs) is executed, it calls CfsController instance's shutdown_cfs function.
    """
    with patch('os.system') as mock_system:
        mock_system.return_value = 0
        assert cfs_controller_inited.shutdown_cfs()
        mock_system.assert_any_call('kill -9 42')
        mock_system.assert_called_with('pkill -fe -9 "tail -f /dev/null"')
    assert not cfs_controller_inited.cfs


def test_cfs_controller_shutdown_cfs_fail_pid(cfs_controller_inited, utils):
    """
    Test CfsController class shutdown_cfs method: os.system call returns an error code for one process
    Implementation of CFS plugin instructions shutdown_cfs. When CFS plugin instructions
    (shutdown_cfs) is executed, it calls CfsController instance's shutdown_cfs function.
    """
    # case: no cfs pid
    with patch('os.system') as mock_system:
        cfs_controller_inited.cfs_pid = None
        assert not cfs_controller_inited.shutdown_cfs()
        assert not cfs_controller_inited.cfs
        assert utils.has_log_level("WARNING")
        assert utils.has_log_level("ERROR")
        mock_system.assert_called_once_with('pkill -fe -9 "tail -f /dev/null"')


def test_cfs_controller_shutdown_cfs_fail_ps(cfs_controller_inited, utils):
    # case: ps fails
    with patch('os.system') as mock_system:
        mock_system.return_value = 1
        assert not cfs_controller_inited.shutdown_cfs()
        assert not cfs_controller_inited.cfs
        assert utils.has_log_level("ERROR")
        mock_system.assert_any_call("ps -p 42")
        mock_system.assert_called_with('pkill -fe -9 "tail -f /dev/null"')


def test_cfs_controller_shutdown_cfs_fail_kill(cfs_controller_inited, utils):
    # case: kill and pkill fail
    with patch('os.system') as mock_system:
        mock_system.side_effect = [0, 1, 1]
        assert not cfs_controller_inited.shutdown_cfs()
        assert not cfs_controller_inited.cfs
        assert utils.has_log_level("ERROR")
        mock_system.assert_any_call('ps -p 42')
        mock_system.assert_any_call('kill -9 42')
        mock_system.assert_called_with('pkill -fe -9 "tail -f /dev/null"')


def test_cfs_controller_shutdown(cfs_controller_inited, utils):
    """
    Test CfsController class shutdown method:
    This function will shut down the CFS application being tested even if the JSON test file does not
    include the shutdown test command
    """
    with patch('plugins.cfs.pycfs.cfs_controllers.CfsController.shutdown_cfs') as mock_shutdown_cfs:
        # case: nominal
        assert cfs_controller_inited.shutdown() is None
        assert cfs_controller_inited.cfs is None
        assert not utils.has_log_level("ERROR")
        mock_shutdown_cfs.assert_called_once()
        mock_shutdown_cfs.reset_mock()
        # case: cfs already shut down
        assert cfs_controller_inited.shutdown() is None
        assert cfs_controller_inited.cfs is None
        assert not utils.has_log_level("ERROR")
        mock_shutdown_cfs.assert_not_called()


def test_cfs_controller_shutdown_not_started(cfs_controller_inited, utils):
    """
    Test CfsController class shutdown method:
    This function will not shut down the CFS application being tested if it was not started by CTF
    """
    with patch('plugins.cfs.pycfs.cfs_controllers.CfsController.shutdown_cfs') as mock_shutdown_cfs:
        # case: nominal
        cfs_controller_inited.cfs.started_by_ctf = False
        assert cfs_controller_inited.shutdown() is None
        assert cfs_controller_inited.cfs is None
        assert utils.has_log_level("WARNING")
        mock_shutdown_cfs.assert_not_called()


def test_cfs_controller_shutdown_exception(cfs_controller_inited, utils):
    """
    Test CfsController class shutdown method: raise exception
    This function will shut down the CFS application being tested even if the JSON test file does not
    include the shutdown test command
    """
    with patch('plugins.cfs.pycfs.cfs_controllers.CfsController.shutdown_cfs') as mock_shutdown_cfs:
        utils.clear_log()
        mock_shutdown_cfs.side_effect = CtfTestError("Raise Exception for shutdown_cfs")
        assert cfs_controller_inited.shutdown() is None
        mock_shutdown_cfs.assert_called_once()
        assert not cfs_controller_inited.cfs
        assert utils.has_log_level("ERROR")


def test_cfs_controller_validate_mid_value(cfs_controller_inited, workspace):
    """
    Test CfsController class validate_mid_value method:
    Implementation of helper function validate_mid_value. Check whether mid_name is in mid_map dictionary.
    """
    assert cfs_controller_inited.validate_mid_value('TO_CMD_MID') == 'TO_CMD_MID'
    assert cfs_controller_inited.validate_mid_value('CFE_ES_CMD_MID') == 'CFE_ES_CMD_MID'
    assert cfs_controller_inited.validate_mid_value('#DUMMY_IO_CMD_MID#') == 'DUMMY_IO_CMD_MID'

    assert cfs_controller_inited.validate_mid_value(workspace['DUMMY_IO_CMD_MID_STR']) == 'DUMMY_IO_CMD_MID'
    assert cfs_controller_inited.validate_mid_value(workspace['DUMMY_IO_CMD_MID']) == 'DUMMY_IO_CMD_MID'


def test_cfs_controller_validate_mid_value_invalid(cfs_controller_inited, utils):
    """
    Test CfsController class validate_mid_value method: return None for invalid input
    Implementation of helper function validate_mid_value. Check whether mid_name is in mid_map dictionary.
    """
    utils.clear_log()
    assert cfs_controller_inited.validate_mid_value(0) is None
    assert cfs_controller_inited.validate_mid_value('INVALID_MID') is None
    assert utils.has_log_level("ERROR")


def test_cfs_controller_validate_mid_value_uninitialized(cfs_controller, utils):
    """
    Test CfsController class validate_mid_value method: return None when MID map is not available
    Implementation of helper function validate_mid_value. Check whether mid_name is in mid_map dictionary.
    """
    utils.clear_log()
    assert cfs_controller.validate_mid_value('TO_CMD_MID') is None
    assert utils.has_log_level("ERROR")


def test_cfs_controller_validate_cc_value(cfs_controller_inited):
    """
    Test CfsController class validate_cc_value method:
    Implementation of helper function validate_cc_value. Check whether cc_name is in the mid dictionary.
    """
    # same command code in different forms
    to_mid = cfs_controller_inited.mid_map['TO_CMD_MID']
    assert cfs_controller_inited.validate_cc_value(to_mid, 0) == 'TO_NOOP_CC'
    assert cfs_controller_inited.validate_cc_value(to_mid, 0x0) == 'TO_NOOP_CC'
    assert cfs_controller_inited.validate_cc_value(to_mid, '0') == 'TO_NOOP_CC'
    assert cfs_controller_inited.validate_cc_value(to_mid, 'TO_NOOP_CC') == 'TO_NOOP_CC'
    assert cfs_controller_inited.validate_cc_value(to_mid, '#TO_NOOP_CC#') == 'TO_NOOP_CC'

    # MID with no command codes
    assert cfs_controller_inited.validate_cc_value(cfs_controller_inited.mid_map['TO_SEND_HK_MID'], '') == ''


def test_cfs_controller_validate_cc_value_invalid(cfs_controller_inited, utils):
    """
    Test CfsController class validate_cc_value method: return None for invalid input
    Implementation of helper function validate_cc_value. Check whether cc_name is in the mid dictionary.
    """
    # invalid CC
    to_mid = cfs_controller_inited.mid_map['TO_CMD_MID']
    utils.clear_log()
    assert cfs_controller_inited.validate_cc_value(to_mid, -1) is None
    assert cfs_controller_inited.validate_cc_value(to_mid, 'INVALID_CC') is None
    assert utils.has_log_level("ERROR")

    # invalid MID type
    assert cfs_controller_inited.validate_cc_value('TO_CMD_MID', 'TO_NOOP_CC') is None


def test_remote_cfs_controller_init(remote_controller):
    """
    Test RemoteCfsController class constructor
    """
    assert remote_controller.cfs is None
    assert remote_controller.ccsds_reader is None
    assert remote_controller.mid_map is None
    assert remote_controller.macro_map is None
    assert remote_controller.first_call_flag
    assert remote_controller.mid_pkt_count is None
    assert remote_controller.execution is None


def test_remote_cfs_controller_initialize_fail(remote_controller, utils):
    """
    Test RemoteCfsController class initialize method: fail to init_connection
    Initialize CfsController instance, including the followings: create mid map; import ccsds header;
    create ssh CFS command interface; create telemetry interface;
    """
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=False):
        assert not remote_controller.initialize()

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True):
        utils.clear_log()
        assert not remote_controller.initialize()
        assert utils.has_log_level("ERROR")


def test_remote_cfs_controller_initialize_pass(remote_controller):
    """
    Test RemoteCfsController class initialize method:
    Initialize CfsController instance, including the followings: create mid map; import ccsds header;
    create ssh CFS command interface; create telemetry interface;
    """

    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True), \
            patch('plugins.cfs.pycfs.cfs_controllers.RemoteCfsInterface') as mock_remotecfsinterface:
        mock_remotecfsinterface.return_value.init_passed = True
        assert remote_controller.initialize()
        assert mock_remotecfsinterface.call_args.args[2].command_socket.getsockname() == ('0.0.0.0', 5011)

    # another case: start_cfs
    with patch('plugins.ssh.ssh_plugin.SshController.init_connection', return_value=True), \
            patch('plugins.cfs.pycfs.cfs_controllers.RemoteCfsInterface') as mock_remotecfsinterface:
        mock_remotecfsinterface.return_value.init_passed = True
        assert remote_controller.initialize()
        assert remote_controller.cfs


def test_remote_cfs_controller_initialize_exception(remote_controller, utils):
    """
    Test RemoteCfsController class initialize method: raise exception from import_ccsds_header_types
    Initialize CfsController instance, including the followings: create mid map; import ccsds header;
    create ssh CFS command interface; create telemetry interface;
    """
    with patch('plugins.cfs.pycfs.cfs_controllers.import_ccsds_header_types') as mock_import:
        utils.clear_log()
        mock_import.side_effect = CtfTestError("Raise Exception for import_ccsds_header_types")
        assert not remote_controller.initialize()
        mock_import.assert_called_once()
        assert utils.has_log_level("ERROR")


def test_remote_cfs_controller_shutdown_cfs(remote_controller_inited, utils):
    """
    Test RemoteCfsController class shutdown_cfs method:
    Implementation of CFS plugin instructions shutdown_cfs. When CFS plugin instructions
    (shutdown_cfs) is executed, it calls RemoteCfsController instance's shutdown_cfs function.
    """
    with patch('plugins.ssh.ssh_plugin.SshController.run_command', return_value=True) as mock_command, \
            patch('plugins.ssh.ssh_plugin.SshController.get_file', return_value=True) as mock_get:
        utils.clear_log()
        temp_dir = Global.current_script_log_dir
        Global.current_script_log_dir = '~/fsw/ctf_tests/results/'
        remote_controller_inited.cfs.cfs_std_out_path = '/tmp/ssh_out.txt'
        assert remote_controller_inited.shutdown_cfs()
        assert not remote_controller_inited.cfs
        mock_command.assert_has_calls([call("pkill -P 42",), call("rm /tmp/ssh_out.txt",)]),
        mock_get.assert_called_once_with('/tmp/ssh_out.txt', '~/fsw/ctf_tests/results/ssh_out.txt', {'delete': True})
        assert not utils.has_log_level("ERROR")
        Global.current_script_log_dir = temp_dir


def test_remote_cfs_controller_shutdown_cfs_fail(remote_controller_inited, utils):
    """
    Test RemoteCfsController class shutdown_cfs method: remote command fails
    Implementation of CFS plugin instructions shutdown_cfs. When CFS plugin instructions
    (shutdown_cfs) is executed, it calls RemoteCfsController instance's shutdown_cfs function.
    """
    with patch('plugins.ssh.ssh_plugin.SshController.run_command', return_value=False), \
            patch('plugins.ssh.ssh_plugin.SshController.get_file', return_value=True):
        utils.clear_log()
        remote_controller_inited.cfs.cfs_std_out_path = '/tmp/ssh_out.txt'
        assert not remote_controller_inited.shutdown_cfs()
        assert utils.has_log_level("ERROR")
        assert not remote_controller_inited.cfs


def test_remote_cfs_controller_shutdown_cfs_fail_get_file(remote_controller_inited, utils):
    """
    Test RemoteCfsController class shutdown_cfs method: remote command fails
    Implementation of CFS plugin instructions shutdown_cfs. When CFS plugin instructions
    (shutdown_cfs) is executed, it calls RemoteCfsController instance's shutdown_cfs function.
    """
    with patch('plugins.ssh.ssh_plugin.SshController.run_command', return_value=True) as mock_run_command, \
            patch('plugins.ssh.ssh_plugin.SshController.get_file', return_value=False):
        utils.clear_log()
        remote_controller_inited.cfs.cfs_std_out_path = '/tmp/ssh_out.txt'
        assert not remote_controller_inited.shutdown_cfs()
        mock_run_command.assert_called_once()
        assert utils.has_log_level("ERROR")
        assert not remote_controller_inited.cfs


def test_remote_cfs_controller_shutdown_cfs_fail_no_pid(remote_controller_inited, utils):
    # case: no cfs pid
    with patch('plugins.ssh.ssh_plugin.SshController.run_command') as mock_run_command, \
            patch('plugins.ssh.ssh_plugin.SshController.get_file', return_value=True):
        utils.clear_log()
        mock_run_command.return_value = False
        remote_controller_inited.cfs_pid = None
        remote_controller_inited.cfs.cfs_std_out_path = '/tmp/ssh_out.txt'
        assert not remote_controller_inited.shutdown_cfs()
        mock_run_command.assert_called_once_with("rm /tmp/ssh_out.txt")
        assert utils.has_log_level("ERROR")
        assert not remote_controller_inited.cfs


def test_remote_cfs_controller_archive_cfs_files_pass(remote_controller_inited):
    """
     Test RemoteCfsController class archive_cfs_files method:
     Implementation of CFS plugin instructions archive_cfs_files. When CFS plugin instructions
     (archive_cfs_files) is executed, it calls RemoteCfsController instance's archive_cfs_files function.
     """
    source_path = 'remote_cfs_controller_temp_archive'
    temp_test_start_time = Global.test_start_time
    Global.test_start_time = (2021, 3, 22, 10, 13, 38, 0, 0, 0)

    with patch('plugins.ssh.ssh_plugin.SshController.run_command', return_value=True), \
            patch('plugins.ssh.ssh_plugin.SshController.get_file', return_value=True), \
            patch.object(Global, 'current_script_log_dir', 'temp_log_dir'):
        assert remote_controller_inited.archive_cfs_files(source_path)
        assert os.path.exists('./temp_log_dir/artifacts')
        os.rmdir('./temp_log_dir/artifacts')

    Global.test_start_time = temp_test_start_time


def test_remote_cfs_controller_archive_cfs_files_fail(remote_controller_inited):
    """
     Test RemoteCfsController class archive_cfs_files method: test fails
     Implementation of CFS plugin instructions archive_cfs_files. When CFS plugin instructions
     (archive_cfs_files) is executed, it calls RemoteCfsController instance's archive_cfs_files function.
     """
    source_path = 'remote_cfs_controller_temp_archive'
    temp_test_start_time = Global.test_start_time
    Global.test_start_time = (2021, 3, 22, 10, 13, 38, 0, 0, 0)
    assert not remote_controller_inited.archive_cfs_files(source_path)
    Global.test_start_time = temp_test_start_time
