# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2023 United States Government as represented by the
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
import pytest
from unittest.mock import patch

from lib import ctf_utility
from lib.ctf_global import Global
from lib.ctf_utility import resolve_dic_variable
from lib.exceptions import CtfParameterError


def test_ctf_utility_expand_path():
    assert ctf_utility.expand_path('') == ''
    assert ctf_utility.expand_path('dir') == 'dir'
    assert ctf_utility.expand_path('./this/is_a/path/') == './this/is_a/path/'
    assert ctf_utility.expand_path('~') == str(pathlib.Path.home())
    with patch.dict(os.environ, {'myvar': 'foo/bar'}):
        assert ctf_utility.expand_path('$myvar/dir') == 'foo/bar/dir'
        assert ctf_utility.expand_path('~/$myvar/path') == str(pathlib.Path.home()) + '/foo/bar/path'


def test_ctf_utility_switch_to_ctf_directory():
    cur_dir = os.getcwd()
    ctf_dir = ctf_utility.switch_to_ctf_directory()
    # restore run dir
    os.chdir(cur_dir)
    assert 'bin' in ctf_dir


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


def test_ctf_utility_resolve_dic_variable():
    assert ctf_utility.set_variable('var_1', '=', 100)
    dict_obj = {1: '$var_1$', '$var_1$': 78}
    assert resolve_dic_variable(dict_obj) == {1: 100, 100: 78}
    dict_obj = [1, '$var_1$', 3]
    assert resolve_dic_variable(dict_obj) == [1, '$var_1$', 3]
    dict_obj = {1: '$var_1$', 2: [100, {1: 'a$var_1$', '$var_1$': 78}, {4: 4}]}
    assert resolve_dic_variable(dict_obj) == {1: 100, 2: [100, {1: 'a100', 100: 78}, {4: 4}]}
    Global.variable_store.clear()


def test_ctf_utility_set_variable_pass():
    assert ctf_utility.set_variable('var_1', '=', 100)
    assert ctf_utility.set_variable('var_2', '=', 100)
    assert ctf_utility.set_variable('var_2', '<', 100)
    Global.variable_store.clear()


def test_ctf_utility_set_variable_cast():
    assert ctf_utility.set_variable('var_1', '=', 1)
    assert ctf_utility.set_variable('var_1', '+', "0xa", "int")
    assert ctf_utility.set_variable('var_1', '-', "10.0", "float")
    assert ctf_utility.set_variable('var_1', '<', "100", "int")
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
    assert ctf_utility.set_variable('var_1', '+', "10", "float")
    assert ctf_utility.get_variable('var_1') == 11.0
    assert isinstance(ctf_utility.get_variable('var_1'), float)
    assert ctf_utility.set_variable('var_1', '=', "0xF3", "int")
    assert ctf_utility.get_variable('var_1') == 243
    assert ctf_utility.set_variable('var_1', '=', "0Xa1", "int")
    assert ctf_utility.get_variable('var_1') == 161
    assert ctf_utility.set_variable('var_1', '=', "12", "int")
    assert ctf_utility.get_variable('var_1') == 12
    assert ctf_utility.set_variable('var_1', '+', "0xA", "int")
    assert isinstance(ctf_utility.get_variable('var_1'), int)
    Global.variable_store.clear()


def test_ctf_utility_set_variable_cast_fail(utils):
    utils.clear_log()
    assert ctf_utility.set_variable('var_1', '=', 1.0)
    assert not ctf_utility.set_variable('var_1', '+', "ten")
    assert utils.has_log_level('ERROR')

    utils.clear_log()
    assert not ctf_utility.set_variable('var_1', '+', "ten", "int")
    assert utils.has_log_level('ERROR')

    assert ctf_utility.set_variable('var_1', '==', "1", "int")
    assert ctf_utility.get_variable('var_1') == 1
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
    utils.clear_log()

    assert not ctf_utility.set_variable('var_1', '=', 's12', 'float')
    assert utils.has_log_level('ERROR')

    assert ctf_utility.set_variable('var_1', '=', '1.0', 'float')
    assert not ctf_utility.set_variable('var_1', '+', 's1.0', 'float')
    Global.variable_store.clear()


def test_ctf_utility_get_variable():
    assert ctf_utility.get_variable('var_1') is None
    assert ctf_utility.set_variable('var_1', '=', 100)
    assert ctf_utility.get_variable('var_1') == 100
    Global.variable_store.clear()


def test_ctf_utility_set_nested_attr():
    class NestedObject:
        y = 1

    class TestObject:
        seq = "x"
        value = NestedObject()

    obj = TestObject()
    assert obj.value.y == 1
    assert ctf_utility.set_nested_attr(obj, 'value.y', 3) is None
    assert obj.value.y == 3


def test_ctf_utility_set_nested_attr_exception():
    class NestedObject:
        y = 1

    class TestObject:
        seq = "x"
        value = NestedObject()

    obj = TestObject()
    with pytest.raises(CtfParameterError):
        ctf_utility.set_nested_attr(obj, 'value', 3)


def test_ctf_utility_set_nested_attr_exception2():
    class NestedObject:
        y = 1

    obj = NestedObject()
    with pytest.raises(CtfParameterError):
        ctf_utility.set_nested_attr(obj, 'y.a', 3)
    with pytest.raises(CtfParameterError):
        ctf_utility.set_nested_attr(obj, 'x.a', 3)