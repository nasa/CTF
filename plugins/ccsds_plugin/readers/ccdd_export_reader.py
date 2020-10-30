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
ccsds_export_reader.py: Implements the CCSDS Interface to read JSON CCSDS data exported from CCDD.

- This file is handles reading the raw CCSDS definitions from JSON, and returns an mid map and macro map
   from the given path where the CCSDS definitions are.
"""


from plugins.ccsds_plugin.ccsds_interface import CCSDSInterface
import os
import fnmatch
import json
import ctypes

from lib.logger import logger as log

from .command_builder import populateMessage


# Helper Functions
def ctypes_name(name):
    return "c_{0}".format(name.replace("_t", ""))


def dynamic_init(self, *args, **kwargs):
    super(type(self), self).__init__(*args, **kwargs)
    self.__dict__.update(kwargs)


def to_string(self):
    string = "{}: {{{}}}".format(self.__class__.__name__,
                                 ", ".join(["{}: {}".format(field[0], getattr(self, field[0]))
                                            for field in self._fields_]))
    return string


def create_type_class(name, supertype, params):
    fields = {
        "_pack_": 1,
        "_fields_": params,
        "__init__": dynamic_init,
        "__str__": to_string
    }
    try:
        return type(name, (supertype,), fields)
    except Exception as e:
        log.error("Failed to create type class {}!".format(name))
        log.debug(e)


class CCDDExportReader(CCSDSInterface):
    def __init__(self, config):
        super().__init__(config)
        self.current_file_name = None
        self.type_dict = {}
        self.ctype_structure = ctypes.Structure
        if config.endianess_of_target == 'little':
            self.ctype_structure = ctypes.LittleEndianStructure
        elif config.endianess_of_target == 'big':
            self.ctype_structure = ctypes.BigEndianStructure
        else:
            log.error("No valid endianess_of_target in config")

    def is_command_msg(self, json_dict):
        return type(json_dict) is dict and json_dict.get("cmd_mid_name", None) is not None

    def is_telemetry_msg(self, json_dict):
        return type(json_dict) is dict and json_dict.get("tlm_mid_name", None) is not None

    def is_command_tlm(self, json_dict):
        return self.is_command_msg(json_dict) or self.is_telemetry_msg(json_dict)

    def is_types_macros(self, json_dict):
        return not self.is_command_tlm(json_dict)

    # TODO - Validate each JSON file against the appropriate schema before attempting to parse it
    def validate_json_schema(self, json_dict, schema_path):
        if not os.path.exists(schema_path):
            log.error("Cannot find JSON schema {}. Skipping ".format(schema_path))

    def process_command(self, json_dict):
        cmd_mid_name = None

        if "cmd_mid_name" not in json_dict.keys():
            log.error("No cmd_mid_name field in JSON.")
        else:
            cmd_mid_name = json_dict["cmd_mid_name"]

        command_class = populateMessage(json_dict)

        command_codes = {}
        for cc in command_class.command_codes:
            try:
                [cls, _] = self._create_parameterized_type(cc, type_id="cc_data_type", arg_id="args")
                code = int(cc.cc_value, 0) if isinstance(cc.cc_value, str) else cc.cc_value
                command_codes[cc.cc_name] = {
                    "CODE": code,
                    "ARG_CLASS": cls
                }
                if cc.cc_name:
                    self.type_dict[cc.cc_name] = cls
                    self.add_enumeration(cc.cc_name, code)
            except Exception as e:
                log.error("Failed to create command data type {}: {}".format(cc.cc_name, e))

        if cmd_mid_name is not None:
            if cmd_mid_name in self.mids:
                command_message_id = self.mids[cmd_mid_name]
                self.add_cmd_msg(cmd_mid_name, command_message_id, command_codes)
            else:
                log.warn("Unknown MID name {} in {}. Skipping this message"
                         .format(cmd_mid_name, self.current_file_name))
        else:
            log.warn("{} has no cmd_mid_name. Skipping this message".format(self.current_file_name))

    def _build_data_type_and_field(self, param, fields, subtypes=None):
        param_name = param['name']
        type_name = param['data_type']
        array_size = param.get('array_size')
        bit_length = param.get('bit_length')
        data_type = None

        # If this is NOT a composite type and we have already created it, return
        if (subtypes is None) and (param_name in self.type_dict):
            log.warn("Data type {} already defined.".format(param_name))
            return

        if subtypes and param_name in subtypes:
            data_type = subtypes[param_name]
        elif type_name in self.type_dict:
            data_type = self.type_dict[type_name]
        elif ctypes_name(type_name) in ctypes.__dict__:
            data_type = ctypes.__dict__[ctypes_name(type_name)]

        if data_type is not None:
            if array_size:
                if isinstance(array_size, int) or (isinstance(array_size, str) and array_size.isdigit()):
                    array_size = int(array_size)
                    if array_size > 0:
                        data_type = data_type * array_size
                elif isinstance(array_size, str) and str(array_size) in self.type_dict:
                    data_type = data_type * self.type_dict[array_size]
                else:
                    log.error("Invalid array size {} in {}".format(array_size, param_name))

            if bit_length is not None and bit_length != 'None' and int(bit_length) > 0:
                fields.append((str(param_name), data_type, int(bit_length)))
            else:
                fields.append((str(param_name), data_type))

        return data_type

    def _create_parameterized_type(self, type_dict, type_id=None, arg_id=None, subtypes=None):
        fields = []
        subtypes = subtypes or {}
        type_enums = {}
        data_type_name = str(type_dict.get(type_id, None))
        parameters = type_dict.get(arg_id, [])

        for param in parameters:
            param_name = param['name']

            if param_name == "Byte" or param_name in fields:
                continue

            if 'parameters' in param and len(param['parameters']) > 0:
                subtypes[param_name], type_enums = self._create_parameterized_type(param,
                                                                                   'data_type',
                                                                                   'parameters',
                                                                                   subtypes)

            param_data_type = self._build_data_type_and_field(param, fields, subtypes)
            if param_data_type is None:
                log.error("Cannot resolve argument {}".format(param))
                continue

            if param.get('enumeration'):
                for enum in param['enumeration']:
                    type_enums.update({enum["label"]: enum["value"]})

        if len(parameters) == 0:
            type_name = type_dict.get('data_type')
            if type_name is None:
                if self.config.log_ccsds_imports:
                    log.debug("{} has no fields.".format(data_type_name))
                return create_type_class(data_type_name, self.ctype_structure, []), type_enums
            else:
                data_type = self._build_data_type_and_field(type_dict, fields)
                if data_type is None:
                    log.error("Data type {} unknown.".format(type_name))
                    return

        data_type = create_type_class(data_type_name, self.ctype_structure, fields)
        return data_type, type_enums

    def process_telemetry(self, json_dict):
        tlm_mid_name = None
        tlm_data_type = None

        if "tlm_mid_name" not in json_dict.keys():
            log.error("No tlm_mid_name field in JSON.")
        else:
            tlm_mid_name = json_dict["tlm_mid_name"]

        if "tlm_data_type" not in json_dict.keys():
            log.error("No tlm_data_type field in JSON.")
        else:
            tlm_data_type = json_dict["tlm_data_type"]

        try:
            param_class, param_enums = self._create_parameterized_type(json_dict,
                                                                       type_id="tlm_data_type",
                                                                       arg_id="tlm_parameters")
            self.type_dict[json_dict['tlm_data_type']] = param_class
            if tlm_mid_name is not None:
                if tlm_mid_name in self.mids:
                    mid = self.mids[tlm_mid_name]
                    self.add_telem_msg(tlm_mid_name, mid, tlm_data_type, param_class, param_enums)
                else:
                    log.warn("Unknown MID name {} in {}. Skipping this message"
                             .format(tlm_mid_name, self.current_file_name))
            else:
                log.warn("{} has no MID. Skipping this message".format(self.current_file_name))
        except Exception as e:
            log.error("Failed to create telemetry data type {}: {}".format(tlm_data_type, e))

    def process_types(self, json_list):
        for typedef in json_list:
            if 'alias_name' in typedef:
                cfs_type_name = typedef['alias_name']
                c_type_name = typedef['actual_name']
                if c_type_name in ctypes.__dict__:
                    c_type = ctypes.__dict__[c_type_name]
                    self.type_dict[cfs_type_name] = c_type
                else:
                    log.error("Unknown ctype name {} in {}".format(c_type_name, self.current_file_name))
            elif 'constant_name' in typedef:
                cfs_macro_type = typedef['constant_name']
                c_macro = typedef['constant_value']
                self.type_dict[cfs_macro_type] = c_macro
            elif 'target' in typedef:
                if typedef['target'] == self.config.CCSDS_target:
                    if self.config.log_ccsds_imports:
                        log.info("Found {} MIDs for {}".format(len(typedef['mids']), self.config.CCSDS_target))
                    self.mids.update({mid['mid_name']: int(mid['mid_value'], 0) for mid in typedef['mids']})
            else:
                log.error("Invalid type definition in {}".format(self.current_file_name))

    def process_ccsds_json_file(self, filename, file_filter=None):
        with open(filename) as file:
            try:
                json_dict = json.load(file)
            except json.decoder.JSONDecodeError:
                log.error("Invalid JSON CCDD Export File: {}. Skipping".format(file))
            if file_filter is None or file_filter(json_dict):
                if self.config.log_ccsds_imports:
                    log.info("Processing {}".format(filename))
                # Determine if file is a telemetry or command message
                if self.is_command_msg(json_dict):
                    self.process_command(json_dict)
                elif self.is_telemetry_msg(json_dict):
                    self.process_telemetry(json_dict)
                else:
                    self.process_types(json_dict)

    def get_ccsds_messages_from_dir(self, directory, common_command_code_file=None):
        # Get list of JSON Files in the directory
        files = []
        for root, dirs, f in os.walk(directory):
            for basename in f:
                if fnmatch.fnmatch(basename, "*.json"):
                    filename = os.path.join(root, basename)
                    files.append(filename)
        # Process only types & macros first, then others
        for file in files:
            self.current_file_name = os.path.basename(file)
            self.process_ccsds_json_file(file, self.is_types_macros)
        for file in files:
            self.current_file_name = os.path.basename(file)
            self.process_ccsds_json_file(file, self.is_command_tlm)

        # Collect and convert integer values from enum_map and type_dict
        macro_map = dict(filter(lambda item: isinstance(item[1], int), self.type_dict.items()))
        for k, v in self.enum_map.items():
            v = int(v, 0) if isinstance(v, str) else v
            macro_map[k] = v
        return self.mid_map, macro_map
