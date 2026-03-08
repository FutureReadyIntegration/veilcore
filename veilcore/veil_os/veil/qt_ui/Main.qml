import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    visible: true
    width: 1100
    height: 700
    title: "Veil Hospital (Qt)"

    // Dark modern vibe
    color: "#0f1220"

    property string currentPage: "Patients"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar
        Rectangle {
            Layout.preferredWidth: 240
            Layout.fillHeight: true
            color: "#141833"
            border.color: "#232a55"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: "🏥 Veil Hospital"
                    color: "white"
                    font.pixelSize: 18
                    font.bold: true
                }

                Rectangle { height: 1; Layout.fillWidth: true; color: "#232a55" }

                function navButton(label) {
                    return label
                }

                Repeater {
                    model: ["Patients", "Appointments", "Billing", "Settings"]
                    delegate: Button {
                        text: modelData
                        Layout.fillWidth: true
                        onClicked: currentPage = modelData

                        // Styling
                        background: Rectangle {
                            radius: 12
                            color: (currentPage === modelData) ? "#2b67f6" : "#1b2147"
                            border.color: "#2a3366"
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "white"
                            font.pixelSize: 14
                        }
                    }
                }

                Item { Layout.fillHeight: true } // spacer
                Text { text: "vNext"; color: "#8a92c6"; font.pixelSize: 12 }
            }
        }

        // Main content with animated transitions
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#0f1220"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Text {
                    text: currentPage
                    color: "white"
                    font.pixelSize: 22
                    font.bold: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 16
                    color: "#121634"
                    border.color: "#232a55"

                    // Simple "VFX": fade + slide transition when page changes
                    Loader {
                        id: pageLoader
                        anchors.fill: parent
                        anchors.margins: 16
                        sourceComponent: currentPage === "Patients" ? patientsPage
                                       : currentPage === "Appointments" ? apptPage
                                       : currentPage === "Billing" ? billingPage
                                       : settingsPage

                        opacity: 0.0
                        x: 20

                        Behavior on opacity { NumberAnimation { duration: 180 } }
                        Behavior on x { NumberAnimation { duration: 180 } }

                        onLoaded: {
                            opacity = 0.0
                            x = 20
                            opacity = 1.0
                            x = 0
                        }
                    }
                }
            }

            Component {
                id: patientsPage
                Column {
                    spacing: 10
                    Text { text: "Patient List"; color: "white"; font.pixelSize: 16; font.bold: true }
                    Text { text: "Add tables, search, filters, etc."; color: "#b7bde6" }
                }
            }
            Component {
                id: apptPage
                Column {
                    spacing: 10
                    Text { text: "Appointments"; color: "white"; font.pixelSize: 16; font.bold: true }
                    Text { text: "Calendar + booking UI goes here."; color: "#b7bde6" }
                }
            }
            Component {
                id: billingPage
                Column {
                    spacing: 10
                    Text { text: "Billing"; color: "white"; font.pixelSize: 16; font.bold: true }
                    Text { text: "Invoices, payments, exports."; color: "#b7bde6" }
                }
            }
            Component {
                id: settingsPage
                Column {
                    spacing: 10
                    Text { text: "Settings"; color: "white"; font.pixelSize: 16; font.bold: true }
                    Text { text: "Themes, accounts, data source."; color: "#b7bde6" }
                }
            }
        }
    }
}
