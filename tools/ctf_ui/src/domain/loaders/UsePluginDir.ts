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

import { LoadPluginInstructions } from "./LoadPluginInstructions";
import { CtfPlugin } from "../../model/ctf-plugin";
import * as path from 'path';

export class UsePluginDir {
    static async use(dir: string): Promise<CtfPlugin[]> {
        return LoadPluginInstructions.load(path.resolve(dir), '.*.json').then((pluginCommandGroups) => {
            return pluginCommandGroups;
        });
    }
}

export class UsePluginDirArray {
    static async use(dirArray): Promise<CtfPlugin[]> {
        let pluginInfo = [];
        let promiseArray = dirArray.map(dir => {
            return LoadPluginInstructions.load(path.resolve(dir), '.*.json');
         });

        return Promise.all(promiseArray).then( (infoArray) => {
           return infoArray;
        });
    }
}
