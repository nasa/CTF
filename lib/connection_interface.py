# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2020 United States Government as represented by the
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


class ConnectionInterface(object):
    def __init__(self):
        pass

    def init(self):
        pass

    def connect(self):
        pass

    def disconnect(self):
        pass

    def send_command(self):
        pass

    def start_process(self):
        pass

    def check_output(self):
        pass

    def put_files(self):
        pass

    def get_files(self):
        pass


class LocalConnection(ConnectionInterface):
    pass


class SshConnection(ConnectionInterface):
    pass


class SP0Connection(ConnectionInterface):
    pass
