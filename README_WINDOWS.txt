Vision AI v6.7.0 — Windows 10
================================

1. Unzip this folder (right-click → Extract All). Avoid paths with only spaces.
2. Install Python 3.10+ from https://www.python.org/downloads/
   - Check "Add Python to PATH"
3. Open Command Prompt in this folder:
     cd path\to\VISION_AI_v6.7.0
     python -m pip install -r requirements.txt
4. Copy .env.example to .env and add API keys (GOOGLE_API_KEY, etc.)
5. Start:
     python run.py
   or:
     python -m uvicorn main:app --host 127.0.0.1 --port 8080
6. Browser: http://127.0.0.1:8080

Touch gestures (phone / tablet browser or touch laptop):
- Swipe right from left edge → open menu
- Swipe left when menu open → close
- Double-tap logo → scroll chat to top

If Windows blocks the zip: Properties → Unblock → OK, then extract again.
