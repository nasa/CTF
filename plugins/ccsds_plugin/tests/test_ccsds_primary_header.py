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

from plugins.ccsds_plugin.ccsds_primary_header import CcsdsPrimaryHeaderBase


@pytest.fixture(name="primary_header_base")
def _ccsds_primaryheaderbase_instance():
    return CcsdsPrimaryHeaderBase()


def test_ccsdsprimaryheaderbase_init(primary_header_base):
    """
    Test CcsdsPrimaryHeaderBase class attributes
    """
    assert CcsdsPrimaryHeaderBase._pack_ == 1
    assert len(CcsdsPrimaryHeaderBase._fields_) == 7

    assert primary_header_base.version_number == 0
    assert primary_header_base.app_id == 0
    assert primary_header_base.secondary_header_flag == 0
    assert primary_header_base.sequence_count == 0
    assert primary_header_base.length == 0
    assert primary_header_base.type == 0


def test_ccsdsprimaryheaderbase_set_ccsds_version(primary_header_base):
    """
    Test CcsdsPrimaryHeaderBase class method: set_ccsds_version
    """
    assert primary_header_base.set_ccsds_version(2) is None
    assert primary_header_base.version_number == 2

    with pytest.raises(TypeError):
        primary_header_base.set_ccsds_version(1.1)

    with pytest.raises(TypeError):
        primary_header_base.set_ccsds_version(-12.3)

    with pytest.raises(TypeError):
        primary_header_base.set_ccsds_version("15")

    with pytest.raises(TypeError):
        primary_header_base.set_ccsds_version("15.5")

    assert primary_header_base.version_number == 2

    # test ctypes.c_uint16 overflow
    primary_header_base.set_ccsds_version(999999999999999)
    assert primary_header_base.version_number != 999999999999999


def test_ccsdsprimaryheaderbase_set_app_id(primary_header_base):
    """
    Test CcsdsPrimaryHeaderBase class method: set_app_id
    Sets the app ID field
    """
    assert primary_header_base.set_app_id(987) is None
    assert primary_header_base.app_id == 987

    with pytest.raises(TypeError):
        primary_header_base.set_app_id(11.1)

    with pytest.raises(TypeError):
        primary_header_base.set_app_id(-22.3)

    with pytest.raises(TypeError):
        primary_header_base.set_app_id("165")

    with pytest.raises(TypeError):
        primary_header_base.set_app_id("95.5")

    assert primary_header_base.app_id == 987

    # test ctypes.c_uint16 overflow
    primary_header_base.set_ccsds_version(899999999999999)
    assert primary_header_base.version_number != 899999999999999


def test_ccsdsprimaryheaderbase_set_secondary_header_flag(primary_header_base):
    """
    Test CcsdsPrimaryHeaderBase class method: set_secondary_header_flag
    Sets the secondary header flag field
    """
    assert primary_header_base.set_secondary_header_flag(1) is None
    assert primary_header_base.secondary_header_flag == 1

    assert primary_header_base.set_secondary_header_flag(0) is None
    assert primary_header_base.secondary_header_flag == 0

    with pytest.raises(TypeError):
        primary_header_base.set_secondary_header_flag(11.1)

    with pytest.raises(TypeError):
        primary_header_base.set_secondary_header_flag(-22.3)

    with pytest.raises(TypeError):
        primary_header_base.set_secondary_header_flag("165")

    with pytest.raises(TypeError):
        primary_header_base.set_secondary_header_flag("95.5")

    assert primary_header_base.secondary_header_flag == 0

    # test  ("secondary_header_flag", ctypes.c_uint16, 1) overflow
    primary_header_base.set_secondary_header_flag(10)
    assert primary_header_base.secondary_header_flag != 10


def test_ccsdsprimaryheaderbase_set_segmentation_flags(primary_header_base):
    """
    Test CcsdsPrimaryHeaderBase class method: set_segmentation_flags
    Sets the segmentation flags field
    """
    assert primary_header_base.set_segmentation_flags(1) is None
    assert primary_header_base.segmentation_flags == 1

    assert primary_header_base.set_segmentation_flags(0) is None
    assert primary_header_base.segmentation_flags == 0

    with pytest.raises(TypeError):
        primary_header_base.set_segmentation_flags(11.1)

    with pytest.raises(TypeError):
        primary_header_base.set_segmentation_flags(-22.3)

    with pytest.raises(TypeError):
        primary_header_base.set_segmentation_flags("165")

    with pytest.raises(TypeError):
        primary_header_base.set_segmentation_flags("95.5")

    assert primary_header_base.segmentation_flags == 0

    # test ("segmentation_flags", ctypes.c_uint16, 2) overflow
    primary_header_base.set_segmentation_flags(4)
    assert primary_header_base.segmentation_flags != 4


def test_ccsdsprimaryheaderbase_set_sequence_count(primary_header_base):
    """
    Test CcsdsPrimaryHeaderBase class method: set_sequence_count
    Sets the sequence count field
    """
    assert primary_header_base.set_sequence_count(100) is None
    assert primary_header_base.sequence_count == 100

    assert primary_header_base.set_sequence_count(7890) is None
    assert primary_header_base.sequence_count == 7890

    with pytest.raises(TypeError):
        primary_header_base.set_sequence_count(11.1)

    with pytest.raises(TypeError):
        primary_header_base.set_sequence_count(-22.3)

    with pytest.raises(TypeError):
        primary_header_base.set_sequence_count("165")

    with pytest.raises(TypeError):
        primary_header_base.set_sequence_count("95.5")

    assert primary_header_base.sequence_count == 7890

    # test ("sequence_count", ctypes.c_uint16, 14) overflow
    primary_header_base.set_sequence_count(99999999)
    assert primary_header_base.sequence_count != 99999999


def test_ccsdsprimaryheaderbase_set_packet_length(primary_header_base):
    """
    Test CcsdsPrimaryHeaderBase class method: set_packet_length
    Sets the packet length field
    """
    assert primary_header_base.set_packet_length(100) is None
    assert primary_header_base.length == 100

    assert primary_header_base.set_packet_length(7890) is None
    assert primary_header_base.length == 7890

    with pytest.raises(TypeError):
        primary_header_base.set_packet_length(11.1)

    with pytest.raises(TypeError):
        primary_header_base.set_packet_length(-22.3)

    with pytest.raises(TypeError):
        primary_header_base.set_packet_length("165")

    with pytest.raises(TypeError):
        primary_header_base.set_packet_length("95.5")

    assert primary_header_base.length == 7890

    # test ("length", ctypes.c_uint16, 16)  overflow
    primary_header_base.set_packet_length(99999999)
    assert primary_header_base.length != 99999999


def test_ccsdsprimaryheaderbase_packet_type(primary_header_base):
    """
    Test CcsdsPrimaryHeaderBase class method: set_packet_type & is_command
    Sets the packet length field
    """
    assert primary_header_base.set_packet_type(1) is None
    assert primary_header_base.is_command() == 1

    assert primary_header_base.set_packet_type(0) is None
    assert primary_header_base.is_command() == 0

    with pytest.raises(TypeError):
        primary_header_base.set_packet_type(11.2)

    with pytest.raises(TypeError):
        primary_header_base.set_packet_type(-22.3)

    with pytest.raises(TypeError):
        primary_header_base.set_packet_type("165")

    with pytest.raises(TypeError):
        primary_header_base.set_packet_type("95.5")

    # test ("type", ctypes.c_uint16, 1),  overflow
    primary_header_base.set_packet_type(3)
    assert primary_header_base.is_command() != 3


def test_ccsdsprimaryheaderbase_get_msg_id(primary_header_base):
    """
    Test CcsdsPrimaryHeaderBase class method: get_msg_id
    Returns the message ID value derived from the header fields
    """
    primary_header_base.set_packet_type(1)
    primary_header_base.set_ccsds_version(4)
    primary_header_base.set_secondary_header_flag(1)
    primary_header_base.set_app_id(9876)
    assert primary_header_base.get_msg_id() == 138900

    primary_header_base.set_packet_type(0)
    primary_header_base.set_ccsds_version(3)
    primary_header_base.set_secondary_header_flag(1)
    primary_header_base.set_app_id(789)
    assert primary_header_base.get_msg_id() == 101141
