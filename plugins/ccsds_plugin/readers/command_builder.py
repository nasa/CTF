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

"""
command_builder.py: Provides functionality for building CCSDS Command Messages
"""


class CommandArg(dict):
    """
    Class representing a CCSDS Command Argument

    @param name: argument name
    @param data_type: argument type
    """
    def __init__(self, name, data_type):
        super().__init__()
        self.name = name
        self.data_type = data_type

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)


class CommandCode(dict):
    """
    Class representing a Command Code for a CCSDS Command

    @param name: command code name
    @param code: command code value
    """
    def __init__(self, name, code):
        super().__init__()
        self.cc_name = name
        self.cc_value = code
        self.args = []

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)


class CommandMessage(dict):
    """
    Class representing a CCSDS Command Message
    """
    def __init__(self):
        super().__init__()
        self.command_codes = []

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)


def populate_arg(arg_dict):
    """
    Helper function to construct a CommandArg object
    """
    new_arg = CommandArg(None, None)
    for key, value in arg_dict.items():
        if key != "enumeration":
            new_arg[key] = value

    return new_arg


def populate_command_code(cmd_code_dict):
    """
    Helper function to construct a CommandCode object
    """
    new_code = CommandCode(None, None)
    for key, value in cmd_code_dict.items():
        if key == "cc_parameters":
            for arg in value:
                new_code.args.append(populate_arg(arg))
        else:
            new_code[key] = value
    return new_code


def populate_message(msg_dict):
    """
    Helper function to construct a CommandMessage object, populating the message
    with the respective command codes and arguments.
    """
    new_msg = CommandMessage()
    for key, value in msg_dict.items():
        if key == "cmd_codes":
            for code in value:
                new_msg.command_codes.append(populate_command_code(code))
        elif key == "cmd_parameters":
            new_code = CommandCode("", 0)
            new_msg.command_codes.append(new_code)
            for arg in value:
                new_code.args.append(populate_arg(arg))
        else:
            new_msg[key] = value
    return new_msg
