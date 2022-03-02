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

import * as React from 'react';
import { Button, Input, Tag } from 'antd';
import * as uuid from 'uuid/v4';

interface FunctionParametersProps {
    params: string[];
    onChange?: (varlist: string[]) => void
}

interface FunctionParametersState extends FunctionParametersProps {
    inputVisible: boolean,
    inputValue: string
}

export class FunctionParameters extends React.Component<FunctionParametersProps, FunctionParametersState> {
    constructor(props: FunctionParametersProps) {
        super(props);
        this.state = Object.assign({}, props, { inputVisible: false, inputValue: '' });
    }

    componentWillReceiveProps(props: FunctionParametersProps) {
        this.setState({ params: props.params, onChange: props.onChange });
    }

    handleEnterPressed = () => {
        if (this.state.inputValue.length > 0) {
            const newParams = Array.from(this.state.params);
            newParams.push(this.state.inputValue);
            if (this.state.onChange) this.state.onChange(newParams);
            this.setState({ inputVisible: false, inputValue: '' })
        }
    }

    deleteParam = (name: string) => {
        const newParams = this.state.params.filter((p) => p !== name);
        if (this.state.onChange) this.state.onChange(newParams);
    }

    render() {
        return <div>
            {this.state.params.map((param, i) => {
                // use new uuid every time so react must remount the Tag
                // this is because antd tries to be helpful and hide the tag after it closes
                // however, we are pushing state updates back down to this component
                // so the hiding logic is unnecessary and actually hides a tag
                // that was not deleted
                return <Tag key={uuid()} closable={true} onClose={(e) => this.deleteParam(param)} hidden={false}>{param}</Tag>
            })}
            { this.state.inputVisible ? <Input 
                size="small"
                style={{ width: 80 }}
                onChange={(e) => this.setState({ inputValue: e.target.value })} 
                onPressEnter={this.handleEnterPressed}
                autoFocus={true}
                onBlur={(e) => this.setState({ inputVisible: false, inputValue: '' })}/>
                : <Button size="small" type="dashed" icon="plus" onClick={() => this.setState({ inputVisible: true })}>ADD PARAMETER</Button> }
            
        </div>
    }    
}