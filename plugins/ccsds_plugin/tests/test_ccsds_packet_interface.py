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

import importlib
import os
import sys
from unittest.mock import patch
import pytest

from lib.exceptions import CtfTestError
from plugins.ccsds_plugin.ccsds_packet_interface import CcsdsVer, CcsdsPacketType, CcsdsPacketInterface, \
    import_ccsds_header_types


@pytest.fixture(name="packet_interface")
def _ccsds_ccsdspacketinterface_instance():
    return CcsdsPacketInterface()


def test_cccsds_packet_interface_ccsdsver():
    """
    Test CcsdsVer class attribute
    """
    assert CcsdsVer.Ccsds_ver_1 == 1
    assert CcsdsVer.Ccsds_ver_2 == 2
    assert CcsdsVer.Ccsds_ver_GW == 3


def test_cccsds_packet_interface_ccsdspacketype():
    """
    Test CcsdsPacketType class attribute
    """
    assert CcsdsPacketType.CommandPacket == 1
    assert CcsdsPacketType.TelemetryPacket == 0


def test_ccsdspacketinterface_get_msg_id(packet_interface):
    """
    Test CcsdsPacketInterface class method: get_msg_id
    Convenience method to get the message ID from the packet
    """
    with pytest.raises(NotImplementedError):
        packet_interface.get_msg_id()


def test_ccsdspacketinterface_set_msg_id(packet_interface):
    """
    Test CcsdsPacketInterface class method: set_msg_id
    Convenience method to set the message ID on the packet
    """
    with pytest.raises(NotImplementedError):
        packet_interface.set_msg_id(12345)


def test_ccsdspacketinterface_has_secondary_header(packet_interface):
    """
    Test CcsdsPacketInterface class method: has_secondary_header
    Convenience method to check for the presence of a secondary header
    """
    with pytest.raises(NotImplementedError):
        packet_interface.has_secondary_header()


def test_ccsdspacketinterface_get_function_code(packet_interface):
    """
    Test CcsdsPacketInterface class method: get_function_code
    Convenience method to get the function code from the packet
    """
    with pytest.raises(NotImplementedError):
        packet_interface.get_function_code()


def test_ccsdspacketinterface_set_function_code(packet_interface):
    """
    Test CcsdsPacketInterface class method: set_function_code
    Convenience method to set the function code on the packet
    """
    with pytest.raises(NotImplementedError):
        packet_interface.set_function_code(98765)


def test_ccsds_packet_interface_import_ccsds_header_types():
    """
    Test import_ccsds_header_types function
    Dynamically imports the appropriate CCSDS primary header, command, and telemetry types from the location given
    in the config value 'CCSDS_header_path' and if found, returns them in a tuple.
    """
    header_types = import_ccsds_header_types()
    assert len(header_types) == 3
    assert header_types[0].__name__ == 'CcsdsV2PrimaryHeader'
    assert header_types[1].__name__ == 'CcsdsV2CmdPacket'
    assert header_types[2].__name__ == 'CcsdsV2TlmPacket'


def test_ccsds_packet_interface_import_ccsds_header_types_module_attributes():
    """
    Test import_ccsds_header_types function: check missing module attributes
    Dynamically imports the appropriate CCSDS primary header, command, and telemetry types from the location given
    in the config value 'CCSDS_header_path' and if found, returns them in a tuple.
    """
    headers_path = "./plugins/ccsds_plugin/cfe/ccsds_v2/ccsds_v2.py"
    sys.path.append(os.path.dirname(headers_path))
    headers_module = importlib.import_module(os.path.basename(headers_path).replace(".py", ""))
    # test case: if headers_module does not have required attributes, return None
    del headers_module.CcsdsTelemetry
    assert import_ccsds_header_types() is None
    del headers_module.CcsdsCommand
    assert import_ccsds_header_types() is None
    del headers_module.CcsdsPrimaryHeader
    assert import_ccsds_header_types() is None

    # restore class attributes
    importlib.reload(headers_module)
    assert len(import_ccsds_header_types()) == 3


def test_ccsds_packet_interface_import_ccsds_header_types_class_attributes():
    """
    Test import_ccsds_header_types function:
    check whether class methods (is_command/get_function_code/get_msg_id) are implemented
    Dynamically imports the appropriate CCSDS primary header, command, and telemetry types from the location given
    in the config value 'CCSDS_header_path' and if found, returns them in a tuple.
    """
    headers_path = "./plugins/ccsds_plugin/cfe/ccsds_v2/ccsds_v2.py"
    sys.path.append(os.path.dirname(headers_path))
    headers_module = importlib.import_module(os.path.basename(headers_path).replace(".py", ""))

    ccsds_telemetry = getattr(sys.modules['ccsds_v2'], "CcsdsTelemetry")
    setattr(ccsds_telemetry, 'get_msg_id', None)
    assert import_ccsds_header_types() is None

    ccsds_command = getattr(sys.modules['ccsds_v2'], "CcsdsCommand")
    setattr(ccsds_command, 'get_function_code', None)
    assert import_ccsds_header_types() is None

    ccsds_primary_header = getattr(sys.modules['ccsds_v2'], "CcsdsPrimaryHeader")
    print("in test ccsds_primary_header=", ccsds_primary_header)
    setattr(ccsds_primary_header, 'is_command', None)
    assert import_ccsds_header_types() is None

    # restore class attributes
    importlib.reload(headers_module)
    assert import_ccsds_header_types() is not None


def test_ccsds_packet_interface_import_ccsds_header_types_exception():
    """
    Test import_ccsds_header_types function: raise exception
    Dynamically imports the appropriate CCSDS primary header, command, and telemetry types from the location given
    in the config value 'CCSDS_header_path' and if found, returns them in a tuple.
    """
    with patch("os.path.exists", return_value=False):
        assert import_ccsds_header_types() is None

    with pytest.raises(CtfTestError):
        with patch("importlib.import_module") as mock_import_module:
            mock_import_module.side_effect = CtfTestError("Raise import_module exception for unit test")
            assert import_ccsds_header_types() is None
