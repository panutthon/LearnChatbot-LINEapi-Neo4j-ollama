import requests

# Dictionary to store the user's previous inputs or information
user_memory = {}

def get_ollama_response(prompt):
    url = "http://localhost:11434/api/generate"  # Change this if needed
    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "model": "supachai/llama-3-typhoon-v1.5",  # Assuming "tinyllama" is the correct model name in Ollama
        "prompt": prompt + " ตอบไม่เกิน 10 คำและเป็นภาษาไทยเท่านั้น",
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("response", "No response from the model.")
    except requests.RequestException as e:
        return f"Error: {e}"

def chat():
    print("Welcome to the Ollama chatbot! Type 'bye' to exit.")
    user_name = None

    while True:
        user_input = input("You: ")
        
        # Check for exit command
        if user_input.lower() in ['bye', 'exit']:
            print("Bot: Goodbye! Have a great day!")
            break

        # Check if the user is asking for their name
        if "ชื่ออะไร" in user_input and user_memory.get('name'):
            print(f"Bot: คุณชื่อ {user_memory['name']}")
            continue

        # Check if the user mentions their name
        if "ชื่อ" in user_input and "อะไร" not in user_input:
            # Extract the name from the input
            user_name = user_input.split("ชื่อ")[-1].strip()
            user_memory['name'] = user_name  # Store the name in memory
            print(f"Bot: สวัสดี {user_name} ยินดีที่ได้รู้จัก!")
            continue
        
        # Use the stored name in responses if available
        if user_memory.get('name'):
            user_input = f"{user_memory['name']} ถามว่า {user_input}"
        
        # Get response from Ollama
        response = get_ollama_response(user_input)
        print("Bot:", response)

if __name__ == "__main__":
    chat()
