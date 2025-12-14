from google import genai

client = genai.Client(api_key="AIzaSyAwBX9tFcnUnj-CjBmVvBtzZMUJYgV2SD8")
chat = client.chats.create(model="gemini-2.5-flash")

# Optional: add system instruction
response = chat.send_message("You are a STIX validation expert. Validate this JSON versus the document.")
print(response.text)
