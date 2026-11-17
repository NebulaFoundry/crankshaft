import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCore

ScrollView {
    id: root
    contentWidth: availableWidth
    clip: true

    Settings {
        id: preferences
        category: "Gauges"
        property var order: ["rpm", "coolant", "speed"]
        property var hidden: []
        property bool metric: false
    }

    function gaugeName(key) {
        switch (key) {
        case "rpm": return qsTr("Engine RPM")
        case "coolant": return qsTr("Coolant temperature")
        case "speed": return qsTr("Vehicle speed")
        default: return key
        }
    }

    function moveGauge(index, offset) {
        const order = Array.from(preferences.order)
        const destination = index + offset
        if (destination < 0 || destination >= order.length)
            return
        const gauge = order.splice(index, 1)[0]
        order.splice(destination, 0, gauge)
        preferences.order = order
    }

    function setGaugeVisible(key, visible) {
        const hidden = Array.from(preferences.hidden).filter(value => value !== key)
        if (!visible)
            hidden.push(key)
        preferences.hidden = hidden
    }

    ColumnLayout {
        width: root.availableWidth

        Switch {
            text: qsTr("Use metric units")
            checked: preferences.metric
            onToggled: preferences.metric = checked
        }

        Repeater {
            model: preferences.order

            RowLayout {
                required property int index
                required property string modelData
                Layout.fillWidth: true

                CheckBox {
                    Layout.fillWidth: true
                    text: root.gaugeName(parent.modelData)
                    checked: Array.from(preferences.hidden).indexOf(parent.modelData) < 0
                    onToggled: root.setGaugeVisible(parent.modelData, checked)
                }

                ToolButton {
                    text: "↑"
                    Accessible.name: qsTr("Move %1 up").arg(root.gaugeName(parent.modelData))
                    enabled: parent.index > 0
                    onClicked: root.moveGauge(parent.index, -1)
                }

                ToolButton {
                    text: "↓"
                    Accessible.name: qsTr("Move %1 down").arg(root.gaugeName(parent.modelData))
                    enabled: parent.index + 1 < preferences.order.length
                    onClicked: root.moveGauge(parent.index, 1)
                }
            }
        }
    }
}
