#!/usr/bin/env python

# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2023 United States Government as represented by the
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
import fnmatch
import json
import os
import sys
import traceback


def check_attribute_order(list1: list, list2: list):
    new_list1 = [k for k in list1 if k in list2]
    new_list2 = [k for k in list2 if k in list1]
    return new_list1 == new_list2


def check_key_existence(dictionary: dict, ordered_key: list):
    for k in dictionary.keys():
        if k not in ordered_key:
            print(f"Need to check attribute definition key={k} {dictionary}")


def update_attribute_order(dictionary: dict, ordered_key: list):
    # check_key_existence(dictionary, ordered_key)
    if not check_attribute_order(ordered_key, list(dictionary.keys())):
        # not in order, first add key-value pairs from ordered_key list
        reordered_dictionary = {k: dictionary[k] for k in ordered_key if k in dictionary}
        # then merge two dictionaries, keeping the order
        reordered_dictionary.update(dictionary)
        return reordered_dictionary
    return None


def update_data_attribute_order(instruction: dict):
    data_ordered_key = ["target", "verification_id", "mid", "cc", "host", "payload_length", "args", "header", "run_args",
                        "variable_name", "tlm_variable", "file", "hex_buffer", "header_variable", "search_str",
                        "operator", "value", "variable_type", "arg1", "arg2", "source_path",
                        "label", "conditions", "prompt",  "source", "destination", "path", "is_regex", "comment"]
    in_order = True
    data = instruction.get("data", None)
    if data:
        reordered_data = update_attribute_order(data, data_ordered_key)
        if reordered_data:
            instruction["data"] = reordered_data
            in_order = False
    return in_order


def update_funcs_attribute_order(funcs, func_key):
    in_order = True
    for k, v in funcs.items():
        reordered_attr = update_attribute_order(v, func_key)
        if reordered_attr:
            funcs[k] = reordered_attr
            in_order = False
        instructions = v.get("instructions", None)
        if instructions:
            in_order &= update_instructions_attribute_order(instructions)
    return in_order


def update_instructions_attribute_order(instructions):
    instruction_ordered_key = ["instruction", "description", "data", 'verify_timeout', "disabled", "wait"]
    funct_ordered_key = ["function","description", "params", "wait"]
    in_order = True
    for i in range(len(instructions)):
        instruction = instructions[i]
        if "function" in instruction:
            ordered_key = funct_ordered_key
        else:
            ordered_key = instruction_ordered_key
            in_order &= update_data_attribute_order(instruction)
        reordered_instruction = update_attribute_order(instruction, ordered_key)
        if reordered_instruction:
            instructions[i] = reordered_instruction
            in_order = False
    return in_order


def update_tests_attribute_order(tests: list, tests_key: list):
    in_order = True
    for i in range(len(tests)):
        reordered_test = update_attribute_order(tests[i], tests_key)
        if reordered_test:
            tests[i] = reordered_test
            in_order = False

        test = tests[i]
        instructions = test.get("instructions", None)
        # no instruction defined
        if not instructions:
            continue
        in_order &= update_instructions_attribute_order(instructions)
    return in_order


def update_file_attribute_order(filepath):
    print(f'{filepath=}')
    # "environment" may be removed from key values
    script_key = ["test_script_number", "test_script_name", "owner", "description", "requirements",  "ctf_options",
                  "test_setup", "environment", "import", "functions", "tests"]

    tests_key = ["test_number", "description", "instructions"]
    function_key = ["description", "varlist", "instructions"]
    json_data = None
    in_order = True
    with open(filepath, 'r') as file:
        try:
            json_data = json.load(file)
            if not check_attribute_order(script_key, list(json_data.keys())):
                in_order = False
            if "tests" in json_data:
                in_order &= update_tests_attribute_order(json_data["tests"], tests_key)
            if "functions" in json_data and json_data["functions"]:
                in_order &= update_funcs_attribute_order(json_data["functions"], function_key)

        except (json.decoder.JSONDecodeError, KeyError):
            print("FAILED TO READ {}".format(filepath))
            print(traceback.format_exc())

    if not in_order:
        with open(filepath, 'w') as file:
            try:
                json_data_ordered = {k: json_data[k] for k in script_key if k in json_data}
                json_string = json.dumps(json_data_ordered, indent=4)
                file.write(json_string)
                print("Updated json attribute order in {}".format(filepath))
            except Exception:
                print("FAILED TO WRITE {}".format(filepath))
                print(traceback.format_exc())


if __name__ == '__main__':
    if not len(sys.argv) > 1:
        print('This script will re-order the attributes of CTF test json files under the provided paths')
        print("Usage: re_order.py [ROOTPATH ...]")
    if sys.version_info < (3, 8):
        print("WARNING: Running an older version of Python ({})."
              "Make sure your CTF virtual environment is activated, as older versions may behave differently."
              .format(sys.version))
        input("Press Enter to continue, or CTRL-C to cancel.")
    for root_path in sys.argv[1:]:
        if not os.path.exists(root_path):
            print("Path {} does not exist, exiting".format(root_path))
            break

        # the path is a file
        if os.path.isfile(root_path) and fnmatch.fnmatch(root_path, "*.json"):
            update_file_attribute_order(root_path)

        # the path is a folder
        if os.path.isdir(root_path):
            for cwd, dirs, files in os.walk(root_path):
                print("Checking files in {}".format(cwd))
                for basename in files:
                    path = os.path.join(cwd, basename)
                    if fnmatch.fnmatch(basename, "*.json"):
                        update_file_attribute_order(path)

        print("Finished")
