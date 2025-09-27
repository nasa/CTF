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
# File: ccsds_export_reader.py
#
# Purpose: This file defines the CCSDS Interface to read JSON CCSDS data exported from CCDD.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================

"""
ccsds_export_reader.py: Implements the CCSDS Interface to read JSON CCSDS data exported from CCDD.

- This file is handles reading the raw CCSDS definitions from JSON, and returns an mid map and macro map
   from the given path where the CCSDS definitions are.
"""
import ast
import os
import fnmatch
import json
import ctypes
from pprint import pformat

from lib.logger import logger as log
from lib.exceptions import CtfTestError
from lib.ctf_global import Global
from core_plugins.ccsds_plugin.ccsds_interface import CCSDSInterface

try:
    TLM_FORMATTER = Global.config.get("logging", "tlm_formatter", fallback=None)
    PPRINT_DEPTH = int(Global.config.get("logging", "pprint_depth", fallback="7"))
except (AttributeError, ValueError) as exception:
    log.error("Exception from getting INI logging config")
    TLM_FORMATTER = "compact"
    PPRINT_DEPTH = 7


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


def build_obj_from_ctype(ctype_object):
    # pylint: disable=protected-access
    """
    Build a python dictionary object from a ctypes structure object with mapped attributes.

    @note - Utility function used by __str__ for formatted output.

    @param ctype_object: The ctypes structure object instance being represented
    """
    shadow_obj = dict()
    key = ctype_object.__class__.__name__
    if isinstance(ctype_object, ctypes.Structure):
        val = dict()
        for field in ctype_object._fields_:
            val[field[0]] = build_obj_from_ctype(getattr(ctype_object, field[0]))
        shadow_obj[key] = val
    elif isinstance(ctype_object, ctypes.Array):
        lst = [build_obj_from_ctype(field) for field in ctype_object]
        shadow_obj[key] = lst
    else:
        return ctype_object

    return shadow_obj


def build_str_from_ctype(ctype_object):
    # pylint: disable=protected-access
    """
    Build a string from a ctype object that prints name-value pairs of each field.

    @note - Utility function used by __str__ for formatted output.

    @param ctype_object: The ctypes structure object instance being represented
    """

    max_shown_array = 1000
    string = ""
    name = ctype_object.__class__.__name__
    if hasattr(ctype_object, '_fields_'):
        string = "{}: {{{}}}".format(name, ", ".join(["{}: {}".format(
            field[0], build_str_from_ctype(getattr(ctype_object, field[0]))) for field in ctype_object._fields_]))
    elif hasattr(ctype_object, '_length_'):
        string = "[{}{}]".format(", ".join([build_str_from_ctype(e) for e in ctype_object[:max_shown_array]]),
                                 f"... ({len(ctype_object) - max_shown_array} more)"
                                 if len(ctype_object) > max_shown_array else "")
    else:
        string = str(ctype_object)
    return string


def to_string(self):
    """
    A generic implementation of __str__ for a dynamic type that prints name-value pairs for each of its fields.

    @note - Utility function used by create_type_class to assign as a type method.

    @param self: The object instance being represented
    """
    string = ""
    if TLM_FORMATTER == "pprint":
        dict_obj = build_obj_from_ctype(self)
        string = pformat(dict_obj, sort_dicts=False, depth=PPRINT_DEPTH, width=400)
    else:
        string = build_str_from_ctype(self)
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


def _compare_field(field_a: tuple, field_b: tuple) -> bool:
    # pylint: disable=protected-access
    """
    Comparison of a single ctypes field of the form (name, type). Returns true IFF both fields have the same
    name and type.
    """
    # compare names
    if field_a[0] != field_b[0]:
        return False
    # compare nested fields
    if hasattr(field_a[1], '_fields_') or hasattr(field_b[1], '_fields_'):
        return _compare_ctypes(field_a[1], field_b[1])
    # compare nested arrays
    if hasattr(field_a[1], '_length_') or hasattr(field_b[1], '_length_'):
        return _compare_ctypes(field_a[1], field_b[1])
    # base case: both simple types
    return field_a[1]._type_ == field_b[1]._type_


def _compare_ctypes(type_a: type, type_b: type) -> bool:
    # pylint: disable=protected-access
    """
    Recursive comparison of fields in two ctypes structures. Returns true IFF both objects have fields
    with the same count, order, name, and type.
    """
    # compare arrays
    if hasattr(type_a, '_length_') and hasattr(type_b, '_length_'):
        if hasattr(type_a._type_, '_fields_') or hasattr(type_b._type_, '_fields_'):
            return _compare_ctypes(type_a._type_, type_b._type_)
        return type_a._type_ == type_b._type_ and type_a._length_ == type_b._length_
    # check for mismatched arrays
    if hasattr(type_a, '_length_') or hasattr(type_b, '_length_'):
        return False
    # compare nested fields
    if hasattr(type_a, '_fields_') and hasattr(type_b, '_fields_'):
        if len(type_a._fields_) != len(type_b._fields_):
            return False
        return all([_compare_field(af, bf) for af, bf in zip(type_a._fields_, type_b._fields_)])
    # check for mismatched nested fields
    if hasattr(type_a, '_fields_') or hasattr(type_b, '_fields_'):
        return False
    # base case: both simple types
    return type_a._type_ == type_b._type_


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

        # The parameters for this type were already defined elsewhere
        if not parameters and data_type_name in self.type_dict:
            log.debug("Found definition for type {}".format(data_type_name))
            return self.type_dict[data_type_name], None
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

        data_type = create_type_class(data_type_name, self.ctype_structure, fields)

        primary_type_names = ('int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64',
                              'float', 'double', 'char', 'string', 'bool', 'boolean', 'address', 'cpuaddr')
        if data_type_name in self.type_dict:
            if data_type_name in primary_type_names:
                log.error("Override of primary data type {} may be a CCDD error!".format(data_type_name))
            elif not _compare_ctypes(data_type, self.type_dict[data_type_name]):
                log.error("Override of custom data type {} may be a CCDD error! "
                          "Compare definitions of this type in other files".format(data_type_name))

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
                            log.debug("Update mids dict with key:{} value:{} ({})".format(mid['mid_name'],
                                                                                          int(mid['mid_value'], 0),
                                                                                          hex(int(mid['mid_value'], 0)))
                                      )
                            self.mids.update({mid['mid_name']: int(mid['mid_value'], 0)})
                elif '_export_control_01_' in typedef:
                    pass # Do nothing.
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
            for basename in sorted(file_names):
                if fnmatch.fnmatch(basename, "*.json"):
                    filename = os.path.join(root, basename)
                    files.append(filename)

        # Seperate the valid files containing type definitions from ones containing type alias/macros.
        types_structs_files = []
        types_macros_files = []
        for file in files:
            with open(file) as opened_file:
                try:
                    json_dict = json.load(opened_file)

                    if self.is_command_tlm(json_dict) or self.is_custom_types(json_dict):
                        types_structs_files.append(file)
                    else:
                        types_macros_files.append(file)

                except json.decoder.JSONDecodeError:
                    log.error("Invalid JSON CCDD Export File: {}. Skipping file..".format(file))

        # Sort the files based on file dependencies
        sorted_types_structs_files = self.get_sorted_file_order(types_structs_files)

        # Process only types & macros first.
        for file in types_macros_files:
            self.current_file_name = os.path.basename(file)
            self.process_ccsds_json_file(file, self.is_types_macros)

        # Process the sorted definition files (cmd/tlm & custom types)
        for file in sorted_types_structs_files:
            self.current_file_name = os.path.basename(file)
            self.process_ccsds_json_file(file, self.is_custom_types)
        for file in sorted_types_structs_files:
            self.current_file_name = os.path.basename(file)
            self.process_ccsds_json_file(file, self.is_command_tlm)

        # Process macros again for custom type aliases.
        for file in types_macros_files:
            self.current_file_name = os.path.basename(file)
            self.process_ccsds_json_file(file, self.is_types_macros, True)

        # Collect and convert integer values from enum_map and type_dict
        macro_map = dict(filter(lambda item: isinstance(item[1], (int, float, bool, str)), self.type_dict.items()))
        for key, value in self.enum_map.items():
            value = int(value, 0) if isinstance(value, str) else value
            macro_map[key] = value
        return self.mid_map, macro_map

    def get_all_parameters(self, json_dict, type_to_dependent_types, filename,
                           param_type_id, data_type_name, arg_id=None):
        """
        Given a json dict pertaining to a cmd/tlm/custom type json file, recursively retrieves all the parameters

        @note: Some type definitions that are referenced by the provided definition files are stored in
        type alias / macro files. This function does not account for these definitions,
        since those files are always processed first anyway.

        @param json_dict: A dictionary containing JSON data defining a data type
        @param type_to_dependent_types: Stores a list of dependent types for each type, along with the filename.
        @param filename: The path to the file to be read
        @param param_type_id: The dictionary key for the name of the nested parameter type
        @param data_type_name: The name of the datatype being parsed
        @param arg_id: The dictionary key for the definitions of subtypes, if any
        """
        parameters = json_dict.get(arg_id, [])

        # Handle CMD files with no CCs
        cmd_data_type_name = json_dict.get("cmd_data_type", None)
        if cmd_data_type_name and not parameters:
            # If this type is not a primitive type, create dependency
            if not hasattr(ctypes, ctypes_name(cmd_data_type_name)):
                type_to_dependent_types[json_dict["cmd_mid_name"]] = ([cmd_data_type_name], filename)
            return

        if data_type_name not in type_to_dependent_types:
            type_to_dependent_types[data_type_name] = ([], filename)

        for param in parameters:
            nested_type_name = param[param_type_id] if param_type_id in param else param['data_type']

            # Ignore C types
            if hasattr(ctypes, ctypes_name(nested_type_name)):
                continue

            # Check for nested parameters
            has_params = 'parameters' in param and len(param['parameters']) > 0
            # Also check for nested command parameters
            has_cmd_params = 'cc_parameters' in param and len(param['cc_parameters']) > 0

            # Retrieve nested parameters if any
            if has_params or has_cmd_params:
                if nested_type_name not in type_to_dependent_types:
                    type_to_dependent_types[nested_type_name] = ([], filename)

                arg_id = 'cc_parameters' if has_cmd_params else 'parameters'
                self.get_all_parameters(param, type_to_dependent_types, filename,
                                        param_type_id, nested_type_name, arg_id)
            else:
                # This is a reference to a type - update dict
                type_to_dependent_types[data_type_name][0].append(nested_type_name)

    def get_prereqs(self, file, file_to_prereqs_map, sorted_files, visited, current_path):
        """
        Recursive function that sorts files based on dependencies.

        @note - appends to the provided 'sorted' collection

        @param file: The path to the JSON Definition file to be read.
        @param file_to_prereqs_map: Stores a list of prerequisite file(s) that need to be processed before each file.
        @param sorted_files: A list that holds the sorted order of files.
        @param visited: A set that stores the names of visited files.
        @param current_path: A set that stores the names of files visited in the current recursive stack
        for cycle detection.
        """
        # Base case - file already processed
        if file in visited:
            return

        visited.add(file)
        current_path.add(file)

        # Grab all prerequisites for this file
        for prereq in file_to_prereqs_map[file]:
            # Detect circular reference
            if prereq in current_path:
                log.error("Circular reference detected to JSON CCDD File: {}".
                          format(os.path.basename(prereq)))
            else:
                # Process prereqs for this file
                self.get_prereqs(prereq, file_to_prereqs_map, sorted_files, visited, current_path)

        current_path.remove(file)

        # All prerequisites processed - now we can add this file to sorted order
        sorted_files.append(file)

    def parse_definition_file(self, filename, type_to_dependent_types):
        """
        Reads the (valid) json file, determines the file type, and makes a call to a recursive function to
        iterate over the parameters using the file type information.

        @note - Only parses definition files: command, telemetry, and custom types.
        @note - Assumes json file has already been validated to be in correct JSON format.

        @param filename: The path to the JSON Definition file to be read.
        @param type_to_dependent_types: Stores a list of dependent types for each type, along with the filename.
        """
        with open(filename) as file:
            json_dict = json.load(file)
            type_id = None
            arg_id = None
            param_type_id = 'data_type'

            # filter and set variables based on file type
            if self.is_command_msg(json_dict):
                # CMD with no command code
                if "cmd_data_type" in json_dict:
                    type_id = "cmd_data_type"
                    arg_id="cmd_parameters"
                else:
                    type_id = "cmd_mid_name"
                    param_type_id = "cc_data_type"
                    arg_id = "cmd_codes"
            elif self.is_telemetry_msg(json_dict):
                type_id = "tlm_data_type"
                arg_id = "tlm_parameters"
            elif self.is_custom_types(json_dict):
                type_id = "data_type"
                arg_id = "parameters"
            else:
                # Not a definition file - do not process
                return

            data_type_name = str(json_dict.get(type_id, None))
            self.get_all_parameters(json_dict, type_to_dependent_types, filename,
                                    param_type_id, data_type_name, arg_id)

    def get_sorted_file_order(self, types_structs_files):
        """
        Given a list of files (paths), determines the dependencies b/w files and returns a sorted list
        representing a valid order for the files to be processed in.

        @param types_structs_files: A list of paths to the JSON files that contain type definitions
        (i.e, cmd/tlm & custom type files)
        """
        # Stores a list of dependent types for each type, along with the filename
        # in the format {type: ([list of dependent types], "filename")}
        type_to_dependent_types = {}

        # Populate {type - dependent_types} dict
        for file in types_structs_files:
            self.parse_definition_file(file, type_to_dependent_types)

        # Stores a list of prerequisite file(s) that need to be processed before this file
        file_to_prereqs_dict = {file: [] for file in types_structs_files}

        # Populate the file-prereqs dictionary
        for _, (dependent_types, filename) in type_to_dependent_types.items():
            for dependent_type in dependent_types:
                if dependent_type in type_to_dependent_types:
                    file_with_dependent_def = type_to_dependent_types[dependent_type][1]
                    if file_with_dependent_def not in file_to_prereqs_dict[filename]:
                        file_to_prereqs_dict[filename].append(file_with_dependent_def)

        # Sort the remaining definition files and add to sorted list
        visited = set()
        current_path = set()
        sorted_types_structs_files = []
        for file in types_structs_files:
            self.get_prereqs(file, file_to_prereqs_dict, sorted_types_structs_files, visited, current_path)

        return sorted_types_structs_files
