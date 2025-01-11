(function (input) {
    const KEYDOWN_TYPE = 'keyDown';
    const CHAR_TYPE = 'char';
    const ELECTRON_MODULE = 'electron';
    const SENT_EVENT = 'sent_keydown_event';
    
    try {
        const electron = process.mainModule.require(ELECTRON_MODULE);
        const win = electron.BrowserWindow.getAllWindows()[0];

        if (!win) {
            return 'No BrowserWindow found';
        }

        console.clear();
        if (win) {
            if (input.type === 'char') {
                win.webContents.sendInputEvent({
                    type: CHAR_TYPE,
                    keyCode: input.text
                });
            } else {
                win.webContents.sendInputEvent({
                    type: KEYDOWN_TYPE,
                    keyCode: input.key,
                    modifiers: input.modifiers || []
                });
            }
            return SENT_EVENT;
        }
        return 'No window found';
    } catch (e) {
        return 'Error: ' + e.message;
    }
})
