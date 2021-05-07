"""
@namespace lib.test_time_manager.py
Unit Test for TimeManager: Default implementation for a minimal OS time manager.
"""
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2021 United States Government as represented by the
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

from lib.time_manager import TimeManager


@pytest.fixture(name="time_manager_instance")
def _time_manager_instance():
    return TimeManager()


def test_time_manager_init(time_manager_instance):
    """
    Test TimeManager class constructor
    """
    assert time_manager_instance.exec_time == 0
    assert time_manager_instance.last_command_completion_time == 0
    assert time_manager_instance.time_since_last_command == 0


def test_time_manager_wait(time_manager_instance):
    """
    Test TimeManager class wait method: Wait the specified number of seconds
    """
    assert time_manager_instance.wait(1) is None
    assert time_manager_instance.wait(0.5) is None


def test_time_manager_pre_command(time_manager_instance):
    """
    Test TimeManager class pre_command method:
    Optional implementation of logic to be executed *before* a CTF instruction is invoked.
    It has no logic, just return
    """
    assert time_manager_instance.pre_command() is None


def test_time_manager_post_command(time_manager_instance):
    """
    Test TimeManager class post_command method:
    Optional implementation of logic to be executed *after* a CTF instruction is invoked.
    It has no logic, just return
    """
    assert time_manager_instance.post_command() is None
