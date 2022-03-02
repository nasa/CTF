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
import fnmatch
import itertools
import json
import os
import sys
import traceback

try:
    from configobj import ConfigObj
except ImportError:
    ConfigObj = None


def update_json_file(filepath):
    json_data = None
    count = 0
    with open(filepath, 'r') as file:
        try:
            json_data = json.load(file)
            if "tests" in json_data or "functions" in json_data:
                if "command_watch_list" in json_data:
                    del json_data["command_watch_list"]
                    count += 1
                if "telemetry_watch_list" in json_data:
                    del json_data["telemetry_watch_list"]
                    count += 1
                for j in itertools.chain(json_data.get("functions", {}).values(), json_data.get("tests", [])):
                    for inst in j.get("instructions"):
                        if inst.get("instruction") == "SendInvalidLengthCfsCommand":
                            inst["instruction"] = "SendCfsCommandWithPayloadLength"
                            count += 1
                        elif inst.get("instruction") == "SetUserVariableFromTlm" and "user_variable" in inst["data"]:
                            inst["data"]["variable_name"] = inst["data"].pop("user_variable", None)
                            count += 1
                        elif inst.get("instruction") in ["CheckEvent", "CheckNoEvent"] and "args" not in inst["data"]:
                            args = {
                                "app": inst["data"].pop("app", None),
                                "id": inst["data"].pop("id", None),
                                "msg": inst["data"].pop("msg", None),
                                "msg_args": inst["data"].pop("msg_args", None),
                                "is_regex": inst["data"].pop("is_regex", None)
                            }
                            inst["data"]["args"] = [{k: v for k, v in args.items() if v is not None}]
                            count += 1
                        # now inst["data"]["args"] is a list of objects, rename it if necessary.
                        if inst.get("instruction") in ["CheckEvent", "CheckNoEvent"] and "args" in inst["data"]:
                            args = inst["data"]['args']
                            for i in range(len(args)):
                                arg = args[i]
                                if "app" in arg or "id" in arg or "msg" in arg or "msg_args" in arg:
                                    count += 1
                                app_name_value = arg["app_name"] if "app_name" in arg else arg.pop("app", None)
                                event_id_value = arg["event_id"] if "event_id" in arg else arg.pop("id", None)
                                event_str_value = arg["event_str"] if "event_str" in arg else arg.pop("msg", None)
                                event_str_args_value = arg["event_str_args"] if "event_str_args" in arg else arg.pop("msg_args", None)
                                is_regex_value = arg.pop("is_regex", None)
                                temp_arg = {
                                    "app_name": app_name_value,
                                    "event_id": event_id_value,
                                    "event_str": event_str_value,
                                    "event_str_args": event_str_args_value,
                                    "is_regex": is_regex_value
                                }
                                copied_arg = {k: v for k, v in temp_arg.items() if v is not None}
                                args[i] = copied_arg
            else:
                print("{} is not a test script".format(filepath))
        except (json.decoder.JSONDecodeError, KeyError):
            print("FAILED TO READ {}".format(filepath))
            print(traceback.format_exc())

    if count:
        with open(filepath, 'w') as file:
            try:
                file.write(json.dumps(json_data, indent=4))
                print("Updated {} elements in {}".format(count, filepath))
            except Exception:
                print("FAILED TO WRITE {}".format(filepath))
                print(traceback.format_exc())


def update_ini_file(filepath):
    config = ConfigObj(filepath)
    config.write_empty_values = True
    count = 0
    for section in config:
        if config[section].get('cfs_protocol') == 'local' and 'cfs_ram_drive_path' not in config[section]:
            config[section]["cfs_ram_drive_path"] = "/dev/shm/osal:RAM"
            config[section].comments.update(
                {"cfs_ram_drive_path": ["", "The ram drive path to be deleted. It is only needed, when '-RPR' "
                                            "argument is not included in cfs_run_args.",
                                        "It only applies on Linux targets."]}
            )
            count += 1

        if 'cfs_protocol' in config[section] and 'telemetry_debug' not in config[section]:
            config[section]["telemetry_debug"] = "false"
            config[section].comments.update(
                {"telemetry_debug": ["", "Log every telemetry packet received? "]}
            )
            count += 1

        if config[section].get('cfs_protocol') == 'sp0':
            if not config[section].get("stop_command"):
                config[section]["stop_command"] = "reboot()"
                config[section].comments.update({
                    "stop_command": ["", "Command to be issued when CFS is shut down"]
                })
                count += 1
            if not config[section].get("auto_start"):
                config[section]["auto_start"] = "False"
                config[section].comments.update(
                    {"auto_start": ["", "Manual software loading will be skipped during startup"]}
                )
                count += 1
    if count:
        try:
            config.write()
            print("Updated {} options in {}".format(count, filepath))
        except Exception:
            print("FAILED TO WRITE {}".format(filepath))
            print(traceback.format_exc())


if __name__ == '__main__':
    if not len(sys.argv) > 1:
        print('This script will find and update .json and .ini files under the provided paths to comply with CTF v1.4')
        print("Usage: python upgrade_v1_4.py [ROOTPATH ...]")
    if not ConfigObj:
        print("Python package configobj not found: INI files will not be updated. Install with 'pip install configobj'")
    for root_path in sys.argv[1:]:
        if not os.path.exists(root_path):
            print("Path {} does not exist, exiting".format(root_path))
            break
        for cwd, dirs, files in os.walk(root_path):
            print("Checking files in {}".format(cwd))
            for basename in files:
                path = os.path.join(cwd, basename)
                if fnmatch.fnmatch(basename, "*.json"):
                    update_json_file(path)
                elif fnmatch.fnmatch(basename, "*.ini") and ConfigObj:
                    update_ini_file(path)
        print("Finished")
