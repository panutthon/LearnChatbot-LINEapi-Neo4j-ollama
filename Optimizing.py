import requests


def get_ollama_response(prompt, history_chat):
    url = "http://localhost:11434/api/generate"  # Change this if needed
    headers = {
        "Content-Type": "application/json",
    }
   
    # Combine prompt with chat history
    history = "\n".join(history_chat)  # Join the history into a single string
    full_prompt = f"{history}\nUser: {prompt}\nBot: "  # Format the prompt


    payload = {
        "model": "supachai/llama-3-typhoon-v1.5",  # Assuming "supachai/llama-3-typhoon-v1.5" is the correct model name in Ollama
        "prompt": full_prompt + "คำตอบ หรือ response ไม่เกิน 20 คำ และเป็นภาษาไทยเท่านั้น",
        "stream": False,
        "options":{"num_predict": 100, "num_ctx": 1024, "temperature": 0.8,}
    }


    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("response", "No response from the model.")
    except requests.RequestException as e:
        return f"Error: {e}"


def chat():
    print("Welcome to the Ollama chatbot! Type 'bye' to exit.")
    history_chat = []  # Initialize chat history
   
    while True:
        user_input = input("You: ")
       
        if user_input.lower() in ['bye', 'exit']:
            print("Bot: Goodbye! Have a great day!")
            break
       
        history_chat.append(f"User: {user_input}")  # Add user input to history
        response = get_ollama_response(user_input, history_chat)
        print("Bot:", response)
       
        history_chat.append(f"Bot: {response}")  # Add bot response to history


if __name__ == "__main__":
    chat()


