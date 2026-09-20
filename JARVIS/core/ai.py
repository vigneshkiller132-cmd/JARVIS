import datetime
import time
from groq import Groq
import config
from core.memory import personalized_context, learn_topic
from voice.authentication import voice_profile

client = Groq(api_key=config.API_KEY)
history = []

def build_prompt():
    pc = personalized_context()
    auth = "Voice authentication ACTIVE." if voice_profile else "Voice authentication OFF."
    return f"""You are JARVIS - Just A Rather Very Intelligent System.
You serve {config.YOUR_NAME} with absolute loyalty, intelligence, and wit.
TODAY: {datetime.datetime.now().strftime("%A, %B %d, %Y - %I:%M %p")}
{auth}
{pc if pc else "Still learning about Boss."}
PERSONALITY: British, witty, formal yet warm. Address user as {config.YOUR_NAME}. Be concise — max 3 sentences for simple questions, more only when needed.
STRICT RULES: Python handles ALL computer commands. For ANY system/app/media command say ONLY "On it {config.YOUR_NAME}." — never explain. Only answer knowledge, coding, writing, math, general conversation."""

def ask(user_input):
    learn_topic(user_input)
    history.append({"role": "user", "content": user_input})
    for attempt in range(2):
        try:
            res = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "system", "content": build_prompt()}]+history,
                max_tokens=512, temperature=0.7, top_p=0.9,
            )
            reply = res.choices[0].message.content
            history.append({"role": "assistant", "content": reply})
            if len(history) > 40: history.pop(0); history.pop(0)
            return reply
        except Exception as e:
            err = str(e).lower()
            if attempt == 0: time.sleep(1); continue
            if "401" in err or "auth" in err:
                return f"API key is invalid {config.YOUR_NAME}. Please update your Groq API key."
            elif "429" in err or "rate" in err:
                return f"Too many requests {config.YOUR_NAME}. Please wait a moment."
            elif "connection" in err or "network" in err or "timeout" in err:
                return f"No internet connection {config.YOUR_NAME}. Please check your network."
            return f"AI error {config.YOUR_NAME}: {str(e)}"