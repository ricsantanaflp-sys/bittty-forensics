# Change Documentation: `terminal.py` vs. `forensicsterminal.py`

  This documentation details the modifications made to the **`terminal.py`** file to create **`forensicsterminal.py`**.  

The goal of this change was to transform the demonstration terminal emulator into a **forensic evidence collection tool**, capable of intercepting keyboard shortcuts (`Ctrl+S`), recording the last executed command with its sanitized output, calculating an integrity hash (SHA-256), and saving the snapshot in JSON format.  

## 1.0 Installation 

Before running **`forensicsterminal.py`**, make sure the project dependencies and the core module (`bittty`) are properly set up in your Python environment.  

Below are the different ways to prepare the environment and run the application:  

### 1. Installation and Execution Methods

#### Option A: Editable Mode Installation (Recommended)

Installs the package in the current Python environment in development mode (`-e`), allowing changes to the `bittty` source code to take effect immediately.  

```bash
# Install the project in editable mode
pip install -e .

# Run the forensic terminal
python demo/forensicsterminal.py
```



#### Option B: Direct Execution via `PYTHONPATH`

Ideal for quick tests without needing to install the package into a global or virtual environment. The `PYTHONPATH=src` parameter tells Python where to directly locate the project's source files.  

```bash
PYTHONPATH=src python demo/forensicsterminal.py
```



#### Option C: Isolated Virtual Environment via `Makefile` (Automated)

To keep your environment completely clean and isolated, you can use `make` to automate `.venv` creation and dependency installation.  

```bash
# 1. Create the virtual environment and install dependencies/package in dev mode
make dev

# 2. Activate the created virtual environment
source .venv/bin/activate

# 3. Run the demo
python demo/forensicsterminal.py
```

### Forensic Usage Tip

Once the terminal is running:  

1. Type commands normally in the *shell* session.  

2. Whenever you want to record evidence of the **last executed command and its corresponding output**, press the shortcut **`Ctrl + S`**.  

3. The sanitized entry along with its corresponding SHA-256 hash will automatically be saved to the `evidencia_snapshot.json` file.  

   

## 1.1 Overview of Differences

| **Component / Feature**    | **terminal.py (Original) PY  MD**         | **forensicsterminal.py (Forensic) PY  MD**            |
| -------------------------- | ----------------------------------------- | ----------------------------------------------------- |
| **Additional Modules**     | Terminal I/O and `asyncio` only           | `datetime`, `hashlib`, `json`, `re`                   |
| **Keyboard Shortcuts**     | Passes data directly to PTY only          | Intercepts `Ctrl+S` (`\x13`) to save evidence         |
| **Command Tracking**       | Does not store typing history             | Reconstructs user command line in buffer              |
| **Output Capture (PTY)**   | Passes directly to visual parser          | Stores raw data and removes ANSI/VT100 codes          |
| **Data Persistence**       | None                                      | Saves structured records to `evidencia_snapshot.json` |
| **Integrity Calculation**  | None                                      | Generates SHA-256 hash (`cmd` + `output`)             |
| **Interface / Status Bar** | Displays dimensions and instructions only | Displays dynamic save confirmation status             |



## 1.2 Technical Implementation Details

### 1. Inclusion of System Dependencies

In `forensicsterminal.py`, native Python libraries were imported for JSON manipulation, hash generation, and regular expression handling:  

```python
from datetime import datetime
import hashlib
import json
import re
```

### 2. Class State Expansion (`__init__`)

The `StdoutFrontend` class received additional attributes to maintain the state of the active command and the output buffer received from the PTY:  

```python
# Attributes added in forensicsterminal.py
self.current_cmd_buffer = ""      # Text buffer while user types
self.last_command = ""            # Stores last command confirmed with Enter
self.last_output_raw = ""         # Stores raw output sent by the PTY
self.json_filename = "evidencia_snapshot.json"
self.status_msg = ""              # Temporary message for bottom status bar
```

### 3. Key Tracking and Interception (`handle_input`)

In `terminal.py`, keyboard input was directly passed to `bittty.input()`. In `forensicsterminal.py`, the function analyzes character by character before forwarding:  

1. **`Ctrl+S` (`\x13`) Interception**: When detected in the data stream, it triggers the `save_evidence_json()` method and removes the character from the PTY stream.  
2. **Command Reconstruction**:
   - **`Enter` (`\r`, `\n`)**: Sets `self.last_command`, clears buffers to prepare for the next command, and resets status messages.  
   - **`Backspace` (`\b`, `\x7f`)**: Removes the last typed character from the buffer.  
   - **Printable characters**: Accumulates characters in the `current_cmd_buffer` variable.  

### 4. PTY Output Capture and Sanitization

- **Capture (`handle_pty_data`)**: For each new block of data returned by the PTY process, raw text is accumulated in `self.last_output_raw += data`.  
- **Sanitization (`clean_output`)**: A new method created to remove ANSI escape sequences (such as color codes or cursor movement) via Regex and standardize line breaks (`\r\n` → `\n`), ensuring clean text for archiving:  

```python
def clean_output(self, raw_data: str) -> str:
    """Remove ANSI control codes and adjust line breaks."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    cleaned = ansi_escape.sub("", raw_data)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "")
    return cleaned.strip()
```

### 5. Evidence Generation and Persistence (`save_evidence_json`)

This new method executes the following forensic steps:  

1. Obtains the command (`last_command`) and sanitized output (`clean_output`).  
2. Records the timestamp in `YYYY-MM-DD HH:MM:SS` format.  
3. Calculates the **SHA-256** hash by concatenating the command string with the output string (`cmd + output`).  
4. Reads the existing JSON file (if any), appends the new record, and writes it with readable formatting (`indent=4`).  
5. Updates `self.status_msg` to visually notify the user in the terminal status bar.  

### 6. Status Bar Visual Update (`render_screen`)

The bottom bar of the interface was adapted to indicate the new available command or provide visual feedback as soon as evidence is saved:  

```python
# Snippet from render_screen() in forensicsterminal.py
if self.status_msg:
    status = f"bittty demo | {self.status_msg}"
else:
    status = f"bittty demo | {self.width}x{self.height} | [Ctrl+S] Save JSON | exit normally to quit"
```



## 1.3 Structure of the Generated JSON File (`evidencia_snapshot.json`)

As a result of these modifications, each press of the `Ctrl+S` shortcut generates a new entry in the final file with the following structure:  

```json
[
    {
        "timestamp": "2026-05-16 14:54:37",
        "cmd": "ls -lh",
        "output": "total 128K\n-rw-r--r-- 1 user user  227 mai 16 14:54 evidencia_snapshot.json\n-rw-r--r-- 1 user user    0 mai 16 14:54 malware",
        "hash_sha256": "e9dfe43af7f47848cb8e4b7d4ae9399cbbc0b360dd35262b29eed98ed7069ec9"
    }
]
```

  