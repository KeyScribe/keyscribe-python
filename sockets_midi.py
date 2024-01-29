import ast
import json
import RPi.GPIO as GPIO
import asyncio
import websockets
import ssl
import pathlib
import time
import requests
import pygame
import pygame.midi
import board
import neopixel


ID = "12345678"
auto_id = ""
token = ""
headers = ""
midi_input = ""
connected = False
server_url = "wss://10.136.148.138:8000/ws"
http_url = "https://10.136.148.138:8000/authorize"


ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.load_verify_locations("keys/cert.pem")
ssl_context.load_default_certs(ssl.Purpose.CLIENT_AUTH)
ssl_context.check_hostname = False  # Disable hostname verification


pixels = neopixel.NeoPixel(board.D18, 144, brightness=0.5)

#########################################################################################################

# Initialize units
def setup():
    global midi_input, pixels

    # initializing the midi module
    pygame.init()
    pygame.midi.init()
    midi_input = pygame.midi.Input(3) #the midi input device

    # initializing the neopixel
    pixels.fill((0,0,0))

#########################################################################################################

# Handles the turning on and off of the LEDs
def led_handler(key, state):
    # when key is pressed
    if state == 144:
        pixels[key - 21] = (255, 0, 0)
    # when key released
    elif state == 128:
        pixels[key - 21] = (0, 0, 0)

#########################################################################################################

# Function to handle the received WebSocket message
async def receive_messages(websocket):
    global auto_id, token
    try:
        while True:
            raw_message = await websocket.recv()
            if raw_message:
                message = json.loads(raw_message)
                msg_array = ast.literal_eval(message.get("note"))

                for note in msg_array:
                    state = note[0][0]
                    key = note[0][1]
                    led_handler(int(key), int(state))
                await asyncio.sleep(0.05)  # Add a small delay to avoid busy-wait
    except websockets.ConnectionClosed as e:
        # Handle a closed connection
        print("Connection closed:", e)
            
#########################################################################################################

async def main():
    global midi_input, connected, headers, token
    setup()

    # Sending HTTP request to authorize websocket connection
    message = {'hardwareId': ID}
    response = requests.get(http_url, params = message, verify=False)

    # if not verified
    if response.status_code != 200:
        print("No authorization")
    # if verified, save token and establish websocket connection
    else:
        json_object_returned = response.json()
        print(json_object_returned) ##
        token = json_object_returned.get("token")
        headers = [('Authorization', 'Bearer ' + token)]
        print(headers) ##
        print("I got the token: ", token)##

        async with websockets.connect(server_url, ssl=ssl_context, extra_headers = headers) as websocket:
            print("Connected to Server")
            # Create a task to receive messages
            recv_task = asyncio.ensure_future(receive_messages(websocket))

            while True:
                # listen to midi port for new events
                midi_event = midi_input.read(10)

                if midi_input.poll():
                    print(midi_event) ##

                # send that message back
                message = {"token": token, "note": str(midi_event)}
                await websocket.send(json.dumps(message))
                await asyncio.sleep(0.05)  # Add a small delay to avoid busy-wait

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())