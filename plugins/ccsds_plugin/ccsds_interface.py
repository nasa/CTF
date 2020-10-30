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

""""
ccsds_interface.py: Defines the interface by which a CCSDS reader class can conform to.
                    Conforming to this interface allows CTF to use any set of CCSDS import files,
                    as long as a specialized reader class is developed.
"""


from lib.logger import logger as log


class CCSDSInterface:
    def __init__(self, config):
        self.mids = {}
        self.mid_map = {}
        self.enum_map = {}

        # Exports may have CCSDS Header included or not.
        # Ensure CCSDS_header_info_included is set to True in config if
        #   CCSDS Primary/Secondary headers are included in the CCSDS Files.
        self.config = config
        self.header_info_included = self.config.CCSDS_header_info_included
        self.log_ccsds_imports = self.config.log_ccsds_imports

    # TODO - Suggest reworking the mid_map field_names to make more sense.
    #  Potentially mirroring json field_name
    def add_telem_msg(self, mid_name, mid, name, parameters, parameter_enums=None):
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
            log.info("Added Telemetry Message {}:{} with MID {}".format(name, mid_name, mid))

    def add_cmd_msg(self, mid_name, mid, command_code_map, command_enums=None):
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
            log.info("Added Command Message {}:{} with MID {}".format(mid_name, mid, command_code_map))

    def add_enumeration(self, key, value):
        self.enum_map.update({key: value})
        if self.log_ccsds_imports:
            log.info("Added Enumeration {}:{}".format(key, value))

    # Virtual Functions
    def get_ccsds_messages_from_dir(self, directory):
        pass
