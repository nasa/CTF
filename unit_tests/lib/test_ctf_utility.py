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
import pathlib
from unittest.mock import patch

import pytest

from lib import ctf_utility
from lib.ctf_global import Global
from lib.exceptions import CtfParameterError


def test_ctf_utility_expand_path():
    assert ctf_utility.expand_path('') == ''
    assert ctf_utility.expand_path('dir') == 'dir'
    assert ctf_utility.expand_path('./this/is_a/path/') == './this/is_a/path/'
    assert ctf_utility.expand_path('~') == str(pathlib.Path.home())
    with patch.dict(os.environ, {'myvar': 'foo/bar'}):
        assert ctf_utility.expand_path('$myvar/dir') == 'foo/bar/dir'
        assert ctf_utility.expand_path('~/$myvar/path') == str(pathlib.Path.home()) + '/foo/bar/path'


def test_ctf_utility_switch_to_cft_directory():
    cur_dir = os.getcwd()
    dir = ctf_utility.switch_to_cft_directory()
    assert 'anaconda3/envs/pythonEnv3/bin' in dir
    # restore run dir
    os.chdir(cur_dir)


def test_ctf_utility_get_current_instruction_index():
    assert ctf_utility.get_current_instruction_index() is None


def test_ctf_utility_set_goto_instruction_index():
    assert Global.goto_instruction_index is None
    assert ctf_utility.set_goto_instruction_index(1) is None
    assert Global.goto_instruction_index == 1
    Global.goto_instruction_index = None


def test_ctf_utility_resolve_variable():
    assert ctf_utility.set_variable('var_1', '=', 100)
    assert ctf_utility.resolve_variable('var_1') == 'var_1'
    assert ctf_utility.resolve_variable('$var_1$') == 100
    assert ctf_utility.resolve_variable('A$var_1$B') == 'A100B'
    Global.variable_store.clear()


def test_ctf_utility_resolve_variable_exception(utils):
    with pytest.raises(CtfParameterError):
        utils.clear_log()
        ctf_utility.resolve_variable('$var_1$')
        assert utils.has_log_level('ERROR')

    with pytest.raises(CtfParameterError):
        utils.clear_log()
        ctf_utility.resolve_variable('123$var_1$')
        assert utils.has_log_level('ERROR')


def test_ctf_utility_set_variable_pass():
    assert ctf_utility.set_variable('var_1', '=', 100)
    assert ctf_utility.set_variable('var_2', '=', 100)
    assert ctf_utility.set_variable('var_2', '<', 100)
    Global.variable_store.clear()


def test_ctf_utility_set_variable_cast():
    assert ctf_utility.set_variable('var_1', '=', 1)
    assert ctf_utility.set_variable('var_1', '+', "10")
    assert ctf_utility.set_variable('var_1', '-', "10.0")
    assert ctf_utility.set_variable('var_1', '<', "100")
    assert ctf_utility.set_variable('var_1', '==', 1)
    assert ctf_utility.get_variable('var_1') == 1
    Global.variable_store.clear()


def test_ctf_utility_set_variable_specify_type():
    assert ctf_utility.set_variable('var_1', '=', "1")
    assert isinstance(ctf_utility.get_variable('var_1'), str)
    assert ctf_utility.set_variable('var_1', '=', "1", "int")
    assert isinstance(ctf_utility.get_variable('var_1'), int)
    assert ctf_utility.set_variable('var_1', '=', "1", "string")
    assert isinstance(ctf_utility.get_variable('var_1'), str)
    assert ctf_utility.set_variable('var_1', '=', "1", "boolean")
    assert isinstance(ctf_utility.get_variable('var_1'), bool)
    assert ctf_utility.set_variable('var_1', '=', "1", "float")
    assert isinstance(ctf_utility.get_variable('var_1'), float)
    assert ctf_utility.get_variable('var_1') == 1.0
    assert ctf_utility.set_variable('var_1', '+', "10")
    assert ctf_utility.get_variable('var_1') == 11.0
    assert isinstance(ctf_utility.get_variable('var_1'), float)
    Global.variable_store.clear()


def test_ctf_utility_set_variable_cast_fail(utils):
    assert ctf_utility.set_variable('var_1', '=', 1.0)
    assert not ctf_utility.set_variable('var_1', '+', "ten")
    assert ctf_utility.set_variable('var_1', '==', "1")
    assert ctf_utility.get_variable('var_1') == 1
    assert utils.has_log_level('ERROR')
    Global.variable_store.clear()


def test_ctf_utility_set_variable_fail(utils):
    utils.clear_log()
    assert not ctf_utility.set_variable('var_1', '?', 100)
    assert not ctf_utility.set_variable('var_2', '<', 100)
    assert utils.has_log_level('ERROR')
    Global.variable_store.clear()


def test_ctf_utility_set_variable_invalid_type(utils):
    utils.clear_log()
    assert not ctf_utility.set_variable('var_1', '=', 100, 'list')
    assert utils.has_log_level('ERROR')
    Global.variable_store.clear()


def test_ctf_utility_set_variable_exception(utils):
    utils.clear_log()
    assert not ctf_utility.set_variable('var_1', '=', 's12', 'int')
    assert utils.has_log_level('ERROR')
    Global.variable_store.clear()


def test_ctf_utility_get_variable():
    assert ctf_utility.get_variable('var_1') is None
    assert ctf_utility.set_variable('var_1', '=', 100)
    assert ctf_utility.get_variable('var_1') == 100
    Global.variable_store.clear()
