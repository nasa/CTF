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

import { CtfFile, CtfInstruction, CtfComparisonType, CtfTlmArgType, CtfFunctionCall, CtfInstructionData, CtfInstructionArg } from '../../model/ctf-file';
import { SaveJsonFile } from '../file-util/SaveJsonFile';
import { FindCommandInPlugins } from '../editor-actions/FindCommandInPlugins';
import { CtfPlugin } from '../../model/ctf-plugin';
import { VehicleData } from '../../model/vehicle-data';
import { EditingContextFunction } from '../../model/editing-context';
import { jsonclone } from '../jsonclone';

const isTlmField = (mid: string, field: string, vehicleData: VehicleData) => {
    const msg = vehicleData.telemetry.find(
        t => t.mid == mid
    )

    const f = msg ? msg.params.find(
        p => p.name.indexOf(field) != -1
    ) : false

    const ret = f ? true : false
    return ret;
};

function jsonConcat(o1, o2) {
    for (var key in o2) {
        o1[key] = o2[key];
    }
    return o1;
}

/**
* Simple is object check.
* @param item
* @returns {boolean}
*/
export function isObject(item) {
    return (item && typeof item === 'object' && !Array.isArray(item) && item !== null);
}

export function setValue(object, path, value): void {
    // console.log(object)
    // console.log(path)
    // console.log(value)
    // path = path.replace(/[\[]/gm, '.').replace(/[\]]/gm, ''); //to accept [index]
    var keys = path.split('.'),
        last = keys.pop();
    keys.reduce(function (o, k) { return o[k] = o[k] || {}; }, object)[last] = value;
}

export class SaveProjectFile {
    static save(
        filePath: string,
        file: CtfFile,
        plugins: CtfPlugin[],
        vehicleData: VehicleData,
        importedFunctions: EditingContextFunction[]
    ): Promise<boolean> {

        const testInstructions = file.tests.flatMap(t => t.instructions);
        const functionInstructions = file.functions ? Object.keys(file.functions).flatMap(
            f => file.functions[f].instructions
        ) : [];

        const importedFunctionInstructions = importedFunctions.flatMap((f) => f.function.instructions)

        var allInstructions = testInstructions.concat(functionInstructions);
        allInstructions = allInstructions.concat(importedFunctionInstructions);

        for (var index in allInstructions) {
            const call = allInstructions[index];
            if (call.hasOwnProperty('instruction')) {
                const instruction = call as CtfInstruction;
                const def = FindCommandInPlugins.find(instruction.instruction, plugins);
                if (def === undefined)
                {
                    continue;
                }
                const cmdMidParam = def.instructionDef.parameters.find(
                    p => p.type === 'cmd_mid'
                );
                const cmdMid = cmdMidParam
                    ? (instruction.data[cmdMidParam.name] as string)
                    : 'unknown';
                const tlmMidParam = def.instructionDef.parameters.find(
                    p => p.type === 'tlm_mid'
                );
                const tlmMid = tlmMidParam
                    ? (instruction.data[tlmMidParam.name] as string)
                    : 'unknown';

                for (var paramIdx in def.instructionDef.parameters) {
                    const param = def.instructionDef.parameters[paramIdx];
                    if (param.type === 'cmd_code') {
                        var codes: string | any[];
                        if (param.isArray) {
                            codes = instruction.data[param.name] as string[];
                        } else {
                            codes = [instruction.data[param.name] as string];
                        }
                    } else if (param.type === 'tlm_field') {
                        let fields = [];
                        if (param.isArray) {
                            fields = instruction.data[param.name] as string[];
                        } else {
                            fields = [instruction.data[param.name] as string];
                        }

                    } else if (param.type === 'comparison') {
                        let comparisons = [];
                        if (param.isArray) {
                            comparisons = instruction.data[
                                param.name
                            ] as CtfComparisonType[];
                        } else {
                            comparisons = [
                                instruction.data[param.name] as CtfComparisonType
                            ];
                        }
                    }
                    else if (param.type === 'tlm_arg') {
                        let tlm_args = [];
                        if (param.isArray) {
                            tlm_args = instruction.data[
                                param.name
                            ] as CtfTlmArgType[];
                        } else {
                            tlm_args = [
                                instruction.data[param.name] as CtfTlmArgType
                            ];
                        }
                    }
                    else if (param.type === 'cmd_arg') {
                        let args = instruction.data[param.name] as CtfInstructionArg[]
                        var finalArgs = {}

                        if (Array.isArray(args) && args.length > 0) {
                            args = args.filter((arg)=> {
                                let argKey = Object.keys(arg)[0];
                                // in case the arg is not defined, for example args = ["", {key: value}, "", ""]
                                if (typeof (argKey) === "undefined") return false;
                                if (argKey.indexOf('[...]') != -1) return false;
                                return true;
                             });
                        }

                        if (args.length > 0){
                            args.forEach((arg: CtfInstructionArg) => {
                                if (arg){
                                var argKey = Object.keys(arg)[0]
                                var argValue = arg[argKey]
                                setValue(finalArgs, argKey, argValue)
                                }
                            })
                            instruction.data['args'] = Object.assign({}, finalArgs);
                        }
                    }
                }
            }
        }

        const withLists = Object.assign({}, jsonclone(file));

        // telemetry_watch_list and command_watch_list are no longer needed
        if ('telemetry_watch_list' in withLists)
            delete withLists.telemetry_watch_list;
        if ('command_watch_list' in withLists)
                delete withLists.command_watch_list;        

        withLists.tests.forEach((t) => {
            delete t.id;
            t.instructions.forEach((c) => {
                c
                delete c.id;
            });
        });

        if (withLists.functions) {
            Object.keys(withLists.functions).forEach((k) => {
                withLists.functions[k].instructions.forEach((c) => {
                    delete c.id
                })
            })
        }
        return SaveJsonFile.save(filePath, withLists);
    }
}
