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

"""
cfs_time_manager.py: CFS Time Manager for CTF.

- When initialized by the cFS plugin, the default CTF time manager (OS Time)
  is disabled, and the cFS time manager is used instead.

- The cFS time manager implements a serialized telemetry receive implementation
  as CTF instructions are "waiting".

- The cFS time manager also invokes the continuous verification checks
  between polls to ensure each packet is verified if a continuous verification
  exists.
"""

import traceback
import time
import logging as log

from lib.ctf_global import Global
from lib.exceptions import CtfTestError
from lib.time_interface import TimeInterface
from plugins.cfs.pycfs.cfs_interface import CtfConditionError


class CfsTimeManager(TimeInterface):
    """
    CfsTimeManager: CFS Time Manager for CTF.

    @note When initialized by the cFS plugin, the default CTF time manager (OS Time)
    is disabled, and the cFS time manager is used instead.

    @note The cFS time manager implements a serialized telemetry receive implementation
    as CTF instructions are "waiting".

    @note The cFS time manager also invokes the continuous verification checks
    between polls to ensure each packet is verified if a continuous verification exists.
    """

    def __init__(self, cfs_targets):
        """
        Constructor implementation for CfsTimeManager class.
        @note CfsTimeManager is inherited from TimeInterface class.
        @note The constructor assigns ctf_verification_poll_period attribute based on INI File config, and cfs_targets
        attribute from passed argument.
        """
        TimeInterface.__init__(self)
        self.ctf_verification_poll_period = Global.config.getfloat("core", "ctf_verification_poll_period", fallback=0.1)
        log.info("CfsTimeManager Initialized. Verification Poll Period = {}."
                 .format(self.ctf_verification_poll_period))
        self.cfs_targets = cfs_targets

    @staticmethod
    def handle_test_exception_during_wait(error, msg, do_raise=False):
        """
        Test exception handler, log error, and raise exception if do_raise is True
        """
        log.error("Error: {}".format(msg))
        log.debug(error)
        if do_raise:
            raise error

    def wait(self, seconds):
        """
        Do polling for certain seconds. Continue to do pre_command(), post_command(),
        and sleep until exec_time expires.

        @param seconds: polling duration.

        @return None
        """
        start_time = self.exec_time
        while self.exec_time < start_time + seconds:
            try:
                self.pre_command()
            except CtfTestError as exception:
                self.handle_test_exception_during_wait(exception, "CfsTimeManager: Pre-Command Failed", True)

            try:
                self.post_command()
            except CtfTestError as exception:
                self.handle_test_exception_during_wait(exception, "CfsTimeManager: Post-Command Failed", True)

            time.sleep(self.ctf_verification_poll_period)
            self.exec_time += self.ctf_verification_poll_period

    def pre_command(self):
        """
        Read Telemetry Packets for CFS Target, and run continuous verification.
        Raise any occurring Exception
        """
        super().pre_command()
        for target in self.cfs_targets.values():
            try:
                target.cfs.read_sb_packets()
            except Exception as exception:
                log.error("Failed to receive CFS Telemetry Packets for CFS Target: {}."
                          .format(target.config.name))
                log.debug(traceback.format_exc())
                raise CtfTestError('Error from read_sb_packets') from exception
        try:
            self.run_continuous_verifications()
        except CtfConditionError as exception:
            # Raise ConditionError to Test in order to fail the test...
            raise exception
        except CtfTestError as exception:
            # Raise other generic CtfTestError to Test to react to it if needed...
            log.debug(exception)
            raise exception

    def run_continuous_verifications(self):
        """
        Check all unchecked telemetry message by mid and vid by triggering target's target.cfs.check_tlm_conditions().
        Raise any occurring Exception
        """
        try:
            for target in self.cfs_targets.values():
                if target is not None and target.cfs is not None:
                    target.cfs.check_tlm_conditions()
        except CtfConditionError as exception:
            log.error("Test condition(s) failed in Post Command.")
            raise exception
