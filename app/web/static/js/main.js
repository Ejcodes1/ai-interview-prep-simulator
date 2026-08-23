// Small UX helper: show the chosen file name next to each file input.
// No form validation logic lives here — that stays server-side (FR-16).
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('input[type="file"]').forEach((input) => {
    input.addEventListener("change", () => {
      const label = input.previousElementSibling;
      if (!label || !input.files.length) return;
      const baseText = label.dataset.baseText || label.textContent;
      label.dataset.baseText = baseText;
      label.textContent = `${baseText} — selected: ${input.files[0].name}`;
    });
  });
});
