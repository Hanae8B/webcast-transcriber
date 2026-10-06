# Webcast Transcriber

A lightweight Windows desktop application that captures system audio and transcribes English webcasts in real time using **Faster-Whisper**.

## Features

* 🎙️ Captures Windows system audio using WASAPI loopback
* 📝 Real-time English transcription
* 🤖 Powered by Faster-Whisper
* 🖥️ Simple desktop interface built with Tkinter
* ⚡ Runs locally on your computer
* 🔒 No audio is sent to an external transcription service

## Requirements

* Windows 10 or Windows 11
* Python 3.10+
* A working Windows audio output device
* Internet connection for the initial installation and model download

## Installation

Clone the repository:

```bash
git clone https://github.com/Hanae8B/webcast-transcriber.git
cd webcast-transcriber
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Then launch the application:

```bash
python webcast_transcriber.py
```

You can also use the included `run.bat` file to start the application.

## Usage

1. Start the application.
2. Play the webcast or other English audio on your computer.
3. Select the appropriate audio output device if required.
4. Start transcription.
5. The recognized text will appear in the application window.

The application captures the audio currently being played through the Windows output device using WASAPI loopback.

## Whisper Models

The application uses Faster-Whisper models for transcription.

The model can be configured in `webcast_transcriber.py`.

For example:

```python
MODEL_NAME = "small.en"
```

Available English models include:

* `base.en` — faster, lower resource usage
* `small.en` — better accuracy, recommended for most users
* `medium.en` — higher accuracy, requires more processing power

For speakers with different accents or non-native English pronunciation, a larger model may provide better results.

## Performance

Transcription quality and speed depend on your hardware, audio quality, background noise, accents, and the selected Whisper model.

For better accuracy, `small.en` or `medium.en` is recommended when your computer can handle it.

## Project Structure

```text
webcast-transcriber/
│
├── webcast_transcriber.py
├── run.bat
├── .gitignore
├── requirements.txt
└── README.md
```

## Privacy

Audio processing and transcription are performed locally using Faster-Whisper.

The application does not require sending your webcast audio to a cloud transcription service.

## License

This project is distributed under the **BSD 3-Clause License**.

Copyright (c) 2026 Hanae8B

See the `LICENSE` file for the complete license text.

## Author

**Hanae8B**

If you use or redistribute this project, please retain the copyright and license notices as required by the BSD 3-Clause License.