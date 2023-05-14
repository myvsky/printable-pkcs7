const dropArea = document.querySelector(".drag-area"),
    dragText = dropArea.querySelector("header"),
    button = dropArea.querySelector("button"),
    input = dropArea.querySelector("input");
let file; 
button.onclick = () => {
    input.click();
}
input.addEventListener("change", function() {
    file = this.files[0];
    dropArea.classList.add("active");
    showFile();
});
dropArea.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropArea.classList.add("active");
    dragText.textContent = "Release to Upload File";
});
dropArea.addEventListener("dragleave", () => {
    dropArea.classList.remove("active");
    dragText.textContent = "Drag & Drop to Upload File";
});
dropArea.addEventListener("drop", (event) => {
    event.preventDefault();
    file = event.dataTransfer.files[0];
    showFile();
});
function showFile() {
    console.log("Filename:" + file.name);
    let ext = getFileExt(file.name);
    let validExt = "sig"; 
    if (ext == validExt) {
    } 
    else {
        alert("*.sig file required");
    }
    dropArea.classList.remove("active");
    dragText.textContent = "Drag & Drop to Upload File";
}
function getFileExt(file) {
    return file.slice(((file.lastIndexOf(".") - 1) >>> 0) + 2);
}