"""
@namespace lib.ctf_utility
Utility library functions
"""

# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2021 United States Government as represented by the
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
from lib.ctf_global import Global
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
}


def expand_path(path):
    """
    Given a directory path, expand the path with the user directory and variables, returning the expanded path
    """
    return os.path.expanduser(os.path.expandvars(path))


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


def set_variable(variable_name, op_code, value):
    """
    Set/Update the user defined variable, which will be used in ControlFlow and Variable Plugins
    """
    if op_code == "=":
        log.info("Set Variable {} {} {}".format(variable_name, op_code, value))
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
        Global.variable_store[variable_name] = op_function(variable, value)
        log.info("Set Variable {} = '{}' {}".format(variable_name, op_code, value))
    return True


def get_variable(variable_name):
    """
    Get the user defined variable, which will be used in variable plugin
    """
    return Global.variable_store.get(variable_name, None)


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
