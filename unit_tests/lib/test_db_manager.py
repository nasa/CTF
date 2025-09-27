# =========================================================================================
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
# distributed and modified only pursuant to the terms of that agreement.
# See the License for the specific language governing permissions and limitations under the
# License at https://software.nasa.gov/ .
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either expressed or implied.
#
# Copyright © 2019-2025 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# File: test_db_manager.py
#
# Purpose: This file contains test cases for unit testing of utility functions to manage sqlite database.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================


import pytest
import datetime

from lib.db_manager import DBManager

DB_FILE_NAME = "ctf_test_db_manager.db"

@pytest.fixture(name="db_manager")
def __db_manager_instance():
    return DBManager(db_file_name=DB_FILE_NAME)

# Test teardown to clear tables after each test run
@pytest.fixture(autouse=True)
def test_teardown(db_manager):
    yield
    db_manager.db_table_manager.empty_tables()

def get_manager_instance(db_file_name):
    return DBManager(db_file_name)

def test_db_manager_init(db_manager):
    """
    Test DBManager class constructor
    Verify all the tables are initialized
    """
    db_tbl_mgr = db_manager.db_table_manager
    assert db_tbl_mgr.readall("cmd") != None
    assert db_tbl_mgr.readall("tlm") != None
    assert db_tbl_mgr.readall("event") != None

    assert not db_manager.background_thread.is_alive()
    
def test_db_manager_start_background_logging_task(db_manager):
    """
    Test DBManager class method: start_background_logging_task
    Calls method and verifies expected behavior 
    """
    # Act
    is_started = db_manager.start_background_logging_task()

    # Assert
    assert is_started == True
    assert db_manager.run_logging_task == True
    assert db_manager.background_thread.is_alive()
    # stop background task to clean test setting
    db_manager.stop_background_logging_task()


def test_db_manager_start_background_logging_task_repeated_start(db_manager):
    """
    Test DBManager class method: start_background_logging_task
    """
    # Act
    first_start = db_manager.start_background_logging_task()
    second_start = db_manager.start_background_logging_task()

    assert first_start == True
    assert second_start == False
    # stop background task to clean test setting
    db_manager.stop_background_logging_task()


def test_db_manager_start_background_logging_task_restart(db_manager):
    """
    Test DBManager class method: start_background_logging_task
    Start background logging, then stop, and attempt to restart
    Verify failure to restart since thread object can only be started once.
    """
    # Act
    first_start = db_manager.start_background_logging_task()
    second_start = db_manager.start_background_logging_task()
    db_manager.stop_background_logging_task()
    restart = db_manager.start_background_logging_task()

    assert first_start == True
    assert second_start == False
    assert restart == False

def test_db_stop_background_logging_task(db_manager):
    """
    Test DBManager class method: stop_background_logging_task
    Starts background logging task, stops it, and verifies state. 
    """
    # Arrange
    db_manager.start_background_logging_task()

    # Act 
    db_manager.stop_background_logging_task()

    # Assert
    assert db_manager.run_logging_task == False
    assert not db_manager.background_thread.is_alive()


def test_run_ctf_background_db_task(db_manager):
    """
    Test db_manager global method: run_ctf_background_db_task
    Start the background task, insert data into the queues, 
    and verify the data is consumed by the background task. 
    """
    # Arrange
    db_manager.start_background_logging_task()

    # Populate queues
    num_cmds = 100000
    for i in range(0, num_cmds):
        timestamp = datetime.datetime.now() + datetime.timedelta(milliseconds=i)
        db_manager.log_cmd(timestamp, "target_1", 1, "header", "payload")

    num_tlm = 150000
    for i in range(0, num_tlm):
        timestamp = datetime.datetime.now() + datetime.timedelta(milliseconds=i)
        db_manager.log_tlm(timestamp, "target_1", 50, 1, "header", "payload", "formatted payload")

    num_events = 200000
    for i in range(0, num_events):
        timestamp = datetime.datetime.now() + datetime.timedelta(milliseconds=i)
        db_manager.log_event(timestamp, "target_1", 50, 1, "header", "payload", "formatted payload",
                             "SBNG", 10, 2, "Event Message")
        
    # Send termination signal
    db_manager.stop_background_logging_task()

    # Verify queues are fully consumed
    assert db_manager.cmd_queue.empty()
    assert db_manager.tlm_queue.empty()
    assert db_manager.event_queue.empty()

    # Verify all data was written to db table object
    db_tbl_mgr = db_manager.db_table_manager
    assert len(db_tbl_mgr.readall("cmd")) == num_cmds
    assert len(db_tbl_mgr.readall("tlm")) == num_tlm
    assert len(db_tbl_mgr.readall("event")) == num_events

    # Verify all data is persisted to disk by closing and re-establishing connection
    db_tbl_mgr.db_conn.close()
    db_tbl_mgr.db_conn.connect(DB_FILE_NAME)
    assert len(db_tbl_mgr.readall("cmd")) == num_cmds
    assert len(db_tbl_mgr.readall("tlm")) == num_tlm
    assert len(db_tbl_mgr.readall("event")) == num_events

def test_db_manager_log_cmd(db_manager):
    """
    Test DBManager static method: log_cmd
    Adds command info into the queue and verifies. 
    """
    # Arrange
    test_row = (datetime.datetime.now(), "target_1", 1, "header", "payload")

    # Act
    db_manager.log_cmd(test_row[0], test_row[1], test_row[2], test_row[3], test_row[4])

    # Assert
    assert db_manager.cmd_queue.get() == test_row

def test_db_manager_log_tlm(db_manager):
    """
    Test DBManager static method: log_tlm
    Adds tlm info into the queue and verifies. 
    """
    # Arrange
    test_row = (datetime.datetime.now(), "target_1", 50, 1, "header", "payload", "formatted payload")

    # Act
    db_manager.log_tlm(test_row[0], test_row[1], test_row[2], test_row[3], 
                       test_row[4], test_row[5], test_row[6])

    # Assert
    assert db_manager.tlm_queue.get() == test_row

def test_db_manager_log_event(db_manager):
    """
    Test DBManager static method: log_event
    Adds event info into the queue and verifies. 
    """
    # Arrange
    test_row = (datetime.datetime.now(), "target_1", 50, 1, "header", "payload", 
                "formatted payload", "SBNG", 1, 1, "Event Message")

    # Act
    db_manager.log_event(test_row[0], test_row[1], test_row[2], 
                         test_row[3], test_row[4], test_row[5], 
                         test_row[6], test_row[7], test_row[8], 
                         test_row[9], test_row[10])

    # Assert
    assert db_manager.event_queue.get() == test_row
