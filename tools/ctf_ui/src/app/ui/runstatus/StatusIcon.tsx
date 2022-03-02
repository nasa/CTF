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
import { Tooltip, Icon } from "antd";
import { CtfRunStatus } from "../../../model/ctf-engine";

export const StatusIcon: React.FC<{
    status?: CtfRunStatus;
}> = ({ status }) => {
    switch (status) {
        case 'waiting':
            return (
                <Tooltip title="Waiting">
                    <Icon style={{ color: "gray" }} type="ellipsis" />
                </Tooltip>
            );
        case 'active':
            return (
                <Tooltip title="Running">
                    <Icon style={{ color: "#1890ff" }} type="loading" />
                </Tooltip>
            );
        case 'passed':
            return (
                <Tooltip title="Test Passed">
                    <Icon style={{ color: "green" }} type="check-circle" theme="filled" />
                </Tooltip>
            );
        case 'failed':
            return (
                <Tooltip title="Test Failed">
                    <Icon style={{ color: "red" }} type="close-circle" />
                </Tooltip>
            );
        case 'disabled':
            return (
                <Tooltip title="Instruction Disabled">
                     <Icon style={{ color: "grey" }} type="stop" theme="twoTone"/>
                </Tooltip>
                );
        case 'error':
            return (
                <Tooltip title="Error occured while running test">
                    <Icon style={{ color: "orange" }} type="warning" theme="filled" />
                </Tooltip>
            );
        default:
            return (
                <span></span>
            );
    }
};
