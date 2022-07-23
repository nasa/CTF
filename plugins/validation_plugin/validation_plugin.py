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
validation_plugin.py: Validation Plugin Implementation for CTF.

- Defines the plugin instructions to allow user to delete files/folders and copy files/folders on host machine.
- The plugin provides functionality to interpret cFE binary event log to human readable text file.
  And it allows user to search text string in the text file.
"""

# ENHANCE - support binary files interpretation for other types of CFS log files.
import re
from pathlib import Path
import shutil

from lib.ctf_global import Global
from lib.ctf_utility import resolve_variable
from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log

CFE_FS_HDR_DESC_MAX_LEN = 32
CFE_PLATFORM_EVS_LOG_MAX = 20
CFE_EVS_PACKETID_T_SIZE = 32


class ValidationPlugin(Plugin):
    """
    The Validation Plugin Class Definition

    @note The plugin uses const values / macros to interpret log files,
           some of these values comes from registered target's controller (which reads ccdd json files).
           So InterpretCfsFile instruction could NOT be used before RegisterCfs/StartCfs instructions.
    """

    def __init__(self):
        """
        Constructor implementation for validation plugin.
        """
        super().__init__()
        ## Plugin Name
        self.name = "ValidationPlugin"

        ## Plugin Description
        self.description = "CTF Validation Plugin"

        ## Plugin Command Map
        self.command_map = {
            "DeleteFiles": (self.delete_file, [ArgTypes.string]),
            "CopyFiles": (self.copy_file, [ArgTypes.string] * 2),
            "SaveFileAsText": (self.save_file_as_text, [ArgTypes.string] * 4),
            "SearchStr": (self.search_txt_file, [ArgTypes.string] * 2),
            "SearchNoStr": (self.search_no_txt_file, [ArgTypes.string] * 2),
            "InsertUserComment": (self.insert_comment, [ArgTypes.string])
        }

    @staticmethod
    def initialize() -> bool:
        """
        Initialize implementation for the validation plugin.

        @note The initialize function is called by the CTF plugin manager *after* all plugins have been loaded.

        @return bool: True
        """
        log.info("Initialized Validation Plugin!")
        return True

    @staticmethod
    def insert_comment(comment: str):
        """
        Insert comments into the test log
        @return bool: True
        """
        log.info("User Comment - {}".format(comment))
        return True

    @staticmethod
    def delete_file(path: str) -> bool:
        """
        Delete a file / folder on the host file system
        @return bool: True, unless the delete fails.
        """
        file_path = Path(path)
        status = True

        if not file_path.exists():
            log.error("File {} does not exist ".format(file_path.resolve()))
            return False

        try:
            if file_path.is_file():
                log.info("Deleting file {}".format(path))
                file_path.unlink(missing_ok=True)
            elif file_path.is_dir():
                log.info("Deleting folder {}".format(path))
                shutil.rmtree(file_path.resolve(), ignore_errors=True)
        except IOError:
            log.error("Deleting file/folder fails")
            status = False

        return status

    @staticmethod
    def copy_file(source: str, destination: str) -> bool:
        """
        Copy a file or folder on the host file system
        @return bool: True, unless the copy fails.
        """
        source_path = Path(source)
        destination_path = Path(destination)
        status = True

        if not source_path.exists():
            log.error("{} is not valid file or folder".format(source))
            return False

        try:
            if source_path.is_dir():
                log.info("Copying folder from {} to {}".format(source, destination))
                shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
            if source_path.is_file():
                log.info("Copying file from {} to {}".format(source, destination))
                shutil.copy(source_path, destination_path)
        except IOError:
            log.error("Copying file/folder fails")
            status = False

        return status

    def save_file_as_text(self, input_file: str, output_file: str, file_type: str, target: str = None) -> bool:
        """
        Interpret a Cfs (binary) file and convert it to a human readable text file.
        Worth note, as it needs const values / macros to interpret log files,
        the instruction could NOT be used before RegisterCfs/StartCfs.
        It is assumed that the the cfs binary file is on the host local machine.
        If not, download it from target to the local machine prior to interpreting the input file.

        ENHANCE:  support binary files interpretation for more types of CFS log files.
         """

        log.info("Interpreting Cfs file input_file={} output_file={}".format(input_file, output_file))
        input_file_path = Path(input_file)
        if not input_file_path.is_file():
            log.error("{} is not valid file".format(input_file))
            return False

        event_data = input_file_path.read_bytes()
        file_description = event_data[32:32 + CFE_FS_HDR_DESC_MAX_LEN].decode('utf-8', 'ignore')

        status = True
        if "cFE EVS Log File" in file_description and file_type == 'EVS':
            self.interpret_event_log(input_file, output_file, target)
        else:
            log.error("Error: Unknown File Type, The File Description is {}".format(file_description))
            status = False

        return status

    @staticmethod
    def convert_timestamp(subsecs) -> str:
        """
        Helper function: convert subsecs to microseconds
        """
        if subsecs > 0xffffdf00:
            microsecs = 999999
        else:
            microsecs = subsecs * ((2 ** -32) / (10 ** -6))
            if (subsecs & 0x3ffffff) != 0:
                microsecs = microsecs + 1
            if microsecs > 500000:
                microsecs = microsecs - 1

        # Format microseconds so it can be entered into event time
        microsecs = str(microsecs * (10 ** -6))
        microsecs2print = microsecs.split('.')
        microsecs2print = microsecs2print[1]
        microsecs2print = microsecs2print[:5]
        num_zeros_needed = 5 - len(microsecs2print)
        microsecs2print = microsecs2print.ljust(num_zeros_needed + len(microsecs2print), '0')

        return microsecs2print

    def interpret_binary_data(self, event_data, entry_id, offset, endianess_of_target, os_max_api_name) -> str:
        """
        Helper function: interpret each line of the binary cFE Event Log data to a human readable message
        """
        # List of verification type commands

        event_types = {1: "DEBUG      ", 2: "INFORMATION", 3: "ERROR      ", 4: "CRITICAL   "}

        # Extract Data
        seconds = int.from_bytes(event_data[76 + offset:80 + offset], 'big')
        subsecs = int.from_bytes(event_data[80 + offset:82 + offset], 'big')
        subsecs = subsecs << 16
        app_name = event_data[84 + offset:104 + offset].decode('utf-8', 'ignore')
        event_id = int.from_bytes(event_data[104 + offset:106 + offset], endianess_of_target)
        event_type = int.from_bytes(event_data[106 + offset:108 + offset], endianess_of_target)
        event_text = event_data[116 + offset:238 + offset].decode('utf-8', 'ignore')

        app_name = app_name.split("\0")[0]
        event_text = event_text.split("\0")[0]
        app_name_length = len(app_name)
        added_pad = os_max_api_name - len(app_name)
        app_name = app_name.ljust(added_pad + app_name_length)
        event_type_str = event_types.get(event_type, "Invalid Event Type")

        years = seconds // 31556926 + 1980
        days = seconds // 86400 + 1
        hours = seconds // 3600 % 24
        minutes = seconds // 60 % 60
        seconds = seconds % 60
        microsecs2print = self.convert_timestamp(subsecs)

        # Build message
        message = "Entry-{:02} {:04}:{:03}:{:02}:{:02}:{:02}.{} {}  " \
                  "{:03}  {} - {} \n".format(entry_id, years, days, hours, minutes, seconds, microsecs2print,
                                             app_name, event_id, event_type_str, event_text)

        if seconds == 0 and event_type_str == 'Invalid Event Type':
            message = "Entry-{:02}      No Event Logged\n".format(entry_id)

        return message

    def interpret_event_log(self, input_file: str, output_file: str, target: str = None) -> bool:
        """
        Interpret the cFE Event Log file (binary file created via the CFE_EVS_WRITE_LOG_DATA_FILE_CC command)
        to a human readable text file
        """
        input_file_path = Path(input_file)
        if not input_file_path.is_file():
            log.error("{} is not valid file".format(input_file))
            return False

        cfs_controller = None
        macro_map = None
        if target in Global.plugins_available['CFS Plugin'].targets:
            cfs_controller = Global.plugins_available['CFS Plugin'].targets[target]
            macro_map = cfs_controller.macro_map
        else:
            for key, controller in Global.plugins_available['CFS Plugin'].targets.items():
                if 'cfs' in key:
                    log.warning("Do not find the specified target {}, use the default target {}".format(target, key))
                    cfs_controller = controller
                    macro_map = controller.macro_map

        if macro_map is None:
            log.error("No registered cFS target is found")
            macro_map = {}

        event_data = input_file_path.read_bytes()

        output_file_path = Path(output_file)
        output_file_path.parents[0].mkdir(parents=True, exist_ok=True)
        log.info("Creating interpreted evs log file at = {}".format(output_file_path.resolve()))
        parsed_file = output_file_path.open(mode='w+', encoding="utf-8")

        if 'CFE_MISSION_EVS_MAX_MESSAGE_LENGTH' not in macro_map:
            log.warning('CCDD json files do not define CFE_MISSION_EVS_MAX_MESSAGE_LENGTH macro, use default value')
        if 'OS_MAX_API_NAME' not in macro_map:
            log.warning('CCDD json files do not define OS_MAX_API_NAME macro, use default value')

        endianess_of_target = cfs_controller.config.endianess_of_target if cfs_controller is not None else 'little'
        cfe_mission_eve_max_message_length = macro_map.get('CFE_MISSION_EVS_MAX_MESSAGE_LENGTH', 122)
        os_max_api_name = macro_map.get('OS_MAX_API_NAME', 20)

        cfe_evs_long_event_tlm_t = 20 + CFE_EVS_PACKETID_T_SIZE + cfe_mission_eve_max_message_length + 2

        for i in range(CFE_PLATFORM_EVS_LOG_MAX):
            offset = i * cfe_evs_long_event_tlm_t
            # Build message and write to file
            msg = self.interpret_binary_data(event_data, i + 1, offset, endianess_of_target, os_max_api_name)
            parsed_file.write(msg)

        parsed_file.close()
        return True

    @staticmethod
    def read_file(file: str) -> any:
        """
        Helper method: read the file content. If the file does not exist, return None;
                       else return the content as a string
        """
        file_path = Path(file)
        if not file_path.is_file():
            log.error("File {} not found  ".format(file_path.resolve()))
            return None

        # Replace malformed data by Python’s backslashed escape sequences.
        # errors='backslashreplace' is for files which have mixed printable and non-printable characters
        file_data = file_path.read_text(errors='backslashreplace')
        log.debug("Text content in file {} = \n{}".format(file_path.resolve(), file_data))
        return file_data

    @staticmethod
    def check_str(file_data:str, search_str: str, is_regex: bool = False) -> bool:
        """
        Helper method: Check whether a given text string is in text data.
        @return bool: True, if text string is found; False otherwise.
        """
        status = False
        if is_regex:
            if re.search(search_str, file_data):
                log.info("String value {} Found by Regex".format(search_str))
                status = True
        else:
            if search_str in file_data:
                log.info("String value {} Found".format(search_str))
                status = True
        return status

    @staticmethod
    def search_txt_file(file: str, search_str: str, is_regex: bool = False) -> bool:
        """
        Search a text file for a given text string.
        @return bool: True, if text string is found; False otherwise.
        """
        file = resolve_variable(file)
        search_str = resolve_variable(search_str)

        file_data = ValidationPlugin.read_file(file)
        if not file_data:
            return False

        status = ValidationPlugin.check_str(file_data, search_str, is_regex)
        if not status:
            log.error("String value {} not Found".format(search_str))

        return status

    @staticmethod
    def search_no_txt_file(file: str, search_str: str, is_regex: bool = False) -> bool:
        """
        Search a text file for a given text string. It has the reversed logic of search_txt_file.
        @return bool: True, if text string is NOT found; False otherwise
        """
        file = resolve_variable(file)
        search_str = resolve_variable(search_str)

        file_data = ValidationPlugin.read_file(file)
        if not file_data:
            return False

        status = ValidationPlugin.check_str(file_data, search_str, is_regex)
        if status:
            log.error("String value {} Found".format(search_str))

        return not status

    def shutdown(self):
        """
        Shutdown implementation for the validation plugin.
        @note The shutdown function is called by the CTF plugin manager upon completion of a test run.
        @note The shutdown function can be exposed to test scripts by adding it to the command map.
        """
        log.info("Optional shutdown/cleanup implementation for Validation Plugin")
