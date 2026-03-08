import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: win
    visible: true
    title: "Veil Hospital"
    width: 1100
    height: 700
    minimumWidth: 900
    minimumHeight: 600
    color: "#0f1220"

    Component.onCompleted: {
        var w = settings.get("win/w", 1100)
        var h = settings.get("win/h", 700)
        win.width = w; win.height = h
        var x = settings.get("win/x", -1)
        var y = settings.get("win/y", -1)
        if (x !== -1 && y !== -1) { win.x = x; win.y = y }
    }
    onClosing: {
        settings.set("win/w", win.width)
        settings.set("win/h", win.height)
        settings.set("win/x", win.x)
        settings.set("win/y", win.y)
    }

    property string currentPage: "Patients"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0b0f1e" }
            GradientStop { position: 1.0; color: "#0f1220" }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        Rectangle {
            Layout.preferredWidth: 270
            Layout.fillHeight: true
            radius: 18
            border.color: "#24306a"
            color: "#121734"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text { text: "🏥 Veil Hospital"; color: "white"; font.pixelSize: 18; font.bold: true }
                Text { text: "Qt/QML GUI"; color: "#9aa3d6"; font.pixelSize: 12 }

                Rectangle { height: 1; Layout.fillWidth: true; color: "#24306a" }

                Repeater {
                    model: ["Patients","Appointments","Billing","Inventory","Settings"]
                    delegate: Rectangle {
                        id: navItem
                        Layout.fillWidth: true
                        height: 38
                        radius: 14
                        border.color: "#2a3366"
                        property bool active: (currentPage === modelData)
                        property bool hovered: false

                        color: active ? "#2b67f6" : hovered ? "#1d2551" : "#171d43"
                        Behavior on color { ColorAnimation { duration: 140 } }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: navItem.hovered = true
                            onExited: navItem.hovered = false
                            onClicked: currentPage = modelData
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 12
                            text: modelData
                            color: "white"
                            font.pixelSize: 14
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 18
            border.color: "#24306a"
            color: "#121634"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    height: 56
                    radius: 16
                    border.color: "#24306a"
                    color: "#0f1433"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        Text {
                            text: currentPage
                            color: "white"
                            font.pixelSize: 20
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        TextField {
                            placeholderText: "Search patients…"
                            Layout.preferredWidth: 320
                            text: backend.search
                            onTextChanged: backend.set_search(text)

                            background: Rectangle {
                                radius: 12
                                color: "#0b0f1e"
                                border.color: "#2a3366"
                            }
                            color: "white"
                            placeholderTextColor: "#7f89c7"
                        }

                        Button {
                            visible: currentPage === "Patients"
                            text: "+ New"
                            onClicked: newPatientDialog.open()

                            background: Rectangle { radius: 12; color: "#2b67f6"; border.color: "#2a3366" }
                            contentItem: Text {
                                text: parent.text
                                color: "white"
                                font.pixelSize: 13
                                font.bold: true
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 16
                    border.color: "#24306a"
                    color: "#0f1433"

                    Loader {
                        anchors.fill: parent
                        anchors.margins: 14

                        sourceComponent:
                            currentPage === "Patients" ? patientsPage :
                            currentPage === "Appointments" ? apptPage :
                            currentPage === "Billing" ? billingPage :
                            currentPage === "Inventory" ? inventoryPage :
                            settingsPage

                        opacity: 0.0
                        y: 14
                        Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        Behavior on y { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        onLoaded: { opacity = 1.0; y = 0 }
                    }
                }
            }
        }
    }

    Component { id: patientsPage; Column { spacing: 10
        Text { text: "Patient List"; color: "white"; font.pixelSize: 16; font.bold: true }
        Text { text: "Search works. Add dialog works."; color: "#b7bde6" }
    } }
    Component { id: apptPage; Column { spacing: 10; Text { text: "Appointments"; color: "white"; font.pixelSize: 16; font.bold: true } } }
    Component { id: billingPage; Column { spacing: 10; Text { text: "Billing"; color: "white"; font.pixelSize: 16; font.bold: true } } }
    Component { id: inventoryPage; Column { spacing: 10; Text { text: "Inventory"; color: "white"; font.pixelSize: 16; font.bold: true } } }
    Component { id: settingsPage; Column { spacing: 10; Text { text: "Settings"; color: "white"; font.pixelSize: 16; font.bold: true } } }

    Dialog {
        id: newPatientDialog
        modal: true
        title: "New Patient"
        standardButtons: Dialog.Ok | Dialog.Cancel

        onAccepted: {
            backend.add_patient(nameField.text, parseInt(ageField.text), statusField.currentText)
            nameField.text = ""
            ageField.text = ""
            statusField.currentIndex = 0
        }

        contentItem: Item {
            implicitWidth: 420
            implicitHeight: 220

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                TextField { id: nameField; placeholderText: "Name"; Layout.fillWidth: true }
                TextField { id: ageField; placeholderText: "Age"; inputMethodHints: Qt.ImhDigitsOnly; Layout.fillWidth: true }
                ComboBox { id: statusField; Layout.fillWidth: true; model: ["Admitted", "Discharged"] }
            }
        }
    }
}
