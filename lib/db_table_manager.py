"""
@namespace lib.db_table_manager
Utility functions to manage sqlite database tables
"""

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
# File: db_table_manager.py
#
# Purpose: This file defines utility functions to manage sqlite database tables.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================


import sqlite3


class DbConn:
    """
    DbConn Class Definition

    Establishes connection with the database file.

    The DB connection may be accessed across multiple threads, ensure proper
    synchronization is enforced. If multi thread access is not desired,
    set 'check_same_thread' parameter of the .connect() call to True.
    """
    def __init__(self, db_file):
        """
        Constructor for DbConn Class

        Connects to existing db file with provided name if exists,
        creates a new one otherwise.
        """
        self.conn = sqlite3.connect(db_file, check_same_thread=False)

    def __del__(self):
        """
        Destructor for DbConn Class
        """
        self.close()

    def execute(self, query_str, parameters=()):
        """"
        Executes an insert query.
        """
        return self.conn.execute(query_str, parameters)

    def execute_many(self, query_str, items):
        """
        Executes a batch insert query.
        """
        self.conn.executemany(query_str, items)

    def commit(self):
        """
        Commits any pending transaction to the database.
        """
        self.conn.commit()

    def connect(self, db_file):
        """
        Establishes connection to the specified db file.
        """
        self.conn = sqlite3.connect(db_file, check_same_thread=False)

    def close(self):
        """
        Closes connection to the Db file. Any uncommited changes will be lost.
        """
        self.conn.close()


class DbTable:
    """
    DbTable Class Definition
    """
    def __init__(self, db_conn, tbl_name, tbl_hdr):
        """
        Constructor for DbTable Class

        Creates the table with specified format if it doesnt exist already.
        """
        self.db_conn = db_conn
        self.tbl_name = tbl_name
        self.tbl_hdr = tbl_hdr
        exec_str = "CREATE TABLE IF NOT EXISTS {0} ({1})".format(self.tbl_name, self.tbl_hdr)
        self.db_conn.execute(exec_str)
        self.db_conn.commit()

        # Track table insert failures to allow checking table integrity
        self.failed_inserts = 0

    def insert(self, value):
        """
        Executes query to insert value into table
        """
        if value:
            # create placeholders to bind data to query
            placeholders = ', '.join(['?'] * len(value))

            try:
                query = f"INSERT INTO {self.tbl_name} VALUES ({placeholders})"
                self.db_conn.execute(query, value)
                self.db_conn.commit()
                return True
            except sqlite3.Error:
                self.failed_inserts = self.failed_inserts + 1
                return False
        else:
            return False

    def insert_many(self, values):
        """
        Executes query to insert values into table
        """
        if values:
            # create placeholders to bind data to query
            placeholders = ', '.join(['?'] * len(values[0]))

            try:
                query = f"INSERT INTO {self.tbl_name} VALUES ({placeholders})"
                self.db_conn.execute_many(query, values)
                self.db_conn.commit()
                return True
            except sqlite3.Error:
                self.failed_inserts = self.failed_inserts + len(values)
                return False

        else: return False

    def readall(self):
        """
        Executes query to read all rows in the table.
        Returns the result of the query.
        """
        cursor = self.db_conn.execute("SELECT * FROM " + self.tbl_name)
        return cursor.fetchall()

    def empty(self):
        """"
        Executes query to empty the table, then commits the change.
        """
        exec_str = "DELETE FROM {0}".format(self.tbl_name)
        self.db_conn.execute(exec_str)
        self.db_conn.commit()


class DbTableManager:
    """
    DbTableManager Class Defintiion
    """
    def __init__(self, db_conn, db_tables):
        """
        Constructor for the DbTableManager Class
        """
        self.db_conn = db_conn
        self.db_tables = db_tables

    def __del__(self):
        """"
        Destructor for the DbTableManager Class
        """
        self.db_conn.commit()
        self.db_conn.close()

    def insert(self, tbl_name, value):
        """"
        Inserts value into the specified table, if found
        Returns True if insert into db succeeded, False otherwise
        """
        for db_table in self.db_tables:
            if db_table.tbl_name == tbl_name:
                result = db_table.insert(value)
                return result

        return False

    def insert_many(self, tbl_name, values):
        """"
        Inserts values into the specified table, if found
        Returns True if insert into db succeeded, False otherwise
        """
        for db_table in self.db_tables:
            if db_table.tbl_name == tbl_name:
                result = db_table.insert_many(values)
                return result

        return False

    def readall(self, tbl_name):
        """
        Returns all the rows in specified table, if found
        """
        for db_table in self.db_tables:
            if db_table.tbl_name == tbl_name:
                return db_table.readall()
        return []

    def delete_tbl(self, tbl_name):
        """
        Deletes the specified table, if found
        """
        for db_table in self.db_tables:
            if db_table.tbl_name == tbl_name:
                self.db_conn.execute("DROP TABLE " + tbl_name)
                self.db_conn.commit()
                self.db_tables.remove(db_table)

    def empty_tables(self):
        """
        Deletes all rows in the existing tables
        without deleting the tables themselves.
        """
        for db_table in self.db_tables:
            db_table.empty()
            self.db_conn.commit()
