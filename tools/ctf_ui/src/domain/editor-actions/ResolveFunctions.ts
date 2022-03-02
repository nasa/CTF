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

import { CtfFile, CtfFunction } from "../../model/ctf-file";
import { EditingContextFunction } from "../../model/editing-context";

export class ResolveFunctions {
    static resolve(ctfFile: CtfFile, availImports?: { [path: string]: { [name: string]: CtfFunction } }): EditingContextFunction[] {
        let result = Object.keys(ctfFile.functions || {}).map((name) => ({
            name: name,
            function: ctfFile.functions[name]
        }));

        if (ctfFile.import && availImports) {
            result.push(...Object.keys(ctfFile.import).filter((file) => (
                availImports[file]
            )).flatMap((file) => {
                return ctfFile.import[file].filter((funcName) => (
                    availImports[file][funcName]
                )).map((funcName) => (
                    {
                        name: funcName,
                        src: file,
                        function: availImports[file][funcName]
                    }
                ))
            }));
        }
        return result.filter((func) => func.function);
    }
}