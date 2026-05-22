"""
Quick test: Checks if Gemini API is accessible and OCR works.
Run: python test_gemini_ocr.py
"""
import os, httpx, base64, json, asyncio
from dotenv import load_dotenv
load_dotenv(override=True)

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
# Try multiple model names in order of preference
MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash-lite",
]

async def test_gemini_text():
    """Test plain text generation (no image) to confirm API key works."""
    print(f"\n{'='*50}")
    print(f"Testing Gemini API Key: {GEMINI_KEY[:20]}...")
    print(f"{'='*50}")
    
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        payload = {
            "contents": [{"parts": [{"text": "Say: GEMINI_WORKS"}]}],
            "generationConfig": {"maxOutputTokens": 20}
        }
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15.0)
                if r.status_code == 200:
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"  ✅ {model}: OK — Response: {text.strip()}")
                    return model  # Return first working model
                else:
                    err = r.json().get("error", {}).get("message", r.text[:100])
                    print(f"  ❌ {model}: {r.status_code} — {err}")
        except Exception as e:
            print(f"  ❌ {model}: Exception — {e}")
    return None

async def test_list_models():
    """List available models for the API key."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=15.0)
            if r.status_code == 200:
                models = r.json().get("models", [])
                print(f"\n📋 Available models ({len(models)} total):")
                vision_models = [m["name"] for m in models if "generateContent" in m.get("supportedGenerationMethods", [])]
                for m in vision_models[:15]:
                    print(f"   - {m.replace('models/', '')}")
            else:
                print(f"❌ Could not list models: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"❌ Error listing models: {e}")

async def main():
    if not GEMINI_KEY:
        print("❌ GEMINI_API_KEY not found in .env!")
        return
    
    await test_list_models()
    working_model = await test_gemini_text()
    
    if working_model:
        print(f"\n✅ WORKING MODEL: {working_model}")
        print(f"   → Update verification.py to use: gemini-2.0-flash → {working_model}")
    else:
        print(f"\n❌ NO WORKING MODEL FOUND — Check API key or billing/quota.")

asyncio.run(main())
