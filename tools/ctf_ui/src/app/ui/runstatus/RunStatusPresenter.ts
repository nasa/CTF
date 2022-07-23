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

import { LoadProjectFile } from '../../../domain/loaders/LoadProjectFile';
import {
    CtfScriptRunner,
    CtfScriptRunnerError
} from '../../../domain/run/CtfScriptRunner';
import {
    RunStatusListener,
    RunStatusListenerError
} from '../../../domain/run/RunStatusListener';
import { CtfEngineRunStatusMsg } from '../../../model/ctf-engine';
import { CtfFile } from '../../../model/ctf-file';
import * as path from 'path';
import { ReadStream, WriteStream, createReadStream, createWriteStream } from 'fs';

export interface IRunStatusView {
    showRunStatusMsg(msg: CtfEngineRunStatusMsg): void;
    runDidFinish(): void;
    showError(title: string, message: string): void;
    showMessage(content: string): void;
    showOutput(content: string): void;
}

export interface IRunStatusPresenter {
    viewDidLoad(): void;
    viewWillUnload(): void;
    onOutput(data): Promise<void>;
}

const PORT = 5555;
const HOST = '127.0.0.1';

export class RunStatusPresenter implements IRunStatusPresenter {
    view: IRunStatusView;
    scriptFiles: string[];
    listener?: RunStatusListener;
    runner?: CtfScriptRunner;
    pythonCmd: string;
    projectDir: string;
    promptmsg: string;

    onOutput: (data) => Promise<void>;
    constructor(view: IRunStatusView, pythonCmd: string, projectDir: string, scripts: string[]) {
        this.view = view;
        this.scriptFiles = scripts;
        this.pythonCmd = pythonCmd;
        this.projectDir = projectDir;
        this.promptmsg = '';
    }

    viewWillUnload = (): void => {
        // try to stop the listener if necessary
        if (this.listener) {
            this.listener.stop().then(_ => {
                this.view.showMessage('Stopped run status listener');
            });
        }

        // stop the runner
        if (this.runner) {
            this.runner.kill();
            this.view.showMessage('Killed backend engine');
        }
    };

    viewDidLoad = (): void => {
        // start the run
        this.listener = new RunStatusListener(
            PORT,
            HOST,
            (msg: CtfEngineRunStatusMsg) => {
                this.view.showRunStatusMsg(msg);
            }
        );

        this.onOutput = async (data): Promise<void> => {
            await this.view.showOutput(data)
            var confirmed;
            var promptmsg = "";

            if (data.includes('userio_plugin') && data.includes('Wait for user input') )  {

                 const searchstr = 'Executed with args:';
                 const len = searchstr.length;
                 const start = data.indexOf(searchstr)
                 const end   = data.indexOf('\n');
                 promptmsg = data.substring((start+len), end);

                 // promptmsg could be very long, ignore long messages
                 if (promptmsg != '' && promptmsg.length <= 10) this.promptmsg = promptmsg;

                 console.log('RunstatusPresenter:: promptmsg=', promptmsg);
            }

            if (data.includes("Please Enter 'Y' to continue")) {
                 console.log('RunStatusPresenter:: user input needed, test pauses', data);

                 if (confirm(this.promptmsg + " \nClick OK to continue tests or Click 'Cancel' to cancel tests")) {
                    confirmed = true;
                  } else {
                    confirmed = false;
                 }

                 this.promptmsg = '';

                 if (confirmed)
                    this.runner.processstdin.write('y\n');
                 else
                    this.runner.processstdin.write('n\n');


            }
        }

        this.runner = new CtfScriptRunner(
            //TODO parametrize python executable
            this.pythonCmd,
            PORT,
            this.scriptFiles,
            this.onOutput,
            this.projectDir
        );
        this.listener
            .start()
            .then(_ => {
                return this.runner.run();
            })
            .catch(err => {
                if (err instanceof RunStatusListenerError) {
                    this.view.showError(
                        'Unable to Start Status Listener',
                        err.toString()
                    );
                } else if (err instanceof CtfScriptRunnerError) {
                    this.view.showError(
                        'Unable to Start Script Engine',
                        err.toString()
                    );
                }
            })
            .finally(() => {
                this.runner = null;
                this.view.runDidFinish();
                return this.listener.stop();
            })
            .then(_ => {
                this.listener = null;
            });
    };
}
