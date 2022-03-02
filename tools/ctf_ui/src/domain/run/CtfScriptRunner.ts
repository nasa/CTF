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

import { exec, ExecException, ChildProcess } from 'child_process';
import { WriteStream } from 'fs';
import { SIGINT } from 'constants';
import * as path from 'path';

export class CtfScriptRunnerError {
    err: string;
    constructor(err: string) {
        this.err = err;
    }

    toString = (): string => {
        return this.err;
    }
}

export class CtfScriptRunner {
    pythonCmd: string;
    port: number;
    scripts: string[];
    _process?: ChildProcess;
    _cwd: string;
    onOutput: (data) => Promise<void>;
    processstdin; 
    constructor(pythonCmd: string, port: number, scripts: string[], onOutput: (data) => Promise<void>, cwd?: string) {
        this.pythonCmd = pythonCmd;
        this.port = port;
        this.scripts = scripts;
        this.onOutput = onOutput
        this._cwd = cwd;
    }

    kill = (): void => {
        if (this._process) {
            this._process.kill(SIGINT);
        }
    };

    run = (): Promise<boolean> => {
        return new Promise((res, rej) => {
            var fullCommand = this.pythonCmd.split('--')
            var pythonExecutable = fullCommand[0]
            var wd = this._cwd
            var additional_args = []
            if (fullCommand.length > 1){
                additional_args = fullCommand.slice(1)
                additional_args[0] = "--" + additional_args
                additional_args.join(' --')
            } 
            
            const cliStr = `bash -c "${pythonExecutable} --port ${this.port} ${additional_args} ${this.scripts.join(' ')}"`;
            console.log('wd= ',wd);
            console.log('cliStr=',cliStr)
            this._process = exec(cliStr, { cwd: wd , maxBuffer: 10*1024*1024}, (err, stdout, stderr) => {
                if (err) {
                    this._process = null;
                    console.log(err.toString());
                    rej(new CtfScriptRunnerError(err.toString()));
                } else {
                    this._process = null;
                    res(true);
                }
                // stdout shows the cFS build messages
                // stderr shows the CTF log messages
            });
            this._process.stdout.on('data', this.onOutput);
            //TODO alternatively direct logging streamhandler to sys.stdout
            this._process.stderr.on('data', this.onOutput);

            this.processstdin = this._process.stdin;
        });
    };
}
