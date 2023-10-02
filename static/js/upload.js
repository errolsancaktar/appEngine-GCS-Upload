const uploadForm = document.getElementById("fileuploader");
const upfiles = document.getElementById("file");
const modal = document.getElementById("myModal")
const uploadText = document.createElement("div");
const modalContent = document.getElementById("modal-content");
const modalUpdate = document.getElementById("modal-update");
const formName = document.getElementById("formName");
const formEmail = document.getElementById("formEmail");



uploadForm.addEventListener("submit", e => {
    e.preventDefault();

    // Set up Modals
    modal.style.display = "block";

    var modHead = document.createElement('div');
    modHead.id = 'modHead';

    modHead.innerHTML = "<H1>Preparing Files</H1><br>";
    modalUpdate.parentNode.prepend(modHead);



    let formData = new FormData();
    const fileHeader = {
        'x-goog-meta-email': formEmail.value,
        'x-goog-meta-uploader': formName.value
    }
    const fileList = upfiles.files
    for (file = 0; file < fileList.length; file++) {
        params = {
            type: fileList[file].type,
            email: formEmail.value,
            name: formName.value
        }
        formData.append(fileList[file].name, JSON.stringify(params));
    }

    console.log(fileList)
    console.log(formData)
    fetchGet(formData, fileHeader, fileList)

});


async function fetchGet(data, headers, files) {
    console.log(data)
    const resp = await fetch(
        "/sup", {
        method: "post",
        body: data,

    })
    fetchPut(resp.json(), headers, files)
}

async function fetchPut(data, headers, files) {
    const items = await data;
    document.getElementById('modHead').innerHTML = "<H1>Uploading:</H1><br>"
    console.log("fetchput: ", items, headers, files);
    fileCount = 0
    promises = []
    for (const put of items) {

        for (fObject of files) {
            if (fObject.name == put.filename) {
                console.log(fObject.name)

                // Add Content type to the header
                const fullHeader = Object.assign({}, headers, { 'content-type': fObject.type })
                console.log(fullHeader)
                console.log(put.url)
                console.log(fObject)

                //Perform Fetch
                modalUpdate.innerHTML = fObject.name;
                promises.push(fetch(put.url, {
                    method: "PUT",
                    body: fObject,
                    referer: window.location.href,
                    headers: fullHeader,
                }))
                fileCount += fileCount;


            }

        }
    }
    const resul = await Promise.all(promises).catch(function (err) {
        modHead.innerHTML = "<H1>Error Please Try Again: " + resul + "</H1>"
        return err;

    })
    // console.log("allpromises:", resul);
    modHead.innerHTML = "<H1>Upload Complete</H1>";
    modalUpdate.innerHTML = "Thank you for sharing your memories with us<br><br><br><button onclick='location.reload(true);'class='btn-secondary rounded btn-lg mx-auto d-block'>Close</button>";
    // location.reload(true);

}