import QtQuick 2.15
import QtQuick.Controls 2.15 as QQC2
import QtQuick.Layouts 1.15

QQC2.Button {
    id: control
    property string buttonText: "ACTION"
    
    Layout.preferredHeight: 30
    
    background: Rectangle {
        color: "transparent"
        // Minimalist hover underline matching the input fields exactly
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: control.hovered ? 1 : 0
            color: config.accentColor
            Behavior on height { NumberAnimation { duration: 150; easing.type: Easing.OutQuart } }
        }
    }
    
    contentItem: Text {
        text: control.buttonText
        color: config.accentColor
        font.pointSize: 10
        font.family: "Sans Serif" 
        font.letterSpacing: 1.5
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        opacity: control.hovered ? 1.0 : 0.4 // Very subtle until hovered
        Behavior on opacity { NumberAnimation { duration: 250; easing.type: Easing.OutQuart } }
    }
    
    scale: control.pressed ? 0.95 : 1.0
    Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutQuart } }
}
