"""
@namespace plugins.control_flow_plugin
The Control-Flow Plugin provides the functionality of CTF control flow statement,
including looping and conditional statements.
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


from lib import ctf_utility
from lib.ctf_global import Global
from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log
from plugins.variable_plugin.variable_plugin import VariablePlugin


class ControlFlowPlugin(Plugin):
    """
    The ControlFlow Plugin Class Definition

    @note The Control-Flow Plugin provides the functionality of CTF control flow statement,
    including looping and conditional statements.

    @note The custom plugin class *must* inherit from the Plugin base-class.

    @note All plugin functions mapped to a test instruction *must* return true/false to indicate pass/fail of
        that instruction.
    """

    def __init__(self):
        """
        Constructor of ControlFlow plugin.

        @note The __init__ function is called once a plugin is loaded.

        @note The __init__ function should not reference/interact with any other plugin since the other plugin may not
            be loaded at this stage.

        @note The constructor of a plugin must define the following fields:
            - name
            - description
            - command map: dictionary mapping CTF instructions to a tuple defining the
                          python function to use for that instruction, and a list of argument types
            - [optional] verify_required_commands: List of instructions that require verification (i.e polling
            until verification passes or timeout.
            - other class variables that can store state, etc...
        """
        super().__init__()

        ## Plugin Name
        self.name = "ControlFlow Plugin"

        ## Plugin Description
        self.description = "CTF ControlFlow Plugin"

        ## Plugin Command Map
        self.command_map = {
            #   "GoTo": (self.control_flow__goto, [ArgTypes.number]),
            #   "ControlFlowDo": (self.control_flow_do, []),
            #   "ControlFlowWhile": (self.control_flow_while, [ArgTypes.string, ArgTypes.string, ArgTypes.other,
            #                                                  ArgTypes.number]),
            # "ConditionalGoTo": (self.control_flow_conditional_goto, [ArgTypes.string, ArgTypes.string, ArgTypes.other,
            #                                                         ArgTypes.number, ArgTypes.number]),
            "BeginLoop": (self.begin_loop, [ArgTypes.string, ArgTypes.condition]),
            "EndLoop": (self.end_loop, [ArgTypes.string])
        }

        self.begin_loop_index = None

    def initialize(self):
        """
        Initialize implementation for the ControlFlow plugin.

        @note The initialize function is called by the CTF plugin manager *after* all plugins have been loaded.

        @note This function may interact with other plugins, since all plugins have been loaded at this stage.

        @return bool: True if successful, False otherwise.
        """
        log.info("Initialized ControlFlow Plugin!")
        return True

    @staticmethod
    def control_flow_goto(command_index):
        """
        Deprecated function, may be removed in future.

        @return bool: always True .
        """
        log.info("Setting next instruction index: {}".format(command_index))
        ctf_utility.set_goto_instruction_index(command_index)
        return True

    @staticmethod
    def control_flow_conditional_goto(variable_name, operator, value, true_label='', false_label=''):
        """
        Deprecated function, may be removed in future.

        @return bool: always True .
        """
        if true_label == '' and false_label == '':
            log.error("Could not both true_label and false_label be '' ")
            return False

        op_func = ctf_utility.operator_map.get(operator, None)
        variable_value = ctf_utility.get_variable(variable_name)
        if variable_value is None:
            log.error("User defined variable {} does not exist!".format(variable_name))
            return False

        log.info("Variable {} = {}".format(variable_name, value))
        status = op_func(variable_value, value)
        log.info("Checking {} {} {} => {}".format(variable_value, operator, value, status))
        # ENHANCE Check index out of range
        if status:
            if true_label != '':
                index = Global.goto_label_map[true_label]
                ctf_utility.set_goto_instruction_index(index)
        else:
            if false_label != '':
                index = Global.goto_label_map[false_label]
                ctf_utility.set_goto_instruction_index(index)

        return True

    def control_flow_do(self):
        """
        Deprecated function, may be removed in future.

        @return bool: always True .
        """
        log.info("Starting Do-While...")
        self.begin_loop_index = ctf_utility.get_current_instruction_index() + 1
        return True

    @staticmethod
    def begin_loop(label, conditions):
        """
        Create a loop entry point. The loop is identified by a unique label.
        The BeginLoop must be in pairs with EndLoop instruction. The loop condition is defined in parameter
        "conditions" as a list of variables and the associated comparison operations. The condition is True,
        only if all comparison operations are True.

        @param label: a user defined label (example: "LOOP_1")
        @param conditions: a list of comparison conditions. Each includes "name", "operator" and "value".
         (example: {"name": "my_var", "operator": "<", "value": 20})

        @return bool: always True .
        """

        log.info("Begin_loop instruction is labeled with '{}'".format(label))
        control_flow = Global.label_map[label]
        status = True

        if isinstance(conditions, dict):
            # instruction = conditions
            # log.info("Execute instruction {}... ".format(instruction))
            # status = Global.plugin_manager.find_plugin_for_command_and_execute(instruction)
            # log.info("Wrapped instruction execution status: {} ".format(status))
            # condition as test instruction result is disabled
            # conditions is a test instruction
            status = False
        elif isinstance(conditions, list):
            for condition in conditions:
                status = status and VariablePlugin.check_user_defined_variable(condition['variable'],
                                                                               condition['compare'],
                                                                               condition['value'])
            log.info("{} ".format(conditions))

        if status:
            log.info("Continuing Loop...  Proceed To The Next Test Instruction")
            Global.label_map[label][2] = True
        else:
            log.info("Ending Loop... Jump to the End_loop")
            Global.label_map[label][2] = False
            ctf_utility.set_goto_instruction_index(control_flow[1])

        return True

    @staticmethod
    def end_loop(label):
        """
       Create a loop exit point. It must match a BeginLoop instruction with the same label.
       If the looping condition in BeginLoop is False, the control flow jumps to the corresponding EndLoop instruction,
       and exits the loop.

        @param label: a user defined label (example: "LOOP_1")

        @return bool: always True
        """
        # Global.label_map dict is set by lib.test.process_control_flow_label
        # each item in Global.label_map includes 3 elements: instruction "BeginLoop" index (int);
        # instruction "EndLoop" index (int); and loop_condition (bool)
        if Global.label_map[label][2]:
            log.info("Continuing Loop... Jump to the Begin_loop instruction labeled with '{}' ".format(label))
            ctf_utility.set_goto_instruction_index(Global.label_map[label][0])
        else:
            log.info("Ending Loop... ")
        return True

    def control_flow_while(self, variable_name, operator, value):
        """
        Deprecated function, may be removed in future.

        @return bool: always True .
        """
        status = VariablePlugin.check_user_defined_variable(variable_name, operator, value)
        # If the while comparison passed, go to the do instruction index + 1
        if status:
            log.info("Continuing Do-While...")
            ctf_utility.set_goto_instruction_index(self.begin_loop_index)
        else:
            log.info("Ending Do-While...")
        return True

    # ENHANCE - Implement cFS capabilities and process variable markers (maybe ${my_var})

    def shutdown(self):
        """
        Shutdown implementation for the controlflow plugin.
        @note The shutdown function is called by the CTF plugin manager upon completion of a test run.
        @note The shutdown function can be exposed to test scripts by adding it to the command map.
        """
        log.info("Optional shutdown/cleanup implementation for ControlFlow Plugin")
