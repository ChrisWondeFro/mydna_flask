// Upload form: filename feedback, drag and drop, and a busy state so the user
// is not left staring at an unresponsive page during a long analysis.
(function () {
  "use strict";

  const form = document.querySelector("[data-upload-form]");
  if (!form) return;

  const drop = form.querySelector("[data-file-drop]");
  const input = form.querySelector("[data-file-input]");
  const nameEl = form.querySelector("[data-file-name]");
  const sizeEl = form.querySelector("[data-file-size]");
  const button = form.querySelector("[data-submit-button]");

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function showSelection() {
    const file = input.files && input.files[0];
    if (!file) {
      drop.classList.remove("has-file");
      nameEl.textContent = "Choose a file or drag it here";
      sizeEl.textContent = "No file selected";
      return;
    }
    drop.classList.add("has-file");
    nameEl.textContent = file.name;
    sizeEl.textContent = formatSize(file.size) + " \u2014 ready to analyse";
  }

  input.addEventListener("change", showSelection);

  ["dragenter", "dragover"].forEach(function (type) {
    drop.addEventListener(type, function (event) {
      event.preventDefault();
      drop.classList.add("is-dragging");
    });
  });

  ["dragleave", "drop"].forEach(function (type) {
    drop.addEventListener(type, function (event) {
      event.preventDefault();
      drop.classList.remove("is-dragging");
    });
  });

  drop.addEventListener("drop", function (event) {
    const files = event.dataTransfer && event.dataTransfer.files;
    if (files && files.length) {
      input.files = files;
      showSelection();
    }
  });

  form.addEventListener("submit", function () {
    if (!input.files || !input.files.length) return;
    form.classList.add("is-submitting");
    button.disabled = true;
  });

  // Restoring from the back/forward cache leaves the button disabled otherwise.
  window.addEventListener("pageshow", function () {
    form.classList.remove("is-submitting");
    button.disabled = false;
  });

  showSelection();
})();
