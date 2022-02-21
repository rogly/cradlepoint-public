import zipfile
import os
import shutil
import sys

version = sys.argv[1]

shutil.copytree('source/s3', version + '/s3')

shutil.copytree('source/cloudformation', version + '/cloudformation')
os.mkdir(version + "/lambda")

zf = zipfile.ZipFile(version + "/lambda/deploy_router.zip", "w")

for root, dirs, files in os.walk("source/lambda/deploy_router"):
    for file in files:
        fullpath = os.path.join(root, file)
        newpath = fullpath.removeprefix('source/lambda/deploy_router')
        zf.write(fullpath, newpath)
        print (newpath)

zf = zipfile.ZipFile(version + "/lambda/api_handler.zip", "w")

for root, dirs, files in os.walk("source/lambda/api_handler"):
    for file in files:
        fullpath = os.path.join(root, file)
        newpath = fullpath.removeprefix('source/lambda/api_handler')
        zf.write(fullpath, newpath)
        print (newpath)

