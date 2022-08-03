esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
# esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 ESP32CAM-firmware_20220716.bin
esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 delivery/ESP32CAM-firmware.bin