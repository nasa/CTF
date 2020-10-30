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


import os
import ftputil
from ftplib import FTP
from lib.Global import expand_path
from lib.logger import logger as log

#ftputil does not work for the SP0 so the ftplib components FTP is also made available


class ftp_interface(object):
    def __init__(self):
        self.uploadLevel = 0
        self.ftp = None
        self.curDir = ""
        self.ip = ""
        self.ftpConnect = False
        self.ftp_timeout = 5


    def stor_file_FTP(self, path, file):

        status = True
        if self.ftpConnect:
            fileToUpload = os.path.abspath(os.path.join(path, file))
            log.debug("Uploading {}...".format(fileToUpload))
            if os.path.isfile(fileToUpload):
                fh = open(fileToUpload, 'rb')
                if self.ftp:
                    try:
                        self.ftp.storbinary('STOR %s' % file, fh)
                    except:
                        log.warn("FTP put file failed {}".format(file))
                        status = False
                else:
                    log.warn("FTP connection invalid for: %s."%self.ip)
                    status = False
                fh.close()
            else:
                log.warn("File does not exist %s"%fileToUpload)
                status = False
        else:
            log.warn("FTP not Connected")
        return status

    def get_file_FTP(self, remote_file, local_path=None):

        status = True
        remote_path,file = os.path.split(remote_file)
        log.debug("fileToDownload {}...".format(file))
        if local_path:
            local_file = os.path.join(local_path,file)
        else:
            local_file = file
        if self.ftpConnect:
            fh = open(local_file, 'wb')
            if self.ftp:
                def callback(data):
                    fh.write(data)
                try:
                    self.ftp.retrbinary('RETR %s' % remote_file, callback)
                except:
                    log.warn("FTP get file failed {} ".format(remote_file))
                    status = False
            else:
                log.warn("FTP connection invalid for: %s."%self.ip)
                status = False
            fh.close()
            if status == False:
                os.remove(file)
        else:
            log.warn("FTP not connected.")
        return status


    def upload_FTP(self, localpath, ip=None, remotepath=None, file=None, id=None):
        status = True
        if (ip):
            self.ip = ip
            status = self.connect_FTP(ip, id)
            if status == False:
                log.warn("FTP not connected.")
                return status
        if remotepath:
            try:
                self.ftp.cwd(remotepath)
            except:
                log.warn("FTP cwd Failed for %s@%s"%(remotepath,self.ip))
                status = False
        try:
            os.chdir(localpath)
        except:
            log.warn("Cwd Failed for %s"%(localpath))
            status = False

        if status:
            self.uploadLevel +=1
            if (file):
               files = [file]
            else:
                files = os.listdir(".")

            for f in files:
                log.debug("Upload file  {}...".format(os.path.abspath(os.path.join(".",f))))
                if os.path.isfile(f):
                    status = self.stor_file_FTP(".", f)
                    if (status == False):
                        break
                elif os.path.isdir(f):
                    try:
                        log.debug("Creating remote directory {}...".format(f))
                        #The mkdir will fail if the directory already exist
                        self.ftp.mkd(f)
                    except:
                        log.debug("Creating remote directory failed {}...".format(f))
                        pass
                    self.ftp.cwd(f)
                    status = self.upload_FTP(f)
                else:
                    status = False
            if self.uploadLevel != 1:
                self.ftp.cwd('..')
                os.chdir('..')
            self.uploadLevel -= 1
        if self.uploadLevel == 0:
            log.debug("Upload complete.")
            self.disconnect_FTP()
        return status


    def download_FTP(self, remotepath, ip=None, localpath=None, file=None, id=None):
        status = True
        files = dict()
        if (ip):
            self.ip = ip
            status = self.connect_FTP(ip, id)
            if status == False:
                log.warn("FTP not connected.")
                return status
        if localpath:
            if not os.path.isdir(localpath):
                log.debug("Creating local directory {}...".format(localpath))
                os.mkdir(localpath)
            try:
                os.chdir(localpath)
            except:
                log.warn("Cwd Failed for %s"%(localpath))
                status = False

        if status:
            self.uploadLevel +=1
            try:
                self.ftp.cwd(remotepath)
            except:
                log.warn("FTP invalid directory {}".format(remotepath))
                status = False

            if status:
                if (file):
                   files[file] = "-rwxrwxrwx"
                else:
                    def getfiles(data):
                        parsedata = data.split(" ")
                        files[parsedata[len(parsedata)-1]] = parsedata[0]

                    self.ftp.retrlines('LIST',getfiles)

                for f in files.keys():
                    log.debug("Download file  {}...".format(f))
                    if "d" not in files[f]:
                        status = self.get_file_FTP(f)
                        if (status == False):
                            break
                    else:
                        try:
                            log.debug("Creating local directory {}...".format(f))
                            os.mkdir(f)
                        except:
                            log.debug("Creating directory failed {}...".format(f))
                            pass
                        os.chdir(f)
                        status = self.download_FTP(f)

            if self.uploadLevel != 1:
                self.ftp.cwd('..')
                os.chdir('..')
            self.uploadLevel -= 1
        if self.uploadLevel == 0:
            log.debug("Download complete.")
            self.disconnect_FTP()
        return status

    def connect_FTP(self, ip, id):
        status = True
        self.uploadLevel = 0
        self.curDir = os.getcwd()

        try:
            self.ftp = FTP(ip, id, "", timeout=self.ftp_timeout)
        except:
            status = False
        if status:
            try:
                self.ftp.login()
                self.remoteBase = self.ftp.pwd()
            except:
                status = False

        if status == False:
            log.warn("FTP connection failed for {}".format(ip))
        else:
            self.ftpConnect = True

        return status

    def disconnect_FTP(self):
            if self.ftpConnect:
                os.chdir(self.curDir)
                self.ftp.cwd(self.remoteBase)
                self.ftp.quit()
                self.ftpConnect = False
            else:
                log.warn("FTP not connected.")


    def upload_ftputil(self, host, local_path, remote_path, id='anonymous'):
        self.ip = host
        try:
            os.chdir(expand_path(local_path))
            # noinspection PyDeprecation
            with ftputil.FTPHost(host, id, '') as ftp:
                ftp.login()
                for path, dirs, files in os.walk('.'):
                    remote_dir = ftp.path.join(remote_path, path)
                    if not ftp.path.exists(remote_dir):
                        log.debug("Creating remote directory {}...".format(remote_dir))
                        ftp.makedirs(remote_dir)
                    for file in files:
                        log.debug("Uploading {}...".format(file))
                        local_file = os.path.join(path, file)
                        remote_file = ftp.path.join(remote_dir, file)
                        ftp.upload(local_file, remote_file)
                log.debug("FTP upload complete.")
        except Exception as e:
            log.warn("FTP upload failed: {}".format(e))
            return False
        else:
            return True

    def download_ftputil(self, host, remote_path, local_path, id='anonymous'):
        self.ip = host
        try:
            local_path = expand_path(local_path)
            # noinspection PyDeprecation
            with ftputil.FTPHost(host, id, '') as ftp:
                for path, dirs, files in ftp.walk(remote_path):
                    rel_path = os.path.relpath(path, remote_path)
                    local_dir = os.path.join(local_path, rel_path)
                    if not ftp.path.exists(local_dir):
                        log.debug("Creating local directory {}...".format(local_dir))
                        os.makedirs(local_dir)
                    for file in files:
                        log.debug("Downloading {}...".format(file))
                        remote_file = ftp.path.join(path, file)
                        local_file = os.path.join(local_dir, file)
                        ftp.download(remote_file, local_file)
                log.debug("FTP download complete.")
        except Exception as e:
            log.warn("FTP download failed: {}".format(e))
            return False
        else:
            return True