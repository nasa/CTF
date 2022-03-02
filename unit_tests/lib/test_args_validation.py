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

import logging
from unittest.mock import patch
import pytest
from mock import Mock

from lib.args_validation import ArgsValidation


@pytest.fixture(name="argsval")
def args_validation():
    return ArgsValidation()


def test_init(argsval):
    assert argsval.parameter_errors == 0, "Initialized with no errors"


def test_add_error(caplog, argsval):
    caplog.set_level(logging.DEBUG)
    assert argsval.parameter_errors == 0, "Start with no errors"
    argsval.add_error("foo", ValueError("My Value"))
    assert argsval.parameter_errors == 1, "Error count increased by 1"
    assert "My Value" in caplog.text, "My Value has been logged"


def test_get_error_count(argsval):
    argsval.add_error("foo")
    assert argsval.get_error_count() == argsval.parameter_errors, "Error count is returned"


def test_is_param_none(argsval):
    assert argsval.is_param_none(None), "None is None"
    assert not argsval.is_param_none(0), "0 is not None"


def test_increment_error_count(argsval):
    before_count = argsval.get_error_count()
    argsval.increment_error_count()
    assert argsval.get_error_count() == before_count + 1, "Error count has been incremented"


def test_verify_symbol_none(argsval):
    assert not argsval.verify_symbol("", None)


def test_verify_symbol_no_file(argsval):
    assert not argsval.verify_symbol("no_file", "symbol")


def test_verify_symbol_no_section(argsval):
    with patch("lib.args_validation.ELFFile") as mock_elf:
        mock_elf.return_value.get_section_by_name.side_effect = [False]
        assert not argsval.verify_symbol("ctf", "symbol")


def test_verify_symbol_symbol(argsval):
    with patch("lib.args_validation.ELFFile") as mock_elf, \
            patch("lib.args_validation.isinstance", return_value=True):
        mock_section = Mock()
        mock_symbols = Mock()
        mock_symbols.name = "symbol2"
        mock_section.iter_symbols.side_effect = [[mock_symbols, mock_symbols]]
        mock_elf.return_value.get_section_by_name.side_effect = [mock_section]
        assert not argsval.verify_symbol("ctf", "symbol")


def test_validate_symbol_path_none(argsval):
    with patch("lib.args_validation.ArgsValidation.validate_file", return_value=None):
        assert argsval.validate_symbol("symbol", "./") is None

    with patch("lib.args_validation.ArgsValidation.validate_file", return_value="./"), \
         patch("lib.args_validation.ArgsValidation.verify_symbol", return_value=True):
        assert argsval.validate_symbol("symbol", "./") == "symbol"

    with patch("lib.args_validation.ArgsValidation.validate_file", return_value="./"), \
         patch("lib.args_validation.ArgsValidation.verify_symbol", return_value=False):
        assert argsval.validate_symbol("symbol", "./") is None


def test_validate_file(argsval, caplog):
    with patch("os.path.isfile") as isfile:
        isfile.side_effect = [True, False, False]
        assert argsval.validate_file("a/valid/path") == "a/valid/path", "Valid path is returned"
        assert argsval.get_error_count() == 0, "No errors captured"
        assert argsval.validate_file(
            "a/missing/path") == "a/missing/path", "Missing path is returned and warning is logged"
        assert argsval.get_error_count() == 0, "No errors captured"
        assert any(record.levelname == "WARNING" for record in caplog.records), "Warning was logged"
        assert argsval.validate_file("an/invalid/path",
                                     True) is None, "Invalid path is not returned and error is logged"
        assert argsval.get_error_count() == 1, "Error was captured"


def test_validate_directory(argsval, caplog):
    caplog.set_level(logging.WARN)
    assert argsval.validate_directory("./plugins") == "./plugins", "Valid directory is validated"
    assert "Directory does not exist" not in caplog.text, "Error was not logged"
    assert argsval.validate_directory("./foo") is None, "Invalid directory is not validated"
    assert "Directory does not exist" in caplog.text, "Error was logged"


def test_validate_number(argsval, caplog):
    assert argsval.validate_number("3.14") == 3.14
    assert argsval.parameter_errors == 0
    assert argsval.validate_number("pi") is None
    assert argsval.parameter_errors == 1
    assert "Number (float)" in caplog.text


def test_validate_int(argsval, caplog):
    assert argsval.validate_int("10") == 10
    assert argsval.parameter_errors == 0
    assert argsval.validate_int("3.14") is None
    assert argsval.parameter_errors == 1


def test_validate_ip(argsval, caplog):
    assert argsval.validate_ip("127.0.0.1") == "127.0.0.1"
    assert argsval.parameter_errors == 0
    assert argsval.validate_ip("foo") is None
    assert argsval.parameter_errors == 1
    assert "IP" in caplog.text


def test_validate_boolean(argsval, caplog):
    assert argsval.validate_boolean(True)
    assert not argsval.validate_boolean(False)
    assert argsval.parameter_errors == 0
    assert argsval.validate_boolean(1) is None
    assert argsval.parameter_errors == 1
    assert "Boolean" in caplog.text
