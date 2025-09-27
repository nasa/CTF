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
# File: test_db_table_manager.py
#
# Purpose: This file contains test cases for unit testing of utility functions to
#          manage sqlite database tables.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

import pytest

from lib.db_table_manager import DbTableManager, DbTable, DbConn

# DB Name and schema used for the test
DB_FILE_NAME = "ctf_test_db_table_manager.db"
tbl_name = "Telemetry"
tbl_hdr = "timestamp TEXT PRIMARY KEY NOT NULL, mid NUMERIC, data BLOB"

@pytest.fixture(name="db_conn")
def __db_conn_instance():
    return DbConn(DB_FILE_NAME)

@pytest.fixture(name="db_table")
def __db_table_instance(db_conn):
    return DbTable(db_conn, tbl_name, tbl_hdr)

@pytest.fixture(name="db_table_manager")
def __db_tbl_mgr_instance(db_conn, db_table):
    return DbTableManager(db_conn, [db_table])

# Clear tables after every test
@pytest.fixture(autouse=True)
def test_teardown(db_table_manager):
    yield
    db_table_manager.empty_tables()

def test_db_table_init(db_conn, db_table):
    """
    Test DbTable class constructor
    Verify table initialization
    """
    # Arrange
    validation_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='{}'".format(tbl_name)
    cursor = db_conn.execute(validation_query)

    # Assert
    assert len(cursor.fetchall()) == 1
    assert db_table.readall() != None
    assert len(db_table.readall()) == 0

def test_db_table_insert(db_table):
    # Arrange
    insert_row = ('timestamp', 1, "data blob")

    # Act
    result = db_table.insert(insert_row)

    # Assert
    assert result
    rows = db_table.readall()
    assert rows
    assert insert_row in rows

    # Verify data written to disk by closing and re-establishing connection
    db_table.db_conn.close()
    db_table.db_conn.connect(DB_FILE_NAME)

    # Assert
    rows = db_table.readall()
    assert rows
    assert insert_row in rows

def test_db_table_insert_invalid_entry(db_table):
    prev_db_table_state = db_table.readall()

    # Act
    invalid_insert_1 = db_table.insert(None)
    invalid_insert_2 = db_table.insert((None, 100, "valid data"))

    # Assert
    assert not invalid_insert_1
    assert not invalid_insert_2
    assert db_table.readall() == prev_db_table_state

def test_db_table_insert_many(db_table):
    # Arrange
    insert_rows = []
    insert_rows.append(('1', '', ''))
    insert_rows.append(('2', '', ''))
    insert_rows.append(('3', '', ''))

    # Act
    result = db_table.insert_many(insert_rows)

    # Assert
    assert result
    db_rows = db_table.readall()
    assert all(row in db_rows for row in insert_rows)

    # Verify data written to disk by closing and re-establishing connection
    db_table.db_conn.close()
    db_table.db_conn.connect(DB_FILE_NAME)

    # Assert
    db_rows = db_table.readall()
    assert all(row in db_rows for row in insert_rows)

def test_db_table_empty(db_table):
    # Arrange
    db_table.insert((1, "", ""))
    db_table.insert((2, "", ""))

    # Act
    db_table.empty()

    # Assert
    assert len(db_table.readall()) == 0

def test_db_table_manager_insert(db_table_manager):
    insert = ('100', '', '')

    db_table_manager.insert(tbl_name, insert)

    # Assert
    db_rows = db_table_manager.readall(tbl_name)

    assert len(db_rows) == 1
    assert insert in db_rows

def test_db_table_manager_insert_many(db_table_manager):
    inserts = []
    inserts.append(('1', '', ''))
    inserts.append(('2', '', ''))
    inserts.append(('3', '', ''))

    db_table_manager.insert_many(tbl_name, inserts)

    # Assert
    db_rows = db_table_manager.readall(tbl_name)

    assert len(db_rows) == len(inserts)
    assert all(row in db_rows for row in inserts)

def test_db_table_manager_insert_many_inserts_only_valid_rows(db_table_manager):
    valid_inserts = []
    valid_inserts.append(('1', '', ''))
    valid_inserts.append(('2', '', ''))

    invalid_inserts = []
    invalid_inserts.append((None, '', ''))
    invalid_inserts.append((100, "mid", "data"))

    # Act
    valid_insert = db_table_manager.insert_many(tbl_name, valid_inserts)
    invalid_insert = db_table_manager.insert_many(tbl_name, invalid_inserts)

    # Assert
    assert valid_insert
    assert not invalid_insert
    db_rows = db_table_manager.readall(tbl_name)

    assert len(db_rows) == len(valid_inserts)
    assert all(row in db_rows for row in valid_inserts)

def test_db_manager_delete_tbl(db_table_manager):
    db_table_manager.delete_tbl(tbl_name)

    validation_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='{}'".format(tbl_name)
    cursor = db_table_manager.db_conn.execute(validation_query)

    assert len(cursor.fetchall()) == 0
    assert len(db_table_manager.readall(tbl_name)) == 0


def test_db_manager_empty_tables(db_table_manager):
    db_table_manager.empty_tables()

    validation_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='{}'".format(tbl_name)
    cursor = db_table_manager.db_conn.execute(validation_query)

    # Assert (table exists but tables are empty)
    assert len(cursor.fetchall()) == 1
    assert all(len(db_tbl.readall()) == 0 for db_tbl in db_table_manager.db_tables)

