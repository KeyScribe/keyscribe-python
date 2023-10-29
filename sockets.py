import RPi.GPIO as GPIO
import asyncio
import websockets

server_url = "wss://10.136.191.190:8001/ws"

# Function to handle WebSocket connections
async def client_send():
    # Initialize GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Push Button connected to GPIO 4
    GPIO.setup(2, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Push Button connected to GPIO 4
    GPIO.setup(3, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Push Button connected to GPIO 4
    GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Push Button connected to GPIO 4
    try:
        async with websockets.connect(server_url) as websocket:
            print("Connected to Server")
            while True:
                # Check the state of the push button
                if GPIO.input(4) == GPIO.LOW:
                    # Button is pressed, send a message to the client
                    await websocket.send("PRESSED GPIO 4")
                elif GPIO.input(27) == GPIO.LOW:
                    await websocket.send("PRESSED GPIO 27")
                elif GPIO.input(2) == GPIO.LOW:
                    await websocket.send("PRESSED GPIO 2")
                elif GPIO.input(3) == GPIO.LOW:
                    await websocket.send("PRESSED GPIO 3")
                await asyncio.sleep(0.1)  # Small delay to reduce CPU usage
    except Exception as e:
        print(f"Error: {e}")

        
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(client_send())
