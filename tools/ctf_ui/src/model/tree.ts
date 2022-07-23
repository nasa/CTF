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

export class FileTreeNode {
    id: string;
    title: string;
    path: string;
    isDirectory: boolean;
    isValidJson: boolean;
    children: string[];
    constructor(id: string, title: string, value: string, isDirectory: boolean, isValidJson: boolean, children?: string[]) {
        this.id = id;
        this.title = title;
        this.path = value;
        this.isDirectory = isDirectory;
        this.isValidJson = isValidJson;
        this.children = children ? children : [];
    }
}

export class FileTree {
    rootId: string;
    items: {
        [id: string]: FileTreeNode;
    };
    constructor(rootId: string, items: { [id: string]: FileTreeNode }) {
        this.rootId = rootId;
        this.items = items;
    }
}