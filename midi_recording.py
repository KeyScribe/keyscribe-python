import ast
import json
#import RPi.GPIO as GPIO
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
from midiutil import MIDIFile
from keys_led_pairs import piano_key_mapping


ID = "12345678"
auto_id = ""
token = ""
headers = ""
midi_input = ""
midi_notes = []
notes_in_progress = []
connected = False
recording = False
start_time = 0
server_url = "wss://10.136.168.150:8000/ws"
http_url = "https://10.136.168.150:8000/api/authorize"

RED = (255, 0 ,0)
GREEN = (0, 255 ,0)
YELLOW = (150, 120 ,0)
OFF = (0, 0 ,0)
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.load_verify_locations("keys/cert.pem")
ssl_context.load_default_certs(ssl.Purpose.CLIENT_AUTH)
ssl_context.check_hostname = False  # Disable hostname verification


pixels = neopixel.NeoPixel(board.D18, 176, brightness=0.6)

#########################################################################################################

# Initialize units
def setup():
    global midi_input, pixels

    # initializing the midi module
    pygame.init()
    pygame.midi.init()

    # checking to see if midi devices connected
    while True:
        # will wait until user connects the module to the keyboard
        device_count = pygame.midi.get_count()
        if device_count != 0:
            print("MIDI device found.")
            break
    midi_input = pygame.midi.Input(3) #the midi input device

    # initializing the neopixel
    pixels[5] = (0,0,255)
    time.sleep(1)
    pixels.fill((0,0,0))

# note turns off after other off signal comes --- need to fix this
#########################################################################################################
# Handles the turning on and off of the LEDs
def led_handler(key, state):
    # when key is pressed
    if state == 144:
        print( pixels[piano_key_mapping[key - 20][0]])
        if pixels[piano_key_mapping[key - 20][0]] != [0, 0, 0]:
            for i in range(len(piano_key_mapping[key - 20])):
                pixels[piano_key_mapping[key - 20][i]] = GREEN
        elif pixels[piano_key_mapping[key - 20][0]] == [0, 0, 0]:
            for i in range(len(piano_key_mapping[key - 20])):
                pixels[piano_key_mapping[key - 20][i]] = YELLOW
    # when key released
    elif state == 128:
        for i in range(len(piano_key_mapping[key - 20])):
            pixels[piano_key_mapping[key - 20][i]] = OFF

#########################################################################################################

# Handles the turning on and off of the LEDs
def led_handler2(key, state):
    # when key is pressed
    if state == 144:
        if pixels[piano_key_mapping[key - 20][0]] != [0, 0, 0]:
            for i in range(len(piano_key_mapping[key - 20])):
                pixels[piano_key_mapping[key - 20][i]] = GREEN
        elif pixels[piano_key_mapping[key - 20][0]] == [0, 0, 0]:
            for i in range(len(piano_key_mapping[key - 20])):
                pixels[piano_key_mapping[key - 20][i]] = RED
    # when key released
    elif state == 128:
        for i in range(len(piano_key_mapping[key - 20])):
            pixels[piano_key_mapping[key - 20][i]] = OFF

#########################################################################################################
            
def generate_midi_file():
    track = 0
    channel = 0
    time = 0 # In beats
    tempo = 60 # In BPM
    volume = 100 # 0-127, as per the MIDI standard
    MyMIDI = MIDIFile(1) # One track, defaults to format 1 (tempo track automatically created)
    MyMIDI.addTempo(track,time, tempo)

    for i, (pitch, note_time, duration) in enumerate(midi_notes):
        MyMIDI.addNote(track, channel, pitch, note_time, duration, volume)
    with open("my_midi.mid", "wb") as output_file:
        MyMIDI.writeFile(output_file)

    # send midi file to the server
    file = {'midi_file': open('my_midi.mid', 'rb')}
    response = requests.post(http_url, files=file)

    if response.status_code == 200:
        print("MIDI file sent successfully!")
    else:
        print("Failed to send MIDI file. Status code:", response.status_code)

#########################################################################################################

# Function to handle the received WebSocket message
async def receive_messages(websocket):
    global auto_id, token, recording
    try:
        while True:
            raw_message = await websocket.recv()
            if raw_message:
                message = json.loads(raw_message)
                print(message)
                if message["type"] == "note":

                    msg_array = ast.literal_eval(message.get("note"))

                    for note in msg_array:
                        state = note[0][0]
                        key = note[0][1]
                        led_handler(int(key), int(state))

                elif message["type"] == "jwt":
                    token = message["jwt"]

                elif message["type"] == "rec":
                    recording = message["rec"]
                    if message["rec"] == "start":
                        recording == True
                        start_time = time.time()
                    if recording == "stop":
                        recording == False
                        start_time == 0
                        generate_midi_file()

                await asyncio.sleep(0.05)  # Add a small delay to avoid busy-wait
    except websockets.ConnectionClosed as e:
        # Handle a closed connection
        print("Connection closed:", e)

#########################################################################################################
# Verification to authorize websocket connection
        
def verification():
    global token, headers
    # Sending HTTP request to authorize websocket connection
    message = {'hardwareId': ID}
    response = requests.get(http_url, params = message, verify=False)

    # if not verified
    if response.status_code != 200:
        print("No authorization")
        return False
    else:
        # if verified, save token and establish websocket connection
        print("Websocket connection authorized")
        json_object_returned = response.json()
        token = json_object_returned.get("token")
        headers = [('Authorization', 'Bearer ' + token)]
        print("Got the token: ", token)##
        return True
            
#########################################################################################################

async def main():
    global midi_input, midi_notes, notes_in_progress, connected, headers, token
    setup()

    while True:
        authorization = verification()
        if authorization != True:
            print("No authorization")
        else:
            async with websockets.connect(server_url, ssl=ssl_context, extra_headers = headers) as websocket:
                print("Connected to Server")
                # Create a task to receive messages
                recv_task = asyncio.ensure_future(receive_messages(websocket))

                while True:
                    # check if midi device still connected
                    device_count = pygame.midi.get_count()
                    if device_count == 0:
                        print("MIDI device not found.")
                        continue

                    #listen to midi port for new events
                    midi_event = midi_input.read(20)

                    # if midi_input.poll(): ----- see this
                    #     print(midi_event) ##
                        # send that message back
                    if len(midi_event) != 0:
                        message = {"token": token, "note": str(midi_event)}
                        await websocket.send(json.dumps(message))
                        # lighting up the led on my end
                        msg_array = ast.literal_eval(message.get("note"))
                        for note in msg_array:
                            state = note[0][0]
                            key = note[0][1]
                            led_handler2(int(key), int(state))
                            if recording == "true":
                                if state == 144:
                                    # note pressed
                                    # save time and key
                                    notes_in_progress.append((int(key), note[1] - start_time))
                                    
                                elif state == 128:
                                    # note release
                                    # save duration
                                    for i, (note, time) in enumerate(notes_in_progress):
                                        if note == int(key):
                                            duration = time - note[1]
                                            midi_notes.append((int(key), note[1], duration))
                    await asyncio.sleep(0.05)

                    if websocket.closed:
                        print ("Websocket connection closed. Trying to reconnect ...")
                        pixels.fill((0,0,0))
                        break
        
                
        await asyncio.sleep(0.01)  # Add a small delay before reconnecting
        pixels.fill((0,0,0))

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
