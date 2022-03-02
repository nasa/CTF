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

import { ResolveFunctions } from '../../../domain/editor-actions/ResolveFunctions';
import { SaveProjectFile } from '../../../domain/exporters/SaveProjectFile';
import { LoadProjectFile } from '../../../domain/loaders/LoadProjectFile';
import {
    OpenWorkspace,
    Workspace
} from '../../../domain/loaders/OpenWorkspace';
import { CtfFile } from '../../../model/ctf-file';
import { EditingContext } from '../../../model/editing-context';
import { FileTree } from '../../../model/tree';
import { ipcRenderer } from 'electron';
import { RenameFunction } from '../../../domain/editor-actions/RenameFunction';
import { BuildEmptyCtfFile } from '../../../domain/builders/BuildEmptyCtfFile';
import { jsonclone } from '../../../domain/jsonclone';
import { ResolveFunctionsAvailableForImport } from '../../../domain/editor-actions/ResolveAllAvailableFunctions';
import * as path from 'path';
import * as fs from 'fs';
import { DeleteFiles } from '../../../domain/file-util/DeleteFiles';
import { SelectedItem } from '../FilePane';
import { CreateFolder } from '../../../domain/file-util/CreateFolder';

export interface IHomeView {
    promptForWorkspaceFilePath(): void;
    showCtfFileWithContext(ctfFile: CtfFile, context: EditingContext): void;
    askIfShouldSave(): Promise<boolean>; // returns true if should save
    showProjectTree(tree: FileTree): void;
    updateSavedIndicator(isSaved: boolean): void;
    setSaveMenuItemDisabledState(disabled: boolean): void;
    showLoading(loading: boolean, message?: string): void;
    showAlert(type: string, title: string, message?: string): void;
    promptForSaveLocation(): Promise<string>;
    promptForFileToImport(): void;
    promptForNewFolderName(curPath: string): void;
    promptForRenameFileorFolder(parentPath: string, filename: string): void;
    showRunStatusModal(pythonCmd: string, projectDir: string, scripts: string[]): void;
}

export interface IHomePresenter {
    didClickOpenWorkspace(): void;
    didClickNew(): void;
    didClickSave(): void;
    didClickFile(filePath: string): void;
    didChangeCtfFile(newCtfFile: CtfFile): void;
    didChooseWorkspaceFile(workspaceFilePath: string): void;
    shouldRenameFunctionInCtfFile(oldName: string, newName: string): void;
    didClickAddImport(): void;
    didChooseImportFile(file: string): void;
    didClickDeleteFiles(paths: string[]): void;
    didClickRunFiles(paths: string[], configPath?: string): void;
    didClickCreateNewFolderOnFile(file: string): void;
    didClickRenameFolderorFile(file: string): void;
    didChooseNewFolderName(name: string, parentPath: string);
    didChooseRename(oldfullname: string, newname: string);
    getProjectDir(): string;
}

export class HomePresenter implements IHomePresenter {
    workspace?: Workspace;
    theOpenFilePath?: string;
    theOpenFile?: CtfFile;
    view: IHomeView;
    context?: EditingContext;
    isSaved: boolean = true;
    lastSavedVersion: CtfFile;
    workspaceFile?: string;

    constructor(view: IHomeView) {
        this.view = view;
        this.view.setSaveMenuItemDisabledState(true);
        ipcRenderer.on('close', () => {
            if (this.isSaved) {
                ipcRenderer.send('closed');
            } else {
                this.view.askIfShouldSave().then(async shouldSave => {
                    if (shouldSave) await this.save();
                    ipcRenderer.send('closed');
                });
            }
        });

        ipcRenderer.on('save', () => {
            if (this.theOpenFile && !this.isSaved) {
                this.save().then();
            }
            else{
                this.view.showAlert('warn', `Save File`, "No Changes To Save");
            }
        });
    }

    // override
    didClickOpenWorkspace = (): void => {
        this.view.promptForWorkspaceFilePath();
    };

    // override
    didClickAddImport = (): void => {
        this.view.promptForFileToImport();
    };

    // override
    didChooseImportFile = (file: string): void => {
        if (file.endsWith('.json')) {
            const newFile: CtfFile = jsonclone(this.theOpenFile);
            if (!newFile.import) newFile.import = {};
            newFile.import[
                path.relative(this.getProjectDir() + "/../", file)
            ] = [];
            this.theOpenFile = newFile;
            // need to re resolve import
            ResolveFunctionsAvailableForImport.resolveFromImports(
                path.dirname(this.theOpenFilePath),
                this.getProjectDir(),
                Object.keys(newFile.import)
            ).then(avail => {
                this.context.import = avail;
                this.context.functions = ResolveFunctions.resolve(
                    this.theOpenFile,
                    this.context.import
                );
            }).finally(() => {
                this.view.showCtfFileWithContext(
                    this.theOpenFile,
                    this.context
                );
            });
        }
    };

    createNew = () => {
        const newFile = BuildEmptyCtfFile.build();
        this.theOpenFile = newFile;
        this.theOpenFilePath = '';
        this.isSaved = true;
        this.lastSavedVersion = Object.assign({}, newFile);
        if (this.context) this.context.functions = [];
        // reload the workspace in case the new file was in the workspace
        this.view.showCtfFileWithContext(this.theOpenFile, this.context);
    };

    // override
    didClickNew = () => {
        // check if we might overwrite an existing file
        if (this.isSaved) {
            this.createNew();
        } else {
            this.view.askIfShouldSave().then(async shouldSave => {
                if (shouldSave) {
                    await this.save();
                }
                this.createNew();
            });
        }
    };

    save = async (): Promise<boolean> => {
        let reloadWorkspace = false;
        if (!this.theOpenFilePath || this.theOpenFilePath.length === 0) {
            reloadWorkspace = true;
            this.theOpenFilePath = await this.view.promptForSaveLocation();
            if (!this.theOpenFilePath.endsWith(".json")){
                this.theOpenFilePath += ".json"
            }
        }
        return SaveProjectFile.save(
            this.theOpenFilePath,
            this.theOpenFile,
            this.context.plugins,
            this.context.vehicleData,
            this.context.functions
        ).then(async saved => {
            if (saved) {
                this.lastSavedVersion = Object.assign({}, this.theOpenFile);
                this.isSaved = true;
                this.view.updateSavedIndicator(this.isSaved);
                if (reloadWorkspace) {
                    if (this.workspaceFile)
                        this.openWorkspace(this.workspaceFile);
                }
                this.loadFile(this.theOpenFilePath)
                this.view.showAlert('success', `Save File`, "Success");
            }
            else{
                this.view.showAlert('error', `Save File`, "Error");
            }
            return saved;
        });
    };

    // override
    didClickSave = () => {
        this.save().then();
    };

    loadFile = (filePath: string) => {
        this.view.showLoading(true, 'Loading file...');
        LoadProjectFile.load(filePath)
            .then(async ctfFile => {
                this.theOpenFile = ctfFile;
                this.theOpenFilePath = filePath;
                this.lastSavedVersion = Object.assign({}, this.theOpenFile);
                this.isSaved = true;
                try {
                    this.context.import = await ResolveFunctionsAvailableForImport.resolveFromImports(
                        path.dirname(this.theOpenFilePath),
                        this.getProjectDir(),
                        this.theOpenFile.import
                            ? Object.keys(this.theOpenFile.import)
                            : []
                    );
                } catch (err) {
                    this.context.import = {};
                }
                this.context.functions = ResolveFunctions.resolve(
                    this.theOpenFile,
                    this.context.import
                );
                this.view.showCtfFileWithContext(
                    this.theOpenFile,
                    this.context
                );
                this.view.setSaveMenuItemDisabledState(false);
                this.view.showProjectTree
            })
            .catch(err => {
                this.view.showAlert(
                    'error',
                    'Unable to Open File',
                    err.toString()
                );
                throw err;
            })
            .finally(() => {
                this.view.showLoading(false)
            });
    };

    // override
    didClickFile = (filePath: string) => {
        if (filePath.endsWith('.json')) {
            if (this.isSaved) {
                this.loadFile(filePath);
            } else {
                this.view.askIfShouldSave().then(async shouldSave => {
                    if (shouldSave) {
                        await this.save();
                    }
                    this.loadFile(filePath);
                });
            }
        }
    };

    // override
    didChangeCtfFile = (newFile: CtfFile) => {
            // update the context if necessary
            if (this.theOpenFile.import && newFile.import) {
                const oldImports = Object.keys(this.theOpenFile.import).sort();
                const newImports = Object.keys(newFile.import).sort();
                if (oldImports !== newImports) {
                    // must have removed an import
                    const removed = oldImports.filter(
                        importFile => newImports.indexOf(importFile) < 0
                    );
                    removed.forEach(oldFile => {
                        delete this.context.import[oldFile];
                    });
                }
            this.context.functions = ResolveFunctions.resolve(
                newFile,
                this.context.import
            );
        }

        // add support here for undo
        this.theOpenFile = newFile;

        this.view.showCtfFileWithContext(this.theOpenFile, this.context);

        this.isSaved = false;
        this.view.updateSavedIndicator(this.isSaved);
    };

    shouldRenameFunctionInCtfFile = (oldName: string, newName: string) => {
        RenameFunction.rename(this.theOpenFile, oldName, newName).then(
            result => {
                this.didChangeCtfFile(result);
            }
        );
    };

    getProjectDir = (): string => {
        return this.workspace.projectDir
    }

    openWorkspace = (filePath: string) => {
        this.workspaceFile = filePath;
        OpenWorkspace.open(filePath).then(async workspace => {
            this.workspace = workspace;
            this.view.showProjectTree(this.workspace.projectTree);
            this.context = {
                plugins: workspace.plugins,
                variables: [],
                parameters: [],
                vehicleData: workspace.vehicleData,
                functions: this.theOpenFile
                    ? ResolveFunctions.resolve(this.theOpenFile)
                    : [],
                import: this.theOpenFile ?(await ResolveFunctionsAvailableForImport.resolveFromImports(
                    path.dirname(this.theOpenFilePath),
                    this.getProjectDir(),
                    this.theOpenFile.import
                        ? Object.keys(this.theOpenFile.import)
                        : []
                )) : {}

            };
            if (this.theOpenFile)
                this
                this.view.showCtfFileWithContext(
                    this.theOpenFile,
                    this.context
                );
        }).catch((err) => {
            this.view.showAlert('error', `Unable to open workspace: ${err}`);
        });
    };

    // override
    didChooseWorkspaceFile = (workspaceFilePath: string) => {
        if (this.isSaved) {
            this.openWorkspace(workspaceFilePath);
        } else {
            this.view.askIfShouldSave().then(async shouldSave => {
                if (shouldSave) {
                    await this.save();
                }
                this.openWorkspace(workspaceFilePath);
            });
        }
    };

    // override
    didClickDeleteFiles = (files: string[]) => {
        DeleteFiles.delete(files).then(success => {
            if (this.workspaceFile) this.openWorkspace(this.workspaceFile);
            this.createNew()
        });
    };

    // override
    didClickRunFiles = (files: string[], configPath?: string) => {
        var pythonScriptCall = this.workspace.pythonScriptPath;
        configPath?
            pythonScriptCall = this.workspace.pythonScriptPath + " --config_file " + configPath
            : this.workspace.pythonScriptPath
        console.log("Running " + pythonScriptCall + "On test scripts: ")
        console.log(files)
        this.view.showRunStatusModal(pythonScriptCall, this.workspace.projectDir, files);
    };

    // override
    didClickCreateNewFolderOnFile = (file: string) => {
        const projectFolder = this.workspace.projectTree.items[
            this.workspace.projectTree.rootId
        ].path;

        this.view.promptForNewFolderName(
            path.relative(projectFolder, file)
        );
    };

     // override
     didClickRenameFolderorFile = (file: string) => {
        const projectFolder = this.workspace.projectTree.items[
            this.workspace.projectTree.rootId
        ].path;

        this.view.promptForRenameFileorFolder(
            path.relative(projectFolder, path.dirname(file)), file
        );
    };


    // override
    didChooseNewFolderName = (name: string, parentPath: string) => {
        const projectFolder = this.workspace.projectTree.items[
            this.workspace.projectTree.rootId
        ].path;
        const folderPath = path.resolve(projectFolder, parentPath, name);
        CreateFolder.create(folderPath).then(success => {
            if (this.workspaceFile) this.openWorkspace(this.workspaceFile);
        });
    };

    // override
    didChooseRename = (oldfullname: string, newname: string) => {
        const projectFolder = this.workspace.projectTree.items[
            this.workspace.projectTree.rootId
        ].path;

        //does the new name end with json: if not, add .json at the end
        const stat = fs.lstatSync(oldfullname);
        const isfile = stat.isFile();

        const newnamesplit = newname.split('.');
        if (isfile && newnamesplit[newnamesplit.length-1] != 'json' ) {
            newname += '.json';
        }

        const splitnames = oldfullname.split('/');
        splitnames.pop();
        const strippedname = splitnames.join('/');
        const modifiedname = path.resolve(strippedname, newname);

        CreateFolder.rename(oldfullname, modifiedname).then(success => {
            if (this.workspaceFile) this.openWorkspace(this.workspaceFile);
        });

    };



}