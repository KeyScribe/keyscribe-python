import json
import RPi.GPIO as GPIO
import asyncio
import websockets
import ssl
import pathlib
import time
import requests

ID = "12345678"
auto_id = ""
token = ""
headers = ""
connected = False
server_url = "wss://10.138.224.13:8000/ws"
http_url = "https://10.138.224.13:8000/authorize"


ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
#localhost_pem1 = pathlib.Path(__file__ + "/keys").with_name("cert.pem")
# localhost_pem2 = pathlib.Path(__file__).with_name("/keys/csr.pem")
# localhost_pem3 = pathlib.Path(__file__).with_name("/keys/key.pem")
ssl_context.load_verify_locations("keys/cert.pem")
# ssl_context.load_verify_locations(localhost_pem2)
# ssl_context.load_verify_locations(localhost_pem3)

# Provide the full paths to your certificate files here
# cert_file_path = "./keys/cert.pem"
# csr_file_path = "./keys/csr.pem"
# key_file_path = "./keys/key.pem"

# ssl_context.load_verify_locations(cert_file_path)
# ssl_context.load_verify_locations(csr_file_path)
# ssl_context.load_verify_locations(key_file_path)

#ssl_context.verify_mode = ssl.CERT_NONE  # No certificate verification
ssl_context.load_default_certs(ssl.Purpose.CLIENT_AUTH)
ssl_context.check_hostname = False  # Disable hostname verification

#[ green, red, yellow, blue]
BUTTON_PINS = [4, 27, 10, 9]
LED_PINS = [15, 14, 17, 18]
BUTTONS_NOTES = [48, 50, 52, 53]

# Pairing each button with an LED
button_led_pairs = {4: 15, 27: 14, 10: 17, 9: 18}
# Keeping track of which LED was press and when
start_time = {pin: 0 for pin in BUTTON_PINS}
#saving the duration for each key pressed to pass to the server
time_duration = {pin: 0 for pin in BUTTON_PINS}
#keeping track of which button state was changed, 0 -> not changed, 1 -> changed (rising or falling edge detected)
button_state = {pin: 0 for pin in BUTTON_PINS}

button_note = {48: 4, 50: 27, 52: 10, 53: 9}
note_button = {4: 48, 27: 50, 10: 52, 9: 53}

#########################################################################################################
# Interrupt handler function, marks the pin that the rising or falling edge was detected from
def button_pressed_callback(channel):
    global button_state
    #to announce change of button status
    button_state[channel] = 1

#########################################################################################################
# Initialize GPIO
def setup_gpio():
    global button_state
    
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    #LED pins  
    for pin in LED_PINS:
        GPIO.setup(pin, GPIO.OUT)

    #Push button pins
    for pin in BUTTON_PINS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Push Button connected to GPIO [PIN]
        #event for each pin, both falling and rising edge interrupt
        GPIO.add_event_detect(pin, GPIO.BOTH, callback=button_pressed_callback, bouncetime=1)

#########################################################################################################
# Handles the turning on and off of the LEDs
def light_up_led(pin, state):
    global time_duration, start_time

    if state == 0:
        start_time[pin] = time.time()
        GPIO.output(button_led_pairs[pin], GPIO.HIGH)
    elif state == 1 and start_time[pin] != 0:
        GPIO.output(button_led_pairs[pin], GPIO.LOW)
        time_duration[pin] = time.time() - start_time[pin]
        time.sleep(0.05)
        print(f"Duration for {button_led_pairs[pin]} is {time_duration[pin]}")

#########################################################################################################
# Function to handle the received WebSocket message
async def receive_messages(websocket):
    global auto_id, token
    try:
        button_message_sent = {pin: False for pin in BUTTON_PINS}

        while True:
            raw_message = await websocket.recv()
            if raw_message:
                message = json.loads(raw_message)
                #print("Received:", message)
                
                note = message.get("note")
                pin = button_note[int(note)]
                state = message.get("state")
                light_up_led(int(pin), int(state))

                if int(state) == 1 and not button_message_sent[int(pin)]:
                    message = {"token": token, "note": note, "state": "1", "start_time": start_time[int(pin)], "duration": time_duration[int(pin)]}
                    print(message)
                    await websocket.send(json.dumps(message))
                    start_time[int(pin)] = 0
                    button_message_sent[int(pin)] = True

                if int(state) == 0:
                    button_message_sent[int(pin)] = False
                    
                await asyncio.sleep(0.05)  # Add a small delay to avoid busy-wait
    except websockets.ConnectionClosed as e:
        # Handle a closed connection
        print("Connection closed:", e)
            
#########################################################################################################
# main loop
async def main():
    global start_time, time_duration, connected, headers, token
    setup_gpio()

    # Sending HTTP request to authorize websocket connection
    message = {'hardwareId': ID}
    response = requests.get(http_url, params = message, verify=False)

    #if not verified
    if response.status_code != 200:
        print("No authorization")
    #if verified, save token and establish websocket connection
    else:
        json_object_returned = response.json()
        print(json_object_returned)
        token = json_object_returned.get("token")
        headers = [('Authorization', 'Bearer ' + token)]
        print(headers)
        print("I got the token: ", token)
        async with websockets.connect(server_url, ssl=ssl_context, extra_headers = headers) as websocket:
            print("Connected to Server")
            # Create a task to receive messages
            recv_task = asyncio.ensure_future(receive_messages(websocket))

            while True:
                # Check the state of the push button, if changed (=1) handle it
                for button_pin, led_pin in button_led_pairs.items():
                    if button_state[button_pin] == 1:
                        if GPIO.input(button_pin) == GPIO.LOW:
                            # Button is pressed, send a message to the client
                            message = {"token": token, "note": str(note_button[button_pin]), "state": "0", "start_time": "-1", "duration": "-1"}
                            await websocket.send(json.dumps(message))
                        elif GPIO.input(button_pin) == GPIO.HIGH:
                            # Button is released, send a message to the client
                            message = {"token": token, "note": str(note_button[button_pin]), "state": "1", "start_time": "-1", "duration": "-1"}
                            print(message)
                            await websocket.send(json.dumps(message))
                        button_state[button_pin] = 0
                await asyncio.sleep(0.05)  # Add a small delay to avoid busy-wait

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

