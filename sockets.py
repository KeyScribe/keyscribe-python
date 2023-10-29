import RPi.GPIO as GPIO
import asyncio
import websockets
import ssl
import pathlib

server_url = "wss://192.168.137.1:8000/ws"

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

# Function to handle WebSocket connections
async def client_send():
    # Initialize GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Push Button connected to GPIO 4
    GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Push Button connected to GPIO 4
    GPIO.setup(9, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Push Button connected to GPIO 4
    GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Push Button connected to GPIO 4
    try:
        async with websockets.connect(server_url, ssl=ssl_context) as websocket:
            print("Connected to Server")
            while True:
                # Check the state of the push button
                if GPIO.input(4) == GPIO.LOW:
                    # Button is pressed, send a message to the client
                    await websocket.send("PRESSED GPIO 4")
                elif GPIO.input(27) == GPIO.LOW:
                    await websocket.send("PRESSED GPIO 27")
                elif GPIO.input(10) == GPIO.LOW:
                    await websocket.send("PRESSED GPIO 10")
                elif GPIO.input(9) == GPIO.LOW:
                    await websocket.send("PRESSED GPIO 9")
                await asyncio.sleep(0.1)  # Small delay to reduce CPU usage
    except Exception as e:
        print(f"Error: {e}")

        
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(client_send())