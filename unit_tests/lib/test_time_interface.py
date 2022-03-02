"""
@namespace lib.test_time_interface.py
Unit Test for TimeInterface: Interface definition for time managers to implement
"""
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

from lib.time_interface import TimeInterface


@pytest.fixture(name="time_interface_instance")
def _time_interface_instance():
    return TimeInterface()


def test_time_interface_init(time_interface_instance):
    """
    Test TimeInterface class constructor
    """
    assert time_interface_instance.exec_time == 0
    assert time_interface_instance.last_command_completion_time == 0
    assert time_interface_instance.time_since_last_command == 0


def test_time_interface_wait_seconds(time_interface_instance):
    """
    Test TimeInterface class static method: wait_seconds
    Helper utility to wait in seconds (OS Time)
    """
    assert TimeInterface.wait_seconds(1) is None


def test_time_interface_wait(time_interface_instance):
    """
    Test TimeInterface class method: wait
    Virtual method to wait an amount of time.
    """
    with pytest.raises(NotImplementedError):
        time_interface_instance.wait(1)


def test_time_interface_pre_command(time_interface_instance):
    """
    Test TimeInterface class method: pre_command
    Optional implementation of logic to be executed *before* a CTF instruction is invoked.
    It has no logic, just return
    """
    assert time_interface_instance.pre_command() is None


def test_time_interface_post_command(time_interface_instance):
    """
    Test TimeInterface class method: post_command
    Optional implementation of logic to be executed *after* a CTF instruction is invoked.
    It has no logic, just return
    """
    assert time_interface_instance.post_command() is None
