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

import { LoadJsonFile } from "../file-util/LoadJsonFile";
import { CtfFile, CtfInstruction, CtfInstructionData, CtfInstructionArg } from "../../model/ctf-file";
import * as uuid from 'uuid/v4';

function flattenObj(obj){
    let flat = {}
        for(let i in obj){
           if(typeof obj[i] == 'object'){
              let flatObj = flattenObj(obj[i])
              for(let x in flatObj){
                  flat[i + "." + x] = flatObj[x]
              }
          } else {
           flat[i] = obj[i]
          }
       }
    return flat
    }

export class LoadProjectFile {
    static async load(path: string): Promise<CtfFile> {
        const file = await LoadJsonFile.load(path) as CtfFile;
        // create ids if necessary
        // these unique ids are necessary for drag and drop
        // to identify items even if the index has changed
        // create ids if necessary
        // these unique ids are necessary for drag and drop
        // to identify items even if the index has changed
        if (file.tests === undefined) {
            file.tests = []
        }
        file.tests.forEach((t) => {
            t.id = uuid();
            t.instructions.forEach((c: CtfInstruction) => {
                if (!c.id) c.id = uuid();
                //TODO get default wait value from CTF
                //TODO update CtfCommand args from the interface side
                if (c.instruction == "SendCfsCommand") {
                    let data = c.data as CtfInstructionData
                    let args = data.args as CtfInstructionArg
                    if (typeof args === 'object') {
                        var flatArgs : {} = flattenObj(args) 
                        var argsKeys = Object.keys(flatArgs)
                        var argsList = []
                        argsKeys.forEach(key => {
                            var newArg = {}
                            newArg[key] = flatArgs[key]
                            argsList.push(newArg)
                        })
                        c.data.args = argsList
                    }
                }
            });
        });
        for (var f in file.functions) {
            file.functions[f].instructions.forEach((c: CtfInstruction) => {
                if (!c.id) c.id = uuid();
                if (c.instruction == "SendCfsCommand") {
                    let data = c.data as CtfInstructionData
                    let args = data.args as CtfInstructionArg
                    if (typeof args === 'object') {
                        var flatArgs : {} = flattenObj(args) 
                        var argsKeys = Object.keys(flatArgs)
                        var argsList = []
                        argsKeys.forEach(key => {
                            var newArg = {}
                            newArg[key] = flatArgs[key]
                            argsList.push(newArg)
                        })
                        c.data.args = argsList
                    }
                }
            });
        }
        return file;
    }
}
