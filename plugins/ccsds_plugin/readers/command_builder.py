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


import json
from collections import OrderedDict


class idGen():
    currentID = 0

    @classmethod
    def gen(cls):
        cls.currentID += 1
        return cls.currentID


class commandArg(dict):
    # List of JSON attributes to be written to the JSON file
    jsonList = ['name', 'description', 'units', 'data_type', 'array_size', 'bit_length',
                'min_val', 'max_val', 'default_value', 'verification_test_num', 'enumeration']

    accessList = ['public', 'private', 'protected']

    def __init__(self, name, data_type):
        self.name = name
        self.description = None
        self.units = None
        self.data_type = data_type
        self.array_size = None
        self.bit_length = None
        # list of "enum" namedtuples
        self.enumeration = []
        self.min_val = None
        self.max_val = None
        self.default_value = None
        self.verification_test_num = None
        self.access = commandArg.accessList[0]
        # Used to ensure uniqueness
        self.ID = idGen.gen()

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    # ----------------------- JSON Functions ----------------------------------
    @classmethod
    def toJsonDict(cls, cmdArg):
        outDict = OrderedDict()
        for attr in cls.jsonList:
            if attr == 'enumeration':
                outDict[attr] = cls.enumToJsonDict(cmdArg.enumeration)
            else:
                outDict[attr] = getattr(cmdArg, attr)
        return outDict

    @classmethod
    def fromJson(cls, argDict):
        newArg = cls(None, None)
        for key, value in argDict.iteritems():
            if key == "enumeration":
                for enum in value:
                    newArg.addEnum(enum['value'], enum['label'])
            else:
                newArg[key] = value
        return newArg

    @staticmethod
    def enumToJsonDict(enumList):
        outList = []
        for enum in enumList:
            outDict = OrderedDict()
            outDict['value'] = enum.value
            outDict['label'] = enum.label
            outList.append(outDict)
        # sort by numerical order
        outList.sort(key=lambda item: item['value'])
        return outList

class commandCode(dict):
    # List of JSON attributes to be written to the JSON file
    jsonList = ['cc_name', 'cc_value', 'cc_description', 'verification_test_num',
                'is_commandable_from_ground', 'is_class']

    def __init__(self, name, code, parentRef=None):
        self.cc_name = name
        self.cc_value = code
        self.cc_description = None
        self.verification_test_num = None
        self.is_commandable_from_ground = False
        self.is_class = False
        self.messageRef = parentRef
        self.args = []

        # Used to ensure uniqueness
        self.ID = idGen.gen()

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    # ------------------------ JSON Funcitons ----------------------------------
    @classmethod
    def toJsonDict(cls, cc):
        outDict = OrderedDict()
        for attr in cls.jsonList:
            outDict[attr] = getattr(cc, attr)
        outDict['args'] = []
        for arg in cc.args:
            outDict['args'].append(commandArg.toJsonDict(arg))
        return outDict

    @classmethod
    def fromJson(cls, cmdCodeDict, subClass=commandArg):
        newCode = cls(None, None)
        for key, value in cmdCodeDict.iteritems():
            if key == "args":
                for arg in value:
                    newCode.args.append(subClass.fromJson(arg))
            else:
                newCode[key] = value
        return newCode

    # ------------------------ GUI Functions -----------------------------------
    def assignCode(self, codeInt):
        # print(codeInt)
        # print(int(codeInt))
        codeHex = hex(codeInt)
        codeHex = codeHex.rstrip('L')
        if len(codeHex) < 4:
            codeHex = '0x0' + codeHex.split('x')[1]
        self.code = codeHex
        return

    def moveArgUp(self, arg):
        index = self.args.index(arg)
        print(index)
        if index != 0:
            item = self.args.pop(index)
            self.args.insert(index - 1, item)
            return True
        else:
            return False

    def moveArgDown(self, arg):
        if arg != self.args[-1]:
            index = self.args.index(arg)
            print(index)
            item = self.args.pop(index)
            self.args.insert(index + 1, item)
            return True
        else:
            return False

    def addBlankArg(self):
        self.args.append(commandArg(None, None))
        return True


class commandMessage(dict):
    # List of JSON attributes to be written to the JSON file
    jsonList = ['destination_system', 'cmd_mid_name', 'cmd_mid',
                'inheritance', 'cmd_description']

    def __init__(self, destination_system):
        self.destination_system = destination_system
        self.cmd_mid_name = None
        self.cmd_mid = None
        self.inheritance = None
        self.cmd_description = None
        self.command_codes = []
        self.status_enums = []
        # Used to ensure uniqueness
        self.ID = idGen.gen()

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    # Class method ensures that correct jsonList will be used always
    @classmethod
    def toJson(cls, cmdMsg):
        outDict = OrderedDict()
        outDict['is_cmd'] = True
        for attr in cls.jsonList:
            outDict[attr] = getattr(cmdMsg, attr)
        outDict['command_codes'] = []
        # pdb.set_trace()
        cmdMsg.sortCodes()
        for cc in cmdMsg.command_codes:
            outDict['command_codes'].append(commandCode.toJsonDict(cc))
        outDict['status_enums'] = commandArg.enumToJsonDict(cmdMsg.status_enums)
        # pdb.set_trace()
        return json.dumps(outDict, indent=4)

    @classmethod
    def fromJson(cls, msgDict, codeClass=commandCode, argClass=commandArg):
        newMsg = cls(None)
        for key, value in msgDict.iteritems():
            if key == "command_codes":
                for code in value:
                    newMsg.command_codes.append(codeClass.fromJson(code, argClass))
            if key == 'is_cmd':
                pass
            else:
                newMsg[key] = value
        return newMsg

    def sortCodes(self):
        self.command_codes.sort(key=lambda x: int(x.code.split('x')[1].strip('L'), 16))

    # ------------------------ GUI Functions -----------------------------------
    def createBlankCode(self):
        newCode = None
        if len(self.command_codes) > 0:
            codes = []
            for code in self.command_codes:
                codes.append(int(code.code.split('x')[1].strip('L'), 16))
            codes.sort()
            newNum = hex(codes[-1] + 1)
            # print(newNum)
            if len(newNum.split('x')[1]) < 2:
                newNum = '0x0' + newNum.split('x')[1]
            newCode = commandCode(None, newNum)
        else:
            newCode = commandCode(None, '0x00')
        return newCode

    def addBlankCode(self):
        newCode = None
        if len(self.command_codes) > 0:
            codes = []
            for code in self.command_codes:
                codes.append(int(code.code.split('x')[1], 16))
            codes.sort()
            newNum = hex(codes[-1] + 1)
            if len(newNum.split('x')[1]) < 2:
                newNum = '0x0' + newNum.split('x')[1]
            newCode = commandCode(None, newNum)
            self.command_codes.append(newCode)
        else:
            newCode = commandCode(None, '0x00')
            self.command_codes.append(newCode)
        return newCode

    def validateCommandCode(self, codeInt):
        # If this code is the only one in the list
        # No need to validate
        if len(self.command_codes) > 1:
            codes = []
            for code in self.command_codes:
                codes.append(int(code.code.split('x')[1], 16))
            if codeInt in codes:
                return False
        return True

    def deleteCode(self, cc):
        self.command_codes.remove(cc)
        cc.args = []
        # Reassign codes
        # for ii in range(len(self.command_codes)):
        #     newNum = hex(ii)
        #     if len(newNum.split('x')[1]) < 2:
        #         newNum = '0x0' + newNum.split('x')[1]
        # self.command_codes[ii].code = newNum
        return

    def printStatus(self):
        outList = []
        # print(self.enumeration)
        for enumeration in self.status_enums:
            outList.append('%s|%s' % (enumeration.value, enumeration.label))
        return ',\n'.join(outList)


def populateArg(argDict):
    newArg = commandArg(None, None)
    for key, value in argDict.items():
        if key == "enumeration":
            if "definition" in value:
                value = value["definition"]
            for enum in value:
                newArg.addEnum(enum['value'], enum['label'])
        else:
            newArg[key] = value

    return newArg
def populateCommandCode(cmdCodeDict):
    newCode = commandCode(None, None)
    for key, value in cmdCodeDict.items():
        if key == "cc_parameters":
            for arg in value:
                newCode.args.append(populateArg(arg))
        else:
            newCode[key] = value
    return newCode

def populateMessage(msgDict):
    newMsg = commandMessage(None)
    for key, value in msgDict.items():
        if key == "cmd_codes":
            for code in value:
                newMsg.command_codes.append(populateCommandCode(code))
        elif key == "cmd_parameters":
            newCode = commandCode("", 0)
            newMsg.command_codes.append(newCode)
            for arg in value:
                newCode.args.append(populateArg(arg))
        else:
            newMsg[key] = value
    return newMsg