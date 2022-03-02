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
import { CtfFile, CtfFunction } from "../../model/ctf-file";
import * as path from 'path';
import { fstat, exists, existsSync } from "fs";

export class ResolveFunctionsAvailableForImport {
    static resolveFromImports(startDir: string, projectDir: string, importFiles: string[]): Promise<{ [path: string]: { [name: string]: CtfFunction } }> { 
        return Promise.all(importFiles.map((f) => {
            var filePath = path.resolve(startDir, f)
            if (!existsSync(filePath)){
                filePath = path.resolve(projectDir + "/../", f)
            }
            var data = LoadJsonFile.load(filePath).then((data) => {
                return (data as CtfFile).functions ? (data as CtfFile).functions : {}
            }).catch((err) => {console.log(err)})
            return data
        })).then((funcs) => {
            const result = {};
            for (let i = 0; i < importFiles.length; i++) {
                result[importFiles[i]] = funcs[i];
            }
            return result;
        });
    }
}
