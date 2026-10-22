"""
This component installs TRNLizard from the server:

Args:
    Install (bool): Script variable Install
        Access: item
        Required: False
    TargetDirectory (object): Script variable Installer
        Access: item
        Required: False

Returns:
"""
version='2.1.2'
import os
import System
import sys
import zipfile
import shutil
from Grasshopper.Folders import UserObjectFolders
from shutil import copyfile
def installTRNLizard(update):
    #url = r"c:\Entwicklung\trnPLOT\dist\trnPLOT.zip"
    url = r"https://backend101.trnsys.de/wp-content/uploads/2020/10/trnPLOT.zip"
    #targetDirectory = UserObjectFolders[0]
    targetDirectory = TargetDirectory
    if os.path.isdir(targetDirectory) is True:
        shutil.rmtree(targetDirectory)
        os.mkdir(targetDirectory)
    if os.path.isdir(targetDirectory) is False:
        os.mkdir(targetDirectory)
    # download the zip file
    print "Downloading the Installer to {}".format(targetDirectory)
    zipFile = os.path.join(targetDirectory, os.path.basename(url))
    #shutil.copyfile(url,zipFile)
    try:
        client = System.Net.WebClient()
        client.DownloadFile(url, zipFile)
    except Exception, e:
        msg = `e` + "\nDownload failed! Try to download and unzip the file manually form:\n" + url
        raise Exception(msg)
    #unzip the file
    """
    with zipfile.ZipFile(zipFile) as zf:
        for f in zf.namelist():
            if f.endswith('/'):
                try: os.makedirs(f)
                except: pass
            else:
                zf.extract(f, targetDirectory)
    zf.close()
    """
    with open(zipFile, 'rb') as fileobj:
        z = zipfile.ZipFile(fileobj)
        z.extractall(targetDirectory)
        z.close()
    print 'Extracted trnPLOT to {}.'.format(targetDirectory)
    os.remove(zipFile)
if Install:
   installTRNLizard(Install)
