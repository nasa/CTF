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

            if "test_name" in json_data:
                count += 1

            if "test_number" in json_data:
                count += 1

            if "ctf_options" in json_data and "verif_timeout" in json_data["ctf_options"]:
                json_data["ctf_options"]["verify_timeout"] = json_data["ctf_options"]["verif_timeout"]
                del json_data["ctf_options"]["verif_timeout"]
                count += 1

            if "tests" in json_data or "functions" in json_data:
                if "command_watch_list" in json_data:
                    del json_data["command_watch_list"]
                    count += 1
                if "telemetry_watch_list" in json_data:
                    del json_data["telemetry_watch_list"]
                    count += 1
                for j in itertools.chain(json_data.get("functions", {}).values(), json_data.get("tests", [])):
                    if "case_number" in j:
                        count += 1

                    for inst in j.get("instructions"):
                        # rename "timeout" to "verify_timeout"
                        if "timeout" in inst:
                            inst["verify_timeout"] = inst.pop("timeout")
                            count += 1

                        if inst.get("instruction") == "SendInvalidLengthCfsCommand":
                            inst["instruction"] = "SendCfsCommandWithPayloadLength"
                            count += 1
                        elif inst.get("instruction") == "SetUserVariableFromTlm" and "user_variable" in inst["data"]:
                            inst["data"]["variable_name"] = inst["data"].pop("user_variable", None)
                            count += 1
                        elif inst.get("instruction") in ["CheckEvent", "CheckNoEvent"] and "args" not in inst["data"]:
                            args = {
                                "app_name": inst["data"].pop("app", None),
                                "event_id": inst["data"].pop("id", None),
                                "event_str": inst["data"].pop("msg", None),
                                "event_str_args": inst["data"].pop("msg_args", None),
                                "is_regex": inst["data"].pop("is_regex", None)
                            }
                            inst["data"]["args"] = [{k: v for k, v in args.items() if v is not None}]
                            count += 1
            else:
                print("{} is not a test script".format(filepath))
        except (json.decoder.JSONDecodeError, KeyError):
            print("FAILED TO READ {}".format(filepath))
            print(traceback.format_exc())

    if count:
        with open(filepath, 'w') as file:
            try:
                # use inline replace for renamed keys to avoid reordering
                json_string = json.dumps(json_data, indent=4)\
                    .replace('"test_number"', '"test_script_number"')\
                    .replace('"test_name"', '"test_script_name"')\
                    .replace('"case_number"', '"test_number"')
                file.write(json_string)
                print("Updated {} elements in {}".format(count, filepath))
            except Exception:
                print("FAILED TO WRITE {}".format(filepath))
                print(traceback.format_exc())


def update_ini_file(filepath):
    config = ConfigObj(filepath)
    config.write_empty_values = True
    count = 0
    for section in config:
        if (section == 'cfs' or config[section].get('cfs_protocol') == 'local')\
                and 'cfs_ram_drive_path' not in config[section]:
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
            if "stop_command" not in config[section]:
                config[section]["stop_command"] = "reboot()"
                config[section].comments.update({
                    "stop_command": ["", "Command to be issued when CFS is shut down"]
                })
                count += 1
            if "auto_start" not in config[section]:
                config[section]["auto_start"] = "False"
                config[section].comments.update(
                    {"auto_start": ["", "Manual software loading will be skipped during startup"]}
                )
                count += 1
            if "pre_reboot_command" not in config[section]:
                config[section]["pre_reboot_command"] = "cmd rm -r /ffx0/URM/*"
                config[section].comments.update({
                    "pre_reboot_command": ["",
                                           "Command to be issued before a reboot when connecting to the SP0",
                                           "Note that this command is only issued if reboot = True"]
                })
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
    if sys.version_info < (3, 8):
        print("WARNING: Running an older version of Python ({})."
              "Make sure your CTF virtual environment is activated, as older versions may behave differently."
              .format(sys.version))
        input("Press Enter to continue, or CTRL-C to cancel.")
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
