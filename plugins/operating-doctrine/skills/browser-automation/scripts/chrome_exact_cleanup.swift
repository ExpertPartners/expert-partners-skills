import AppKit
import Carbon
import Foundation

// This executable runs in Aqua. The broker, not this process, holds the
// ownership ledger lock and checks competing claims before invoking close.
struct Refusal: Error {
    let code: String
    init(_ code: String) { self.code = code }
}

let chromeID = "com.google.Chrome"
let urlClasses = ["blank", "https", "http", "extension", "other"]
let classifyURL = """
on urlClass(u)
    if u is "about:blank" or u starts with "about:blank#" then return "blank"
    if u starts with "https://" then return "https"
    if u starts with "http://" then return "http"
    if u starts with "chrome-extension://" then return "extension"
    return "other"
end urlClass
"""

func tabID(_ value: String) throws -> Int32 {
    guard let n = Int32(value), n > 0, String(n) == value else {
        throw Refusal("invalid_id")
    }
    return n
}

func execute(_ source: String, ask: Bool = false) throws -> NSAppleEventDescriptor {
    let chrome = NSRunningApplication.runningApplications(withBundleIdentifier: chromeID)
    guard chrome.count == 1, let app = chrome.first, !app.isTerminated else {
        throw Refusal("chrome_process_unavailable")
    }
    let target = NSAppleEventDescriptor(processIdentifier: app.processIdentifier)
    let status = AEDeterminePermissionToAutomateTarget(target.aeDesc, typeWildCard, typeWildCard, ask)
    guard status == noErr else {
        throw Refusal(status == -1744 ? "automation_consent_required" : "automation_unavailable")
    }
    var error: NSDictionary?
    guard let result = NSAppleScript(source: source)?.executeAndReturnError(&error), error == nil else {
        throw Refusal("chrome_script_failed")
    }
    return result
}

func run(_ arguments: [String]) throws -> Any {
    if arguments == ["list"] || arguments == ["request-consent"] {
        let source = classifyURL + """

        with timeout of 8 seconds
            tell application id "com.google.Chrome"
                set rows to {}
                repeat with w in windows
                    set wid to id of w as text
                    repeat with t in tabs of w
                        set tid to id of t as text
                        set cls to my urlClass(URL of t)
                        set end of rows to {wid, tid, cls}
                    end repeat
                end repeat
                return rows
            end tell
        end timeout
        """
        let reply = try execute(source, ask: arguments == ["request-consent"])
        guard reply.descriptorType == typeAEList else { throw Refusal("invalid_inventory") }
        var rows: [[String: Any]] = []
        var seen: Set<Int32> = []
        if reply.numberOfItems > 0 {
            for i in 1...reply.numberOfItems {
                guard let row = reply.atIndex(i), row.numberOfItems == 3,
                      let window = row.atIndex(1)?.stringValue,
                      let tab = row.atIndex(2)?.stringValue,
                      let kind = row.atIndex(3)?.stringValue, urlClasses.contains(kind)
                else { throw Refusal("invalid_inventory") }
                let id = try tabID(tab)
                guard seen.insert(id).inserted else { throw Refusal("duplicate_tab_id") }
                rows.append(["windowId": try tabID(window), "tabId": id, "urlClass": kind])
            }
        }
        return ["tabs": rows]
    }
    guard arguments.count == 4, arguments[0] == "close", urlClasses.contains(arguments[3])
    else { throw Refusal("invalid_command") }
    let window = try tabID(arguments[1])
    let tab = try tabID(arguments[2])
    let kind = arguments[3]
    let source = classifyURL + """

    with timeout of 8 seconds
        tell application id "com.google.Chrome"
            set w to window id "\(window)"
            if not (exists w) then return "window_missing"
            set t to tab id "\(tab)" of w
            if not (exists t) then return "tab_missing"
            if my urlClass(URL of t) is not "\(kind)" then return "url_class_changed"
            close t
            if exists (tab id "\(tab)" of window id "\(window)") then return "close_unverified"
            return "closed"
        end tell
    end timeout
    """
    guard let result = try execute(source).stringValue,
          ["closed", "window_missing", "tab_missing", "url_class_changed", "close_unverified"].contains(result)
    else { throw Refusal("invalid_close_result") }
    return ["disposition": result]
}

do {
    let result = try run(Array(CommandLine.arguments.dropFirst()))
    let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    print(String(decoding: data, as: UTF8.self))
} catch let error as Refusal {
    print("{\"error\":\"\(error.code)\"}")
    exit(2)
} catch {
    print("{\"error\":\"helper_failed\"}")
    exit(2)
}
