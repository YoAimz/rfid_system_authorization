@echo off
mosquitto_pub -h [YOUR-IP-HERE] -p 8883 --cafile ./certs/ca.crt --cert ./certs/client.crt --key ./certs/client.key -t "rfid/readings" -m "{\"command\":\"cancel\"}"
echo Cancelled admin mode
pause