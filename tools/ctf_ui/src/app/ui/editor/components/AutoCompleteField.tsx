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

import { AutoComplete, Input, Icon } from "antd";
import { CascaderOptionType } from "antd/lib/cascader";
import * as React from "react";
import styled from "styled-components";

const { Option, OptGroup } = AutoComplete;

interface FieldProps {
    className?: string;
    style?: object;
    title?: string;
    dataSource: CascaderOptionType[];
    defaultValue?: any;
    placeholder?: string;
    onChange?: (e: any) => void;
}

interface FieldState extends FieldProps {}

export class AutoCompleteField extends React.Component<FieldProps, FieldState> {
    constructor(props: FieldProps) {
        super(props);
        this.state = Object.assign({}, props);
    }

    componentWillReceiveProps(props: FieldProps) {
        this.setState(props);
    }

    renderOptions(options: CascaderOptionType[], level: number = 0) {
        return options
            .filter(o => !o.children || (o.children && o.children.length > 0))
            .map(option => {
                if (option.children) {
                    return (
                        <OptGroup
                            key={`${option.value}-${level}-group`}
                            label={"\u2001".repeat(level) + option.label}
                        >
                            {this.renderOptions(option.children, level + 1)}
                        </OptGroup>
                    );
                } else {
                        return (
                            <Option
                                key={`${option.value}-${level}`}
                                style={{ paddingLeft: `${level}em` }}
                                value={option.value}
                            >
                                {option.value}
                            </Option>
                        );
                }
            });
    }

    valueIsInOptions(value: string, options: CascaderOptionType[] = this.state.dataSource): boolean {
        return options.map((o) => (
            (o.children && this.valueIsInOptions(value, o.children)) || o.value === value
        )).indexOf(true) !== -1;
    }

    render() {
        return (
            <AutoComplete
                className={this.state.className}
                style={Object.assign({ marginBottom: 6 }, this.state.style)}
                size={"small"}
                autoFocus={true}
                disabled={this.state.disabled}
                defaultActiveFirstOption={true}
                filterOption={(inputValue, option) => {
                    return (
                        !option.key.toString().endsWith("-group") &&
                        option.props.value &&
                        option.props.value
                            .toString()
                            .toLowerCase()
                            .indexOf(inputValue.toLowerCase()) >= 0
                    );
                }}
                placeholder={this.state.placeholder}
                dataSource={this.renderOptions(this.state.dataSource)}
                defaultValue={this.state.defaultValue !== undefined ? this.state.defaultValue.toString(): ""}
                dropdownMatchSelectWidth={false}
                onChange={value => {
                    if (this.state.onChange) this.state.onChange(value);
                }}
            >
                <Input
                    addonBefore={this.state.title}
                    suffix={this.valueIsInOptions(this.state.defaultValue) ? <Icon type="check-circle" style={{ color: 'forestgreen' }}/> : undefined}
                    />
            </AutoComplete>
        );
    }
}

export const FillWidthAutoCompleteField = styled(AutoCompleteField)`
    display: block;
`;
