"""
@namespace lib.ftp_interface
FTP interface for CTF
"""

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


import os
import ftplib
import ftputil

from lib.ctf_utility import expand_path
from lib.logger import logger as log


class FtpInterface:
    """
    The FtpInterface class provides functionality to connect/disconnect to remote FTP server,
    upload/download files, create folder on server.
    @note - Two parallel FTP implementations are provided: ftputil for use via SSH, and ftplib for SP0
    """

    def __init__(self):
        """
         Constructor for FtpInterface class. Set default values for FtpInterface attributes,
         such as ipaddr, ftp_timeout, etc.
        """
        self.uploadlevel = 0
        self.ftp = None
        self.curdir = ""
        self.ipaddr = ""
        self.ftpconnect = False
        self.ftp_timeout = 5
        self.remotebase = None

    def store_file_ftp(self, path, file):
        """
        Transfer file to FTP server using the FTP command STOR. The file transfer is in binary mode.
        @param path: the path of the transfer file on local computer.
        @param file: the name of the transfer file on local computer.
        @return bool: True if the file is transferred successfully, False otherwise.
        """
        status = True

        if self.ftpconnect:
            path = expand_path(path)
            filetoupload = os.path.abspath(os.path.join(path, file))
            log.debug("Uploading {}...".format(filetoupload))
            if os.path.isfile(filetoupload):
                fileobject = open(filetoupload, 'rb')
                if self.ftp:
                    try:
                        self.ftp.storbinary('STOR %s' % file, fileobject)
                    except ftplib.all_errors:
                        log.warning("FTP put file failed {}".format(file))
                        status = False
                else:
                    log.warning("FTP connection invalid for: {} ".format(self.ipaddr))
                    status = False
                fileobject.close()
            else:
                log.warning("File does not exist {}".format(filetoupload))
                status = False
        else:
            log.warning("FTP not Connected")
            status = False

        return status

    def get_file_ftp(self, remote_file, local_path=None):
        """
        Download a file from the FTP server to the local computer.
        @param remote_file: the path/name of the file on FTP server.
        @param local_path: the path to store the transferred file on local computer.
        @return bool: True if the file is downloaded successfully, False otherwise.
        """
        status = True
        remote_path, file = os.path.split(remote_file)
        log.debug("fileToDownload {}...".format(file))
        if local_path:
            local_file = os.path.join(expand_path(local_path), file)
        else:
            local_file = file
        if self.ftpconnect:
            fileobject = open(local_file, 'wb')
            if self.ftp:
                def callback(data):
                    fileobject.write(data)

                try:
                    self.ftp.retrbinary('RETR %s' % remote_file, callback)
                except ftplib.all_errors:
                    log.warning("FTP get file failed {} @ {} ".format(remote_file, remote_path))
                    status = False
            else:
                log.warning("FTP connection invalid for: {}".format(self.ipaddr))
                status = False

            fileobject.close()

            if not status:
                os.remove(file)
        else:
            log.warning("FTP not connected.")
            status = False

        return status

    def upload_ftp(self, localpath, ipaddr=None, remotepath=None, file=None, usr_id=None):
        """
        Upload a file or files from the local computer to the FTP server.
        @param localpath: the path of the uploaded file/files on local computer.
        @param ipaddr: the IP address of FTP server. If it is None, use the previous FTP connection,
                        otherwise re-connect FTP server using ipaddr and usr_id.
        @param remotepath: the path to store the uploaded file/files on the FTP server.
        @param file: the file to be uploaded on local computer. If the file is None,
                     all files in localpath will be uploaded.
        @param usr_id: the user id to connect to the FTP server.
        @return bool: True if upload successfully, False otherwise.
        """
        status = True
        if ipaddr:
            self.ipaddr = ipaddr
            status = self.connect_ftp(ipaddr, usr_id)
            if not status:
                log.warning("FTP not connected.")
                return status
        if remotepath:
            try:
                self.ftp.cwd(remotepath)
            except ftplib.all_errors:
                log.warning("FTP cwd Failed for {}@{}".format(remotepath, self.ipaddr))
                status = False
        try:
            localpath = expand_path(localpath)
            os.chdir(localpath)
        except OSError:
            log.warning("Cwd Failed for {}".format(localpath))
            status = False

        if status:
            self.uploadlevel += 1
            if file:
                files = [file]
            else:
                files = os.listdir(".")

            for localfile in files:
                log.debug("Upload file  {}...".format(os.path.abspath(os.path.join(".", localfile))))
                if os.path.isfile(localfile):
                    status = self.store_file_ftp(".", localfile)
                    if status is False:
                        break
                elif os.path.isdir(localfile):
                    try:
                        self.ftp.cwd(localfile)
                    except ftplib.all_errors:
                        try:
                            log.debug("Creating remote directory {}...".format(localfile))
                            self.ftp.mkd(localfile)
                            self.ftp.cwd(localfile)
                        except ftplib.all_errors:
                            log.error("Creating remote directory failed {}...".format(localfile))
                            status = False
                            break
                    status = self.upload_ftp(localfile)
                else:
                    status = False

            if self.uploadlevel != 1:
                self.ftp.cwd('..')
                os.chdir('..')
            self.uploadlevel -= 1
        if self.uploadlevel == 0:
            log.debug("Upload complete.")
            self.disconnect_ftp()
        return status

    def download_ftp(self, remotepath, ipaddr=None, localpath=None, file=None, usr_id=None):
        """
        Download a file or files from the FTP server to the local computer.
        @param remotepath: the path to the download file/files on the FTP server.
        @param ipaddr: the IP address of FTP server. If it is None, use the previous FTP connection,
                        otherwise re-connect FTP server using ipaddr and usr_id.
        @param localpath: the path to store the downloaded file/files on local computer.
        @param file: the file to be downloaded from the FTP server. If the file is None,
                     all files in remotepath will be downloaded.
        @param usr_id: the user id to connect to the FTP server.
        @return bool: True if download successfully, False otherwise.
        """
        status = True
        files = dict()
        if ipaddr:
            self.ipaddr = ipaddr
            status = self.connect_ftp(ipaddr, usr_id)
            if not status:
                log.warning("FTP not connected.")
                return status
        if localpath:
            localpath = expand_path(localpath)
            if not os.path.isdir(localpath):
                log.debug("Creating local directory {}...".format(localpath))
                os.makedirs(localpath)
            try:
                os.chdir(localpath)
            except OSError:
                log.warning("Cwd Failed for {}".format(localpath))
                status = False

        if status:
            self.uploadlevel += 1
            try:
                self.ftp.cwd(remotepath)
            except ftplib.all_errors:
                log.warning("FTP invalid directory {}".format(remotepath))
                status = False

            if status:
                if file:
                    files[file] = "-rwxrwxrwx"
                else:
                    def getfiles(data):
                        parsedata = data.split(" ")
                        files[parsedata[len(parsedata) - 1]] = parsedata[0]

                    self.ftp.retrlines('LIST', getfiles)

                for remotefile in files:
                    log.debug("Download file  {}...".format(remotefile))
                    if "d" not in files[remotefile]:
                        status = self.get_file_ftp(remotefile, os.getcwd())
                        if not status:
                            break
                    else:
                        try:
                            os.chdir(remotefile)
                        except OSError:
                            try:
                                log.debug("Creating local directory {}...".format(remotefile))
                                os.mkdir(remotefile)
                                os.chdir(remotefile)
                            except OSError:
                                log.error("Creating local directory failed {}...".format(remotefile))
                                status = False
                                break

                        status = self.download_ftp(remotefile)

            if self.uploadlevel != 1:
                self.ftp.cwd('..')
                os.chdir('..')
            self.uploadlevel -= 1
        if self.uploadlevel == 0:
            log.debug("Download complete.")
            self.disconnect_ftp()
        return status

    def connect_ftp(self, ipaddr, usrid):
        """
        Connect to FTP server, and set the FtpInterface attributes.
        @param ipaddr: the IP address of FTP server.
        @param usrid: the user id to connect to the FTP server.
        @return bool: True if successfully connect to FTP server, False otherwise.
        """
        status = True
        self.uploadlevel = 0
        self.curdir = os.getcwd()

        try:
            self.ftp = ftplib.FTP(ipaddr, usrid, "", timeout=self.ftp_timeout)
        except ftplib.all_errors:
            status = False
        if status:
            try:
                self.ftp.login()
                self.remotebase = self.ftp.pwd()
            except ftplib.all_errors:
                status = False

        if not status:
            log.warning("FTP connection failed for {}".format(ipaddr))
        else:
            self.ftpconnect = True

        return status

    def disconnect_ftp(self):
        """
        Disconnect to FTP server, and reset the FtpInterface attributes.
        @return None
        """
        if self.ftpconnect:
            os.chdir(self.curdir)
            self.ftp.cwd(self.remotebase)
            self.ftp.quit()
            self.ftpconnect = False
        else:
            log.warning("FTP not connected.")

    def upload_ftputil(self, host, local_path, remote_path, usrid='anonymous'):
        """
        FTP upload utility: upload a whole folder content from the local computer to the FTP host.
        @param host: FTP server host/IP.
        @param local_path: the local computer path.
        @param remote_path: the FTP server path to store the uploaded files.
        @param usrid: the user id to connect to the FTP server. The default user is anonymous'
        @return bool: True if upload successfully, False otherwise.
        """
        self.ipaddr = host
        try:
            local_path = expand_path(local_path)
            os.chdir(local_path)
            # noinspection PyDeprecation
            with ftputil.FTPHost(host, usrid, '') as ftp:
                for path, dirs, files in os.walk('.'):
                    remote_dir = ftp.path.join(remote_path, path)
                    if not ftp.path.exists(remote_dir):
                        log.debug("Creating remote directory {}...".format(remote_dir))
                        ftp.makedirs(remote_dir)
                    for file in files:
                        log.debug("Uploading {} in {}...".format(file, dirs))
                        local_file = os.path.join(path, file)
                        remote_file = ftp.path.join(remote_dir, file)
                        ftp.upload(local_file, remote_file)
                log.debug("FTP upload complete.")
        except ftplib.all_errors as exception:
            log.warning("FTP upload failed: {}".format(exception))
            os.chdir(self.curdir)
            return False
        else:
            os.chdir(self.curdir)
            return True

    def download_ftputil(self, host, remote_path, local_path, usrid='anonymous'):
        """
        FTP download utility: download a whole folder content from the FTP host to the local computer.
        @param host: FTP server host/IP.
        @param remote_path: the FTP server path.
        @param local_path: the local computer path to store downloaded files.
        @param usrid: the user id to connect to the FTP server. The default user is anonymous'.
        @return bool: True if download successfully, False otherwise.
        """
        self.ipaddr = host
        try:
            local_path = expand_path(local_path)
            # noinspection PyDeprecation
            with ftputil.FTPHost(host, usrid, '') as ftp:
                for path, dirs, files in ftp.walk(remote_path):
                    rel_path = os.path.relpath(path, remote_path)
                    local_dir = os.path.join(local_path, rel_path)
                    if not os.path.exists(local_dir):
                        log.debug("Creating local directory {}...".format(local_dir))
                        os.makedirs(local_dir)
                    for file in files:
                        log.debug("Downloading {} to {}...".format(file, dirs))
                        remote_file = ftp.path.join(path, file)
                        local_file = os.path.join(local_dir, file)
                        ftp.download(remote_file, local_file)
                log.debug("FTP download complete.")
        except ftplib.all_errors as exception:
            log.warning("FTP download failed: {}".format(exception))
            return False
        else:
            return True
