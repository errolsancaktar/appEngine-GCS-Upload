from gcloud import storage
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
import imagehash
import os
import json
import io
import base64
DEBUG = True
KEYFILE = os.environ['SA_KEY']
bucket = 'theresa-photo-storage'
project = 'theresastrecker'

if "BACKUP_CLIENT_ID" in os.environ:
    credentials_dict = {
        'type': 'service_account',
        'client_id': os.environ['BACKUP_CLIENT_ID'],
        'client_email': os.environ['BACKUP_CLIENT_EMAIL'],
        'private_key_id': os.environ['BACKUP_PRIVATE_KEY_ID'],
        'private_key': os.environ['BACKUP_PRIVATE_KEY'],
    }
elif os.path.exists(KEYFILE):
    with open(KEYFILE) as jsonFile:
        credentials_dict = json.load(jsonFile)
else:
    print("do something")
    exit(199)
#   print(credentials_dict)
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    credentials_dict
)
client = storage.Client(credentials=credentials,
                        project=project)
storageBucket = client.get_bucket(bucket)


def uploadFile(file, filename):
    if DEBUG:
        print(f'Starting Upload of: {filename}')
    blob = storageBucket.blob(filename)
    if DEBUG:
        print(blob)
    try:
        if DEBUG:
            print(file)
        # blob.upload_from_filename(file)
        blob.upload_from_file(file)
    except Exception as e:
        print(e)
        print("Upload Failed")


def fileExists(filename):
    # print(filename)
    files = storageBucket.list_blobs()
    for file in files:
        if filename in file.name:
            return True
    else:
        # print("False")
        return False


def listFiles(prefix=None):
    return storageBucket.list_blobs(prefix=prefix)
    # for file in files:
    #     print("")
    # return files


def getFileList(prefix=None):
    # files = storageBucket.list_blobs(prefix='uploads/')
    fileList = []
    files = listFiles(prefix=prefix)
    for file in files:
        fileList.append(file.name)
    return fileList


def dupExists(inputFile, inputHash=None, prefix='uploads'):
    for i in getFileList(prefix):
        with Image.open(io.BytesIO(storageBucket.get_blob(
                i).download_as_string())) as img:
            # print(type(imagehash.average_hash(img)))
            # print(inputHash - imagehash.average_hash(img))
            if (inputHash - imagehash.average_hash(img) < 5):
                return True
            else:
                return False


def getImage(image):
    blob = storageBucket.get_blob(image)
    content = blob.download_as_string()
    imageData = base64.b64encode(content).decode("utf-8")
    print(blob.content_type)
    print(type(content))
    print(dir(content))
    return [blob]
# print(gcs.fileExists("uploads/dumpsterfire.jpg"))
# # print(fileExists("testFolder/dumpsterfsdfire.jpg"))
# with Image.open('716142554.341542.jpeg') as image:
#     curHash = imagehash.average_hash(image)
# print(dupExists('716142554.341542.jpeg', curHash))
