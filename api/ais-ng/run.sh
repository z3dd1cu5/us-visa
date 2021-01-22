#!/bin/bash

CODE=$1
USERNAME=$2
PASSWORD=$3
FILEPATH=$4
google-chrome "https://ais.usvisa-info.com/"$CODE"/niv/users/sign_in#main" &
sleep 7
WID=`xdotool search --name "Chrome"  |  head  -1` 
xdotool windowfocus $WID
xdotool key f
sleep 2
xdotool key a
sleep 1
xdotool type $USERNAME
sleep 1
xdotool key "Tab"
sleep 1
xdotool type $PASSWORD
sleep 1
xdotool key "Escape"
sleep 1
xdotool key f
sleep 2
xdotool key d
sleep 1
xdotool key "Return"
sleep 3

####################

#xdotool key f
#sleep 2
#xdotool key m
#sleep 3
#xdotool key f
#sleep 2
#xdotool key k
#sleep 1
#xdotool key f
#sleep 2
#xdotool key l
#sleep 3

###################
xdotool key ctrl+a
sleep 1
xdotool key ctrl+c
sleep 1
xdotool key ctrl+shift+k
sleep 1
xdotool key ctrl+w
sleep 1
xdotool key ctrl+alt+t
sleep 2
xdotool type "echo '"
sleep 1
xdotool key ctrl+v
sleep 1
xdotool type "' > "$FILEPATH
sleep 1
xdotool key "Return"
sleep 1
xdotool key ctrl+d
