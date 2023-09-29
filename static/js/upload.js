const uploadForm = document.getElementById("fileuploader");
const upfiles = document.getElementById("file");
const modal = document.getElementById("myModal")
const modalContent = document.getElementById("modal-content");
const modalUpdate = document.getElementById("modal-update");
const formName = document.getElementById("formName");
const formEmail = document.getElementById("formEmail");

uploadForm.addEventListener("submit", e => {
    e.preventDefault();
    modal.style.display = "block";
    let uploadText = document.createElement("div");
    uploadText.innerHTML = "<H1>Uploading...</H1><br>";
    modalUpdate.parentNode.prepend(uploadText);

    // console.log(upfiles.files)
    // console.log(upfiles.files.length)
    const fileCount = upfiles.files.length;
    async function fetchData() {
        for (let i = 0; i < upfiles.files.length; i++) {

            let formData = new FormData();
            // console.log(upfiles.files[i].name)
            // console.log(upfiles.files[i].type)
            formData.append("file_name", upfiles.files[i].name)
            formData.append("file_type", upfiles.files[i].type)
            formData.append("formEmail", formEmail.value)
            formData.append("formName", formName.value)
            modalUpdate.innerHTML = upfiles.files[i].name;
            console.log(formData)
            try {
                let f1 = await fetch("/sup", {
                    method: "post",
                    body: formData,

                })
                let f2 = await f1.text()
                fetch(f2, {
                    method: "PUT",
                    body: upfiles.files[i],
                    referer: window.location.href,
                    headers: {
                        'Accept': upfiles.files[i].type,
                        'Content-Type': upfiles.files[i].type,
                        'x-goog-meta-uploader': formName.value,
                        'x-goog-meta-email': formEmail.value
                    }

                })

            } catch (e) {
                console.log("error: " + e);
            }

        }

    }
    fetchData().then(() => {
        console.log("Done: ", fileCount)
        // if (fileCount > 0)
        //     window.location = '/thanks?count=' + fileCount;
        // else
        //     window.location = '/thanks';
    }
    );
}
);
