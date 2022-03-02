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

import { Collapse, Tooltip, Empty, Button } from 'antd';
import * as React from 'react';
import { Draggable, Droppable } from 'react-beautiful-dnd';
import { PaneHeader } from "../../PaneHeader";

const { Panel } = Collapse;

export interface LibraryElementData {
    name: string,
    description: string
}

export interface LibraryGroup {
    name: string,
    elements: LibraryElementData[]
}

export type LibraryData = LibraryGroup[]

const LibraryElementStyle = {
    paddingTop: 6
}

const LibraryElement: React.FC<{
    elem: LibraryElementData
}> = ({ elem }) => {
    return <div style={LibraryElementStyle}>
        <Tooltip placement="leftTop" title={elem.description ? elem.description : 'No description'}>
            <Button style={{ minWidth: 150 }}>{elem.name}</Button>
        </Tooltip>
    </div>
}

interface LibraryPaneProps {
    title: string;
    data: LibraryData;
    droppableIdPrefix: string;
}

export const LibraryPane: React.FC<LibraryPaneProps> = ({ title, data, droppableIdPrefix }) => {
    return <div>
        <PaneHeader>{title.toUpperCase()}</PaneHeader>
        { 
            (data && data.length) > 0 ? 
                <Collapse 
                    bordered={false}
                    defaultActiveKey={[]}>
                    {data.map((group, i) => (
                        <Panel header={group.name.toUpperCase()} key={group.name}>
                            <Droppable
                                droppableId={droppableIdPrefix + group.name}
                                isDropDisabled={true}>
                                { (provided, snapshot) => (
                                    <div ref={provided.innerRef}>
                                        {group.elements.map((elem, i) => (
                                            <Draggable
                                                key={group.name + '.' + elem.name}
                                                draggableId={group.name + '.' + elem.name}
                                                index={i}
                                                disableInteractiveElementBlocking={true}>
                                                { (provided, snapshot) => (
                                                    <div
                                                        ref={provided.innerRef}
                                                        {...provided.draggableProps}
                                                        {...provided.dragHandleProps}>
                                                        <LibraryElement elem={elem}/>
                                                    </div>
                                                )}
                                            </Draggable>
                                        ))}
                                        {provided.placeholder}
                                    </div>
                                )}
                            </Droppable>
                        </Panel>
                    ))}
                </Collapse>
        : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={'None'} /> }
        
    </div>
}