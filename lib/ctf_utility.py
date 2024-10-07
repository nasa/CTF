"""
@namespace lib.ctf_utility
Utility library functions
"""

# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2024 United States Government as represented by the
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
import functools
import operator
import os
import re
import sys

from lib.ctf_global import Global
from lib.exceptions import CtfParameterError
from lib.logger import logger as log

operator_map = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
    "%": operator.mod,
    "**": operator.pow,
    "//": operator.floordiv,
    "&": operator.and_,
    "|": operator.or_,
    "^": operator.xor,
    "~": operator.invert,
    "<<": operator.lshift,
    ">>": operator.rshift,
}

type_map = {
    "int": int,
    "float": float,
    "string": str,
    "boolean": bool,
    "list": list,
    "dict": dict
}

MACRO_MARKER = '#'


def expand_path(path):
    """
    Given a directory path, expand the path with the user directory and variables, returning the expanded path
    """
    return os.path.expanduser(os.path.expandvars(path))


def switch_to_ctf_directory():
    """
    Switch the working directory to ctf directory, return ctf directory path
    """
    ctf_real_path = os.path.realpath(sys.argv[0])
    ctf_dir = os.path.dirname(ctf_real_path)
    os.chdir(ctf_dir)
    return ctf_dir


def get_current_instruction_index():
    """
    Return the current instruction execution index
    """
    return Global.current_instruction_index


def set_goto_instruction_index(index):
    """
    Set the instruction execution index in Global, which will be used in the ControlFlow Plugin
    """
    Global.goto_instruction_index = index


def set_variable(variable_name, op_code, value, variable_type=None):
    """
    Set/Update the user defined variable, which will be used in ControlFlow and Variable Plugins
    @ note - variables and values may be converted to other types even if variable_type is not specified
    """
    value = resolve_variable(value)

    user_passed_type = None
    if variable_type and variable_type in type_map:
        user_passed_type = type_map[variable_type]

    # cast values from hex to int conversion
    if variable_type == 'int' and isinstance(value, str):
        try:
            value = int(value, 0)
        except ValueError as exception:
            log.error('Could not cast {} to int type, trigger exception {}'.format(value, exception))
            return False

    if op_code == "=":
        if variable_type:
            if variable_type in type_map:
                try:
                    value = type_map[variable_type](value)
                except (ValueError, TypeError):
                    log.error("Unable to convert value {} to type {}".format(value, variable_type))
                    return False
            else:
                log.error("Unknown variable type {}".format(variable_type))
                return False
        else:
            log.warning("Variable type not specified, interpreting {} as type {}".format(value, type(value).__name__))

        log.info("Set Variable {} = {} ({})".format(variable_name, value, type(value).__name__))
        Global.variable_store[variable_name] = value
    else:
        op_function = operator_map.get(op_code, None)
        if op_function is None:
            log.error("Operator {} not defined in operator_map.".format(op_code))
            return False

        variable = Global.variable_store.get(variable_name, None)
        if variable is None:
            log.error("Variable {} does not exist.".format(variable_name))
            return False

        if user_passed_type and not isinstance(value, user_passed_type):
            log.info("Converting value {} to type {}".format(value, user_passed_type.__name__))
            try:
                value = user_passed_type(value)
            except ValueError:
                log.error("Cannot convert {} to {}! The operation will likely fail.".format(value,
                                                                                            user_passed_type.__name__))

        try:
            new_value = op_function(variable, value)
            # set the type of the new value, if variable_type is valid
            if user_passed_type:
                new_value = user_passed_type(new_value)

            Global.variable_store[variable_name] = new_value
            log.info("Set Variable {} = '{}' {}".format(variable_name, op_code, value))
            log.debug("New value of {} is {} ({})".format(variable_name, new_value, type(new_value).__name__))
        except (ValueError, TypeError):
            log.error("Cannot apply operator {} to variable {} for values {} ".format(op_code, variable, value))
            return False

    return True


def get_variable(variable_name):
    """
    Get the user defined variable, which will be used in variable plugin
    """
    return Global.variable_store.get(variable_name, None)


VAR_MARKER = '$'


def resolve_variable(variable):
    """
    A variable may be passed to an instruction argument as a string "xyz$variable_name$abc",
    Search the global variable_store to evaluate its value.
    """
    if isinstance(variable, str):
        # the evaluated variable may not be a string
        if variable.count(VAR_MARKER) == 2 and variable[0] == VAR_MARKER and variable[-1] == VAR_MARKER:
            variable_to_evaluate = variable[1:-1]
            value_evaluated = get_variable(variable_to_evaluate)
            if value_evaluated is None:
                log.error("Could not resolve variable {} !".format(variable))
                raise CtfParameterError("Could not resolve variable {} with format"
                                        " 'xyz$variable$abc'".format(variable), variable)
            log.info("Variable {} is evaluated to {}".format(variable_to_evaluate, value_evaluated))
            return value_evaluated

        # variable converts to string
        variable_str = variable
        while variable_str.count(VAR_MARKER) > 1:
            variable_to_evaluate = variable_str.split(VAR_MARKER)[1]
            value_evaluated = get_variable(variable_to_evaluate)
            if value_evaluated is None:
                log.error("Could not resolve variable {} !".format(variable))
                raise CtfParameterError("Could not resolve variable {} with format"
                                        " 'xyz$variable$abc'".format(variable), variable)
            log.debug("Variable {} is evaluated to {}".format(variable_to_evaluate, value_evaluated))
            variable_str = variable_str.replace("{0}{1}{0}".format(VAR_MARKER, variable_to_evaluate),
                                                str(value_evaluated))
        if variable.count(VAR_MARKER) > 1:
            log.info("Variable {} is evaluated to {}".format(variable, variable_str))
        return variable_str

    return variable


def resolve_dic_variable(var_obj: dict):
    """
    Recursively resolve the user defined variables in dictionary object.
    The function resolve_variable only resolve str type variables.
    """
    if not isinstance(var_obj, dict):
        return var_obj
    new_object = dict()
    for key, value in var_obj.items():
        resolved_key = resolve_variable(key)
        if isinstance(value, dict):
            resolved_value = resolve_dic_variable(value)
        elif isinstance(value, list):
            resolved_value = [resolve_dic_variable(v) for v in value]
        else:
            resolved_value = resolve_variable(value)
        new_object[resolved_key] = resolved_value
    return new_object


INDEX_PATTERN = r'\[(.*?)\]'


def rgetattr(obj, attr, *args):
    """
    Given an object and an attribute name, return the value of the specified attribute.
    """

    # ENHANCE - there is probably a cleaner solution using regex
    def _getattr(obj, attr):
        if '[' in attr:
            idx = int(re.findall(INDEX_PATTERN, attr)[0], 0)
            attr = attr.split('[')[0]
            return getattr(obj, attr, *args)[idx]
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split('.'))


def set_nested_attr(obj, nested_attr, value):
    """
    Set the attribute of the nested object. If the attr is not valid, raise CtfParameterError exception.
    """
    split_attrs = nested_attr.split('.')
    # Check the attribute
    for i in range(len(split_attrs) - 1):
        if hasattr(obj, split_attrs[i]):
            obj = getattr(obj, split_attrs[i])
        else:
            raise CtfParameterError("Could not find the attribute {} in object".format(nested_attr), nested_attr)

    if hasattr(obj, split_attrs[-1]) and type(getattr(obj, split_attrs[-1])) is type(value):
        setattr(obj, split_attrs[-1], value)
    else:
        raise CtfParameterError("Could not set the attribute {} in object {}".format(nested_attr, obj), nested_attr)
