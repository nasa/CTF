/*
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2024 United States Government as represented by the
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
import * as ReactDOM from 'react-dom';
import Home from './home/HomeView';
import { AppContainer, hot } from 'react-hot-loader';

const rootElem = document.createElement('div');
rootElem.style.height = '100%';
document.body.appendChild(rootElem);

const render = Component => {
    ReactDOM.render(<AppContainer><Component /></AppContainer>, rootElem);
}

render(Home);

if ((module as any).hot) {
    (module as any).hot.accept('./home/HomeView', () => { render(Home) });
}