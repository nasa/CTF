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

import { FileTree, FileTreeNode } from "../../model/tree";
import * as fs from 'fs';
import * as path from 'path';

export class FindJsonFiles {
    static async populateResult(rootDirectory: string, previousResult?: FileTree): Promise<FileTree> {
        return new Promise<FileTree>((resolve, reject) => {
            let absolutePath = rootDirectory;
            let result = previousResult || new FileTree(absolutePath, {});
            result.items[absolutePath] = new FileTreeNode(
                absolutePath,
                path.basename(rootDirectory),
                absolutePath,
                true,
                false,
                []
            );
            fs.readdir(
                absolutePath,
                { withFileTypes: true },
                async (err: any, files) => {
                    if (err) {
                        reject(err);
                    } else {
                        await Promise.all(files
                        .filter((item) => {
                            return item.isDirectory() || item.name.toLowerCase().endsWith(".json")
                        })
                        .map(
                            async (item) => {

                                let itemIsvalidjson = item.isDirectory()? false: true

                                const itemAbsPath = path.resolve(absolutePath, item.name);
                                result.items[itemAbsPath] = {
                                    id: itemAbsPath,
                                    title: item.name,
                                    path: itemAbsPath,
                                    isDirectory: item.isDirectory(),
                                    isValidJson: itemIsvalidjson,
                                    children: []
                                };
                                result.items[absolutePath].children.push(itemAbsPath);
                                if (item.isDirectory()) {
                                    await this.populateResult(itemAbsPath, result);
                                }
                            }
                        ));
                        resolve(result);
                    }
                }
            );
        });
    }
    static find(rootDirectory: string): Promise<FileTree> {
        return this.populateResult(rootDirectory);
    }
}