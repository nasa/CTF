"""
@namespace lib.args_validation
Argument Validation Helper Utilities
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
import socket
import os
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from lib.ctf_utility import expand_path
from lib.logger import logger as log


class ArgsValidation:
    """
    Helper class to validate arguments and data used by CTF
    """

    def __init__(self):
        """
        Constructor of ArgsValidation class. Initialize instance variable "parameter_errors",
        which tracks the number of errors encountered during validation.
        """
        self.parameter_errors = 0

    def add_error(self, field, exception=None):
        """
        Increment the number of errors and log an exception if needed
        @param field: Field name where validation error occurred
        @param exception:  Whether to log an exception on failure or not
        """
        log.error("Validation Error - Invalid {}.".format(field))
        if exception:
            log.debug(exception)
        self.increment_error_count()

    def get_error_count(self):
        """
        Returns the number of errors encountered during validation so far
        """
        return self.parameter_errors

    @staticmethod
    def is_param_none(param):
        """
        Returns whether or not a given parameter is None
        @param param: Parameter to check if None
        """
        return param is None

    def increment_error_count(self):
        """
        Increment error count without logging an exception
        """
        self.parameter_errors += 1

    def verify_symbol(self, file_path, symbol):
        """
        Given a file path, verify that a given symbol exists within that file.
        Return True if the symbol exists, otherwise return False

        @note - Primarily used to validate SP0 executables

        @param file_path: Path to executable file to check
        @param symbol: Name of symbol to verify within executable file
        """
        if self.is_param_none(symbol):
            log.error("Symbol not specified.")
            return False
        status = False
        if os.path.isfile(file_path):
            with open(file_path, 'rb') as file:
                elffile = ELFFile(file)
                log.debug('{} sections in file {}'.format(elffile.num_sections(), file_path))
                section = elffile.get_section_by_name('.symtab')
                if not section:
                    log.error("Invalid ELF file no symbol table found.")
                    status = False
                elif isinstance(section, SymbolTableSection):
                    status = any(s.name == symbol for s in section.iter_symbols())
                    if not status:
                        log.error("Section does not have the symbol: {}".format(symbol))
        else:
            log.error("File {} does not exist.".format(file_path))

        return status

    def validate_symbol(self, symbol, file_path):
        """
        Given a file path, verify that the file exists on disk and contains the given symbol.
        Return the symbol if it exists, otherwise return None

        @note - Primarily used to validate SP0 executables

        @param symbol: Name of symbol to verify within executable file
        @param file_path: Path to executable file to check
        """
        new_symbol = None
        file_path = self.validate_file(file_path)
        if file_path is None:
            return new_symbol
        if self.verify_symbol(file_path, symbol):
            new_symbol = symbol
        else:
            log.error("Invalid Symbol -  Not a Valid EntryPoint: {}.".format(symbol))
            self.add_error("Symbol")
        return new_symbol

    def validate_file(self, file_path, fail_if_not_valid=False):
        """
        Given a file path, verify that the file exists on disk.
        Return the expanded absolute path, or None if invalid.

        @param file_path: Path to file to check
        @param fail_if_not_valid: Whether to consider an invalid path a failure or not
        @note fail_if_not_valid is useful when checking a file that is not guaranteed to exist
        """
        new_file_path = file_path
        if not os.path.isfile(file_path):
            if fail_if_not_valid:
                new_file_path = None
                self.add_error("Invalid file path: {}".format(file_path))
            else:
                log.warning("File does not exist - {}".format(file_path))
        return new_file_path

    @staticmethod
    def validate_directory(directory):
        """
        Given a directory path, verify that the directory exists on disk.
        Return the expanded absolute path, or None if invalid.
        """
        new_directory = expand_path(directory)
        if not os.path.isdir(new_directory):
            new_directory = None
            log.warning("Directory does not exist - {}".format(directory))
        return new_directory

    def validate_number(self, number):
        """
        Verify that a given value is valid as a numerical (float).
        Return the converted value, or None if not a number.
        """
        new_number = None
        try:
            new_number = float(number)
        except ValueError as exception:
            self.add_error("Number (float)", exception)
        return new_number

    def validate_int(self, integer):
        """
        Verify that a given value is valid as an integer.
        Return the converted value, or None if not an integer.
        """
        new_integer = None
        try:
            new_integer = int(integer)
        except ValueError as exception:
            self.add_error("Integer", exception)
        return new_integer

    def validate_ip(self, ip_address):
        """
        Verify that the given value is a valid and reachable network destination.
        Return the IP address, or None if invalid.
        """
        new_ip = None
        try:
            # Test that the IP is valid
            socket.gethostbyname(ip_address)
            new_ip = ip_address
        except socket.error as exception:
            self.add_error("IP", exception)
        return new_ip

    def validate_boolean(self, value):
        """
        Verify that the given value is valid as a boolean.
        Return the converted value, or None if not a boolean.
        """
        new_value = None
        if isinstance(value, bool):
            new_value = value
        else:
            self.add_error("Boolean")
        return new_value

    def __repr__(self):
        return "{} errors found".format(self.parameter_errors)
