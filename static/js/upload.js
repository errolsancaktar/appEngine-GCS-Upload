const uploadForm = document.getElementById("fileuploader");
const upfiles = document.getElementById("file");
uploadForm.addEventListener("submit", e => {
    e.preventDefault();
    const formData = new FormData();

    console.log(upfiles.files)

    for (let i = 0; i < upfiles.files.length; i++) {
        console.log(upfiles.files[i].name)
        formData.append("file_name", upfiles.files[i].name)
        formData.append("file_type", upfiles.files[i].type)
        fetch("/", {
            method: "post",
            body: formData,

        }).then(res => res.text()).then(text => postIt(text))
        let postIt = (data) => {
            console.log(data);
            console.log(upfiles.files[i])
            fetch(data, {
                method: "PUT",
                body: upfiles.files[i],
            })
        }


    }
});
