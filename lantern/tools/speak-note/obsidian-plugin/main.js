// Tiny Obsidian plugin: one ribbon button + two commands that run speak_note.py.
// It runs only this one fixed script, never arbitrary shell commands.
// speak_note.py is expected next to this file, in the plugin's own folder.
const { Plugin, Notice, FileSystemAdapter } = require("obsidian");
const { spawn } = require("child_process");
const path = require("path");

const PYTHON = "/usr/bin/python3";

module.exports = class SpeakNote extends Plugin {
  onload() {
    this.child = null;
    const adapter = this.app.vault.adapter;
    this.script = adapter instanceof FileSystemAdapter
      ? path.join(adapter.getBasePath(), this.manifest.dir, "speak_note.py")
      : null;
    this.addRibbonIcon("audio-lines", "Read note aloud / stop", () => this.toggle());
    this.addCommand({ id: "read-aloud", name: "Read note aloud", callback: () => this.read() });
    this.addCommand({ id: "stop", name: "Stop reading", callback: () => this.stop() });
  }

  onunload() { this.stop(); }

  toggle() { this.child ? this.stop() : this.read(); }

  read() {
    const file = this.app.workspace.getActiveFile();
    if (!file || !this.script) { new Notice("Open a note first."); return; }
    this.stop();
    const full = this.app.vault.adapter.getFullPath(file.path);
    let err = "";
    const child = spawn(PYTHON, [this.script, full]);
    this.child = child;
    child.stderr.on("data", (d) => { err += d; });
    child.on("error", (e) => new Notice("Speak note: " + e.message));
    child.on("close", (code) => {
      if (this.child === child) this.child = null;
      if (code && err) new Notice("Speak note: " + err.trim().slice(-300), 10000);
    });
    new Notice("Reading: " + file.basename);
  }

  stop() {
    if (this.script) spawn(PYTHON, [this.script, "--stop"]);
    this.child = null;
  }
};
