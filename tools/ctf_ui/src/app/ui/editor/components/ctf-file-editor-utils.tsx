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

import { Button } from 'antd';
import Text from 'antd/lib/typography/Text';
import * as React from 'react';
import styled from 'styled-components';

export const ParamArray: React.FC<{ name: string }> = ({ name, children }) => (
    <div>
        <Text strong>{name}</Text><br />
        {children}
    </div>
)

export const ButtonWithTopSpacing = styled(Button)`
    margin: 14px 0 0 0;
`;

export const DeleteButton = styled(ButtonWithTopSpacing)`
    margin: 14px 0 0 0;
    flex: 0 0 auto;
    background-color: #d50000;
    border: darkred;
    color: white;
    &:focus {
        background-color: #d50000;
        color: white;
    }
    &:hover {
        background-color: #ff5131;
        color: white;
    }
`;