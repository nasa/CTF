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

import { Layout, Modal, message, Icon, Menu, Input } from 'antd';
import 'antd/dist/antd.css';
import { remote } from 'electron';
import { TitleBar } from 'electron-react-titlebar';
import 'electron-react-titlebar/assets/style.css';
import * as React from 'react';
import { CtfFile } from '../../../model/ctf-file';
import { EditingContext } from '../../../model/editing-context';
import { FileTree } from '../../../model/tree';
import { CtfFileEditorInst } from '../editor/CtfFileEditor';
import { FilePane, SelectedItem } from '../FilePane';
import { ChooseJsonFile, ChooseIniFile } from '../util/ChooseJsonFile';
import { HomePresenter, IHomePresenter, IHomeView } from './HomePresenter';
import { RunStatusView } from '../runstatus/RunStatusView';
const { dialog } = remote;

const { Sider, Header } = Layout;

interface HomeState {
    projectTree?: FileTree;
    fileCurrentlyEditing?: CtfFile;
    context?: EditingContext;
    presenter: IHomePresenter;
    menuTemplate: any[];
    fileIsSaved: boolean;
    showLoading: boolean;
    loadingMessage?: string;
}

class Home extends React.Component<object, HomeState> implements IHomeView {
    activeModal?: any;
    constructor(props: object) {
        super(props);
        this.state = {
            showLoading: false,
            fileIsSaved: true,
            presenter: new HomePresenter(this),
            menuTemplate: [
                {
                    label: 'File',
                    submenu: [
                        {
                            label: 'Open Workspace',
                            click: () =>
                                this.state.presenter.didClickOpenWorkspace()
                        },
                        {
                            label: 'New Test Script',
                            click: () => this.state.presenter.didClickNew()
                        },
                        {
                            label: 'Save Test Script',
                            click: () => this.state.presenter.didClickSave(),
                            enabled: false
                        }
                    ]
                }
            ]
        };
    }

    // override
    promptForSaveLocation = (): Promise<string> => {
        return new Promise((res, rej) => {
            const fileLocation = dialog.showSaveDialog({
                filters: [{ name: 'JSON Files', extensions: ['json']}],
                defaultPath: this.state.presenter.getProjectDir()
            });
            if (fileLocation && fileLocation.length > 0) {
                res(fileLocation);
            } else {
                rej('no path selected');
            }
        });
    };

    // override
    setSaveMenuItemDisabledState = (disabled: boolean) => {
        if (this.state) {
            const { menuTemplate } = this.state;
            menuTemplate[0].submenu[2].enabled = !disabled;
            this.setState({ menuTemplate });
        }
    };

    // override
    promptForWorkspaceFilePath = (): void => {
        const files = ChooseJsonFile.choose('Open Workspace File');
        if (files && files.length === 1) {
            this.state.presenter.didChooseWorkspaceFile(files[0]);
        }
    };

    // override
    promptForFileToImport = (): void => {
        const files = ChooseJsonFile.choose('Choose Import File');
        if (files && files.length === 1) {
            this.state.presenter.didChooseImportFile(files[0]);
        }
    };

    promptForCustomConfig = (): string => {
        const files = ChooseIniFile.choose("Choose Custom Config File")
        if (files && files.length === 1) {
            return files[0]
        }
        return undefined
    }

    // override
    promptForNewFolderName = (curPath: string): void => {
        let name = '';
        Modal.confirm({
            title: 'New Folder',
            width : 650,
            content: (
                <Input
                    placeholder="Folder Name"
                    addonBefore={curPath}
                    onChange={it => (name = it.target.value)}
                    autoFocus
                />
            ),
            onOk: () => {
                this.state.presenter.didChooseNewFolderName(name, curPath);
            }
        });
    };

    // override
    promptForRenameFileorFolder = (parentPath: string, oldfullfilename: string ): void => {
        let splitfilename = oldfullfilename.split('/');
        let nametochange = splitfilename.pop();
        let newname = '';
        Modal.confirm({
            title: 'Rename to: ',
            content: (
                <Input
                    defaultValue={nametochange}
                    onChange={it => (newname = it.target.value)}
                    autoFocus
                />
            ),
            onOk: () => {
                this.state.presenter.didChooseRename(oldfullfilename, newname);
            }
        });
    };


    // override
    askIfShouldSave = (): Promise<boolean> => {
        return new Promise((res, rej) => {
            dialog.showMessageBox(
                {
                    message: 'Do you want to save the open file first?',
                    type: 'warning',
                    buttons: ['No', 'Yes']
                },
                response => {
                    res(response === 1);
                }
            );
        });
    };

    // override
    showProjectTree = (tree: FileTree) => {
        this.setState({ projectTree: tree });
    };

    // override
    showCtfFileWithContext = (file: CtfFile, context: EditingContext): void => {
        this.setState({ fileCurrentlyEditing: file, context: context });
    };

    // override
    fileSelected = (item: SelectedItem) => {
        this.state.presenter.didClickFile(item.value);
    };

    // override
    updateSavedIndicator = (isSaved: boolean) => {
        this.setState({ fileIsSaved: isSaved });
    };

    // override
    showLoading = (show: boolean, message: string) => {
        // this.setState({ showLoading: show, loadingMessage: message });
    };

    // override
    showAlert = (type: string, title: string, content: string) => {
        const options = {
            title: title,
            content: message
        };
        switch (type) {
            case 'error':
                message.error(`${title}: ${content}`);
                break;
            case 'success':
                message.success(`${title}: ${content}`)
                break;
            case 'warn':
                message.warn(`${title}: ${content}`)
                break;
            default:
            message.info(`${title}: ${content}`);
        }
    };

    // override
    showRunStatusModal = (pythonCmd: string, projectDir: string, scripts: string[]) => {
        const modal = Modal.confirm({
            title: 'Run Status',
            width: '70%',
            content: (
                <RunStatusView
                    pythonCommand={pythonCmd}
                    scripts={scripts}
                    projectDir={projectDir}
                    onComplete={() =>
                        modal.update({
                            okText: 'Done',
                            okButtonProps: { disabled: false },
                            cancelButtonProps: { disabled: true }
                        })
                    }
                />
            ),
            cancelText: 'Cancel',
            onCancel: () => {
                modal.destroy();
            },
            okText: 'Running',
            okButtonProps: {
                disabled: true
            }
        });
    };

    render() {
        return (
            <Layout style={{ height: '100%' }}>
                <TitleBar menu={this.state.menuTemplate} />
                <Modal
                    title={this.state.loadingMessage}
                    visible={this.state.showLoading}
                />
                <Layout>
                    <Sider
                        width={300}
                        style={{ overflowX: 'auto' }}
                        theme="light"
                        collapsible
                    >
                        <div style={{marginBottom: '50px'}}>
                        <FilePane
                            title="Test Scripts"
                            directory
                            emptyMessage="File > Open Workspace"
                            tree={this.state.projectTree}
                            onSelect={this.fileSelected}
                            contextMenu={[
                                {
                                    key: 'run',
                                    title: 'Run (Default Config)',
                                    icon: <Icon type="caret-right" />
                                },
                                {
                                    key: 'run_custom_config',
                                    title: 'Run (Custom Config)',
                                    icon: <Icon type="caret-right" />
                                },
                                {
                                    key: 'new-folder',
                                    title: 'New Folder',
                                    icon: <Icon type="folder-add" />
                                },
                                {
                                    key: 'rename',
                                    title: 'Rename',
                                    icon: <Icon type="edit" />
                                },
                                {
                                    key: 'delete',
                                    title: 'Delete',
                                    icon: <Icon type="delete" />
                                }
                            ]}
                            onContextMenuSelected={(key, items) => {
                                if (key === 'delete') {
                                    Modal.confirm({
                                        title: `Delete ${
                                            items.length
                                        } file(s)?`,
                                        onOk: () => {
                                            this.state.presenter.didClickDeleteFiles(
                                                items.map(i => i.value)
                                            );
                                        }
                                    });
                                } else if (key === 'run') {
                                    this.state.presenter.didClickRunFiles(
                                        items.map(i => i.value)
                                    );
                                } else if (key === 'run_custom_config') {
                                    var new_config = this.promptForCustomConfig()
                                    if (new_config === undefined){
                                        this.showAlert("error", "Failed to load custom config file", "Ensure config.ini selected is valid");
                                        return
                                    }
                                    this.state.presenter.didClickRunFiles(
                                        items.map(i => i.value), new_config
                                    );
                                } else if (key === 'new-folder') {
                                    this.state.presenter.didClickCreateNewFolderOnFile(
                                        items[0].value
                                    );
                                } else if (key === 'rename') {
                                    this.state.presenter.didClickRenameFolderorFile(
                                        items[0].value
                                    );
                                }
                            }}
                        />
                        </div>
                    </Sider>
                    <CtfFileEditorInst
                        ctfFile={this.state.fileCurrentlyEditing}
                        context={this.state.context}
                        onChange={this.state.presenter.didChangeCtfFile}
                        showDirtyFlag={!this.state.fileIsSaved}
                        visible = {false}
                        onRenameFunction={
                            this.state.presenter.shouldRenameFunctionInCtfFile
                        }
                        onAddImportFile={this.state.presenter.didClickAddImport}
                    />
                </Layout>
            </Layout>
        );
    }
}

export default Home;
