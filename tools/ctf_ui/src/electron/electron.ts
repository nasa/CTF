import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import electronLocalshortcut from 'electron-localshortcut';
import * as path from 'path';
let mainWindow: BrowserWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        frame: false,
        title: "CFS Test Framework",
        webPreferences: {
            nodeIntegration: true
        }
    })

    mainWindow.removeMenu()

    if (process.env.NODE_ENV === 'production') {
        mainWindow.loadURL('file:///' + path.resolve(__dirname, '../render/index.html'));
    } else {
        mainWindow.loadURL('http://localhost:9000');
        mainWindow.webContents.openDevTools()
    }

    mainWindow.on('close', (e) => {
        if (mainWindow) {
            e.preventDefault();
            mainWindow.webContents.send('close');
        }
    });

    ipcMain.on('closed', () => {
        mainWindow = null
        app.quit();
    });

    electronLocalshortcut.register(mainWindow, 'Ctrl+S', () => {
        mainWindow.webContents.send('save');
    });

    mainWindow.on('closed', () => {
        mainWindow = null
    });
}

app.on('ready', createWindow)

// TODO: Add window-all-closed and active handlers to support common macOS expected behaviors