# Clark — Personal Voice Assistant for Windows

**Clark** is a personal voice assistant built with Python that allows you to interact with your Windows computer using voice commands. It uses **faster-whisper** for local speech recognition and **Tkinter** for its desktop interface.

This project is a work in progress, with the goal of making everyday computer interactions easier through voice-controlled automation.

## Features of the Project

- **Voice Recognition:** Uses faster-whisper to recognize spoken commands locally.
- **Application Launching:** Open supported Windows applications using voice commands.
- **Multi-Command Sessions:** Say the wake phrase once and issue multiple commands without repeating it every time.
- **Resizable Interface:** A Tkinter-based window that can be resized and behaves like a normal desktop application.
- **Offline Recognition:** Speech recognition works offline after the required model has been downloaded.
- **Extensible Design:** A foundation for adding more commands and features in the future.

## Tech Stack

- **Python 3.13** — Core programming language
- **faster-whisper** — Speech-to-text recognition
- **Tkinter** — Graphical user interface
- **Windows Automation** — Launching supported applications

## Supported Commands

Clark currently supports launching applications such as:

- Notepad
- Calculator
- Paint
- File Explorer
- Task Manager
- Command Prompt
- PowerShell

Available commands may vary depending on the version of the source code.

## Getting Started

### Prerequisites

Before running Clark, make sure you have:

- Windows 10 or later
- Python 3.13 installed
- A working microphone
- An internet connection for the initial speech-recognition model download

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/Clark.git
cd Clark
```

Replace `YOUR-USERNAME` with your GitHub username and `Clark` with your repository name if different.

### 2. Create a Virtual Environment (Recommended)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

Install the packages required by your version of the project. For the faster-whisper version, start with:

```powershell
python -m pip install faster-whisper
```

Install any additional packages imported by your source code, such as PyAudio or SpeechRecognition, if required.

**Compatibility note:** During development, an issue involving PyAV and faster-whisper was resolved using:

```powershell
python -m pip install "av<19"
```

You may not need this fix unless you encounter the same error.

### 4. Run Clark

Run the main Python file from your project directory. For example:

```powershell
python Clark.py
```

Replace the filename with the actual name of the Python file in your repository.

The first launch may download the speech-recognition model. Allow it to finish before testing voice commands.

## How to Use

1. Launch Clark.
2. Make sure your microphone is connected and accessible.
3. Say the configured wake phrase, such as **"Hey Clark."**
4. Speak a supported command, such as **"Open Notepad"** or **"Open Calculator."**
5. In conversation mode, continue giving commands without repeating the wake phrase after every command.
6. After a period of inactivity, Clark returns to waiting for the wake phrase.

The exact wake phrase and listening behavior depend on the configuration in the source code.

## Does Clark Work Offline?

Yes! Once the required faster-whisper model has been downloaded, speech recognition can run locally without an internet connection.

Launching locally installed Windows applications also works offline. However, downloading the model initially requires internet access, and any future features that depend on online services will need a connection.

## Future Improvements

Clark is still evolving. Planned improvements include:

- [ ] Support for more Windows applications and system commands
- [ ] Better recognition of different accents and speaking styles
- [ ] Text-to-speech responses
- [ ] Command history and improved error handling
- [ ] A more polished and customizable interface
- [ ] Safer confirmation for sensitive system actions
- [ ] Packaging as a standalone Windows executable
- [ ] Additional intelligent features

## Privacy and Safety

Clark uses local speech recognition through faster-whisper once the model is downloaded.

Always review the source code before running it, especially before adding commands that modify files, change system settings, or perform other sensitive actions.

Never upload passwords, API keys, or other private information to your public repository.

**Clark is a work in progress — built with Python, improved one command at a time.** 
