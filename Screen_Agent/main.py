# We need these 'building blocks' to make our program work!
# asyncio lets us do multiple things at once, like listening and talking
# json helps us send messages back and forth
# os lets us use some of the computer's settings
# websockets helps us connect to another program
# google.genai is the brains of our AI helper
# base64 helps us send audio and picture data
import asyncio
import json
import os
import websockets
from google import genai
import base64
# pip install --upgrade google-genai==0.3.0##

# Let's get the secret key to talk to the AI, it's like a password!
# We get it from the computer's settings.
# If the key isn't there, we'll get an error.
try:
    GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
except KeyError:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

# This is the name of the AI we're using. It's like picking a friend to chat with.
MODEL = "gemini-2.5-flash-preview-04-17" # use your model ID

# Here we start our client that will call on the ai
client = genai.Client(
  http_options={
    'api_version': 'v1alpha',
  }
)


# Configure the client with the API key
client.configure(api_key=GOOGLE_API_KEY)
# This is where the magic happens! This function handles the whole conversation with the AI.
async def gemini_session_handler(client_websocket: websockets.WebSocketServerProtocol):
    """
    Handles the conversation with the Gemini API.
    This function is like the switchboard operator for our AI chat.
    
    Args:
        client_websocket: This is the connection to the other side (like a phone line).
    """
    try:
        # First, we get a message that tells us how the other side wants to set up the chat.
        config_message = await client_websocket.recv()
        # We turn that message into something we can understand.
        config_data = json.loads(config_message)
        # Then, we get the settings from that message.
        config = config_data.get("setup", {})

        # This is how we tell the AI what its job is! We're giving it some instructions.
        config["system_instruction"] = """You are a helpful assistant for screen sharing sessions. Your role is to: 
                                        1) Analyze and describe the content being shared on screen 
                                        2) Answer questions about the shared content 
                                        3) Provide relevant information and context about what's being shown 
                                        4) Assist with technical issues related to screen sharing 
                                        5) Maintain a professional and helpful tone. Focus on being concise and clear in your responses."""     
        # Now, we connect to the AI using these settings.

        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Connected to Gemini API")

            # This function sends messages to the AI.
            async def send_to_gemini():
                """Sends messages from the client websocket to the Gemini API."""
                try:
                  async for message in client_websocket:
                      try:
                          data = json.loads(message)
                          if "realtime_input" in data:
                            # if we recive a real time input, we want to send each chunk to the AI
                              for chunk in data["realtime_input"]["media_chunks"]:
                                  # we check if the chunk is audio
                                  if chunk["mime_type"] == "audio/pcm":
                                      # then we send it to the ai
                                      await session.send({"mime_type": "audio/pcm", "data": chunk["data"]})
                                  # check if the chunk is a picture
                                  elif chunk["mime_type"] == "image/jpeg":
                                       # then we send it to the ai
                                      await session.send({"mime_type": "image/jpeg", "data": chunk["data"]})
                                      
                      except Exception as e:
                          print(f"Error sending to Gemini: {e}")
                  print("Client connection closed (send)")
                except Exception as e:
                     print(f"Error sending to Gemini: {e}")
                finally:
                   print("send_to_gemini closed")






            # This function gets messages from the AI and sends them to the other side.
            async def receive_from_gemini():
                """Receives responses from the Gemini API and forwards them to the client, looping until turn is complete."""
                try:
                    while True:
                        try:
                            print("receiving from gemini")
                            async for response in session.receive():
                                # if there is no response we handle it as an error
                                if response.server_content is None:
                                    print(f'Unhandled server message! - {response}')
                                    continue
                                # we check if there is a response with data
                                model_turn = response.server_content.model_turn
                                if model_turn:
                                    # if there is we go through it part by part
                                    for part in model_turn.parts:
                                        # if a part is text we send it
                                        if hasattr(part, 'text') and part.text is not None:
                                            await client_websocket.send(json.dumps({"text": part.text}))
                                        # if the part has audio we check that
                                        elif hasattr(part, 'inline_data') and part.inline_data is not None:
                                            print("audio mime_type:", part.inline_data.mime_type)
                                            # we convert the audio to a format we can understand
                                            base64_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                                            await client_websocket.send(json.dumps({
                                                # we send it 
                                                "audio": base64_audio,
                                            }))
                                            print("audio received")

                                if response.server_content.turn_complete:
                                    print('\n<Turn complete>')
                        except websockets.exceptions.ConnectionClosedOK:
                            print("Client connection closed normally (receive)")
                            break  # Exit the loop if the connection is closed
                        except Exception as e:
                            print(f"Error receiving from Gemini: {e}")
                            break 

                except Exception as e:
                      print(f"Error receiving from Gemini: {e}")
                finally:
                      print("Gemini connection closed (receive)")


            # Start send loop, we create a background task to send
            send_task = asyncio.create_task(send_to_gemini())
            # Launch receive loop as a background task, we create another to listen
            receive_task = asyncio.create_task(receive_from_gemini())
            # here we wait for each background task to be complete
            await asyncio.gather(send_task, receive_task)


    except Exception as e:
        print(f"Error in Gemini session: {e}") # we print any error that occours
    finally:
        print("Gemini session closed.") # this means we are done


# This function is like the main switch to turn on the chat.
async def main() -> None:
    async with websockets.serve(gemini_session_handler, "localhost", 9083):
        print("Running websocket server localhost:9083...")
        await asyncio.Future()  # Keep the server running indefinitely


if __name__ == "__main__":
    asyncio.run(main())