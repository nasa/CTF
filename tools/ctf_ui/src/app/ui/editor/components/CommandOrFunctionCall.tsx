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

import * as React from "react";
import { CtfInstruction, CtfFunctionCall } from "../../../../model/ctf-file";
import { EditingContext } from "../../../../model/editing-context";
import { FindCommandInPlugins } from "../../../../domain/editor-actions/FindCommandInPlugins";
import { Command as Instruction } from "./Command";
import { FunctionCall } from "./FunctionCall";
import { Tooltip, Button, Popconfirm, Icon, Checkbox} from "antd";
import { CheckCircleTwoTone , CloseCircleTwoTone } from '@ant-design/icons';
// icon="check-circle-o"
// <CheckCircleTwoTone onClick = { ()=> { console.log('Icon CheckCircleTwoTone clicked')} } /> 


export const CommandOrFunctionCall: React.FC<{
    data: CtfInstruction | CtfFunctionCall;
    context: EditingContext;
    onChange?: (next: CtfInstruction | CtfFunctionCall) => void;
    onDelete?: () => void;
}> = ({ data, context, onChange, onDelete }) => {   
    
    let disablechecked = false;
    let buttonicontype = 'check-circle-o'  // <Icon type="close-circle-o" />
    let tooltiptitle = 'Disable Test'

    if (data.hasOwnProperty("instruction")) {
        if ( data.hasOwnProperty("disabled") && data.disabled) {
            disablechecked = true;
            buttonicontype = 'close-circle-o';
            tooltiptitle = 'Enable instruction';
        } else {
             tooltiptitle = 'Disable instruction';
        }
    } 

    if (data.hasOwnProperty("function")) {
        if ( data.hasOwnProperty("disabled") && data.disabled) {
            disablechecked = true;
            buttonicontype = 'close-circle-o';
            tooltiptitle = 'Enable function';
        } else {
             tooltiptitle = 'Disable function';
        }        
    }


    let onChangeCheckbox = e => {
        
        if (data.hasOwnProperty("instruction")) { 
            const next = Object.assign({}, data, {disabled: e.target.checked});
           
            if (onChange) onChange(next);

        }    
      };

      let onIconClick = e => {
        
        if (data.hasOwnProperty("instruction") || data.hasOwnProperty("function") ) { 
            const switchenable = !disablechecked;
            const next = Object.assign({}, data, {disabled: switchenable});
            
            if (onChange) onChange(next);

        }    
      }
    
    
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

            &nbsp; 

            <Tooltip title={tooltiptitle}>

                  <Button
                      type="link"
                      style={disablechecked? { color: "red", flex: "0 0 auto" }: { color: "green", flex: "0 0 auto" }}
                      icon= {disablechecked? 'close-circle-o': 'check-circle-o'}                 
                      onClick = {onIconClick}
                  />    

                 {/* <CheckCircleTwoTone twoToneColor="#52c41a" onClick = { ()=> { console.log('Icon CheckCircleTwoTone clicked')} } />  */ }

            </Tooltip>

        </div>
    );
};
