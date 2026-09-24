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

// FR-10: record a voice answer, send it to the transcribe endpoint, and
// fill the typed-answer textarea with the result so the candidate can
// confirm or edit it before submitting (TR-02 mitigation) — voice input
// never submits on its own.
document.addEventListener("DOMContentLoaded", () => {
  const recordButton = document.querySelector("[data-voice-record]");
  if (!recordButton) return;

  const statusEl = document.querySelector("[data-voice-status]");
  const textarea = document.getElementById("answer_text");
  const transcribeUrl = recordButton.dataset.transcribeUrl;

  const supported =
    navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function" &&
    typeof window.MediaRecorder !== "undefined";

  if (!supported) {
    recordButton.disabled = true;
    if (statusEl) {
      statusEl.textContent = "Voice recording isn't supported in this browser — use the text box instead.";
    }
    return;
  }

  let mediaRecorder = null;
  let chunks = [];
  let recording = false;

  const setStatus = (text) => {
    if (statusEl) statusEl.textContent = text;
  };

  recordButton.addEventListener("click", async () => {
    if (recording) {
      mediaRecorder.stop();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      chunks = [];

      mediaRecorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      });

      mediaRecorder.addEventListener("stop", async () => {
        recording = false;
        recordButton.textContent = "Record voice answer";
        stream.getTracks().forEach((track) => track.stop());

        setStatus("Transcribing...");
        const blob = new Blob(chunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("audio", blob, "answer.webm");

        try {
          const response = await fetch(transcribeUrl, { method: "POST", body: formData });
          const data = await response.json();
          if (!response.ok) {
            setStatus(data.error || "Transcription failed. Please try again or type your answer.");
            return;
          }
          if (textarea) textarea.value = data.transcript;
          setStatus("Transcribed — review and edit below before submitting.");
        } catch (err) {
          setStatus("Transcription failed. Please try again or type your answer.");
        }
      });

      mediaRecorder.start();
      recording = true;
      recordButton.textContent = "Stop recording";
      setStatus("Recording...");
    } catch (err) {
      setStatus("Microphone access was denied or unavailable — use the text box instead.");
    }
  });
});
