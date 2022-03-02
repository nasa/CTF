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

import { CtfInstruction, CtfInstructionArg } from "../../model/ctf-file";
import { CtfPluginInstruction } from "../../model/ctf-plugin";
import * as uuid from 'uuid/v4';

export class BuildEmptyCommand {
    static build(template: CtfPluginInstruction): CtfInstruction {
        const cmd: CtfInstruction = {
            id: uuid(),
            instruction: template.name,
            data: template.parameters.reduce((prevArgs, param) => {
                if (param.isArray) {
                    prevArgs[param.name] = [];
                } else {
                    var defaultValue: CtfInstructionArg = '';
                    if  (param.type === 'comparison'){
                        defaultValue = {
                            variable: "",
                            compare: "",
                            value: [""],
                        };
                    }
                    else if (param.type === 'boolean'){
                        defaultValue = false
                    }
                    prevArgs[param.name] = defaultValue;
                }
                return prevArgs;
            }, {}),
            wait: 0
        };
        return cmd;
    }
}