import requests
import json

# Ollama API endpoint (assuming you're running Ollama locally or using an API endpoint)
OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Adjust URL if necessary

headers = {
    "Content-Type": "application/json"
}

# Prepare the request payload for the supachai/llama-3-typhoon-v1.5 model
payload = {
    "model": "supachai/llama-3-typhoon-v1.5",  # Use the pulled model name here
    "prompt": "รุ้งมีกี่สี",  # Adjust prompt as needed
    "stream": False
}

# Send the POST request to the Ollama API
response = requests.post(OLLAMA_API_URL, headers=headers, data=json.dumps(payload))

# Check if the request was successful
if response.status_code == 200:
    # Parse the response JSON
    response_data = response.text

    # Extract the decoded text from the response (assuming "response" key contains it)
    data = json.loads(response_data)
    decoded_text = data.get("response", "No response found.")

    # Print the decoded text
    print("Decoded text:", decoded_text)
else:
    # Handle errors
    print(f"Failed to get a response: {response.status_code}, {response.text}")