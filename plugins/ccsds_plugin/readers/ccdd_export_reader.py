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
ccsds_export_reader.py: Implements the CCSDS Interface to read JSON CCSDS data exported from CCDD.

- This file is handles reading the raw CCSDS definitions from JSON, and returns an mid map and macro map
   from the given path where the CCSDS definitions are.
"""
import ast
import os
import fnmatch
import json
import ctypes

from lib.logger import logger as log
from lib.exceptions import CtfTestError
from plugins.ccsds_plugin.ccsds_interface import CCSDSInterface


# Helper Functions
def ctypes_name(name):
    """
    Converts a Python type name to an equivalent ctypes type name by prepending 'c_' and stripping '_t'

    @param name: The Python type name to be converted
    """
    return "c_{0}".format(name.replace("_t", ""))


def dynamic_init(self, *args, **kwargs):
    """
    A generic implementation of __init__ for a dynamic type with the given name and attributes.

    @note - Utility function used by create_type_class to assign as a type method.

    @param self: The object instance being constructed
    @param args: Indexed arguments for the type and its supertype
    @param kwargs: Keyword arguments for the type
    """
    super(type(self), self).__init__(*args, **kwargs)
    self.__dict__.update(kwargs)


def to_string(self):
    """
    A generic implementation of __str__ for a dynamic type that prints name-value pairs for each of its fields.

    @note - Utility function used by create_type_class to assign as a type method.

    @param self: The object instance being represented
    """
    string = "{}: {{{}}}".format(self.__class__.__name__,
                                 ", ".join(["{}: {}".format(field[0], getattr(self, field[0]))
                                            for field in self._fields_]))  # pylint: disable=protected-access
    return string


def create_type_class(name, supertype, params):
    """
    Dynamically creates types of a given name, supertype, and attributes
    with essential fields for the metaclass used by ctypes.

    @note - Intended to be used for new types that inherit from a ctypes type.

    @param name: The name of the new type
    @param supertype: The supertype of the new type
    @param params: A dictionary of fields for the new type
    """
    fields = {
        "_pack_": 1,
        "_fields_": params,
        "__init__": dynamic_init,
        "__str__": to_string
    }
    try:
        return type(name, (supertype,), fields)
    except Exception as exception:
        log.error("Failed to create type class {}!".format(name))
        log.debug(exception)
        raise CtfTestError("Error in create_type_class") from exception


class CCDDExportReader(CCSDSInterface):
    """
    This class reads CCSDS export files in JSON format and creates dictionaries mapping names to Python types and values
    """

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

    @staticmethod
    def is_command_msg(json_data):
        """
        Returns whether a JSON dictionary represents a CCSDS command message.
        """
        return isinstance(json_data, dict) and json_data.get("cmd_mid_name", None) is not None

    @staticmethod
    def is_telemetry_msg(json_data):
        """
        Returns whether a JSON dictionary represents a CCSDS telemetry message.
        """
        return isinstance(json_data, dict) and json_data.get("tlm_mid_name", None) is not None

    @staticmethod
    def is_command_tlm(json_data):
        """
        Returns whether a JSON dictionary represents a CCSDS command or telemetry message.
        """
        return CCDDExportReader.is_command_msg(json_data) or CCDDExportReader.is_telemetry_msg(json_data)

    @staticmethod
    def is_types_macros(json_data):
        """
        Returns whether a JSON dictionary represents type aliases or macros.

        @note - A list is assumed to be type aliases or macros.
        """
        return isinstance(json_data, list)

    @staticmethod
    def is_custom_types(json_data):
        """
        Returns whether a JSON dictionary represents custom type definitions.
        """
        return isinstance(json_data, dict) and json_data.get("data_type", None) is not None

    # ENHANCE - Validate each JSON file against the appropriate schema before attempting to parse it
    @staticmethod
    def validate_json_schema(json_data, schema_path):
        """
        Validates a dictionary of JSON data against a schema file.

        @param json_data: A dictionary containing JSON data to be validated
        @param schema_path: Path to a JSON schema file
        """
        log.debug("json_data argument {}".format(json_data))
        if not os.path.exists(schema_path):
            log.error("Cannot find JSON schema {}. Skipping ".format(schema_path))

    def process_command(self, json_dict):
        """
        Parses the contents of a JSON dictionary for a CCSDS command message to dynamically create a new type for each
        command code which is added to the type dictionary. Defines a command message with the MID and command codes,
        and an enumeration for each command code by name.

        @param json_dict: A dictionary containing the JSON data of an exported CCSDS telemetry message
        """
        cmd_mid_name = None

        if "cmd_mid_name" not in json_dict.keys():
            log.error("No cmd_mid_name field in JSON.")
        else:
            cmd_mid_name = json_dict["cmd_mid_name"]

        command_codes = {}

        if "cmd_data_type" in json_dict:
            # This MID has no command codes, so use anonymous/0 CC for compatibility
            try:
                [cls, _] = self._create_parameterized_type(json_dict, type_id="cmd_data_type", arg_id="cmd_parameters")
                command_codes[""] = {
                    "CODE": 0,
                    "ARG_CLASS": cls
                }
            except Exception as ex:
                log.error("Failed to create command data type for MID {}: {}".format(cmd_mid_name, ex))
                raise CtfTestError("Error in process_command") from ex

        for cmd_code in json_dict.get("cmd_codes", []):
            cc_name = cmd_code.get("cc_name", None)
            cc_value = cmd_code.get("cc_value", None)
            try:
                [cls, _] = self._create_parameterized_type(cmd_code, type_id="cc_data_type", arg_id="cc_parameters")
                code = int(cc_value, 0) if isinstance(cc_value, str) else cc_value
                command_codes[cc_name] = {
                    "CODE": code,
                    "ARG_CLASS": cls
                }
                if cc_name:
                    self.type_dict[cc_name] = cls
                    self.add_enumeration(cc_name, code)
            except Exception as ex:
                log.error("Failed to create command data type for MID {} CC {}: {}".format(cmd_mid_name, cc_name, ex))
                raise CtfTestError("Error in process_command") from ex

        if cmd_mid_name is not None:
            if cmd_mid_name in self.mids:
                command_message_id = self.mids[cmd_mid_name]
                self.add_cmd_msg(cmd_mid_name, command_message_id, command_codes)
            else:
                log.warning("Unknown MID name {} in {}. Skipping this message"
                            .format(cmd_mid_name, self.current_file_name))
        else:
            log.warning("{} has no cmd_mid_name. Skipping this message".format(self.current_file_name))

    def _build_data_type_and_field(self, param, fields, subtypes=None):
        """
        Builds a field, containing a simple data type, for a custom type.
        Returns the data type and appends it to fields.

        @note - This method does not create or modify any types. The return value, and the in-out parameter fields,
        should be used to create the type with create_type_class.

        @param param: A dictionary containing JSON data defining a field of a parent type
        @param fields: A list of fields of the parent type
        @param subtypes: A dictionary of subtypes of the parent type
        """
        param_name = param['name']
        type_name = param['data_type']
        array_size = param.get('array_size')
        bit_length = param.get('bit_length')
        data_type = None

        # If this is NOT a composite type and we have already created it, return
        if (subtypes is None) and (param_name in self.type_dict):
            log.warning("Data type {} already defined.".format(param_name))
            return None

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

    def _create_parameterized_type(self, json_dict, type_id=None, arg_id=None, subtypes=None):
        """
        Recursively creates custom type definitions from JSON data and any known subtypes,
        and adds them to the type dictionary. Returns the top-level type and a dictionary of any enumerations.

        @param json_dict: A dictionary containing JSON data defining a data type
        @param type_id: The dictionary key for the name of the type
        @param arg_id: The dictionary key for the definitions of subtypes, if any
        @param subtypes: A dictionary mapping names of subtypes to their types, used in recursive calls
        """
        fields = []
        subtypes = subtypes or {}
        type_enums = {}
        data_type_name = str(json_dict.get(type_id, None))
        parameters = json_dict.get(arg_id, [])

        for param in parameters:
            param_name = param['name']

            if param_name == "Byte" or param_name in fields:
                log.debug("skip param of a known type: {}".format(param_name))
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

        if self.config.log_ccsds_imports:
            if fields:
                log.debug("Creating data type {} with fields {}.".format(data_type_name, [f[0] for f in fields]))
            else:
                log.debug("Creating data type {} with no fields.".format(data_type_name))

        primary_type_names = ('int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64',
                              'float', 'double', 'char', 'string', 'bool', 'boolean', 'address', 'cpuaddr')
        if data_type_name in primary_type_names and data_type_name in self.type_dict:
            log.error("Override of primary data type {} may be a CCDD error!".format(data_type_name))
        elif data_type_name in self.type_dict:
            log.warning("Data type {} is already created, but will be overridden".format(data_type_name))

        data_type = create_type_class(data_type_name, self.ctype_structure, fields)
        self.type_dict[data_type_name] = data_type
        return data_type, type_enums

    def process_telemetry(self, json_dict):
        """
        Parses the contents of a JSON dictionary for a CCSDS telemetry message to dynamically create a new type
        which is added to the type dictionary. Defines a telemetry message with the MID, name, and type.

        @param json_dict: A dictionary containing the JSON data of an exported CCSDS telemetry message
        """
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
                    log.warning("Unknown MID name {} in {}. Skipping this message"
                                .format(tlm_mid_name, self.current_file_name))
            else:
                log.warning("{} has no MID. Skipping this message".format(self.current_file_name))
        except Exception as exception:
            log.error("Failed to create telemetry data type {}: {}".format(tlm_data_type, exception))
            raise CtfTestError("Error in process_telemetry") from exception

    def process_types(self, json_list):
        """
        Parses the contents of a JSON dictionary for type macros, and inserts any aliases, constants, or MID
        mapping into the appropriate dictionaries.

        @note - Only aliases of ctypes which are in the type dictionary will be processed. To process aliases of
        custom types defined in other files, use process_types_second_pass after processing those files.

        @param json_list: A dictionary containing the JSON data of exported CCSDS types
        """
        for typedef in json_list:
            try:
                if 'alias_name' in typedef and 'actual_name' in typedef:
                    # Aliases are type names that evaluate to ctype or custom types. Custom types must be mapped last.
                    alias_name = typedef['alias_name']
                    actual_name = typedef['actual_name']
                    if alias_name not in self.type_dict:
                        if actual_name in ctypes.__dict__:
                            c_type = ctypes.__dict__[actual_name]
                            self.type_dict[alias_name] = c_type
                        elif self.config.log_ccsds_imports:
                            log.debug("Alias {} is not a ctype, skipping...".format(alias_name))
                    elif self.config.log_ccsds_imports:
                        log.debug("Alias {} already defined, skipping...".format(alias_name))
                elif 'constant_name' in typedef and 'constant_value' in typedef:
                    # Constants are CFS macros that evaluate to literal values
                    constant_name = typedef['constant_name']
                    constant_value = typedef['constant_value']
                    if constant_name not in self.type_dict:
                        try:
                            constant_value = ast.literal_eval(constant_value)
                        except (ValueError, SyntaxError):
                            if self.config.log_ccsds_imports:
                                log.debug("Constant {}: {} is not a literal value, preserving as string"
                                          .format(constant_name, constant_value))
                        self.type_dict[constant_name] = constant_value
                    elif self.config.log_ccsds_imports:
                        log.debug("Constant {} already defined, skipping...".format(constant_name))
                elif 'target' in typedef and 'mids' in typedef:
                    # Targets are CFS target names that map MID names to values
                    if typedef['target'] == self.config.ccsds_target:
                        if self.config.log_ccsds_imports:
                            log.info("Found {} MIDs for {}".format(len(typedef['mids']), self.config.ccsds_target))
                        for mid in typedef['mids']:
                            if mid['mid_name'] in self.mids.keys():
                                log.error("Found duplicate MID key: {} with value: {} ".format(
                                    mid['mid_name'], self.mids[mid['mid_name']]))
                            if int(mid['mid_value'], 0) in self.mids.values():
                                log.error("Found duplicate MID value: {}".format(mid['mid_value']))
                            log.debug("Update mids dict with key:{} value:{} ".format(mid['mid_name'],
                                                                                      int(mid['mid_value'], 0)))
                            self.mids.update({mid['mid_name']: int(mid['mid_value'], 0)})
                else:
                    log.error("Invalid type definition in {}".format(self.current_file_name))
            except Exception as exception:
                log.error("Unable to parse type definition in {}: {}".format(self.current_file_name, exception))
                raise CtfTestError("Error in process_types") from exception

    def process_types_second_pass(self, json_list):
        """
        Parses the contents of a JSON dictionary for type aliases only, and adds them to the type dictionary if they
        are not already defined.

        @note - This method should be called after CCSDS command and telemetry messages have been processed so that
        the definitions of those custom types are known.

        @param json_list: A dictionary containing the JSON data of exported CCSDS types
        """
        for typedef in json_list:
            try:
                if 'alias_name' in typedef and 'actual_name' in typedef:
                    # Any aliases left undefined should now evaluate to a custom type
                    alias_name = typedef['alias_name']
                    actual_name = typedef['actual_name']
                    if alias_name not in self.type_dict:
                        if actual_name in self.type_dict:
                            self.type_dict[alias_name] = self.type_dict[actual_name]
                            if self.config.log_ccsds_imports:
                                log.debug("Mapped alias {} to type {}".format(actual_name, alias_name))
                        else:
                            log.error("Unknown alias name {} in {}".format(actual_name, self.current_file_name))
                    elif self.config.log_ccsds_imports:
                        log.debug("Alias {} already defined, skipping...".format(alias_name))
            except Exception as exception:
                log.error("Unable to parse type definition in {}: {}".format(self.current_file_name, exception))
                raise CtfTestError("Error in process_types_second_pass") from exception

    def process_custom_types(self, json_dict):
        """
        Parses the contents of a JSON dictionary for a custom data type which is added to the type dictionary. This type
        may then be referenced by name in other files without redefining its structure.

        @note - json_dict must include the keys "data_type" for the name and "parameters" for the contents regardless
        of whether the data type is to be used in commands or telemetry.

        @note - This method should be called before processing any command and telemetry messages so that the
        definitions of these custom types are known.

        @param json_dict: A dictionary containing the JSON data of an exported data type definition
        """
        if "data_type" not in json_dict:
            raise CtfTestError("Required key data_type not found in {}".format(self.current_file_name))
        if "parameters" not in json_dict:
            raise CtfTestError("Required key parameters not found in {}".format(self.current_file_name))

        try:
            param_class, _ = self._create_parameterized_type(json_dict, type_id="data_type", arg_id="parameters")
            self.type_dict[json_dict['data_type']] = param_class
        except Exception as ex:
            log.error("Unable to parse type definition in {}: {}".format(self.current_file_name, ex))
            raise CtfTestError("Error in process_custom_types") from ex

    def process_ccsds_json_file(self, filename, file_filter=None, second_pass=False):
        """
        Reads JSON from a single file and, if it matches the filter, parses the contents

        @note - Because of interdependency between files, it is necessary to parse macros first for literal values,
        then command and telemetry message types, then macros again for type aliases.

        @param filename: The path to the file to be read
        @param file_filter: A callable that will return True if the file is to be parsed. Pass None to parse all files
        @param second_pass: True if this is the second time parsing type macros, whose types should already be defined
        """
        with open(filename) as file:
            try:
                json_dict = json.load(file)

                if file_filter is None or file_filter(json_dict):
                    if self.config.log_ccsds_imports:
                        log.info("Processing {}".format(filename))
                    # Determine if file is a telemetry or command message
                    try:
                        if self.is_command_msg(json_dict):
                            self.process_command(json_dict)
                        elif self.is_telemetry_msg(json_dict):
                            self.process_telemetry(json_dict)
                        elif self.is_custom_types(json_dict):
                            self.process_custom_types(json_dict)
                        elif second_pass:
                            self.process_types_second_pass(json_dict)
                        else:
                            self.process_types(json_dict)
                    except CtfTestError:
                        log.error("Failed to process json file {} ".format(filename))

            except json.decoder.JSONDecodeError:
                log.error("Invalid JSON CCDD Export File: {}. Skipping".format(file))

    def get_ccsds_messages_from_dir(self, directory):
        """
        Walks through a directory and parses CCSDS command and telemetry messages and type macros
        from the JSON, as appropriate. Creates and returns dictionaries mapping names to these constructs.

        @param directory: The path to the root directory containing CCSDS exports as .json files
        """
        # Get list of JSON Files in the directory
        files = []
        for root, _, file_names in os.walk(directory):
            for basename in file_names:
                if fnmatch.fnmatch(basename, "*.json"):
                    filename = os.path.join(root, basename)
                    files.append(filename)

        # Process only types & macros first, then custom types, then macros again for custom type aliases
        files = sorted(files)
        for file in files:
            self.current_file_name = os.path.basename(file)
            self.process_ccsds_json_file(file, self.is_types_macros)
        for file in files:
            self.current_file_name = os.path.basename(file)
            self.process_ccsds_json_file(file, self.is_custom_types)
        for file in files:
            self.current_file_name = os.path.basename(file)
            self.process_ccsds_json_file(file, self.is_command_tlm)
        for file in files:
            self.current_file_name = os.path.basename(file)
            self.process_ccsds_json_file(file, self.is_types_macros, True)

        # Collect and convert integer values from enum_map and type_dict
        macro_map = dict(filter(lambda item: isinstance(item[1], (int, float, bool, str)), self.type_dict.items()))
        for key, value in self.enum_map.items():
            value = int(value, 0) if isinstance(value, str) else value
            macro_map[key] = value
        return self.mid_map, macro_map
