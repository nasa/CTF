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
from unittest.mock import Mock, patch

import pytest

from lib.exceptions import CtfConditionError, CtfTestError
from plugins.cfs.cfs_time_manager import CfsTimeManager


@pytest.fixture(scope="session", autouse=True)
def init_global():
    from lib.ctf_global import Global
    Global.load_config("./configs/default_config.ini")


@pytest.fixture(name='time_mgr')
def cfs_time_manager():
    return CfsTimeManager({"mock": Mock()})


def test_init(time_mgr):
    assert time_mgr.ctf_verification_poll_period == 0.5
    assert len(time_mgr.cfs_targets) == 1


def test_handle_exception_during_wait(time_mgr, caplog):
    caplog.set_level(logging.ERROR)
    with pytest.raises(ValueError):
        time_mgr.handle_test_exception_during_wait(ValueError("ERROR"), "error message", True)
    assert "error message" in caplog.text
    time_mgr.handle_test_exception_during_wait(ValueError("ERROR"), "warning message", False)
    assert "warning message" in caplog.text


@patch("plugins.cfs.cfs_time_manager.CfsTimeManager.pre_command")
@patch("plugins.cfs.cfs_time_manager.CfsTimeManager.post_command")
@patch("plugins.cfs.cfs_time_manager.CfsTimeManager.handle_test_exception_during_wait")
def test_wait(mock_handle, mock_post, mock_pre, time_mgr):
    with patch("time.sleep") as mock_sleep:
        wait_time = 1.25
        time_mgr.wait(wait_time)
        # wait will take seconds / poll period cycles rounded up
        cycles = -(- wait_time // time_mgr.ctf_verification_poll_period)
        assert mock_pre.call_count == cycles
        assert mock_post.call_count == cycles
        assert mock_sleep.call_count == cycles
        mock_handle.assert_not_called()
        assert time_mgr.exec_time == cycles * time_mgr.ctf_verification_poll_period


@patch("plugins.cfs.cfs_time_manager.CfsTimeManager.pre_command")
@patch("plugins.cfs.cfs_time_manager.CfsTimeManager.handle_test_exception_during_wait")
def test_wait_exception(mock_handle, mock_pre, time_mgr):
    wait_time = 0.25
    with patch('plugins.cfs.cfs_time_manager.CfsTimeManager.post_command') as mock_post_command:
        mock_post_command.side_effect = CtfTestError('Mock post_command call')
        time_mgr.wait(wait_time)
    # wait will take seconds / poll period cycles rounded up
    cycles = -(- wait_time // time_mgr.ctf_verification_poll_period)
    assert mock_pre.call_count == cycles
    assert time_mgr.exec_time == cycles * time_mgr.ctf_verification_poll_period


def test_wait_read_error(time_mgr):
    with patch("time.sleep") as mock_sleep:
        time_mgr.cfs_targets['mock'].cfs.read_sb_packets.side_effect = IOError('Mock error')
        with pytest.raises(CtfTestError):
            time_mgr.wait(1)
        # errors are raised before sleeping
        mock_sleep.assert_not_called()
        assert time_mgr.exec_time == 0


def test_wait_verification_error(time_mgr):
    with patch("time.sleep") as mock_sleep:
        time_mgr.cfs_targets['mock'].cfs.check_tlm_conditions.side_effect = \
            [CtfConditionError('Mock error', None), CtfTestError('Mock error')]
        with pytest.raises(CtfConditionError):
            time_mgr.wait(1)
        # errors are raised before sleeping
        mock_sleep.assert_not_called()
        assert time_mgr.exec_time == 0

        with pytest.raises(CtfTestError):
            time_mgr.wait(1)
        # errors are raised before sleeping
        mock_sleep.assert_not_called()
        assert time_mgr.exec_time == 0


def test_pre_command(time_mgr):
    time_mgr.pre_command()
    [target.cfs.read_sb_packets.assert_called_once() for target in time_mgr.cfs_targets.values()]
    [target.cfs.check_tlm_conditions.assert_called_once() for target in time_mgr.cfs_targets.values()]


def test_run_continuous_verifications(time_mgr):
    time_mgr.run_continuous_verifications()
    [target.cfs.check_tlm_conditions.assert_called_once() for target in time_mgr.cfs_targets.values()]
