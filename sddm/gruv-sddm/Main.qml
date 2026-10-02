import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15 as QQC2
import QtGraphicalEffects 1.15
import SddmComponents 2.0
import "components"

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: config.primaryColor

    FontLoader {
        id: bundledFont
	source : "./fonts/font.ttf"
	//source: "../../../fonts/TTF/CascadiaMono.ttf"
    }

    // Base background image (always crisp and sharp on the left side)
    Image {
        id: backgroundImage
        anchors.fill: parent
        source: config.background ? config.background : ""
        fillMode: Image.PreserveAspectCrop
      }

    // Slight global darken so the wallpaper doesn't blind the user
    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: backgroundImage.source.toString() !== "" ? 0.2 : 1.0
      }

    Item {
        id: mainContainer
        anchors.fill: parent
        opacity: 0.0
        
        transform: Translate {
            id: slideTransform
            x: config.alignment === "left" ? -50 : (config.alignment === "right" ? 50 : 0)
            y: config.alignment === "center" ? 50 : 0
        }

        // 1. Split-screen Glass Panel (covers exactly 35% of the screen)
        Item {
            id: sidePanel
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: config.alignment === "left" ? parent.left : undefined
            anchors.right: config.alignment === "right" ? parent.right : undefined
            anchors.horizontalCenter: config.alignment === "center" ? parent.horizontalCenter : undefined
            
            width: parent.width * 0.35 // Less than half the screen width!
            visible: backgroundImage.source.toString() !== ""

            ShaderEffectSource {
                id: panelBlurSource
                sourceItem: backgroundImage
                // Grabs exactly the 35% portion on the right
                sourceRect: Qt.rect(sidePanel.x, sidePanel.y, sidePanel.width, sidePanel.height)
            }

            FastBlur {
                anchors.fill: parent
                source: panelBlurSource
                radius: 64
            }

            // Dark matte tint over the glass
            Rectangle {
                anchors.fill: parent
                color: config.primaryColor
                opacity: 0.55 // Reduced opacity so the beautiful blur shines through!
            }

            // Crisp edge separator line where the blur ends
            Rectangle {
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.left: config.alignment === "right" ? parent.left : undefined
                anchors.right: config.alignment === "left" ? parent.right : undefined
                width: 1
                color: config.accentColor
                opacity: 0.2
                visible: config.alignment !== "center"
            }
        }
        
        // Solid fallback if no image
        Rectangle {
            anchors.fill: sidePanel
            color: config.inputColor
            opacity: 0.5
            visible: backgroundImage.source.toString() === ""
        }

        // Dynamic Login Panel Layout
        ColumnLayout {
            id: loginPanel
            anchors.verticalCenter: parent.verticalCenter
            
            // Anchor perfectly in the center of our 35% side panel
            anchors.horizontalCenter: sidePanel.horizontalCenter
            
            spacing: 20
            width: 380 

            Clock {
                Layout.alignment: Qt.AlignHCenter
                Layout.bottomMargin: 40
                textColor: config.accentColor
                fontFamily: bundledFont.name 
            }

            Image {
                id: avatar
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 100
                Layout.preferredHeight: 100
                source: config.avatar ? config.avatar : "" 
                visible: source.toString() !== ""
                fillMode: Image.PreserveAspectCrop
                
                layer.enabled: true
                layer.effect: OpacityMask {
                    maskSource: Rectangle {
                        width: avatar.width
                        height: avatar.height
                        radius: width / 2
                    }
                }
            }

            QQC2.TextField {
                id: usernameField
                Layout.fillWidth: true
                visible: config.showUsername !== "false"
                text: userModel.lastUser
                placeholderText: "Username"
                color: config.accentColor
                font.family: bundledFont.name
                font.pointSize: 12
                background: Rectangle {
                    color: "transparent"
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: usernameField.activeFocus ? 2 : 1
                        color: config.accentColor
                        Behavior on height { NumberAnimation { duration: 150; easing.type: Easing.OutQuart } }
                    }
                }
                onAccepted: passwordField.forceActiveFocus()
            }

            QQC2.TextField {
                id: passwordField
                Layout.fillWidth: true
                placeholderText: "Password"
                echoMode: TextInput.Password
                color: config.accentColor
                font.family: bundledFont.name
                font.pointSize: 12
                background: Rectangle {
                    color: "transparent"
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: passwordField.activeFocus ? 2 : 1
                        color: config.accentColor
                        Behavior on height { NumberAnimation { duration: 150; easing.type: Easing.OutQuart } }
                    }
                }
                onAccepted: sddm.login(usernameField.text, passwordField.text, sessionSelector.currentIndex)
            }

            QQC2.ComboBox {
                id: sessionSelector
                Layout.fillWidth: true
                Layout.topMargin: 10
                model: sessionModel
                textRole: "name"
                currentIndex: sessionModel.lastIndex
                font.family: bundledFont.name
                font.pointSize: 10
                
                background: Rectangle {
                    color: config.inputColor
                    radius: 4
                    opacity: 0.6 // More transparent so background blur shows through
                    border.width: 1
                    border.color: sessionSelector.hovered ? config.accentColor : "transparent"
                    Behavior on border.color { ColorAnimation { duration: 250; easing.type: Easing.OutQuart } }
                }
                
                contentItem: Text {
                    text: sessionSelector.currentText
                    color: config.accentColor
                    font: sessionSelector.font
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 15
                }
                
                // Custom glassy popup for the dropdown list
                popup: QQC2.Popup {
                    y: sessionSelector.height + 5
                    width: sessionSelector.width
                    implicitHeight: contentItem.implicitHeight
                    padding: 5
                    
                    background: Rectangle {
                        color: config.primaryColor
                        opacity: 0.75 // Semi-transparent to act as a glass overlay on the blur
                        radius: 6
                        border.color: config.accentColor
                        border.width: 1
                    }

                    contentItem: ListView {
                        clip: true
                        implicitHeight: contentHeight
                        model: sessionSelector.popup.visible ? sessionSelector.delegateModel : null
                        currentIndex: sessionSelector.highlightedIndex
                        QQC2.ScrollIndicator.vertical: QQC2.ScrollIndicator { }
                    }
                }
                
                delegate: QQC2.ItemDelegate {
                    width: sessionSelector.width - 10
                    contentItem: Text {
                        text: model.name
                        color: config.accentColor
                        font: sessionSelector.font
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                        opacity: hovered ? 1.0 : 0.6
                    }
                    background: Rectangle {
                        color: hovered ? config.accentColor : "transparent"
                        opacity: hovered ? 0.15 : 0.0
                        radius: 4
                    }
                }
            }

            QQC2.Button {
                id: loginButton
                Layout.fillWidth: true
                Layout.topMargin: 20
                text: "Validate Login"
                font.family: bundledFont.name
                font.pointSize: 12
                font.letterSpacing: 2
                font.weight: Font.Bold
                
                contentItem: Text {
                    text: loginButton.text
                    color: loginButton.hovered ? config.primaryColor : config.accentColor
                    font: loginButton.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Behavior on color { ColorAnimation { duration: 250; easing.type: Easing.OutQuart } }
                }
                background: Rectangle {
                    color: loginButton.hovered ? config.accentColor : "transparent"
                    border.color: config.accentColor
                    border.width: 1
                    radius: 4
                    Behavior on color { ColorAnimation { duration: 250; easing.type: Easing.OutQuart } }
                }

                onClicked: {
                    sddm.login(usernameField.text, passwordField.text, sessionSelector.currentIndex)
                }
            }
        }
    }

    // 2. Power Controls (Minimal text links in the corner)
    RowLayout {
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.bottomMargin: 30
        anchors.rightMargin: 40
        spacing: 25
        opacity: mainContainer.opacity 

        PowerButton {
            buttonText: "SLEEP" 
            onClicked: sddm.suspend()
        }
        PowerButton {
            buttonText: "RESTART" 
            onClicked: sddm.reboot()
        }
        PowerButton {
            buttonText: "SHUTDOWN" 
            onClicked: sddm.powerOff()
        }
    }

    SequentialAnimation {
        id: startupAnimation
        PauseAnimation { duration: 150 } 
        ParallelAnimation {
            NumberAnimation { 
                target: mainContainer
                property: "opacity"
                to: 1.0
                duration: 800
                easing.type: Easing.OutQuart
            }
            NumberAnimation {
                target: slideTransform
                property: "x"
                to: 0
                duration: 800
                easing.type: Easing.OutQuart
            }
            NumberAnimation {
                target: slideTransform
                property: "y"
                to: 0
                duration: 800
                easing.type: Easing.OutQuart
            }
        }
    }

    Component.onCompleted: {
        startupAnimation.start()
        if (usernameField.visible && usernameField.text === "") {
            usernameField.forceActiveFocus()
        } else {
            passwordField.forceActiveFocus()
        }
    }
}
