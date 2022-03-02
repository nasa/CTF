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

from lib.exceptions import CtfTestError, CtfConditionError, CtfParameterError


@pytest.fixture(scope="session", autouse=True)
def init_logger():
    from lib.logger import logger
    logger.setLevel('DEBUG')


def test_ctftesterror(utils):
    e = CtfTestError('message')
    assert str(e) == 'message'
    assert utils.has_log_level('DEBUG')
    with pytest.raises(CtfTestError):
        raise e


def test_ctfconditionerror(utils):
    e = CtfConditionError('message', 'condition')
    assert str(e) == 'message'
    assert e.condition == 'condition'
    assert utils.has_log_level('DEBUG')
    with pytest.raises(CtfTestError):
        raise e


def test_ctfparametererror(utils):
    e = CtfParameterError('message', 'parameter')
    assert str(e) == 'message'
    assert e.parameter == 'parameter'
    assert utils.has_log_level('DEBUG')
    with pytest.raises(CtfTestError):
        raise e
