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

import json
import glob
from jsonschema import validate, ValidationError

SCHEMA_PATH = "schemas/CCSDS_Telemetry_Export.json"
JSON_DIR = "../../../../../ccdd/json/*.json"

schema = None
with open(SCHEMA_PATH, 'r') as schema:
    s = schema.read()
    schema = json.loads(s)


for filepath in glob.iglob(JSON_DIR):
    cur_json_fp = open(filepath, "r")
    cur_json = json.load(cur_json_fp)
    try:
        validate(instance=cur_json, schema=schema)
    except ValidationError as exception:
        print("Error in file " + filepath)
        print(exception.message)
    cur_json_fp.close()
