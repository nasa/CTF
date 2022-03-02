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

import { Enum } from './ccdd-json'

export class Parameter {
    name: string;
    enum: Enum[];
    data_type: string;
    constructor(name: string, enuMap: Enum[], data_type: string = null) {
        this.name = name
        this.enum = enuMap
        this.data_type = data_type
    }
}

export class Command {
    mid: string;
    cc: string;
    params: Parameter[];
    constructor(mid: string, cc: string, params: Parameter[]) {
        this.mid = mid;
        this.cc = cc;
        this.params = params;
    }
}

export class Telemetry {
    mid: string
    params: Parameter[]
    constructor(mid: string, params: Parameter[]) {
        this.mid = mid;
        this.params = params;
    }
}

export class VehicleData {
    commands: Command[];
    telemetry: Telemetry[];
    constructor(commands: Command[], telemetry: Telemetry[]) {
        this.commands = commands;
        this.telemetry = telemetry;
    }
}