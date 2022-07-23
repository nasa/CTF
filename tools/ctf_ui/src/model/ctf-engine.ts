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

import { CtfInstructionData as CtfInstructionData } from "./ctf-file";

export type CtfRunStatus = 'waiting' | 'active' | 'stopped' | 'passed' | 'failed' | 'error' | 'timeout' | 'disabled';

export interface CtfInstructionStatus {
    status: CtfRunStatus;
    details?: string;
    comment?: string;
    instruction: string; // instruction name
    data: CtfInstructionData; // instruction data
}

export interface CtfEngineTestStatus {
    test_number: string;
    status: CtfRunStatus;
    details?: string;
    instructions: CtfInstructionStatus[];
}

export interface CtfEngineScriptStatus {
    path: string;
    test_script_number: string;
    status: CtfRunStatus;
    details?: string;
    tests: CtfEngineTestStatus[];
}

export interface CtfEngineRunStatusMsg {
    elapsed_time: number;
    status: CtfRunStatus;
    scripts: CtfEngineScriptStatus[];
}

export interface CtfEngineInputRequestMsg {
    path: string;
    test_name: string;
    test_number: string;
    instruction_index: number;
    continue: boolean;
}