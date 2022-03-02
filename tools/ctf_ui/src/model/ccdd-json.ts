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

export interface Enum {
    label: string;
    value: string;
}

export interface Field {
    name: string;
    description: string;
    data_type?: string;
    parameters?: Field[]
    array_size: number;
    bit_length: number;
    enumeration: Enum[];
}

export interface CmdField extends Field {
    min_val: number;
    max_val: number;
    default_value: string;
}

export interface TlmField extends Field {
    telemetered_to_ground: boolean;
    valid_range: any;
    msid: string;
    methods: string;
    access: string;
}

export interface CommandCode {
    cc_name: string;
    cc_value: string;
    description: string;
    cc_data_type: string;
    cc_parameters: CmdField[];
}

export interface CommandDefinition {
    destination_system: string;
    cmd_mid_name: string;
    inheritance: string;
    description: string;
    cmd_codes?: CommandCode[];
    cmd_data_type?: string;
    cmd_parameters?: CmdField[]
}

export interface TelemetryDefinition {
    tlm_mid_name: string;
    tlm_description?: string;
    tlm_data_type: string;
    tlm_parameters: TlmField[];
}

export type CcddData = CommandDefinition | TelemetryDefinition;