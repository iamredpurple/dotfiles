import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: clock
    width: clockLayout.width
    height: clockLayout.height

    property color textColor: "#ffffff"
    property string fontFamily: "Sans Serif"
    property date currentDate: new Date()

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: clock.currentDate = new Date()
    }

    ColumnLayout {
        id: clockLayout
        anchors.centerIn: parent
        spacing: 0

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 5

            // Bold Hours
            Text {
                text: Qt.formatDateTime(clock.currentDate, "hh")
                color: clock.textColor
                font.family: clock.fontFamily
                font.pointSize: 64
                font.weight: Font.Black
            }
            
            // Pulsating Colon
            Text {
                text: ":"
                color: clock.textColor
                font.family: clock.fontFamily
                font.pointSize: 50
                font.weight: Font.Light
                opacity: 0.5
                
                SequentialAnimation on opacity {
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.1; duration: 1000; easing.type: Easing.InOutQuad }
                    NumberAnimation { to: 0.5; duration: 1000; easing.type: Easing.InOutQuad }
                }
            }

            // Light Minutes
            Text {
                text: Qt.formatDateTime(clock.currentDate, "mm")
                color: clock.textColor
                font.family: clock.fontFamily
                font.pointSize: 64
                font.weight: Font.Light
            }
        }

        // Elegantly spaced uppercase date
        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: -10
            text: Qt.formatDateTime(clock.currentDate, "dddd, MMMM d")
            color: clock.textColor
            font.family: clock.fontFamily
            font.pointSize: 11
            font.letterSpacing: 2
            font.capitalization: Font.AllUppercase
            opacity: 0.6
        }
    }
}
