"""
@namespace lib.exceptions
Exception definitions for CTF
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
import traceback

from lib.logger import logger as log


class CtfTestError(Exception):
    """
    General top-level exception that is thrown when a CTF Test Error occurs during a test run.
    """
    def __init__(self, message):
        """
        Constructor of CtfTestError Class
        """
        super().__init__(message)
        log.debug(traceback.format_exc())


class CtfConditionError(CtfTestError):
    """
    CTF Condition Error thrown when a CTF Instruction Condition is not met during test run.
    """
    def __init__(self, message, test_condition):
        """
        Constructor of CtfConditionError Class
        """
        super().__init__(message)
        self.condition = test_condition


class CtfParameterError(CtfTestError):
    """
    CTF Parameter Error thrown when a CTF Instruction Parameter is invalid.
    """
    def __init__(self, message, parameter):
        """
        Constructor of CtfParameterError Class
        """
        super().__init__(message)
        self.parameter = parameter
