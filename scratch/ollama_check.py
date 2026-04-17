import requests

try:
    response = requests.get("http://localhost:11434/api/tags")
    if response.status_code == 200:
        print("Ollama is running.")
        models = [m['name'] for m in response.json().get('models', [])]
        print(f"Models: {models}")
        if 'llama3:latest' in models or 'llama3' in models:
            print("llama3 is available.")
        else:
            print("llama3 is MISSING.")
    else:
        print(f"Ollama returned status code {response.status_code}")
except Exception as e:
    print(f"Ollama is likely NOT running: {e}")
