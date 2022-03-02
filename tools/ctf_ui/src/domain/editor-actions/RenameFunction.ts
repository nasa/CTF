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

import { CtfFile, CtfFunctionCall } from "../../model/ctf-file";

export class RenameFunction {
    static rename(file: CtfFile, oldName: string, newName: string): Promise<CtfFile> {
        return new Promise((res, rej) => {
            // const updated = Object.assign({}, file);
            const json = JSON.stringify(file);
            const count = json.match(new RegExp(`"${oldName}"`, 'g')).length;
            const newJson = json.replace(new RegExp(`"${oldName}"`, 'g'), `"${newName}"`);
            console.log('Replaced ' + count + ' occurences of \'' + `"${oldName}"` + '\'');
            const updated = JSON.parse(newJson);
            res(updated);
        });
    }
}