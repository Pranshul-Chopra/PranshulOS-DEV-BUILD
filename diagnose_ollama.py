"""
Diagnostic script to check Ollama connection and model availability.
Run this to verify Ollama is running and accessible.
"""
import requests
import json
import sys

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_HOST = "http://127.0.0.1:11434"
MODEL = "Qwen3:latest"

def test_ollama_connection():
    """Test if Ollama is running and accessible."""
    print("1. Testing Ollama connection...")
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if resp.status_code == 200:
            print("   ✓ Ollama is running!")
            return True
        else:
            print(f"   ✗ Ollama returned status {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ✗ Cannot connect to Ollama at http://localhost:11434")
        print("   → Make sure Ollama is running: `ollama serve`")
        return False
    except requests.exceptions.Timeout:
        print("   ✗ Ollama connection timed out")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def list_available_models():
    """List all available models in Ollama."""
    print("\n2. Checking available models...")
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            if models:
                print("   Available models:")
                for model in models:
                    name = model.get("name", "unknown")
                    size = model.get("size", 0)
                    size_gb = size / 1e9
                    print(f"     • {name} ({size_gb:.1f} GB)")
                return models
            else:
                print("   ✗ No models found. Pull a model first: `ollama pull qwen3:3b`")
                return []
        else:
            print(f"   ✗ Failed to get models (status {resp.status_code})")
            return []
    except Exception as e:
        print(f"   ✗ Error listing models: {e}")
        return []

def check_model_exists():
    """Check if the configured model (qwen3) exists."""
    print(f"\n3. Checking for model '{MODEL}'...")
    try:
        models = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5).json().get("models", [])
        model_names = [m.get("name", "") for m in models]
        
        if any(MODEL in name for name in model_names):
            print(f"   ✓ Model '{MODEL}' is available!")
            return True
        else:
            print(f"   ✗ Model '{MODEL}' not found.")
            print(f"   → Run: ollama pull {MODEL}")
            return False
    except Exception as e:
        print(f"   ✗ Error checking model: {e}")
        return False

def test_chat_endpoint():
    """Test if the chat endpoint is working."""
    print(f"\n4. Testing chat endpoint...")
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "say 'hello' in one word"}],
                "stream": False
            },
            timeout=60
        )
        if resp.status_code == 200:
            print("   ✓ Chat endpoint is working!")
            data = resp.json()
            reply = data.get("message", {}).get("content", "")
            print(f"   → Model response: {reply[:100]}")
            return True
        else:
            print(f"   ✗ Chat endpoint returned status {resp.status_code}")
            print(f"   → Response: {resp.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        print("   ✗ Chat request timed out (Ollama might be loading the model)")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def test_streaming():
    """Test streaming from the chat endpoint."""
    print(f"\n5. Testing streaming...")
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "say hello"}],
                "stream": True
            },
            stream=True,
            timeout=60
        )
        if resp.status_code == 200:
            print("   ✓ Streaming is working!")
            tokens = 0
            for line in resp.iter_lines():
                if line:
                    tokens += 1
            print(f"   → Received {tokens} tokens")
            return True
        else:
            print(f"   ✗ Streaming returned status {resp.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Streaming error: {e}")
        return False

def test_flask_endpoint():
    """Test the Flask streaming endpoint."""
    print(f"\n6. Testing Flask app at http://localhost:5000...")
    try:
        resp = requests.get("http://localhost:5000/", timeout=5)
        if resp.status_code == 200:
            print("   ✓ Flask server is running!")
            return True
        else:
            print(f"   ✗ Flask returned status {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ✗ Cannot connect to Flask server at http://localhost:5000")
        print("   → Is the app running? Use: Launch PranshulOS.bat")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("PRANSHULOS OLLAMA DIAGNOSTICS")
    print("=" * 60)
    
    results = {}
    results["ollama"] = test_ollama_connection()
    
    if results["ollama"]:
        results["models"] = check_model_exists()
        results["chat"] = test_chat_endpoint()
        if results["chat"]:
            results["streaming"] = test_streaming()
    
    results["flask"] = test_flask_endpoint()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    
    all_pass = all(results.values())
    
    if results.get("ollama"):
        print("✓ Ollama is running")
    else:
        print("✗ Ollama is NOT running")
        print("  → Start Ollama: ollama serve")
    
    if results.get("models"):
        print(f"✓ Model '{MODEL}' is available")
    else:
        print(f"✗ Model '{MODEL}' is NOT available")
        print(f"  → Pull it: ollama pull {MODEL}")
    
    if results.get("chat"):
        print("✓ Chat endpoint is working")
    else:
        print("✗ Chat endpoint is failing")
    
    if results.get("streaming"):
        print("✓ Streaming is working")
    else:
        print("✗ Streaming is failing")
    
    if results.get("flask"):
        print("✓ Flask server is running")
    else:
        print("✗ Flask server is NOT running")
    
    print("=" * 60)
    
    if all_pass:
        print("✓ Everything looks good! Your app should work.")
        return 0
    else:
        print("✗ Some issues found. See above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
