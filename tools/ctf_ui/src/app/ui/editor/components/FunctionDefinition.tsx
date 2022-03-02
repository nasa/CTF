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

import { Divider } from 'antd';
import Text from 'antd/lib/typography/Text';
import * as React from 'react';
import { Draggable, Droppable } from 'react-beautiful-dnd';
import { jsonclone } from '../../../../domain/jsonclone';
import {
    CtfInstruction,
    CtfFunction,
    CtfFunctionCall
} from '../../../../model/ctf-file';
import { EditingContext } from '../../../../model/editing-context';
import { CommandOrFunctionCall } from './CommandOrFunctionCall';
import { FunctionParameters } from './FunctionParameters';

// render a function definition
// note that the parameters element of the editing context
// is updated with the value of the function's varlist
export const FunctionDefinition: React.FC<{
    name: string;
    func: CtfFunction;
    context: EditingContext;
    droppableIdPrefix: string;
    onChange?: (next: CtfFunction) => void;
}> = ({ name, func, context, droppableIdPrefix, onChange }) => {
    const changeHandler = (
        index: number,
        next: CtfInstruction | CtfFunctionCall
    ) => {
        const updatedFunction = jsonclone(func);
        updatedFunction.instructions[index] = next;
        if (onChange) onChange(updatedFunction);
    };
    const deleteHandler = (index: number) => {
        const updatedFunction = jsonclone(func);
        updatedFunction.instructions.splice(index, 1);
        if (onChange) onChange(updatedFunction);
    };
    const handleParameterChange = (next: string[]) => {
        const updatedFunction = jsonclone(func);
        updatedFunction.varlist = next;
        if (onChange) onChange(updatedFunction);
    };
    return (
        <div>
            <Text
                editable={{
                    onChange: str => {
                        if (onChange)
                            onChange(
                                Object.assign(jsonclone(func), {
                                    description: str
                                })
                            );
                    }
                }}
            >
                {func.description}
            </Text>
            <Divider />
            <FunctionParameters
                params={func.varlist}
                onChange={handleParameterChange}
            />
            <Divider />
            <Droppable droppableId={droppableIdPrefix + name}>
                {(provided, snapshot) => (
                    <div ref={provided.innerRef} style={{ minHeight: 40 }}>
                        {func.instructions.map((cmd, index) => (
                            <div key={cmd.id}>
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
                                                context={Object.assign(
                                                    {},
                                                    context,
                                                    { parameters: func.varlist }
                                                )}
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
                            </div>
                        ))}
                        {provided.placeholder}
                    </div>
                )}
            </Droppable>
        </div>
    );
};
