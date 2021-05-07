# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2021 United States Government as represented by the
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

import os
import pathlib
from unittest.mock import patch

from lib import ctf_utility


def test_ctf_utility_expand_path():
    assert ctf_utility.expand_path('') == ''
    assert ctf_utility.expand_path('dir') == 'dir'
    assert ctf_utility.expand_path('./this/is_a/path/') == './this/is_a/path/'
    assert ctf_utility.expand_path('~') == str(pathlib.Path.home())
    with patch.dict(os.environ, {'myvar': 'foo/bar'}):
        assert ctf_utility.expand_path('$myvar/dir') == 'foo/bar/dir'
        assert ctf_utility.expand_path('~/$myvar/path') == str(pathlib.Path.home()) + '/foo/bar/path'
