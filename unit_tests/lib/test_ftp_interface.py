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

import ftplib
import os
import shutil
from unittest.mock import patch, mock_open

import pytest
from ftputil import FTPHost

from lib.ftp_interface import FtpInterface


@pytest.fixture(name='iftp')
def ftp_interface():
    return FtpInterface()


@pytest.fixture(name='iftp_conn')
def ftp_interface_connected(iftp):
    with patch('lib.ftp_interface.ftplib.FTP', spec=ftplib.FTP), \
         patch('lib.ftp_interface.ftputil.FTPHost', spec=FTPHost):
        assert iftp.connect_ftp('ipaddr', 'usrid')
        return iftp


def test_ftp_interface_init(iftp):
    assert iftp.uploadlevel == 0
    assert iftp.ftp is None
    assert not iftp.curdir
    assert not iftp.ipaddr
    assert not iftp.ftpconnect
    assert iftp.ftp_timeout == 5
    assert iftp.remotebase is None


def test_ftp_interface_connect_ftp(iftp_conn, utils):
    iftp_conn.ftp.login.assert_called_once()
    assert iftp_conn.ftp
    assert iftp_conn.curdir
    assert iftp_conn.remotebase
    assert iftp_conn.ftpconnect
    assert not utils.has_log_level('WARNING')


def test_ftp_interface_connect_ftp_errors(iftp, utils):
    with patch('lib.ftp_interface.ftplib.FTP', spec=ftplib.FTP) as mock_ftp:
        mock_ftp.side_effect = OSError('mock error')
        assert not iftp.connect_ftp('ipaddr', 'usrid')
    assert not iftp.ftpconnect
    assert not iftp.remotebase
    assert utils.has_log_level('WARNING')
    utils.clear_log()

    with patch('lib.ftp_interface.ftplib.FTP', spec=ftplib.FTP) as mock_ftp:
        mock_ftp.return_value.login.side_effect = OSError('mock error')
        assert not iftp.connect_ftp('ipaddr', 'usrid')
    assert not iftp.ftpconnect
    assert not iftp.remotebase
    assert utils.has_log_level('WARNING')


def test_ftp_interface_disconnect_ftp(iftp_conn, iftp, utils):
    iftp_conn.disconnect_ftp()
    iftp_conn.ftp.quit.assert_called()
    assert os.getcwd() == iftp_conn.curdir
    assert not iftp_conn.ftpconnect
    assert not utils.has_log_level('WARNING')

    iftp.disconnect_ftp()
    assert utils.has_log_level('WARNING')


def test_ftp_interface_store_file_ftp_fail(iftp_conn, utils):
    with patch('builtins.open', new_callable=mock_open()) as mock_file:
        # ftp does not exist
        iftp_conn.ftp = None
        assert not iftp_conn.store_file_ftp('./configs', 'template_config.ini')


def test_ftp_interface_store_file_ftp(iftp_conn, utils):
    with patch('builtins.open', new_callable=mock_open()) as mock_file:
        # nominal case
        assert iftp_conn.store_file_ftp('./configs', 'template_config.ini')
        iftp_conn.ftp.storbinary.assert_called_once()
        assert not utils.has_log_level('WARNING')
        mock_file.assert_called_once_with(os.path.abspath('./configs/template_config.ini'), 'rb')
        mock_file.return_value.close.assert_called_once()

        # FTP error
        iftp_conn.ftp.storbinary.side_effect = EOFError('mock error')
        assert not iftp_conn.store_file_ftp('./configs', 'template_config.ini')
        assert utils.has_log_level('WARNING')
        utils.clear_log()

        # invalid file
        mock_file.reset_mock()
        assert not iftp_conn.store_file_ftp('./configs', 'invalid.file')
        assert utils.has_log_level('WARNING')
        utils.clear_log()
        mock_file.assert_not_called()

        # invalid FTP

        # FTP is disconnected
        iftp_conn.disconnect_ftp()
        assert not iftp_conn.store_file_ftp('./configs', 'template_config.ini')
        assert utils.has_log_level('WARNING')


def test_ftp_interface_get_file_ftp_fail(iftp_conn, utils):
    with patch('builtins.open', new_callable=mock_open()) as mock_file, \
            patch('lib.ftp_interface.os.remove') as mock_remove:
        # ftp does not exist
        iftp_conn.ftp = None
        assert not iftp_conn.get_file_ftp('/file/to/get', 'local/file/path')


def test_ftp_interface_get_file_ftp(iftp_conn, utils):
    with patch('builtins.open', new_callable=mock_open()) as mock_file, \
            patch('lib.ftp_interface.os.remove') as mock_remove:
        # nominal case
        assert iftp_conn.get_file_ftp('/file/to/get', 'local/file/path')
        iftp_conn.ftp.retrbinary.assert_called_once()
        assert not utils.has_log_level('WARNING')
        mock_file.assert_called_once_with('local/file/path/get', 'wb')
        mock_file.return_value.close.assert_called_once()
        mock_remove.assert_not_called()

        # FTP error
        mock_file.reset_mock()
        iftp_conn.ftp.retrbinary.side_effect = EOFError('mock error')
        assert not iftp_conn.get_file_ftp('/file/to/get')
        assert utils.has_log_level('WARNING')
        utils.clear_log()
        mock_file.assert_called_once_with('get', 'wb')
        mock_file.return_value.close.assert_called_once()
        mock_remove.assert_called_once_with('get')

        # invalid FTP

        # FTP is disconnected
        mock_file.reset_mock()
        iftp_conn.disconnect_ftp()
        assert not iftp_conn.get_file_ftp('/file/to/get')
        assert utils.has_log_level('WARNING')
        mock_file.assert_not_called()


def test_ftp_interface_upload_ftp_exception(iftp):
    with patch('lib.ftp_interface.ftplib.FTP', spec=ftplib.FTP) as mock_ftp:
        # cwd triggers exception
        mock_ftp.return_value.cwd.side_effect = [None, OSError('mock error'), OSError('mock error'), None, None, None]
        assert not iftp.upload_ftp('./configs', 'localhost', '/remote/path')


def test_ftp_interface_upload_ftp(iftp):
    with patch('lib.ftp_interface.ftplib.FTP', spec=ftplib.FTP) as mock_ftp:
        # nominal case, single file
        assert iftp.upload_ftp('./configs', 'localhost', '/remote/path', 'template_config.ini')
        # directory
        assert iftp.upload_ftp('./configs', 'localhost', '/remote/path')
        # invalid file
        assert not iftp.upload_ftp('./configs', 'localhost', '/remote/path', 'filename.ext')
        # mkdir error
        mock_ftp.return_value.mkd.side_effect = OSError('mock error')
        assert iftp.upload_ftp('./configs', 'localhost', '/remote/path')
        # chdir error
        assert not iftp.upload_ftp('./invalid', 'localhost', '/remote/path', 'template_config.ini')
        # cwd error
        mock_ftp.return_value.cwd.side_effect = [OSError('mock error'), None]
        assert not iftp.upload_ftp('./configs', 'localhost', '/remote/path', 'template_config.ini')
        # connection fail
        mock_ftp.side_effect = OSError('mock error')
        assert not iftp.upload_ftp('./configs', 'localhost', '/remote/path', 'template_config.ini')


def test_ftp_interface_download_ftp_exception(iftp):
    with patch('lib.ftp_interface.ftplib.FTP', spec=ftplib.FTP) as mock_ftp, \
            patch('lib.ftp_interface.os.chdir') as mock_chdir:
        # os.chdir causes exception
        mock_chdir.side_effect = [OSError('mock error'), None]
        assert not iftp.download_ftp('/remote/path', 'localhost', './local/path', 'filename.ext')


def test_ftp_interface_download_ftp_folder(iftp):
    with patch('lib.ftp_interface.ftplib.FTP', spec=ftplib.FTP) as mock_ftp:
        assert iftp.download_ftp('/remote/path', 'localhost', './local/path', 'filename.ext')

        # directory (mock FTP operation to call its callback directly)
        def mock_retrlines(cmd, callback=None):
            line = 'drwxrwxr-x  ... /remote/path'
            callback(line)

        mock_ftp.return_value.retrlines.side_effect = mock_retrlines
        assert not iftp.download_ftp('/remote/path', 'localhost', './local/path')


def test_ftp_interface_download_ftp(iftp):
    with patch('lib.ftp_interface.ftplib.FTP', spec=ftplib.FTP) as mock_ftp:
        # nominal case, single file
        assert iftp.download_ftp('/remote/path', 'localhost', './local/path', 'filename.ext')
        # directory (mock FTP operation to call its callback directly)
        files = ['-rwxr-x--- ... file2']
        mock_ftp.return_value.retrlines.side_effect = \
            lambda *args: [mock_ftp.return_value.retrlines.call_args.args[1](file) for file in files]
        assert iftp.download_ftp('/remote/path', 'localhost', './local/path')
        # mkdir error
        # with patch('lib.ftp_interface.os.mkdir', side_effect=OSError('mock error')):
        #     assert not iftp.download_ftp('/remote/path', 'localhost', './local/path')
        # cwd error
        mock_ftp.return_value.cwd.side_effect = [OSError('mock error'), None]
        assert not iftp.download_ftp('/remote/path', 'localhost', './local/path', 'filename.ext')
        # chdir error
        # connection fail
        mock_ftp.side_effect = OSError('mock error')
        assert not iftp.download_ftp('/remote/path', 'localhost', './local/path', 'filename.ext')

        # cleanup
        shutil.rmtree('./local/path')


def test_ftp_interface_upload_ftputil(iftp):
    with patch('lib.ftp_interface.ftplib.FTP', spec=ftplib.FTP), \
         patch('lib.ftp_interface.ftputil.FTPHost', spec=FTPHost) as mock_ftp:
        assert iftp.connect_ftp('ipaddr', 'usrid')
        # nominal case
        mock_ftp.return_value.__enter__.return_value.path.exists.return_value = False
        assert iftp.upload_ftputil('localhost', './configs', './remote/path')
        # error
        assert not iftp.upload_ftputil('localhost', './invalid', './remote/path')


def test_ftp_interface_download_ftputil(iftp):
    with patch('lib.ftp_interface.ftplib.FTP', spec=ftplib.FTP), \
         patch('lib.ftp_interface.ftputil.FTPHost', spec=FTPHost) as mock_ftp:
        assert iftp.connect_ftp('ipaddr', 'usrid')
        # nominal case
        mock_ftp.return_value.__enter__.return_value.walk.return_value = [('/remote/path', ('dir1',), ('file2',))]
        assert iftp.download_ftputil('localhost', '/remote/path', './local/path')
        # error
        mock_ftp.return_value.__enter__.return_value.download.side_effect = OSError('mock error')
        assert not iftp.download_ftputil('localhost', '/remote/path', './local/path')

        # cleanup
        shutil.rmtree('./local/path')
