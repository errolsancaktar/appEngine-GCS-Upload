import hashlib
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import logging
import gcs
import re

from time import sleep
## Logging ##
logger = logging.getLogger("appLog")
logger.setLevel("DEBUG")

app = Flask(__name__)

## Globals ##
app.config['MAX_CONTENT_LENGTH'] = 784 * 1024 * 1024  # 784 MB
app.config['UPLOAD_FOLDER'] = "uploads/"
app.config['GCS_UPLOAD'] = True
app.config['STORAGE_PROJECT'] = 'theresastrecker'
app.config['STORAGE_BUCKET'] = 'theresa-photo-storage'
cloudStorage = gcs.GCS(project=app.config['STORAGE_PROJECT'],
                       bucket=app.config['STORAGE_BUCKET'])

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif', 'webp', 'tif',
                      'tiff', 'raw', 'bmp', 'pdf', 'mpeg', 'mpg', 'ogg', 'mp4', 'avi', 'mov'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def upload():
    return render_template('tsCOL/index.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('tsCOL/index.html'), 404


@app.route('/', methods=['POST'])
def upload_file():
    files = request.files.getlist('file')
    formInfo = request.values
    logger.debug(f'File Object: {files}')
    uploadCount = len(request.files.getlist('file'))
    for file in files:
        logger.info(f'Filename: {file.filename}')
        if file.filename and allowed_file(file.filename):
            logger.debug(secure_filename(file.filename))
            longFileName = prepareFileName(secure_filename(file.filename))
            filename = longFileName.split(app.config['UPLOAD_FOLDER'], 1)[1]
            logger.debug(f"filename: {filename}")
            if app.config['GCS_UPLOAD']:
                fileHash = hashlib.md5(file.read()).hexdigest()
                file.seek(0)
                if not cloudStorage.fileExists(filename):
                    logger.debug("Uploading File")
                    if cloudStorage.uploadFile(
                            file, f"{app.config['UPLOAD_FOLDER']}{filename}", formInfo['name'], formInfo['email']):
                        return render_template(
                            'tsCOL/thanks.html', fileCount=uploadCount)
                    else:
                        return "There was an Error Uploading your Images"
                else:
                    logger.warning("Image Exists in GCS Bucket")
        elif not file.filename:
            return 'No file in the request', 400
        elif file and not allowed_file(file.filename):
            return 'This File type is not allowed', 400

    return render_template('tsCOL/thanks.html', fileCount=uploadCount)


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    return 'File is too large', 413


def addNumbertoFile(filename):
    logger.debug(f'Checking if need to add Number to {filename}')
    # Pull off Extension
    # Return filename parts  after stripping the delimiter whitespace
    filename = filename.lower()
    fileObj = list(filter(None, re.split(r'\.([a-zA-Z]{3,4}$)', filename)))
    baseFile = fileObj[0]
    logger.debug(baseFile)
    regex = re.compile(r'-\d*$')
    match = regex.search(baseFile)
    if match:  # If already had a number at the end convert it to an int and add 1
        iterator = int(re.split("-", baseFile)[-1])
        file = re.split("-", baseFile)[0]
        iterator += 1
        logger.debug(f'{file}-{iterator}.{fileObj[-1]}')
        return f'{file}-{iterator}.{fileObj[-1]}'
    # # Split file name for renaming
    # baseFile = f'{filename.rsplit(".", 1)[0].lower()}'
    # fileExt = f'.{filename.rsplit(".", 1)[1].lower()}'
    # if f'-{iter}' in baseFile:
    #     baseFile = f'{baseFile.rsplit("-", 1)[0]}'
    #     iter = iter + 1
    return f'{baseFile}-1.{fileObj[-1]}'  # return filename with number at end


def prepareFileName(fileExists):
    # Join Upload Folder to filename for testing
    logger.debug(f'Preparing File: {fileExists}')
    if not app.config['UPLOAD_FOLDER'] in fileExists:
        fullFile = os.path.join(app.config['UPLOAD_FOLDER'], fileExists)
    else:
        fullFile = fileExists
    if app.config['GCS_UPLOAD']:
        # Check if filname exists in bucket
        logger.debug(f'preparing: {fullFile}')
        if not cloudStorage.fileExists(fullFile):
            logger.debug(f'File: {fullFile} is new')
            return fullFile.lower()
    logger.debug("looping prepareFileName")
    return prepareFileName(addNumbertoFile(fullFile))


@app.route("/images/<string:blob_name>")
def view(blob_name):
    values = cloudStorage.getImage(f'uploads/{blob_name}')
    return render_template('tsCol/images.html', content_type=values[1],  image=values[0], imageName=blob_name, metadata=values[2])


if __name__ == "__main__":
    # Used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    app.run(host="localhost", port=8080, debug=True)
    logger.setLevel("DEBUG")
    addNumbertoFile("errolphoto.png")
    addNumbertoFile("errolphoto-1.png")
