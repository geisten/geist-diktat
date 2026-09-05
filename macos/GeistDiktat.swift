import AppKit
import AVFoundation
import ApplicationServices
import Carbon

// UTF-8 framing is independent of pipe callback boundaries.
struct TranscriptStream {
    var pending = Data()
    mutating func accept(_ bytes: Data, eof: Bool = false) throws -> [String] {
        pending.append(bytes)
        if pending.count > 65536 { throw StreamError.tooLarge }
        var lines = [String]()
        while let newline = pending.firstIndex(of: 10) {
            let data = pending.prefix(upTo: newline)
            guard let text = String(data: data, encoding: .utf8) else { throw StreamError.invalidUTF8 }
            if !text.isEmpty { lines.append(text.trimmingCharacters(in: .newlines)) }
            pending.removeSubrange(...newline)
        }
        if eof && !pending.isEmpty {
            guard let text = String(data: pending, encoding: .utf8) else { throw StreamError.invalidUTF8 }
            lines.append(text); pending.removeAll()
        }
        return lines
    }
    enum StreamError: Error { case tooLarge, invalidUTF8 }
}

if CommandLine.arguments.contains("--self-test") {
    var stream = TranscriptStream()
    precondition(try! stream.accept(Data([0x47, 0x72, 0xc3])).isEmpty)
    precondition(try! stream.accept(Data([0xbc, 0xc3, 0x9f, 0x65, 10])) == ["Grüße"])
    precondition(try! stream.accept(Data("rest".utf8), eof: true) == ["rest"])
    do { _ = try stream.accept(Data(repeating: 65, count: 65537)); fatalError("limit missing") } catch {}
    print("PASS fragmented UTF-8, EOF and bounded framing")
    exit(0)
}

final class DictationApp: NSObject, NSApplicationDelegate {
    var item: NSStatusItem!
    var process: Process?
    var generation = 0
    var stream = TranscriptStream()
    var hotkey: EventHotKeyRef?
    var target: AXUIElement?
    var insert = false
    var transcript = ""
    var panel: NSPanel?
    var preview: NSTextView?
    var action: NSMenuItem!
    var status: NSMenuItem!
    var insertItem: NSMenuItem!
    let launcher = Bundle.main.bundleURL.appendingPathComponent("Contents/Resources/runtime/bin/geist-diktat")

    func applicationDidFinishLaunching(_ notification: Notification) {
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        item.button?.title = "Diktat ○"
        let menu = NSMenu()
        status = NSMenuItem(title: "Bereit · Vorschau", action: nil, keyEquivalent: ""); menu.addItem(status)
        action = menu.addItem(withTitle: "Aufnahme starten", action: #selector(toggle), keyEquivalent: "")
        menu.addItem(withTitle: "Modelle einrichten", action: #selector(setup), keyEquivalent: "")
        menu.addItem(withTitle: "Diagnose", action: #selector(doctor), keyEquivalent: "")
        menu.addItem(withTitle: "Transkript anzeigen", action: #selector(showPreview), keyEquivalent: "")
        menu.addItem(withTitle: "Transkript kopieren", action: #selector(copyText), keyEquivalent: "")
        insertItem = menu.addItem(withTitle: "Direkt in bestätigtes Textfeld einfügen", action: #selector(toggleInsert), keyEquivalent: "")
        menu.addItem(.separator())
        menu.addItem(withTitle: "Beenden", action: #selector(quit), keyEquivalent: "q")
        for entry in menu.items { entry.target = self }
        item.menu = menu
        var event = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetApplicationEventTarget(), { _, _, _ in
            DispatchQueue.main.async { (NSApp.delegate as? DictationApp)?.toggle() }
            return noErr
        }, 1, &event, nil, nil)
        let result = RegisterEventHotKey(UInt32(kVK_Space), UInt32(controlKey | optionKey), EventHotKeyID(signature: 0x4744494b, id: 1), GetApplicationEventTarget(), 0, &hotkey)
        if result != noErr { status.title = "Hotkey belegt · Menü verwenden" }
    }
    func focusedField() -> AXUIElement? {
        if IsSecureEventInputEnabled() { return nil }
        var focused: CFTypeRef?
        guard AXUIElementCopyAttributeValue(AXUIElementCreateSystemWide(), kAXFocusedUIElementAttribute as CFString, &focused) == .success,
              let value = focused, CFGetTypeID(value) == AXUIElementGetTypeID() else { return nil }
        let field = value as! AXUIElement
        var role: CFTypeRef?
        guard AXUIElementCopyAttributeValue(field, kAXRoleAttribute as CFString, &role) == .success,
              let name = role as? String, [kAXTextFieldRole, kAXTextAreaRole].contains(name) else { return nil }
        var subrole: CFTypeRef?
        _ = AXUIElementCopyAttributeValue(field, kAXSubroleAttribute as CFString, &subrole)
        if subrole as? String == kAXSecureTextFieldSubrole { return nil }
        var writable: DarwinBoolean = false
        guard AXUIElementIsAttributeSettable(field, kAXSelectedTextAttribute as CFString, &writable) == .success, writable.boolValue else { return nil }
        return field
    }
    @objc func toggleInsert() {
        if !insert && !AXIsProcessTrustedWithOptions([kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary) {
            status.title = "Bedienungshilfen erlauben; anschließend erneut aktivieren"; return
        }
        insert.toggle(); insertItem.state = insert ? .on : .off
    }
    @objc func toggle() {
        if process != nil { stop(); return }
        target = insert ? focusedField() : nil
        let current = generation
        AVCaptureDevice.requestAccess(for: .audio) { granted in
            DispatchQueue.main.async {
                guard current == self.generation, self.process == nil else { return }
                if granted { self.start(["run"], recording: true) }
                else { self.status.title = "Mikrofonzugriff fehlt · Systemeinstellungen → Datenschutz" }
            }
        }
    }
    @objc func setup() { if process == nil { start(["setup"], recording: false) } }
    @objc func doctor() { if process == nil { start(["doctor", "--verify"], recording: false) } }
    func start(_ arguments: [String], recording: Bool) {
        generation += 1; let session = generation
        stream = TranscriptStream()
        let child = Process(); child.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        let runner = Bundle.main.bundleURL.appendingPathComponent("Contents/Resources/runtime/share/geist-diktat/command_runner.py")
        child.arguments = ["python3", runner.path, "--", launcher.path] + arguments
        var environment = ProcessInfo.processInfo.environment
        environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + (environment["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin")
        child.environment = environment
        let output = Pipe(); let errors = Pipe(); child.standardOutput = output; child.standardError = errors
        child.standardInput = FileHandle.nullDevice
        output.fileHandleForReading.readabilityHandler = { handle in
            let bytes = handle.availableData
            if bytes.isEmpty { handle.readabilityHandler = nil }
            DispatchQueue.main.async {
                guard self.generation == session else { return }
                do {
                    for text in try self.stream.accept(bytes, eof: bytes.isEmpty) {
                        self.transcript += text + "\n"
                        if self.transcript.utf8.count > 262144 { self.transcript = String(self.transcript.suffix(65536)) }
                        self.preview?.string = self.transcript
                        if recording && self.insert, let old = self.target, let now = self.focusedField(), CFEqual(old, now) {
                            if AXUIElementSetAttributeValue(now, kAXSelectedTextAttribute as CFString, (text + " ") as CFString) != .success {
                                self.status.title = "Einfügen fehlgeschlagen · Transkript in Vorschau"
                            }
                        }
                    }
                } catch { self.status.title = "Ungültige Ausgabe · Aufnahme gestoppt"; self.stop() }
            }
        }
        errors.fileHandleForReading.readabilityHandler = { handle in
            let bytes = handle.availableData
            if bytes.isEmpty { handle.readabilityHandler = nil; return }
            let text = String(decoding: bytes, as: UTF8.self)
            DispatchQueue.main.async {
                guard self.generation == session else { return }
                if text.contains("failed") || text.contains("overload:") || text.contains("missing") {
                    self.status.title = String(text.trimmingCharacters(in: .whitespacesAndNewlines).prefix(120))
                }
            }
        }
        child.terminationHandler = { p in
            DispatchQueue.main.async {
                guard self.generation == session else { return }
                self.process = nil; self.item.button?.title = "Diktat ○"; self.action.title = "Aufnahme starten"
                self.status.title = p.terminationStatus == 0 ? "Beendet · Transkript in Vorschau" : "Fehler \(p.terminationStatus) · Diagnose ausführen"
            }
        }
        do {
            try child.run(); process = child
            item.button?.title = recording ? "Diktat ●" : "Diktat …"
            action.title = "Stoppen"; status.title = recording ? "Aufnahme gestartet · Ctrl-Option-Leertaste stoppt" : "Einrichtung / Diagnose läuft"
        } catch { status.title = "Start fehlgeschlagen: \(error.localizedDescription)" }
    }
    func stop() {
        generation += 1; let stopping = generation; target = nil
        if let child = process {
            child.terminationHandler = { _ in
                DispatchQueue.main.async {
                    if self.generation == stopping { self.process = nil }
                }
            }
            child.terminate()
        }
        item.button?.title = "Diktat ○"; action.title = "Aufnahme starten"; status.title = "Gestoppt · Transkript in Vorschau"
    }
    @objc func showPreview() {
        if panel == nil {
            panel = NSPanel(contentRect: NSRect(x: 200, y: 200, width: 650, height: 400), styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
            panel?.title = "Geist Diktat — Transkript"
            let scroll = NSScrollView(frame: panel!.contentView!.bounds); scroll.autoresizingMask = [.width, .height]; scroll.hasVerticalScroller = true
            let text = NSTextView(frame: scroll.bounds); text.isEditable = false; text.autoresizingMask = [.width]; text.string = transcript
            scroll.documentView = text; panel?.contentView?.addSubview(scroll); preview = text
        }
        panel?.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
    }
    @objc func copyText() { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(transcript, forType: .string) }
    @objc func quit() { stop(); NSApp.terminate(nil) }
    func applicationWillTerminate(_ notification: Notification) { stop(); if let key = hotkey { UnregisterEventHotKey(key) } }
}
let app = NSApplication.shared
let delegate = DictationApp()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
