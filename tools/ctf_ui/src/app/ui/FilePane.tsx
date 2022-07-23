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

import { Dropdown, Empty, Tree, Menu, Popover, Tooltip } from 'antd';
import * as React from 'react';
import { FileTree } from '../../model/tree';
import { PaneHeader } from './PaneHeader';
import * as fs from 'fs';

const { TreeNode, DirectoryTree } = Tree;

export interface SelectedItem {
    title: string;
    value: string;
}

interface FilePaneProps {
    tree?: FileTree;
    contextMenu: Array<{ key: string; title: string; icon: React.ReactNode }>;
    onSelect: (item: SelectedItem) => void;
    onContextMenuSelected: (key: string, items: SelectedItem[]) => void;
    emptyMessage: string;
    directory: boolean;
    title: string;
}

interface FilePaneState extends FilePaneProps {
    selected: SelectedItem[];
    rightClicked?: SelectedItem;
}

export class FilePane extends React.Component<FilePaneProps, FilePaneState> {
    onContextMenuClicked = ({ item, key, keyPath, domEvent }) => {
        domEvent.stopPropagation();
        if (this.state.rightClicked) {
            this.state.onContextMenuSelected(key, [
                this.state.rightClicked,
                ...this.state.selected.filter(
                    it => it.value !== this.state.rightClicked.value
                )
            ]);
        }
    };

    constructor(props: FilePaneProps) {
        super(props);
        this.state = Object.assign({ selected: [] }, props);
    }

    componentWillReceiveProps(props: FilePaneProps) {
        this.setState(props);
    }
    
    renderContextMenu = (text: string, isfolder: boolean, isValidJson: boolean): React.ReactNode => {
        const text_color = (isValidJson || isfolder)? {color: "black" }: {color: "#ffa500" };
        return (
            <Dropdown
                overlay={
                    <Menu onClick={this.onContextMenuClicked}>
                        {this.state.contextMenu.map(item => {
                            if ( isfolder == true ) {
                                return ( <Menu.Item key={item.key}>  {item.icon} {item.title} </Menu.Item> )
                            } else if ( item.key != 'new-folder')
                                return (
                                <Menu.Item key={item.key}>  {item.icon} {item.title} </Menu.Item>
                            );
                           })
                        }
                    </Menu>
                }
                trigger={['contextMenu']}
            >
                <span style={text_color} >{text}</span>
            </Dropdown>
        );
    };

    renderTreeNode = (itemId: string) => {
        if (this.state.tree) {
            const node = this.state.tree.items[itemId];
            if (node.children.length > 0) {
                return (
                    <TreeNode
                        title={this.renderContextMenu(node.title, node.isDirectory, node.isValidJson)}
                        key={node.id}
                    >
                        {node.children.map(this.renderTreeNode)}
                    </TreeNode>
                );
            } else {
                let tooltip_title = node.title;
                try {
                    const data = fs.readFileSync(itemId);
                    JSON.parse(data.toString());
                    node.isValidJson = true;
                } catch (err) {
                    tooltip_title = err.toString();
                    tooltip_title += '; Run jsonlint tool against it for more details ';
                    node.isValidJson = false;
                }

                return (
                    <TreeNode
                        title={
                            <Tooltip placement="top" title={(<div><p> {tooltip_title} </p></div>)}>
                            {this.renderContextMenu(node.title, node.isDirectory, node.isValidJson)}
                            </Tooltip>
                        }

                        key={node.id}
                        isLeaf={!node.isDirectory}
                    />
                );
            }
        } else {
            return <div />;
        }
    };

    onSelect = (itemKeys: string[]) => {
        if (this.state.tree) {
            this.setState({
                selected: itemKeys.map(k => ({
                    title: this.state.tree.items[k].title,
                    value: this.state.tree.items[k].path
                }))
            });
            if (itemKeys.length === 1) {
                this.state.onSelect({
                    title: this.state.tree.items[itemKeys[0]].title,
                    value: this.state.tree.items[itemKeys[0]].path
                });
            }
        }
    };

    onRightClick = ({ node }) => {
        const key = node.props.eventKey;
        if (this.state.tree) {
            this.state.onSelect({
                title: this.state.tree.items[key].title,
                value: this.state.tree.items[key].path
            });
            this.setState({
                rightClicked: {
                    title: this.state.tree.items[key].title,
                    value: this.state.tree.items[key].path
                }
            });
        }
    };

    render() {
        return (
            <div>
                <PaneHeader>{this.state.title}</PaneHeader>
                {this.state.tree ? (
                    <DirectoryTree
                        defaultExpandedKeys={[this.state.tree.rootId]}
                        onSelect={this.onSelect}
                        onRightClick={this.onRightClick}
                        multiple
                    >
                        {this.renderTreeNode(
                            this.state.tree.items[this.state.tree.rootId].id
                        )}
                    </DirectoryTree>
                ) : (
                    <Empty
                        style={{ margin: '24px 0px' }}
                        description={<span>{this.state.emptyMessage}</span>}
                    />
                )}
            </div>
        );
    }
}
