# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import board
import neopixel_write
import digitalio
import busio
import adafruit_hcsr04

sonar = adafruit_hcsr04.HCSR04(trigger_pin=board.IO36, echo_pin=board.IO35, timeout=0.5)

sensorVazao = digitalio.DigitalInOut(board.IO38)
sensorVazao.direction = digitalio.Direction.INPUT

ledGreen = digitalio.DigitalInOut(board.IO40)
ledRed = digitalio.DigitalInOut(board.IO41)
ledBlue = digitalio.DigitalInOut(board.IO42)
ledGreen.direction = digitalio.Direction.OUTPUT
ledRed.direction = digitalio.Direction.OUTPUT
ledBlue.direction = digitalio.Direction.OUTPUT

relay = digitalio.DigitalInOut(board.IO39)
relay.direction = digitalio.Direction.OUTPUT
relay.value = 0

def setLed(led):
    if led == "green":
        ledRed.value = 0
        ledBlue.value = 0
        ledGreen.value = 1
    elif led == "blue":
        ledRed.value = 0
        ledBlue.value = 1
        ledGreen.value = 0
    elif led == "red":
        ledRed.value = 1
        ledBlue.value = 0
        ledGreen.value = 0

def checkDistance(threshold):
    distance = 99999
    count = 0
    while count < 3:
        try:
            distance = sonar.distance
            if threshold >= distance:
                count = count + 1
            else:
                count = 0
            print(distance)
        except RuntimeError:
            print("Retrying!")
        time.sleep(0.1)

setLed("red")

pin = digitalio.DigitalInOut(board.NEOPIXEL)
pin.direction = digitalio.Direction.OUTPUT
pixel_off = bytearray([0, 0, 0])
pixel_green = bytearray([255, 0, 0])

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["pass"])
print("Connected to %s!" % secrets["ssid"])

### Code ###

# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connected(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print("Connected to MQTT Broker!")

def disconnected(client, userdata, rc):
    # This method is called when the client is disconnected
    print("Disconnected from MQTT Broker!")

def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))

def on_battery_msg(client, topic, message):
    # Method called when device/batteryLife has a new value
    print("Battery level: {}v".format(message))

def on_message(client, topic, message):
    # Method callled when a client's subscribed feed has a new value.
    print("New message on topic {0}: {1}".format(topic, message))
    neopixel_write.neopixel_write(pin, pixel_green)
    setLed("blue")
    checkDistance(10)
    setLed("green")
    relay.value = 1
    time.sleep(12)
    neopixel_write.neopixel_write(pin, pixel_off)
    relay.value = 0
    setLed("red")

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Set up a MiniMQTT Client
client = MQTT.MQTT(
    broker=secrets["broker"],
    port=secrets["port"],
    username=secrets["username"],
    password=secrets["password"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Setup the callback methods above
client.on_connect = connected
client.on_disconnect = disconnected
client.on_subscribe = subscribe
client.on_unsubscribe = unsubscribe
client.on_message = on_message
client.add_topic_callback(
    secrets["username"] + "/feeds/device.batterylevel", on_battery_msg
)

# Connect the client to the MQTT broker.
print("Connecting to MQTT broker...")
client.connect()
print("Connected in MQTT broker!")

# Subscribe to all notifications on the device group
client.subscribe(secrets["username"] + "/groups/device", 1)

# Start a blocking message loop...
# NOTE: NO code below this loop will execute
while True:
    try:
        client.loop()
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        client.reconnect()
        continue
    time.sleep(1)
