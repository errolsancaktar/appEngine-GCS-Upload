from flask import *
app = Flask(__name__)


@app.route('/')
def main():
    return render_template("upload.html")


@app.route('/', methods=['POST'])
def upload():
    if request.method == 'POST':

        # Get the list of files from webpage
        # files = request.files.getlist("file")
        file = request.files['file']

        # Iterate for each file in the files List, and Save them
        # for file in files:
        print(dir(file))
        print(file)
        print(file.content_type)
        return "<h1>Files Uploaded Successfully.!</h1>"


if __name__ == '__main__':
    app.run(debug=True)
