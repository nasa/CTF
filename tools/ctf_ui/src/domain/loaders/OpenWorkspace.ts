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

import { CtfPlugin } from '../../model/ctf-plugin';
import { FileTree } from '../../model/tree';
import { VehicleData } from '../../model/vehicle-data';
import { LoadJsonFile } from '../file-util/LoadJsonFile';
import { UsePluginDirArray } from './UsePluginDir';
import { UseProjectDir } from './UseProjectDir';
import { UseVehicleDataDir } from './UseVehicleDataDir';
import * as path from 'path';

interface WorkspaceFile {
    projectDir: string;
    scriptsDir: string;
    ctfExecutable: string;
    pluginDir: string,
    ccddJsonDir: string,
}

export interface Workspace {
    plugins: CtfPlugin[];
    vehicleData: VehicleData;
    projectTree: FileTree;
    pythonScriptPath: string;
    projectDir: string
}

export class OpenWorkspace {
    static async open(workspaceFilePath: string): Promise<Workspace> {
        return LoadJsonFile.load<WorkspaceFile>(workspaceFilePath).then(async (data) => {
                let projectDir = path.join(path.dirname(workspaceFilePath), data.projectDir);

                let scriptsDir = path.join(path.dirname(workspaceFilePath), data.scriptsDir);

                let ccddJsonDir = path.join(path.dirname(workspaceFilePath), data.ccddJsonDir);

                let pluginDir = path.join(path.dirname(workspaceFilePath), data.pluginDir);

                let ctfExecutable = path.join(path.dirname(workspaceFilePath), data.ctfExecutable);

                let pluginInfoArray = data.pluginDir.split(',')
                const pluginInfoPath = pluginInfoArray.map( pluginInfo => {
                    return  path.join(path.dirname(workspaceFilePath), pluginInfo.trim());
                });

                return Promise.all([
                    UseProjectDir.use(scriptsDir),
                    UseVehicleDataDir.use(ccddJsonDir),
                    UsePluginDirArray.use(pluginInfoPath)
                ]).then((workspaceData) => {

                    let plugins_info = [] ;

                    workspaceData[2].forEach(info => {
                         plugins_info = plugins_info.concat(info);
                    });

                    return {
                        projectTree: workspaceData[0],
                        vehicleData: workspaceData[1],
                        plugins: plugins_info,
                        pythonScriptPath: ctfExecutable,
                        projectDir: projectDir,
                        scriptsDir: scriptsDir
                    };
                });
        });
    }
}
