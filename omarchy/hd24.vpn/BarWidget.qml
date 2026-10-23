import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "hd24.vpn"
  property string vpnState: "unknown"
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Process {
    id: status
    command: ["nmcli", "-g", "GENERAL.STATE", "connection", "show", "HD24 Sophos VPN"]
    stdout: StdioCollector {
      onStreamFinished: root.vpnState = this.text.trim()
    }
    onExited: function(code) { if (code !== 0) root.vpnState = "unknown" }
  }
  Timer {
    interval: 3000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: if (!status.running) status.running = true
  }
  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "\uf132"
    slotSize: Style.bar.statusSlot
    foreground: root.vpnState === "activated" ? "#73c991" : root.vpnState === "activating" ? "#e5c07b" : "#aaaaaa"
    tooltipText: root.vpnState === "activated" ? "HD24 VPN connected — click to disconnect" : root.vpnState === "activating" ? "HD24 VPN connecting — complete the login prompt" : "HD24 VPN disconnected — click to enter password + current OTP"
    onPressed: Quickshell.execDetached(["bash", Quickshell.env("HOME") + "/.config/omarchy/plugins/hd24.vpn/toggle.sh"])
  }
}
