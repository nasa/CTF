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
ccsds_plugin.py: CCSDS Plugin Implementation for CTF.

- Defines the CCSDS Plugin command map with the CTF instructions for CCSDS.
- Implements the ValidateCfsCcsdsData instruction.
"""

from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log
from lib.ctf_global import Global


class CCSDSPlugin(Plugin):
    """
    The CCSDS Plugin provides CCSDS validation support for CTF
    """

    def __init__(self):
        super().__init__()
        self.name = "CCSDS Plugin"
        self.description = "CTF CCSDS Plugin"
        self.command_map = {
            "ValidateCfsCcsdsData": (self.validate_cfs_ccsds_data, [ArgTypes.string]),
        }
        self.cfs_plugin = None
        self.get_cfs_plugin()

    def get_cfs_plugin(self):
        """
        Returns the instance of the CFS Plugin registered with the plugin manager
        """
        self.cfs_plugin = Global.plugins_available.get("CFS Plugin")

    def initialize(self):
        log.info("Initialized CCSDS Plugin")

    def validate_cfs_ccsds_data(self, target=None):
        """
        Validates the CCSDS data types by sending an empty instance of each command code found in the MID map to CFS.

        @note - This instruction will cause commands to be sent to the designated CFS target

        @note - The plugin cannot directly verify that CFS is able to process the received data.
                CFS output should be checked to ensure that no invalid length commands were received.

        @param target: The name of the CFS target to be used for validation.
                     If not provided, the default target will be used.
        """

        self.get_cfs_plugin()
        if self.cfs_plugin is None:
            log.error("CFS Plugin Not Initialized... Cannot validate CFS CCSDS Data Integrity.")
            return False

        if not self.cfs_plugin.targets:
            log.error("CFS Plugin has no targets registered... Cannot validate CFS CCSDS Data Integrity.")

        if target and target not in self.cfs_plugin.targets:
            log.error("Target {} is not registered with CfsPlugin".format(target))
            return False

        cfs_targets = [target] if target else self.cfs_plugin.targets.keys()
        status = [self._send_commands_to_target(t) for t in cfs_targets]
        return all(status) if status else False

    def _send_commands_to_target(self, target):
        mid_map = self.cfs_plugin.targets[target].mid_map
        result = []
        for mid_name, data in mid_map.items():
            if 'CC' in data:
                for command_name, command_args in data['CC'].items():
                    log.info("CCSDS Validation - Sending Command: {} with arg {} structure".format(command_name,
                                                                                                   command_args))
                    command_result = self.cfs_plugin.send_cfs_command(mid_name, command_name,
                                                                      command_args["ARG_CLASS"]()
                                                                      if command_args["ARG_CLASS"] is not None else [],
                                                                      target=target,
                                                                      payload_length=None,
                                                                      ctype_args=True)
                    result.append(command_result)
                    Global.time_manager.wait(1)
        return all(result)

    def shutdown(self):
        pass
