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
vv_plugin.py - an implementation of a simple CTF plugin
NOTE: This plugin is for V&V testing and demonstration purposes, and is not intended for use in production.
"""

import logging

from lib.ctf_global import Global
from lib.logger import logger as log
from lib.plugin_manager import ArgTypes, Plugin


class VVPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "VVPlugin"
        self.description = "V&V Plugin"
        self.command_map = {
            "LogComment": (self.log_comment, [ArgTypes.string])
        }

    # This command is used to insert comments into the test log
    @staticmethod
    def log_comment(msg):
        level = Global.config.get("vv_plugin", "comment_level", fallback="DEBUG")
        log.log(getattr(logging, level), "V&V PLUGIN COMMENT: {}".format(msg))
        return True
