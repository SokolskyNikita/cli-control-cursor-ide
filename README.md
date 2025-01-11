### Control Cursor IDE via the CLI

To install dependencies:
- `pip install -r requirements.txt`

1. Start Cursor with debugger port open: `/Applications/Cursor.app/Contents/MacOS/Cursor --inspect=9222 control_cursor` (macOS) or `cursor --inspect=9222 control_cursor` (Linux)
2. Send Composer commands, either alone or with the @Web command:
- `python3 cursor_debug.py "Write me FizzBuzz"`
- `python3 cursor_debug.py "Write me FizzBuzz"` --web 

You can modify it to run other commands by tweaking the code.