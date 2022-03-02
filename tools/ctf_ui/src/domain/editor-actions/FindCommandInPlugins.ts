/*
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
*/

import { CtfPlugin, CtfPluginInstruction } from "../../model/ctf-plugin";

export class FindCommandInPlugins {
    static find(cmdName: string, plugins: CtfPlugin[]): { group_name: string, instructionDef: CtfPluginInstruction } {
        var cmdIndex = -1;
        for (var i in plugins) {
            cmdIndex = plugins[i].instructions.map((cmd: any) => cmd.name).indexOf(cmdName);
            if (cmdIndex >= 0) {
                return {
                    group_name: plugins[i].group_name,
                    instructionDef: plugins[i].instructions[cmdIndex]
                };
            }
        }
        return undefined
    }
}