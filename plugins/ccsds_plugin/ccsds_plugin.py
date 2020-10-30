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


from lib.plugin_manager import Plugin, ArgTypes
from lib.logger import logger as log
from lib.Global import Global


class CCSDSPlugin(Plugin):
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
        self.cfs_plugin = Global.plugins_available.get("CFS Plugin")

    def initialize(self):
        log.info("Initialized CCSDS Plugin")

    def validate_cfs_ccsds_data(self, name=None):
        self.get_cfs_plugin()
        if self.cfs_plugin is None:
            log.error("CFS Plugin Not Initialized... Cannot validate CFS CCSDS Data Integrity.")
            return False

        name = name or self.cfs_plugin.FALLBACK_TARGET_NAME
        target = self.cfs_plugin.targets.get(name)

        if target is None:
            return False

        mid_map = target.mid_map
        result = True
        for mid_name, data in mid_map.items():
            if 'CC' in data:
                for command_name, command_args in data['CC'].items():
                    log.info("CCSDS Validation - Sending Command: {} with arg structure".format(command_name, command_args))
                    result = self.cfs_plugin.send_cfs_command(mid_name, command_name,
                                                              command_args["ARG_CLASS"]() if command_args["ARG_CLASS"] is not None else [],
                                                              name=name, payload_length=None, ctype_args=True)
                    Global.time_manager.wait(1)
        return result

    def shutdown(self):
        pass
