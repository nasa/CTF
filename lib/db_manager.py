"""
@namespace lib.db_manager
Utility functions to manage sqlite database
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
# File: db_manager.py
#
# Purpose: This file defines utility functions to manage sqlite database.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================


import queue
import time
import threading

from lib.db_table_manager import DbConn, DbTable, DbTableManager
from lib.logger import logger as log


def run_ctf_background_db_task(db_tbl_mgr, queue_poll_interval_seconds = 0, batch_size = 5):
    """
    While run flag is True, reads from queues and writes to db
    """
    cmd_queue = DBManager.cmd_queue
    tlm_queue = DBManager.tlm_queue
    event_queue = DBManager.event_queue

    batch = []
    while DBManager.run_logging_task:
        time.sleep(queue_poll_interval_seconds)

        # Process cmd queue
        while not cmd_queue.empty() and len(batch) < batch_size:
            batch.append(cmd_queue.get(block=False))
            cmd_queue.task_done()

        db_tbl_mgr.insert_many("cmd", batch)
        batch.clear()

        # Process tlm queue
        while not tlm_queue.empty() and len(batch) < batch_size:
            batch.append(tlm_queue.get(block=False))
            tlm_queue.task_done()

        db_tbl_mgr.insert_many("tlm", batch)
        batch.clear()

        # Process event queue
        while not event_queue.empty() and len(batch) < batch_size:
            batch.append(event_queue.get(block=False))
            event_queue.task_done()

        db_tbl_mgr.insert_many("event", batch)
        batch.clear()

    # Process any left-over elements in the 3 queues
    batch.clear()
    while not cmd_queue.empty():
        batch.append(cmd_queue.get(block=False))
        cmd_queue.task_done()

    db_tbl_mgr.insert_many("cmd", batch)
    batch.clear()

    while not tlm_queue.empty():
        batch.append(tlm_queue.get(block=False))
        tlm_queue.task_done()

    db_tbl_mgr.insert_many("tlm", batch)
    batch.clear()

    while not event_queue.empty():
        batch.append(event_queue.get(block=False))
        event_queue.task_done()

    db_tbl_mgr.insert_many("event", batch)
    batch.clear()


def initialize_db(db_file_name):
    """
    Connects to existing `db_file_name` file if applicable
    Otherwise, initializes new DB file with defined table structure
    """
    db_conn = DbConn(db_file_name)

    cmd_tbl = DbTable(
        tbl_name="cmd",
        tbl_hdr="ctf_timestamp TEXT PRIMARY KEY NOT NULL, target TEXT NOT NULL, "
                "mid NUMERIC, msghdr BLOB, payload BLOB",
        db_conn=db_conn
    )

    tlm_tbl = DbTable(
        tbl_name="tlm",
        tbl_hdr="ctf_timestamp TEXT PRIMARY KEY NOT NULL, target TEXT NOT NULL, "
                "fsw_timestamp TEXT NOT NULL, mid NUMERIC, msghdr BLOB, payload BLOB, formatted_payload BLOB",
        db_conn=db_conn
    )

    event_tbl = DbTable(
        tbl_name="event",
        tbl_hdr="ctf_timestamp TEXT PRIMARY KEY NOT NULL, target TEXT NOT NULL, "
                "fsw_timestamp TEXT NOT NULL, mid NUMERIC, msghdr BLOB, payload BLOB, formatted_payload BLOB, "
                "app TEXT, event_id NUMERIC, event_type NUMERIC, event_message TEXT",
        db_conn=db_conn
    )

    db_tbl_mgr = DbTableManager(db_conn, [tlm_tbl, event_tbl, cmd_tbl])

    return db_tbl_mgr


class DBManager:
    """
    Manages the initialization of the sqlite database, and provides methods
    to log data as well start/stop the logging task.
    """
    cmd_queue = queue.Queue()
    tlm_queue = queue.Queue()
    event_queue = queue.Queue()

    # flag used to start/stop processing in the background thread
    run_logging_task = False

    def __init__(self, db_file_name):
        """
        Constructor for the DBManager Class. Initializes the local sqlite DB
        and defines the background task.
        """
        # Establish DB Connection and initialize tables
        self.db_table_manager = initialize_db(db_file_name)
        # Define background task
        self.background_thread = threading.Thread(target=run_ctf_background_db_task,
                                                  args=(self.db_table_manager,))

    def __del__(self):
        """
        Destructor for the DBManager Class. Terminates the background logging task.
        """
        self.stop_background_logging_task()

    @staticmethod
    def log_cmd(ctf_timestamp, target, mid, msghdr, payload):
        """"
        Inserts parameters into command queue.
        """
        DBManager.cmd_queue.put((ctf_timestamp, target, mid, msghdr, payload))

    @staticmethod
    def log_tlm(ctf_timestamp, target, fsw_timestamp, mid, msghdr, payload, formatted_payload):
        """"
        Inserts parameters into telemetry queue.
        """
        DBManager.tlm_queue.put((ctf_timestamp, target, fsw_timestamp, mid, msghdr, payload, formatted_payload))

    @staticmethod
    def log_event(ctf_timestamp, target, fsw_timestamp, mid, msghdr,
                  payload, formatted_payload, app_name, eventid, event_type, event_message):
        """
        Inserts parameters into event queue.
        """
        DBManager.event_queue.put((ctf_timestamp, target, fsw_timestamp, mid, msghdr,
                                   payload, formatted_payload, app_name, eventid, event_type, event_message))

    def start_background_logging_task(self) -> bool:
        """"
        Kicks off the logging task in a background thread.
        """
        # Enable run flag
        DBManager.run_logging_task = True

        try:
            self.background_thread.start()

        except RuntimeError as error:
            log.error("CTF DB: Failed to start background db logging, with exception: {}".format(error))
            return False

        log.info("CTF DB: Started background DB logging")
        return True

    def stop_background_logging_task(self):
        """
        Stops background logging task. Once stopped, the task
        cannot be restarted within the same class instance
        """
        if self.background_thread.is_alive():
            # Disable flag to signal thread termination
            DBManager.run_logging_task = False

            # Wait until all remaining queue items are processed
            DBManager.cmd_queue.join()
            DBManager.tlm_queue.join()
            DBManager.event_queue.join()

            # Join background thread
            self.background_thread.join(timeout=5)

            if self.background_thread.is_alive():
                log.error("CTF DB: Failed to terminate background db logging task within timeout")

            else:
                log.info("CTF DB: Stopped background DB logging")

            # Verify table integrity and log warning if missing data
            for table in self.db_table_manager.db_tables:
                if table.failed_inserts > 0:
                    log.warning("CTF DB: {} table may be incomplete - {} inserts failed"
                                .format(table.tbl_name, table.failed_inserts))
