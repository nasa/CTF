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
import os
import sys
import re
import tempfile
from unittest.mock import patch, Mock

import pytest

from lib.xmltodict import _DictSAXHandler, ParsingInterrupted, parse

@pytest.fixture(name="xtd")
def _xmltodict_instance():
    return _DictSAXHandler()


@pytest.fixture(name="xtd_callback")
def _xmltodict_instance_callback():
    return _DictSAXHandler(item_callback=lambda *args: False)


def test_xmltodict_build_name(xtd):
    # namespaces (defaults to empty)
    full_name = 'FullName'
    assert xtd._build_name(full_name) == full_name

    # namespaces is not empty; full_name does not contain a namespace
    xtd.namespaces = {'Namespace': 'ShortName'}
    full_name = 'FullName'
    assert xtd._build_name(full_name) == full_name

    # full_name contains a namespace that's in the namespaces dictionary
    xtd.namespaces = {'Namespace1': 'ShortName1', 'Namespace2': 'ShortName2'}
    full_name = 'Namespace1:FullName'
    assert xtd._build_name(full_name) == 'ShortName1:FullName'

    # full_name contains a namespace that's not in the namespaces dictionary
    xtd.namespaces = {'Namespace1': 'ShortName1', 'Namespace2': 'ShortName2'}
    full_name = 'Namespace0:FullName'
    assert xtd._build_name(full_name) == full_name

    # full_name contains an empty namespace
    xtd.namespaces = {'Namespace1': 'ShortName1', 'Namespace2': 'ShortName2'}
    full_name = ':FullName'
    assert xtd._build_name(full_name) == 'FullName'


def test_xmltodict_start_namespace_decl(xtd):
    xtd.namespace_declarations = {}
    xtd.start_namespace_decl(prefix='Prefix', uri='Uri')
    assert xtd.namespace_declarations == {'Prefix': 'Uri'}

    xtd.namespace_declarations = {}
    xtd.start_namespace_decl(prefix=None, uri='Uri')
    assert xtd.namespace_declarations == {'': 'Uri'}


def test_xmltodict_start_element(xtd):
    full_name = 'FullName'
    attrs = {'a':'b'}
    xtd.namespace_declarations = {'Prefix': 'Uri'}
    xtd.start_element(full_name, attrs)
    assert attrs['xmlns'] == {'Prefix': 'Uri'}
    assert xtd.namespace_declarations == {}

    # xml_attribs is False
    xtd.namespace_declarations = None
    xtd.path = ['path']
    xtd.item_depth = 1
    xtd.xml_attribs = False
    xtd.item = {'a': 'b'}
    xtd.start_element(full_name, attrs)
    assert xtd.item == None

    # post_processor is not None
    def postprocessor(path, key, data):
        return path[0] + '_' + key, path[0] + '_' + data

    xtd.postprocessor = postprocessor
    xtd.namespace_declarations = None
    xtd.attr_prefix = ''
    xtd.path = ['path']
    xtd.item_depth = 1
    xtd.xml_attribs = True
    item = {}
    attrs = {'a':'b'}
    xtd.start_element(full_name, attrs)
    assert xtd.item == {'path_a': 'path_b'}


def test_xmltodict_end_element_ParsingInterupted(xtd_callback):
    xtd_callback.path = []
    xtd_callback.item_depth = 0
    xtd_callback.item = None
    xtd_callback.data = None
    full_name = 'FullName'

    with pytest.raises(ParsingInterrupted):
        xtd_callback.end_element(full_name)


def test_xmltodict_end_element(xtd):
    xtd.path = ['path']
    xtd.item_depth = 0
    xtd.item = None
    xtd.data = None
    xtd.stack = None
    full_name = 'FullName'

    xtd.end_element(full_name)
    assert xtd.item == None
    assert xtd.data == []
    assert xtd.path == []

    # push_data; item is not None
    xtd.item_depth = 2
    xtd.item = None
    xtd.stack = [({'a': 'b'}, ['c'])]
    xtd.data = 'data'
    xtd.force_cdata = True
    xtd.path = ['d']
    xtd.end_element(full_name)
    assert xtd.item == {'FullName': {'#text': 'data'}, 'a': 'b'}
    assert xtd.data == ['c']

    # push_data; item is None
    xtd.item_depth = 2
    xtd.item = None
    xtd.stack = [({'a': 'b'}, ['c'])]
    xtd.data = ''
    xtd.force_cdata = True
    xtd.path = ['d']
    xtd.end_element(full_name)
    assert xtd.item == {'FullName': None, 'a': 'b'}
    assert xtd.data == ['c']


def test_xmltodict_comments(xtd):
    data = ' with whitespace '
    xtd.strip_whitespace = False
    xtd.comments(data)
    assert xtd.item == {'#comment': ' with whitespace '}

    xtd.item = {}
    xtd.strip_whitespace = True
    xtd.comments(data)
    assert xtd.item == {'#comment': 'with whitespace'}


def test_xmltodict_push_data_postprocessor(xtd):
    def postprocessor(path, key, data):
        return key + '_pp_', data + '_pp_'

    xtd.postprocessor = postprocessor
    item = {}
    key = 'key'
    data = 'data'
    assert xtd.push_data(item, key, data) == {key + '_pp_': data + '_pp_'}


def test_xmltodict_push_data_postprocessor_return_none(xtd):
    def postprocessor(path, key, data):
        return None

    xtd.postprocessor = postprocessor
    item = {'a': 'b'}
    key = 'key'
    data = 'data'
    assert xtd.push_data(item, key, data) == item


def test_xmltodict_push_data_key_error(xtd):
    item = {}
    key = 'key'
    data = 'data'
    xtd.force_list = True
    assert xtd.push_data(item, key, data) == {key: [data]}


def test_xmltodict_should_force_list(xtd):
    key = 'key'
    value = 'value'
    xtd.force_list = True
    assert xtd._should_force_list(key, value) == True

    xtd.force_list = [key]
    assert xtd._should_force_list(key, value) == True

    xtd.force_list = 5
    xtd.path = 'path'
    key = 'key'

    with pytest.raises(TypeError):
        assert xtd._should_force_list(key, value) == False


def test_xmltodict_parse():
    # Convert unicode XML input to utf-8 encoding when no encoding specified
    xml_input_unicode = u'\u003C\u0061\u003E\u003C\u0062\u003E\u003C\u0021\u002D\u002D\u0020\u0062\u0020\u0063\u006F\u006D\u006D\u0065\u006E\u0074\u0020\u002D\u002D\u003E\u003C\u0063\u003E\u003C\u0021\u002D\u002D\u0020\u0063\u0020\u0063\u006F\u006D\u006D\u0065\u006E\u0074\u0020\u002D\u002D\u003E\u0031\u003C\u002F\u0063\u003E\u003C\u0064\u003E\u0032\u003C\u002F\u0064\u003E\u003C\u002F\u0062\u003E\u003C\u002F\u0061\u003E'
    assert parse(xml_input_unicode, encoding=None) == {'a': {'b': {'c': '1', 'd': '2', }, }}

    # Include comments in parsed XML
    xml_input = '<a><b><!-- b comment --><c><!-- c comment -->1</c><d>2</d></b></a>'
    assert parse(xml_input, process_comments=True) == {'a': {'b': {'#comment': 'b comment', 'c': {'#comment': 'c comment', '#text': '1', }, 'd': '2', }, }}

    # XML input is a file descriptor
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', encoding='utf-8', delete=False) as tmp:
        tmp.write(xml_input)
        tmp.close()
        with open(tmp.name, 'rb') as fd:
            assert parse(fd) == {'a': {'b': {'c': '1', 'd': '2', }, }}

    os.remove(tmp.name)

    # XML separated by a generator function
    def get_xml_generator(xml_string):
        xml_array = xml_string.splitlines()
        index = 0

        while index < len(xml_array):
            yield xml_array[index]
            index += 1

    xml_input_iter = '<a>\n<b>\n<!-- b comment -->\n<c>\n<!-- c comment -->\n1\n</c>\n<d>\n2\n</d>\n</b>\n</a>'
    assert parse(get_xml_generator(xml_input_iter)) == {'a': {'b': {'c': '1', 'd': '2', }, }}
