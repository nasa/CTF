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

from plugins.ccsds_plugin.cfe.ccsds_secondary_header import CcsdsSecondaryCmdHeader


@pytest.fixture(name="secondary_header")
def _ccsds_secondarycmdheader_instance():
    return CcsdsSecondaryCmdHeader()


def test_ccsdssecondarycmdheader_init(secondary_header):
    """
    Test CcsdsSecondaryCmdHeader class attributes
    """
    assert CcsdsSecondaryCmdHeader._pack_ == 1
    assert len(CcsdsSecondaryCmdHeader._fields_) == 2
    assert secondary_header.checksum == 0
    assert secondary_header.function_code == 0


def test_ccsdssecondarycmdheader_function_code(secondary_header):
    """
    Test CcsdsSecondaryCmdHeader class method: set_function_code & get_function_code
    Sets the function code field
    """
    assert secondary_header.set_function_code(2) is None
    assert secondary_header.get_function_code() == 2

    with pytest.raises(TypeError):
        secondary_header.set_function_code(1.1)

    with pytest.raises(TypeError):
        secondary_header.set_function_code(-12.3)

    with pytest.raises(TypeError):
        secondary_header.set_function_code("15")

    with pytest.raises(TypeError):
        secondary_header.set_function_code([10])

    assert secondary_header.get_function_code() == 2

    # test ("function_code", ctypes.c_uint8), overflow
    secondary_header.set_function_code(257)
    assert secondary_header.get_function_code != 257


def test_ccsdssecondarycmdheader_checksum(secondary_header):
    """
    Test CcsdsSecondaryCmdHeader class method: set_checksum & get_checksum
    Sets/Gets the checksum field
    """
    assert secondary_header.set_checksum(2) is None
    assert secondary_header.get_checksum() == 2

    with pytest.raises(TypeError):
        secondary_header.set_checksum(5.2)

    with pytest.raises(TypeError):
        secondary_header.set_checksum(-111.3)

    with pytest.raises(TypeError):
        secondary_header.set_checksum("24")

    with pytest.raises(TypeError):
        secondary_header.set_checksum([100])

    assert secondary_header.get_checksum() == 2

    # test ("checksum", ctypes.c_uint8), overflow
    secondary_header.set_checksum(258)
    assert secondary_header.get_checksum != 258
