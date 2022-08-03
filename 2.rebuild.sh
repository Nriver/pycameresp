# 重新编译要把之前的缓存删了
rm -rf firmware/micropython/mpy-cross/build/
rm -rf firmware/micropython/ports/esp32/build-ESP32CAM/
python3 build.py --patch --build "ESP32CAM"