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

export interface CtfComparisonType {
    variable: string;
    compare: string;
    value: string[];
}

export interface CtfEventType {
    app_name: string;
    event_id: string;
    event_str: string;
    event_str_args: string;
    is_regex:boolean;
}

export interface CtfTlmArgType {
    variable: string;
    value: string;
}

type CtfMessageIdType = string;
type CtfCommandCodeType = string;
type  CtfCmdArgType = object

export type CtfInstructionArg = string | number | boolean | CtfComparisonType
    | CtfMessageIdType | CtfCommandCodeType | CtfTlmArgType | CtfCmdArgType;

export interface CtfInstructionData {
    [arg: string]: CtfInstructionArg | CtfInstructionArg[]
}

export interface CtfInstruction {
    id?: string,
    instruction: string;
    data: CtfInstructionData;
    wait: number;
    comment: string;
    description: string;
    disabled: boolean;
}

export interface CtfFunctionCall {
    id?: string;
    function: string;
    params: {
        [name: string]: any;
    };
    wait: number;
    comment: string;
    description: string;
    disabled: boolean;
}

export interface CtfFunction {
    varlist: string[];
    description?: string;
    instructions: Array<CtfInstruction | CtfFunctionCall>;
}

export interface CtfTest {
    id?: string;
    test_number: string;
    description: string;
    instructions: Array<CtfInstruction | CtfFunctionCall>;
}

export interface CtfFile {
    test_number: string;
    test_name: string;
    requirements: {
        [req: string]: string;
    };
    description: string;
    owner: string;
    ctf_options: object;
    test_setup: string;
    environment: object;
    telemetry_watch_list: {
        [tlm_mid: string]: string[];
    };
    command_watch_list: {
        [cmd_mid: string]: string[];
    };
    functions: {
        [name: string]: CtfFunction;
    };
    import?: {
        [path: string]: string[];
    };
    tests: CtfTest[];
}
