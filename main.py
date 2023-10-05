import json
from flask import Flask, render_template, request, jsonify, Response, redirect
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import logging
import google.cloud.logging
from google.cloud.logging_v2.handlers import CloudLoggingHandler
import gcs
import re

LOCAL_DEV = False


app = Flask(__name__)
auth = HTTPBasicAuth()


## Globals ##

app.config['MAX_CONTENT_LENGTH'] = 784 * 1024 * 1024  # 784 MB
app.config['UPLOAD_FOLDER'] = "uploads/"
app.config['GCS_UPLOAD'] = True
app.config['UPLOAD_METHOD'] = "GCS"
app.config['STORAGE_PROJECT'] = 'theresastrecker'
app.config['STORAGE_BUCKET'] = 'theresa-photo-storage'
cloudStorage = gcs.GCS(project=app.config['STORAGE_PROJECT'],
                       bucket=app.config['STORAGE_BUCKET'], prefix=app.config['UPLOAD_FOLDER'])

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif', 'webp', 'tif',
                      'tiff', 'raw', 'bmp', 'pdf', 'mpeg', 'mpg', 'ogg', 'mp4', 'avi', 'mov'}
PATH_BASE = os.path.dirname(os.path.abspath(__file__))
PATH_STATIC = os.path.join(PATH_BASE, "static")

users = {
    "kristin": cloudStorage.getSecret('projects/422051208073/secrets/user/versions/latest')
}


@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

## Routing ##


@app.route('/')
def upload():
    '''Returns main site page from template'''
    return render_template('tsCOL/index.html')


@app.route('/', methods=['POST'])
def upload_file():
    '''Legacy method to upload to gcs without signed urls
        this doesnt work well if the payload is going to be larger than 30MB
        due to appengine limitations

        Post Data required:
            multipart form with files as body

        Form Data:
            name
            email

        '''

    # Get all the Files
    files = request.files.getlist('file')

    # Get the Form Text
    formInfo = request.values

    logger.debug(f'File Object: {files}')
    uploadCount = len(request.files.getlist('file'))
    for file in files:
        logger.info(f'Filename: {file.filename}')
        if file.filename and allowed_file(file.filename):
            logger.debug(secure_filename(file.filename))
            lowerFileName = file.filename.lower()
            longFileName = prepareFileName(secure_filename(lowerFileName))
            filename = longFileName.split(app.config['UPLOAD_FOLDER'], 1)[1]
            logger.debug(f"filename: {filename}")
            content_type = file.content_type
            if app.config['UPLOAD_METHOD'] == "APPENGINE":
                file.seek(0)
                if not cloudStorage.fileExists(filename):
                    logger.debug("Uploading File")
                    try:
                        cloudStorage.uploadFile(
                            file, f"{app.config['UPLOAD_FOLDER']}{filename}", formInfo['name'], formInfo['email'])
                    except Exception as e:
                        logger.error(e)
                        return "There was an Error Uploading your Images"
                else:
                    logger.warning("Image Exists in GCS Bucket")
            if app.config['UPLOAD_METHOD'] == "GCS":
                file.seek(0)
                if not cloudStorage.fileExists(filename):
                    logger.debug("Uploading File")

                    try:

                        respo = cloudStorage.generate_upload_signed_url(
                            f"{app.config['UPLOAD_FOLDER']}{filename}", content_type)
                        logger.debug(respo)

                    except Exception as e:

                        logger.error(e)
                        return "There was an Error Uploading your Images"
                else:
                    logger.warning("Image Exists in GCS Bucket")
        elif not file.filename:
            return 'No file in the request', 400
        elif file and not allowed_file(file.filename):
            return 'This File type is not allowed', 400
    # return "true"
    return render_template('tsCOL/thanks.html', fileCount=uploadCount)


@app.route('/sup', methods=['POST'])
def supload():
    '''
    Takes post data with list of filenames to be uploaded to GCS
    Collects Filenames, Content-type and form data

    Sends all information to function to return signed urls for the upload

    returns list of dicts containing info needed for fetch on browser side
    '''
    responseList = []
    for req in request.form:
        item = json.loads(request.form.get(req))

        if request.method == 'POST':
            # Gather values from post data #
            content_type = item['type']
            filename = req
            logger.debug(f'FileName: {filename}')
            fileHeader = {
                'x-goog-meta-email': item['email'],
                'x-goog-meta-uploader': item['name']
            }
            logger.debug(fileHeader)
            logger.debug(
                f"{filename} -> {item['type']} -> {item['name']} -> {item['email']} -> {allowed_file(filename)}")
            # validation
            if app.config['UPLOAD_METHOD'] == "GCS":
                logger.debug("In Upload Phase")
                # Check filetype is ok
                if filename and allowed_file(filename):
                    logger.debug(
                        f'SecureFilename: {secure_filename(filename)}')
                    lowerFileName = filename.lower()
                    logger.debug("Filename exists and Type is Allowed")
                    # Validates filename checking if exists, increments if it does - returns filename
                    longFileName = prepareFileName(
                        secure_filename(lowerFileName))
                    filename = longFileName.split(
                        app.config['UPLOAD_FOLDER'], 1)[1]
                    logger.debug(f"filename: {filename}")
                    content_type = content_type
                    logger.debug("Getting Upload URL")
                    logger.debug(
                        f"{app.config['UPLOAD_FOLDER']}{filename}, {content_type}, {fileHeader}")
                    # Request Signed URL from the googs and return it for the browser to do things
                    respo = cloudStorage.generate_upload_signed_url(
                        f"{app.config['UPLOAD_FOLDER']}{filename}", content_type, fileHeader
                    )
                    # Fail if its not really a google link
                    # logger.debug(respo)
                    print(respo)
                    # if 'https://storage.googleapis.com' not in respo:
                    #     logger.error("issue with url")
                    #     return "Somethings wrong with Googles"

                    # logger.debug(f"{app.config['UPLOAD_FOLDER']}{filename}")
                    responseList.append({'filename': req, 'url': respo})
                    # # Add all that awesome information
                    # try:
                    #     cloudStorage.addMetadata(
                    #         f"{app.config['UPLOAD_FOLDER']}{filename}", uploader, email)
                    #     return "Thanks"

                    # except Exception as e:
                    #     return f"Problem With Googs - {e}"

                else:
                    return "something about not being an allowed file"
            else:
                return "Good"
        print(responseList)
        logger.debug(f'Response: {jsonify(responseList)}')
    return jsonify(responseList)


# @app.route("/images/<string:blob_name>", methods=['GET'])
# def view(blob_name):
#     values = cloudStorage.getImage(f"{app.config['UPLOAD_FOLDER']}{blob_name}")
#     return render_template('tsCOL/images.html', content_type=values[1],  image=values[0], imageName=blob_name, metadata=values[2])


@app.route("/photo/move", methods=['POST'])
@auth.login_required
def moveImage():
    '''
    Takes filenames and new location prefix as form data

    Sends to backend func to do the actual move

    Formdata:
        list of filenames
    Header:
        prefix: should be the prefix of the new location
    '''
    print('in post')
    files = request.json
    prefix = request.headers.get('prefix')
    print(files)
    for file in files:
        print(file)
        cloudStorage.moveFile(file=file, newPrefix=prefix + '/')
    if prefix == "slideshow":
        loc = "Slideshow"
    else:
        loc = "Gallery"
    return f"Moved {len(files)} to {loc}"


@app.route("/gallery", defaults={'prefix': app.config['UPLOAD_FOLDER']}, methods=['GET'])
@app.route("/show", defaults={'prefix': "slideshow/"}, methods=['GET'])
@auth.login_required
def viewGallery(prefix):
    '''
    Gallery
        location to view uploaded images and move them between 2 folders
    '''
    images = cloudStorage.listFiles(prefix)
    return render_template("tsCOL/gallery.html", images=images)


@app.route('/dupes', methods=['GET'])
def cleanUP():
    '''
    Duplicate Finder
        endpoint to allow for scheduled runs of the cleanDupes function

    '''
    count = f"<H1>Removed {cloudStorage.cleanDupes(app.config['UPLOAD_FOLDER'])} Duplicates</H1>"
    return count


@app.route('/thanks')
def thanks():
    '''
    Nice formatted location to send after upload
    deprecated in lieu of js mutations

    '''
    count = request.args.get('count')
    logger.debug(f'File Count: {count}')
    # if not fileCount:
    #     fileCount = "Many"
    return render_template('tsCOL/thanks.html', fileCount=count)


def allowed_file(filename):
    '''
    Checks to make sure the files being uploaded are appropriate

    '''
    lower = filename.lower()
    return '.' in lower.lower() and \
           lower.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

### Error Pages ###


@app.errorhandler(405)
@app.errorhandler(404)
def page_not_found(e):
    '''
    Redirect if issue with uri
    '''
    # return render_template('tsCOL/index.html'), 404
    return redirect("/", code=302)


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    return 'File is too large', 413


### Methods ###

def setupCloudLogging():
    '''
    Send logs to cloud logging when not running locally
    '''
    logging_client = google.cloud.logging.Client()
    handler = CloudLoggingHandler(logging_client)
    # Set Cloud Side
    logger = logging.getLogger('COLApp')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    logger.info("Cloud Logging Setup")
    return logger


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
    if app.config['UPLOAD_METHOD'] == "GCS" or app.config['UPLOAD_METHOD'] == "APPENGINE":
        # Check if filname exists in bucket
        logger.debug(f'preparing: {fullFile}')
        if not cloudStorage.fileExists(fullFile):
            logger.debug(f'File: {fullFile} is new')
            return fullFile.lower()
    logger.debug("looping prepareFileName")
    return prepareFileName(addNumbertoFile(fullFile))


## Logging ##
logging.info("Setup Logging")
if LOCAL_DEV != False:
    logger = setupCloudLogging()
    logger.setLevel("DEBUG")
else:
    logger = logging.getLogger()
    logger.setLevel("DEBUG")


## Debugging ##
if __name__ == "__main__":
    LOCAL_DEV = True
    print("DEV")
    print(app.instance_path)
    app.run(host="localhost", port=8080, debug=True)
