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

import { Button, Divider, Popover, Tooltip, InputNumber, Input } from "antd";
import Text from "antd/lib/typography/Text";
import * as React from "react";
import { CtfFunctionCall } from "../../../../model/ctf-file";
import { EditingContext } from "../../../../model/editing-context";
import { FillWidthAutoCompleteField } from "./AutoCompleteField";
import { CheckCircleTwoTone, MessageOutlined,MessageTwoTone  } from '@ant-design/icons';

const { TextArea } = Input;

const FunctionCallStyle: React.CSSProperties = {
    flex: "1 1 auto",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis"
};

export const FunctionCall: React.FC<{
    call: CtfFunctionCall;
    context: EditingContext;
    onChange?: (next: CtfFunctionCall) => void;

}> = ({ call, context, onChange }) => {
    const changeHandler = (paramName, value) => {
        const next = Object.assign({}, call);
        next.params[paramName] = value.length == 0? value : 
            (isNaN(Number(value)) ? value : Number(value));
        if (onChange) onChange(next);
    };

    const waitChangeHandler = (newWait) => {
        const next = Object.assign({}, call);
        next.wait = newWait;
        if (onChange) onChange(next);
    }

    const renderDescription = (description: string) => {
       
        return (

            <TextArea   name = 'description_input'
                        defaultValue={description} 
                        autoSize={{ minRows: 2, maxRows: 6 }}
                        onChange = { e => {
                            const next = Object.assign({}, call, {description: e.target.value});
                            if (onChange) onChange(next);
                         }
                        
                        }  
            />             
            )

    }

    

    const functionInfo = context.functions.find(f => f.name === call.function);
    if (functionInfo) {
        const funcDef = functionInfo.function;
        const dataSource = [
            {
                label: "Parameters",
                value: "Parameters",
                children: context.parameters.map(v => ({ label: v, value: v }))
            },
            {
                label: "Variables",
                value: "Variables",
                children: context.variables.map(v => ({ label: v, value: v }))
            }
        ];
        for (var param in call.params) {
            if (funcDef.varlist.indexOf(param) === -1) {
                // bad argument name
                delete call.params[param];
            }
        }

        let buttondisabled = false;
        let textbackgroundcolor = { backgroundColor: 'White' };
        let groupcolor = 'blue'

        if (call.hasOwnProperty("disabled") && call.disabled ) {
            buttondisabled = true;
            textbackgroundcolor = { backgroundColor: '#F3F3F3' };
            groupcolor = '#F3F3F3' ;
        } 

        return (
            <div style={FunctionCallStyle}>

                <Tooltip title={call.description}>
                        <Popover
                            placement="rightTop"
                            title="Description"
                            trigger="click"
                            content= {renderDescription(call.description)} 
                        >
                            
                            <MessageTwoTone/>         
                        
                        </Popover>
                </Tooltip> 

                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;

                <Tooltip                         
                        placement="top"
                        title={`Delay before running this instruction`}
                    >
                    <InputNumber
                        defaultValue={call.wait}
                        onChange={num => {
                        if (waitChangeHandler)
                            waitChangeHandler(num);
                        }}
                        size="small"
                        step={0.1}
                        min={0}
                        disabled = {buttondisabled} 
                    />
                </Tooltip>

                <Divider type="vertical" />
                <Popover
                    placement="rightTop"
                    title="Arguments"
                    trigger="click"
                    content={
                        funcDef.varlist.length > 0 ? (
                            funcDef.varlist.map((paramName, index) => (
                                <FillWidthAutoCompleteField
                                    title={paramName}
                                    defaultValue={
                                        (call.params && call.params[paramName] !== undefined)
                                            ? call.params[paramName]
                                            : ""
                                    }
                                    key = {index}
                                    dataSource={dataSource}
                                    onChange={value =>
                                        changeHandler(paramName, value)
                                    }
                                />
                            ))
                        ) : (
                            <em>None</em>
                        )
                    }
                >
                    <Button type="dashed" style={{ minWidth: 150 }} disabled = {buttondisabled} >
                        {call.function}
                    </Button>
                </Popover>
                <span>
                    {funcDef.varlist.map(arg => (
                        <span key={arg}>
                            <Divider type="vertical" />
                            <Text type="secondary" style={textbackgroundcolor} >
                                {arg} = {JSON.stringify(call.params[arg])}
                            </Text>
                        </span>
                    ))}
                </span>


            </div>
        );
    } else {
        return (
            <div style={FunctionCallStyle}>
                <Tooltip
                    placement="right"
                    title={`Unable to resolve ${call.function}`}
                >
                    <Button
                        type="dashed"
                        icon="warning"
                        style={{ minWidth: 150 }}
                    >
                        {call.function}
                    </Button>
                </Tooltip>
            </div>
        );
    }
};
