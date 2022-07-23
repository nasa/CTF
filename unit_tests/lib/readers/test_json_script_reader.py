"""
@namespace tests.lib.readers.test_json_script_reader
Unit Test for JSONScriptReader class: Loads and validates input CTF test scripts.
                                      Manages execution of loaded test scripts.
"""

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

import pytest

from lib.ctf_global import Global
from lib.exceptions import CtfTestError
from lib.plugin_manager import PluginManager
from lib.readers.json_script_reader import JSONScriptReader


@pytest.fixture(scope="session", autouse=True)
def init_global():
    Global.load_config("./configs/default_config.ini")
    Global.plugin_manager = PluginManager(['plugins'])


@pytest.fixture(name="json_script_reader")
def _json_script_reader_instance():
    input_script_path = 'functional_tests/plugin_tests/Test_CTF_All_Instructions.json'
    return JSONScriptReader(input_script_path)


def test_json_script_reader_init(json_script_reader):
    """
    test JSONScriptReader class constructor
    """
    assert json_script_reader.valid_script
    assert json_script_reader.input_script_path == 'functional_tests/plugin_tests/Test_CTF_All_Instructions.json'
    assert json_script_reader.script.input_file_path == 'functional_tests/plugin_tests'
    assert json_script_reader.script.input_file == 'Test_CTF_All_Instructions.json'


def test_json_script_reader_init_exception(utils):
    """
    test JSONScriptReader class constructor  -- raise exception when loading an invalid json file
    """
    utils.clear_log()
    input_script_path = 'functional_tests/plugin_tests/test_ctf_all_instructions_fail.json'
    reader = JSONScriptReader(input_script_path)
    assert not reader.valid_script
    assert utils.has_log_level('ERROR')


def test_json_script_reader_init_exception2(utils):
    """
    test JSONScriptReader class constructor  -- raise exception when calling json.load
    """
    utils.clear_log()
    input_script_path = 'functional_tests/plugin_tests/Test_CTF_All_Instructions.json'
    with patch("json.load") as mock_load:
        mock_load.side_effect = ValueError()
        reader = JSONScriptReader(input_script_path)
        assert not reader.valid_script
        assert utils.has_log_level('ERROR')


def test_json_script_reader_init_exception3(utils):
    """
    test JSONScriptReader class constructor  -- raise exception when calling process_header
    """
    utils.clear_log()
    input_script_path = 'functional_tests/plugin_tests/Test_CTF_All_Instructions.json'
    with patch("lib.readers.json_script_reader.JSONScriptReader.process_header") as mock_process_header:
        mock_process_header.side_effect = CtfTestError('mock_process_header')
        reader = JSONScriptReader(input_script_path)
        assert utils.has_log_level('ERROR')
        assert reader.valid_script == False


def test_json_script_reader_process_header(json_script_reader):
    """
    test JSONScriptReader class method : process_header
    Parse and process test information from script header
    """
    assert json_script_reader.process_header() is None
    assert json_script_reader.valid_script


def test_json_script_reader_process_exception(json_script_reader, utils):
    """
    test JSONScriptReader class method : process_header  -- trigger KeyError exception
    Parse and process test information from script header
    """
    # delete an element from raw_data
    json_script_reader.raw_data.pop('owner')
    utils.clear_log()
    assert json_script_reader.process_header() is None
    assert not json_script_reader.valid_script
    assert utils.has_log_level('ERROR')


def test_json_script_reader_process_functions(json_script_reader):
    """
    test JSONScriptReader class method : process_functions
    Parse the function definitions and imports in the test script
    """
    json_script_reader.raw_data['import'] = {
        "./functional_tests/cfe_6_7_tests/libs/CiFunctions.json":
        ["SendCheckCiEnableToCmd"]
    }
    assert json_script_reader.process_functions() is None
    assert 'SendCheckCiEnableToCmd' in json_script_reader.functions


def test_json_script_reader_process_functions_with_function():
    """
    test JSONScriptReader class method : process_functions
    Parse the function definitions and imports in the test script
    """
    input_script_path = 'functional_tests/cfe_6_7_tests/app_tests/CiFunctionTests.json'
    reader = JSONScriptReader(input_script_path)
    assert reader.process_functions() is None
    assert 'SendCheckCiEnableToCmd' in reader.functions


def test_json_script_reader_process_functions_exception(utils):
    """
    test JSONScriptReader class method : process_functions  -- raise exception when calling json.load
    Parse the function definitions and imports in the test script
    """
    utils.clear_log()
    input_script_path = './functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json'
    reader = JSONScriptReader(input_script_path)
    with patch("json.load") as mock_load:
        mock_load.side_effect = ValueError
        with pytest.raises(ValueError):
            reader.process_functions()
            assert utils.has_log_level('ERROR')

    with patch("json.load") as mock_load:
        utils.clear_log()
        mock_load.side_effect = KeyError
        with pytest.raises(KeyError):
            reader.process_functions()
            assert utils.has_log_level('ERROR')


def test_json_script_reader_process_functions_invalid_import(utils):
    """
    test JSONScriptReader class method : process_functions  -- invalid import
    Parse the function definitions and imports in the test script
    """
    utils.clear_log()
    input_script_path = './functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json'
    reader = JSONScriptReader(input_script_path)
    invalid_import = {'invalid_file.json': []}
    reader.raw_data['import'].update(invalid_import)

    with pytest.raises(CtfTestError):
        reader.process_functions()


def test_json_script_reader_sanitize_args_dict(json_script_reader):
    """
    test JSONScriptReader class method : sanitize_args  -- input is dictionary
    Iterates over arguments within test instructions and decodes arguments if needed.
    """
    assert json_script_reader.sanitize_args(None) is None

    args = {'expectedCmdCnt': 1, 'expectedErrCnt': 0, 'destIp': '127.0.0.1', 'destPort': 5011}
    assert json_script_reader.sanitize_args(args) == args

    args_bytes = {'expectedCmdCnt': 1, 'expectedErrCnt': 0, 'destIp': b'127.0.0.1', 'destPort': 5011}
    assert json_script_reader.sanitize_args(args_bytes) == args


def test_json_script_reader_sanitize_args_list(json_script_reader):
    """
    test JSONScriptReader class method : sanitize_args  -- input is list
    Iterates over arguments within test instructions and decodes arguments if needed.
    """

    args = [{'expectedCmdCnt': 1, 'expectedErrCnt': 0, 'destIp': '127.0.0.1', 'destPort': 5011}]
    assert json_script_reader.sanitize_args(args) == args

    args_bytes = [{'expectedCmdCnt': 1, 'expectedErrCnt': 0, 'destIp': b'127.0.0.1', 'destPort': 5011}]
    assert json_script_reader.sanitize_args(args_bytes) == args

    args_bytes = ['expectedCmdCnt', b'destIp']
    assert json_script_reader.sanitize_args(args_bytes) == ['expectedCmdCnt', 'destIp']

    with patch('builtins.bytes') as mock_bytes:
        mock_bytes.return_value.decode = UnicodeDecodeError
        assert json_script_reader.sanitize_args(args_bytes) is None


def test_json_script_reader_process_tests_empty_test(json_script_reader):
    """
    test JSONScriptReader class method : process_tests   -- empty test
    Iterates over tests within the test script and parses each test.
    """
    json_script_reader.raw_data['tests'] = None
    assert json_script_reader.process_tests() is None
    assert not json_script_reader.valid_script


def test_json_script_reader_process_tests():
    """
    test JSONScriptReader class method : process_tests
    Iterates over tests within the test script and parses each test.
    """
    input_script_path = 'functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json'
    reader = JSONScriptReader(input_script_path)
    with patch("lib.readers.json_script_reader.JSONScriptReader.resolve_function", return_value=None):
        assert reader.process_tests() is None


def test_json_script_reader_process_tests_no_commands_in_function():
    """
    test JSONScriptReader class method : process_tests - No commands in function
    Iterates over tests within the test script and parses each test.
    """
    input_script_path = 'functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json'
    reader = JSONScriptReader(input_script_path)
    with patch("lib.readers.json_script_reader.JSONScriptReader.resolve_function", return_value=False):
        assert reader.process_tests() is None


def test_json_script_reader_process_tests_no_wait():
    """
    test JSONScriptReader class method : process_tests  no wait keyword in json file
    Iterates over tests within the test script and parses each test.
    """
    input_script_path = 'functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json'
    reader = JSONScriptReader(input_script_path)
    print(reader.raw_data['tests'][0]['instructions'])
    reader.raw_data['tests'][0]['instructions'][4].pop('wait')
    assert reader.process_tests() is None


def test_json_script_reader_resolve_function(json_script_reader):
    """
    test JSONScriptReader class method : resolve_function
    Perform in-line replacement of function calls with the set of instructions within the function definition
    """
    name = 'SendCheckCiEnableToCmd'
    params = {'expectedCmdCnt': 1, 'expectedErrCnt': 0, 'destIp': '127.0.0.1', 'destPort': 5011, 'routeMask': 0,
              'fileDesc': 0}
    functions = {'SendCheckCiEnableToCmd': {'description': 'Send and check CI_ENABLE_TO_CC',
                                            'varlist': ['expectedCmdCnt', 'expectedErrCnt', 'destIp', 'destPort',
                                                        'routeMask', 'fileDesc'], 'instructions': [
            {'instruction': 'SendCfsCommand',
             'data': {'target': '', 'mid': 'CI_CMD_MID', 'cc': 'CI_ENABLE_TO_CC',
                      'args': {'cDestIp': 'destIp', 'usDestPort': 'destPort', 'usRouteMask': 'routeMask',
                               'iFileDesc': 'fileDesc'}}, 'wait': 0},
            {'instruction': 'CheckTlmValue', 'data': {'target': '', 'mid': 'CI_HK_TLM_MID',
                                                      'args': [
                                                          {'value': ['expectedCmdCnt'], 'compare': '=='},
                                                          {'variable': 'usCmdErrCnt',
                                                           'value': ['expectedErrCnt'], 'compare': '=='}]},
             'wait': 0}]}}

    assert json_script_reader.resolve_function('invalid_cmd', params, functions) is None
    assert json_script_reader.resolve_function(name, params, functions) == [
        {'instruction': 'SendCfsCommand', 'data': {'target': '', 'mid': 'CI_CMD_MID', 'cc': 'CI_ENABLE_TO_CC',
                                                   'args': {'cDestIp': '127.0.0.1', 'usDestPort': 5011,
                                                            'usRouteMask': 0, 'iFileDesc': 0}}, 'wait': 0},
        {'instruction': 'CheckTlmValue', 'data': {'target': '', 'mid': 'CI_HK_TLM_MID',
                                                  'args': [{'value': [1], 'compare': '=='},
                                                           {'variable': 'usCmdErrCnt', 'value': [0], 'compare': '=='}]},
         'wait': 0}]


def test_json_script_reader_resolve_function_inside_func(json_script_reader):
    """
    test JSONScriptReader class method : resolve_function
    Perform in-line replacement of function calls with the set of instructions within the function definition
    """
    name = 'SendCheckCiEnableToCmd'
    params = {'expectedCmdCnt': 1, 'expectedErrCnt': 0, 'destIp': '127.0.0.1', 'destPort': 5011, 'routeMask': 0,
              'fileDesc': 0}
    functions = {'SendCheckCiEnableToCmd': {'description': 'Send and check CI_ENABLE_TO_CC',
                                            'varlist': ['expectedCmdCnt', 'expectedErrCnt', 'destIp', 'destPort',
                                                        'routeMask', 'fileDesc'], 'instructions': [
            {'instruction': 'SendCfsCommand',
             'data': {'target': '', 'mid': 'CI_CMD_MID', 'cc': 'CI_ENABLE_TO_CC',
                      'args': {'cDestIp': 'destIp', 'usDestPort': 'destPort', 'usRouteMask': 'routeMask',
                               'iFileDesc': 'fileDesc'}}, 'wait': 0},
            {'function': 'SendCheckCiEnableToCmd_2',
             "params": {"expectedCmdCnt": 1, "stackSize": 12345, "exceptionAction": 0, }
             },
            {'instruction': 'CheckTlmValue', 'data': {'target': '', 'mid': 'CI_HK_TLM_MID',
                                                      'args': [
                                                          {'value': ['expectedCmdCnt'], 'compare': '=='},
                                                          {'variable': 'usCmdErrCnt',
                                                           'value': ['expectedErrCnt'], 'compare': '=='}]},
             'wait': 0}]},
                 'SendCheckCiEnableToCmd_2': {'description': 'Send and check CI_ENABLE_TO_CC',
                                              'varlist': ['expectedCmdCnt', 'expectedErrCnt', 'destIp', 'destPort',
                                                          'routeMask', 'fileDesc'], 'instructions': [
                         {'instruction': 'SendCfsCommand',
                          'data': {'target': '', 'mid': 'CI_CMD_MID', 'cc': 'CI_ENABLE_TO_CC',
                                   'args': {'cDestIp': 'destIp', 'usDestPort': 'destPort', 'usRouteMask': 'routeMask',
                                            'iFileDesc': 'fileDesc'}}, 'wait': 0},
                     ]
                                              }
                 }

    assert json_script_reader.resolve_function(name, params, functions) is None


def test_json_script_reader_resolve_function_mismatch(json_script_reader):
    """
    test JSONScriptReader class method : resolve_function  -- mismatch cases
    Perform in-line replacement of function calls with the set of instructions within the function definition
    """
    name = 'SendCheckCiEnableToCmd'
    params = {'expectedCmdCnt': 1, 'expectedErrCnt': 0, 'destIp': '127.0.0.1', 'destPort': 5011, }
    functions = {'SendCheckCiEnableToCmd': {'description': 'Send and check CI_ENABLE_TO_CC',
                                            'varlist': ['expectedCmdCnt', 'expectedErrCnt', 'destIp', 'destPort',
                                                        'routeMask', 'fileDesc'], 'instructions': [
            {'instruction': 'SendCfsCommand',
             'data': {'target': '', 'mid': 'CI_CMD_MID', 'cc': 'CI_ENABLE_TO_CC',
                      'args': {'cDestIp': 'destIp', 'usDestPort': 'destPort', 'usRouteMask': 'routeMask',
                               'iFileDesc': 'fileDesc'}}, 'wait': 0},
            {'instruction': 'CheckTlmValue', 'data': {'target': '', 'mid': 'CI_HK_TLM_MID',
                                                      'args': [
                                                          {'value': ['expectedCmdCnt'], 'compare': '=='},
                                                          {'variable': 'usCmdErrCnt',
                                                           'value': ['expectedErrCnt'], 'compare': '=='}]},
             'wait': 0}]}}

    assert json_script_reader.resolve_function('invalid_cmd', params, functions) is None
    assert json_script_reader.resolve_function(name, params, functions) is None


def test_json_script_reader_resolve_function_exception(json_script_reader, utils):
    """
    test JSONScriptReader class method : resolve_function  -- raise exception
    Perform in-line replacement of function calls with the set of instructions within the function definition
    """
    name = 'SendCheckCiEnableToCmd'
    params = {'expectedCmdCnt': 1, 'expectedErrCnt': 0, 'destIp': '127.0.0.1', 'destPort': 5011, }
    functions = {'SendCheckCiEnableToCmd': {'description': 'Send and check CI_ENABLE_TO_CC',
                                            'varlist_invalid': ['expectedCmdCnt', 'expectedErrCnt', 'destIp',
                                                                'destPort',
                                                                'routeMask', 'fileDesc'],
                                            'instructions': [
                                                {'instruction': 'SendCfsCommand',
                                                 'data': {'target': '', 'mid': 'CI_CMD_MID', 'cc': 'CI_ENABLE_TO_CC',
                                                          'args': {'cDestIp': 'destIp', 'usDestPort': 'destPort',
                                                                   'usRouteMask': 'routeMask',
                                                                   'iFileDesc': 'fileDesc'}},
                                                 'wait': 0},
                                            ]}}

    with pytest.raises(KeyError):
        utils.clear_log()
        json_script_reader.resolve_function(name, params, functions)
        assert utils.has_log_level('ERROR')


def test_json_script_reader_resolve_command_data(json_script_reader):
    """
    test JSONScriptReader class method : resolve_command_data
    Perform in-line replacement of arguments passed into a function
    """
    data = {}
    params = {}
    assert json_script_reader.resolve_function_params(params, data) == {}

    data = {'a': 1, 'b': 2, 'c': 3}
    params = {1: 'a', 2: 'b'}
    assert json_script_reader.resolve_function_params(params, data) == {'a': 'a', 'b': 'b', 'c': 3}

    data = {'a': 1, 'b': 2, 'c': 3}
    params = {'a': 1, 'b': 2}
    assert json_script_reader.resolve_function_params(params, data) == data

    data = {'cDestIp': 'destIp', 'usDestPort': 'destPort', 'usRouteMask': 'routeMask', 'iFileDesc': 'fileDesc'}
    params = {'expectedCmdCnt': 1, 'expectedErrCnt': 0, 'destIp': '127.0.0.1', 'destPort': 5011, 'routeMask': 0,
              'fileDesc': 0}
    assert json_script_reader.resolve_function_params(params, data) == {
        'cDestIp': '127.0.0.1',
        'usDestPort': 5011,
        'usRouteMask': 0,
        'iFileDesc': 0
    }
