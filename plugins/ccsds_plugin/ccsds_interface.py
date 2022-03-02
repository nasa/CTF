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

""""
ccsds_interface.py: Defines the interface by which a CCSDS reader class can conform to.
                    Conforming to this interface allows CTF to use any set of CCSDS import files,
                    as long as a specialized reader class is developed.
"""


from lib.logger import logger as log


class CCSDSInterface:
    """
    This class provides an interface and partial implementation for a CCSDS reader to process CCSDS data from
    a directory into dynamic type definitions. The method of parsing the data is left to a subclass.
    """

    def __init__(self, config):
        self.mids = {}
        self.mid_map = {}
        self.enum_map = {}

        # Exports may have CCSDS Header included or not.
        # Ensure CCSDS_header_info_included is set to True in config if
        #   CCSDS Primary/Secondary headers are included in the CCSDS Files.
        self.config = config
        self.header_info_included = self.config.ccsds_header_info_included
        self.log_ccsds_imports = self.config.log_ccsds_imports

    # ENHANCE - Suggest reworking the mid_map field_names to make more sense.
    #  Potentially mirroring json field_name
    def add_telem_msg(self, mid_name, mid, name, parameters, parameter_enums=None):
        """
        Adds a telemetry message to the internal types

        @param mid_name: Name of the MID associated with the command
        @param mid: Value of the MID associated with the command
        @param name: Name of the telemetry message
        @param parameters: Type of the telemetry message parameters
        @param parameter_enums: Dictionary of enumerations associated with this telemetry message
        """
        msg = {
            mid_name: {
                "MID": mid if isinstance(mid, int) else int(mid, 0),
                "name": name,
                "PARAM_CLASS": parameters
            }
        }
        self.mid_map.update(msg)
        self.enum_map.update({mid_name: mid})
        if parameter_enums:
            self.enum_map.update(parameter_enums)
        if self.log_ccsds_imports:
            log.info("Added Telemetry Message {}:{} with MID {}".format(name, mid_name, hex(mid)))

    def add_cmd_msg(self, mid_name, mid, command_code_map, command_enums=None):
        """
        Adds a command message to the internal types

        @param mid_name: Name of the MID associated with the command
        @param mid: Value of the MID associated with the command
        @param command_code_map: Dictionary mapping command code values to their corresponding types
        @param command_enums: Dictionary of enumerations associated with this command
        """
        msg = {
            mid_name: {
                "MID": mid if isinstance(mid, int) else int(mid, 0),
                "CC": command_code_map,
            }
        }
        self.enum_map.update({mid_name: mid})
        if command_enums:
            self.enum_map.update(command_enums)
        self.mid_map.update(msg)
        if self.log_ccsds_imports:
            log.info("Added Command Message {} with MID {}".format(mid_name, hex(mid)))

    def add_enumeration(self, key, value):
        """
        Adds an enumeration definition to the internal types

        @param key: Name of the enumeration
        @param value: Value of the enumeration
        """
        self.enum_map.update({key: value})
        if self.log_ccsds_imports:
            log.info("Added Enumeration {}:{}".format(key, value))

    # Virtual Functions
    def get_ccsds_messages_from_dir(self, directory):
        """
        Virtual function to be implemented by a reader.
        Processes the CCSDS data from a directory and returns the data types defined in them.

        @param directory: Path to the directory containing CCSDS data type definitions.
        """
