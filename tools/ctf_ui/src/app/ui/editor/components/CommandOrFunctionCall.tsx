/*
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2020 United States Government as represented by the
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

import * as React from "react";
import { CtfInstruction, CtfFunctionCall } from "../../../../model/ctf-file";
import { EditingContext } from "../../../../model/editing-context";
import { FindCommandInPlugins } from "../../../../domain/editor-actions/FindCommandInPlugins";
import { Command as Instruction } from "./Command";
import { FunctionCall } from "./FunctionCall";
import { Tooltip, Button, Popconfirm, Icon } from "antd";

export const CommandOrFunctionCall: React.FC<{
    data: CtfInstruction | CtfFunctionCall;
    context: EditingContext;
    onChange?: (next: CtfInstruction | CtfFunctionCall) => void;
    onDelete?: () => void;
}> = ({ data, context, onChange, onDelete }) => {
    return (
        <div style={{ display: "flex", alignItems: "center", paddingTop: 6 }}>
            {(() => {
                if (data.hasOwnProperty("instruction")) {
                    const command = data as CtfInstruction;
                    const pluginInfo = FindCommandInPlugins.find(
                        command.instruction,
                        context.plugins
                    );
                    return (
                        <Instruction
                            ctfCommand={command}
                            groupName={pluginInfo ? pluginInfo.group_name : null}
                            definition={pluginInfo ? pluginInfo.instructionDef : null}
                            context={context}
                            onChange={onChange}
                        />
                    );                    
                } else {
                    const functionCall = data as CtfFunctionCall;
                    return (
                        <FunctionCall
                            call={functionCall}
                            context={context}
                            onChange={onChange}
                        />
                    );
                }
            })()}
            <Tooltip title={"Delete"}>
                <Popconfirm
                    title="Delete this element?"
                    placement="right"
                    icon={<Icon type="warning" />}
                    onConfirm={onDelete}
                    okText="Delete"
                    okType="danger"
                    cancelText="Cancel"
                >
                    <Button
                        type="link"
                        style={{ color: "gray", flex: "0 0 auto" }}
                        icon="minus-circle"
                    />
                </Popconfirm>
            </Tooltip>
        </div>
    );
};
