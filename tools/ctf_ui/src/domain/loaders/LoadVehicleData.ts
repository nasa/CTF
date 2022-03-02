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

import { LoadJsonFile } from '../file-util/LoadJsonFile';
import { Parameter, VehicleData, Command, Telemetry } from '../../model/vehicle-data';
import { FileTree } from '../../model/tree';
import { TelemetryDefinition, CommandDefinition, CcddData, CommandCode, Field } from '../../model/ccdd-json';
import { FindJsonFiles } from '../file-util/FindJsonFiles';

export class LoadVehicleData {
    static flattenFields(fields:Field[], type:string, identifier?: string, ): Parameter[] {
        return fields.filter(field => field !== undefined).flatMap((field: Field) => {
            field.array_size = Number(field.array_size)
            field.bit_length = Number(field.bit_length)
            var array_selector = '';
            if (field.array_size > 0 && field.data_type != "char"){
                if (type === 'tlm')
                    array_selector = '[]'
                else
                    array_selector = '[<CTF_IDX_PLACEHOLDER>]'
            }
            if (field.parameters && field.parameters.length > 0) {
                console.log(field)

                return LoadVehicleData.flattenFields(field.parameters, 
                    type, identifier ? (identifier + '.' + field.name + array_selector) : field.name + array_selector);
            } 
            else {
                console.log(field)
                var param = []
                if (type === "tlm"){
                    param = [new Parameter(
                        identifier ? identifier + '.' + field.name + array_selector: field.name + array_selector,
                        field.enumeration, field.data_type
                    )];
                }
                if (type === "cmd"){
                    if (field.array_size > 0 && field.data_type != "char"){
                        for (let i =0 ; i < field.array_size; i++){
                            var array_index_selector = array_selector.replace("<CTF_IDX_PLACEHOLDER>", i.toString())
                            param.push(new Parameter(
                                identifier ? 
                                    identifier + '.' + field.name + array_index_selector
                                    : field.name + array_index_selector,
                                field.enumeration, field.data_type  
                            ))
                        } 
                    }
                    else{
                        param = [new Parameter(
                            identifier ? identifier + '.' + field.name: field.name,
                            field.enumeration, field.data_type
                        )];    
                    }
                }
                return param
            }
        }) 
    }

    static async load(pathToAppsRoot: string): Promise<VehicleData> {
        return FindJsonFiles.find(pathToAppsRoot).then(async (vehicleDataFiles: FileTree) => {
            const leaves = Object.values(vehicleDataFiles.items).filter((item) => item.children.length == 0);
            const loaded = await Promise.all(leaves.map((item) => (
                LoadJsonFile.load(item.path)
            )));
            const ccddData = loaded as CcddData[];
            const vehicleData: VehicleData = new VehicleData(
                ccddData
                    .filter((data: CcddData) => data.hasOwnProperty('cmd_mid_name'))
                    .map((data: CcddData) => {return data as CommandDefinition})
                    .flatMap((cmd: CommandDefinition) => {
                        if (!cmd.hasOwnProperty('cmd_codes')){
                            return [new Command(cmd.cmd_mid_name, "", 
                                LoadVehicleData.flattenFields(cmd.cmd_parameters, "cmd"))]
                        }
                        return cmd.cmd_codes.flatMap((command_code: CommandCode) => (
                            new Command(
                                cmd.cmd_mid_name,
                                command_code.cc_name,
                                LoadVehicleData.flattenFields(command_code.cc_parameters, "cmd")
                            )
                    ))}),
                ccddData
                    .filter((data: CcddData) => data.hasOwnProperty('tlm_mid_name'))
                    .map((data: CcddData) => data as TelemetryDefinition)
                    .map((tlm: TelemetryDefinition) => (
                        new Telemetry(
                            (tlm.tlm_mid_name.length > 0) ? tlm.tlm_mid_name : tlm.tlm_data_type,
                            LoadVehicleData.flattenFields(tlm.tlm_parameters, "tlm")
                        )
                    ))
            );
            console.log(vehicleData)
            return vehicleData;
        });
    }
}