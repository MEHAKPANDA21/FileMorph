script.js/* FileMorph JavaScript */

/* Homepage Tool Navigation */

function goToTool() {

const tool =
    document.getElementById("toolSelect").value;

if(tool === "") {

    alert("Please select a tool first.");

    return;
}

window.location.href = tool;

}

/* File Upload Validation */

document.addEventListener("DOMContentLoaded", function(){

const fileInput =
    document.querySelector('input[type="file"]');

if(!fileInput) return;

fileInput.addEventListener("change", function(){

    const file =
        this.files[0];

    if(!file) return;

    const fileName =
        file.name;

    const fileSize =
        (file.size / 1024 / 1024).toFixed(2);

    alert(
        "Selected File:\n\n" +
        fileName +
        "\nSize: " +
        fileSize +
        " MB"
    );

});

});

/* Drag and Drop Support */

document.addEventListener("DOMContentLoaded", function(){

const dropArea =
    document.querySelector(".drop-area");

if(!dropArea) return;

dropArea.addEventListener("dragover", function(e){

    e.preventDefault();

    dropArea.style.borderColor =
        "#138808";

    dropArea.style.transform =
        "scale(1.02)";

});

dropArea.addEventListener("dragleave", function(){

    dropArea.style.borderColor =
        "#FF9933";

    dropArea.style.transform =
        "scale(1)";

});

dropArea.addEventListener("drop", function(e){

    e.preventDefault();

    dropArea.style.borderColor =
        "#FF9933";

    dropArea.style.transform =
        "scale(1)";

    const files =
        e.dataTransfer.files;

    const fileInput =
        document.querySelector(
            'input[type="file"]'
        );

    if(fileInput){

        fileInput.files = files;

    }

});

});

/* Success Animation */

function showSuccess(message){

alert("✅ " + message);

}

/* Error Animation */

function showError(message){

alert("❌ " + message);

}