# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2020 United States Government as represented by the
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


from lib.Global import expand_path
from lib.logger import logger as log

import socket
import ipaddress
import os
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection

class ArgsValidation(object):
    def __init__(self):

        self.parameterErrors = 0

    def add_error(self, field, exception = None):
        log.error("Validation Error - Invalid {}.".format(field))
        if exception:
            log.debug(exception)
        self.parameterErrors += 1

    def get_error_count(self):
        return self.parameterErrors

    def is_param_none(self, param):
        return param is None

    def increment_error_count(self):
        self.parameterErrors += 1

    def verify_symbol(self, file, symbol):
        if self.is_param_none(symbol):
           log.error("Symbol not specified.")
           return False
        status = False
        if os.path.isfile(file):
            with open(file, 'rb') as f:
                elffile = ELFFile(f)
                log.debug('  %s sections' % elffile.num_sections())
                section = elffile.get_section_by_name('.symtab')
                if not section:
                    log.error("Invalid ELF file no symbol table found.")
                    status = False
                elif isinstance(section, SymbolTableSection):
                    num_symbols = section.num_symbols()
                    for symbolNum in range(0, num_symbols):
                        if section.get_symbol(symbolNum).name == symbol:
                            status = True
                            break
        else:
            log.error("File {} does not exist.".format(file))

        return status


    def validate_symbol(self, symbol, file_path):
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
        new_file_path = file_path
        if not os.path.isfile(file_path):
            if fail_if_not_valid:
                new_file_path = None
                log.error("Invalid file path: {}".format(file_path))
            else:
                log.warn("File does not exist - {}".format(file_path))
        return new_file_path

    def expand_directory(self, directory):
        new_directory = expand_path(directory)
        return new_directory

    def validate_directory(self, directory):
        new_directory = expand_path(directory)
        if not os.path.isdir(new_directory):
            new_directory = None
            log.warn("Directory does not exist - {}".format(directory))
        return new_directory

    def validate_number(self, number):
        new_number = None
        try:
            new_number = float(number)
        except Exception as e:
            self.add_error("Number (float)", e)
            self.parameterErrors += 1
        return new_number

    def validate_int(self, integer):
        new_integer = None
        try:
            new_integer = int(integer)
        except Exception as e:
            self.add_error("Integer", e)

        return new_integer

    def validate_ip(self, ip):
        new_ip = None
        try:
            # Test that the IP is valid
            socket.gethostbyname(ip)
            new_ip = ip
        except Exception as e:
            self.add_error("IP", e)
        return new_ip

    def validate_boolean(self, value):
        new_value = None
        if type(value) is bool:
            new_value = value
        else:
            self.add_error("Boolean")
        return new_value
