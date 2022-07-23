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

import Text from 'antd/lib/typography/Text';
import Title from 'antd/lib/typography/Title';

import * as React from 'react';
import { Draggable, Droppable } from 'react-beautiful-dnd';
import { jsonclone } from '../../../../domain/jsonclone';
import { CtfInstruction, CtfFunctionCall, CtfTest } from '../../../../model/ctf-file';
import { EditingContext } from '../../../../model/editing-context';
import { CommandOrFunctionCall } from './CommandOrFunctionCall';

export const TestCase: React.FC<{
    className?: string;
    test: CtfTest;
    context: EditingContext;
    droppableIdPrefix: string;
    onChange?: (testCase: CtfTest) => void;
}> = ({ className, test, context, droppableIdPrefix, onChange }) => {
    const changeHandler = (index: number, next: CtfInstruction | CtfFunctionCall) => {
        const updatedTest: CtfTest = jsonclone(test);
        updatedTest.instructions[index] = next;
        if (onChange) onChange(updatedTest);
    };
    const deleteHandler = (index: number) => {
        const updatedTest: CtfTest = jsonclone(test);
        updatedTest.instructions.splice(index, 1);
        if (onChange) onChange(updatedTest);
    };


    return (

        <div className={className}>
            <Text
                editable={{
                    onChange: str => {
                        if (onChange)
                            onChange(
                                Object.assign(jsonclone(test), {
                                    description: str
                                })
                            );
                    }
                }}
            >
                {test.description}
            </Text>
            <br/>
            <Droppable droppableId={droppableIdPrefix + test.test_number}>
                {(provided, snapshot) => (
                    <div ref={provided.innerRef} style={{ minHeight: 40 }}>
                        {test.instructions.map((cmd, index) => (
                            <Draggable
                                key={cmd.id}
                                draggableId={cmd.id}
                                index={index}
                            >
                                {(provided, snapshot) => (
                                    <div
                                        ref={provided.innerRef}
                                        {...provided.draggableProps}
                                        {...provided.dragHandleProps}
                                    >
                                        <CommandOrFunctionCall
                                            data={cmd}
                                            context={context}
                                            onChange={value =>
                                                changeHandler(index, value)
                                            }
                                            onDelete={() =>
                                                deleteHandler(index)
                                            }
                                        />
                                    </div>
                                )}
                            </Draggable>
                        ))}
                        {provided.placeholder}
                    </div>
                )}
            </Droppable>
        </div>
    );
};
