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

import { CtfEngineRunStatusMsg } from '../../model/ctf-engine';
import * as dgram from 'dgram';

export class RunStatusListenerError {
    err: string;
    constructor(err: string) {
        this.err = err;
    }

    toString = (): string => {
        return this.err;
    };
}

export class RunStatusListener {
    port: number;
    host: string;
    socket: dgram.Socket;
    onError?: (err: RunStatusListenerError) => void;
    onRunStatus: (msg: CtfEngineRunStatusMsg) => void;
    constructor(
        port: number,
        host: string,
        onRunStatus: (msg: CtfEngineRunStatusMsg) => void,
        onError?: (err: RunStatusListenerError) => void
    ) {
        this.port = port;
        this.host = host;
        this.socket = dgram.createSocket('udp4');
        this.socket.on('message', this._on_message);
        this.socket.on('error', this._on_error);
        this.onError = onError;
        this.onRunStatus = onRunStatus;
    }

    start = (): Promise<boolean> => {
        return new Promise((res, rej) => {
            this.socket.once('listening', () => {
                res(true);
            });
            this.socket.once('error', err =>
                rej(new RunStatusListenerError(err.toString()))
            );
            this.socket.bind(this.port, this.host);
        });
    };

    stop = (): Promise<boolean> => {
        return new Promise((res, rej) => {
            this.socket.close(() => res(true));
        });
    };

    _on_error = (err: Error) => {
        console.log(err);
        if (this.onError) {
            this.onError(new RunStatusListenerError(err.toString()));
        }
    };

    _on_message = (msg: Buffer) => {
        try {
            const jsonMsg = JSON.parse(msg.toString());
            if (jsonMsg.hasOwnProperty('elapsed_time')) {
                // must be a run status message
                const runStatus = jsonMsg as CtfEngineRunStatusMsg;
                this.onRunStatus(runStatus);
            } else if (jsonMsg.hasOwnProperty('continue')) {
                // TODO: must be an input request message
            }
        } catch (err) {
            console.log(err);
        }
    };
}
