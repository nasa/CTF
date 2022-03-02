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

import * as fs from 'fs'
import * as path from 'path'

export class LoadJsonFile {
    static load<T>(filepath: string): Promise<T> {
        return new Promise((resolve, reject) => {
            let absolutePath = path.resolve(filepath);
            if (!fs.existsSync(absolutePath)) {
                reject(absolutePath + ": file not found");
            } else {
                try {
                    const data = fs.readFileSync(absolutePath);
                    resolve(JSON.parse(data.toString()));
                } catch (err) {
                    reject(err);
                }
            }
        });
    }
}