# Physical loudspeaker test: Windows steps

This experiment is **prepared, not yet performed**. It needs your actual phone
recordings. Digital noise, file copying, or synthetic software fixtures cannot
complete it. No physical result is claimed before those recordings are evaluated.

## Update your existing project

Download the latest `updated-voiceguard-ai` ZIP and copy its contents into your
existing project folder, replacing updated files and keeping `.venv`. Include
the whole `voiceguard` and `frontend` folders and the new root Python/Windows
launcher files. No new runtime packages are required.

## Record the eight clips

1. Stop your running backend with **Ctrl+C**; the physical-test tools do not
   need it running. This also saves memory during evaluation.
2. Double-click **prepare_physical_test.bat**. It downloads only eight short
   public clips, checks their pinned source waveforms, and opens a playback page
   plus an empty **recordings** folder.
3. Disconnect headphones/Bluetooth audio. Use the **laptop speaker** at a
   comfortable constant volume. Put your phone about **50 cm** away in a quiet
   room; keep the distance, volume and devices unchanged for all samples.
4. Open your phone's voice recorder. Start recording, then press Play for
   **sample_01** on the laptop. Wait for playback to finish, then stop the phone
   recording. Do not speak over it or read the words aloud yourself.
5. Repeat separately for **sample_02 through sample_08**. Capture the complete
   clip, with a little silence before/after it. Avoid recording bystanders.
6. Transfer those eight phone files to the **recordings folder opened in step 2**.
   Name them `sample_01.m4a`, `sample_02.m4a`, ..., `sample_08.m4a`. WAV/MP3/WebM/
   OGG/FLAC also work: keep the actual extension and only one file per sample.
   Do not rename a file's extension just to change its format.
7. Double-click **evaluate_physical_test.bat**. Confirm only if the files were
   captured through a **real speaker and microphone** and you have permission
   for the new recordings. Wait for evaluation to finish.
8. The results folder opens. Attach **physical-report.json** in the chat so the
   measured results can be reviewed. That report contains scores and hashes,
   not audio. Treat hashes as potentially sensitive metadata.

The Windows tools store the kit under
`%LOCALAPPDATA%\VoiceGuardAI\physical-test`, normally
`C:\Users\rbaze\AppData\Local\VoiceGuardAI\physical-test`. This keeps it out of
your OneDrive Desktop project folder. The scripts do not upload phone recordings;
your own file-transfer/cloud-sync choices still apply. Public clips/model files
may be downloaded if uncached. No VS Code or CSV editing is needed.

## What evaluation measures

The tool verifies each original waveform, matches each new recording to its
original using normalized waveform correlation, and crops to the original
duration. Alignment uses audio content, never the detector score; it removes
phone lead-in/trailing silence without choosing a flattering score. Short or
unmatched recordings fail visibly. Original files must remain unchanged.

The report compares original versus physical-capture fake-class scores,
accuracy, precision/recall, ROC/EER and score changes. With the calibrated profile
it also reports abstention coverage and errors. Eight pairs are a small pilot,
not evidence for all speakers, rooms or devices. Physical capture is user-attested,
not independently authenticated by the software.

Source: ArAD / DeepFake-Audio-Rangers, pinned revision
`9dbe1c09acc5907741dcd8c64d7a1d092ff1886d`, stated ODC-By-1.0 license. Speaker
consent records are unavailable and are not invented. The eight samples were
reserved before scoring, outside training, development, calibration and both
previous/fresh test selections. Source waveforms are not committed to Git.

Advanced CLI use: `python physical_loudspeaker_test.py prepare`; after genuine
capture, `python physical_loudspeaker_test.py evaluate --confirm-recording-permission
--confirm-physical-capture` on one line. CLI output defaults to the ignored
`physical-test` folder; `--folder` can choose another private location.
