import os.path

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSETS_DIR = os.path.join(APP_DIR, 'assets')
FONTS_DIR = os.path.join(ASSETS_DIR, 'fonts')
DATA_DIR = os.path.join(APP_DIR, 'data')
CONFIG_DIR = os.path.join(APP_DIR, 'config')

FALLBACK_QUOTES = [
    "Your journey isn't just about reaching the destination; it's about who you become along the way. Embrace every challenge, celebrate every small victory, and never stop growing. The path you carve is as significant as the dream you chase.",
    "The world doesn't need perfection, it needs your authentic self. Unleash your unique talents, embrace your quirks, and let your passion be your loudest voice. When you shine genuinely, you inspire others to do the same.",
    "Don't let yesterday's shadows dim today's light. Every moment is a fresh opportunity to pivot, to learn, and to build something extraordinary. Focus forward, trust your grit, and watch as new possibilities unfold before you.",
    "True strength isn't about never falling, but about rising with courage every single time you stumble. Each setback is a setup for a stronger comeback. Dust yourself off, learn the lesson, and keep pushing toward your dreams.",
    "Your potential is an untapped ocean, vast and full of wonders. Dive deep, explore your capabilities, and don't be afraid to make waves. The greatest adventures lie just beyond the shore of your comfort zone.",
    "Success isn't found in a single, massive leap, but in the consistent, courageous steps you take every single day. Keep showing up, keep learning, and keep believing in the power of your persistent effort to build the life you envision.",
    "Your ideas are sparks, capable of igniting incredible change.Don't let fear extinguish them. Nurture your creativity, speak your truth, and have the courage to bring your unique vision to life. The world is waiting for what you have to offer.",
    "The most valuable investment you'll ever make is in yourself. Pour into your knowledge, your skills, and your well-being. Every moment spent on self-improvement is a building block for a stronger, more capable, and ultimately happier you.",
    "Challenges aren't meant to break you; they're designed to reveal your resilience. When faced with a hurdle, remember your inner strength.You possess the wisdom to navigate, the power to overcome, and the grit to emerge even more formidable.",
    "Don't just dream of a better future; actively construct it, brick by imaginative brick. Your actions today are the foundation of your tomorrow. Be intentional, be bold, and build a reality that truly reflects your highest aspirations."
]

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = os.path.join(CONFIG_DIR, 'client_secret.json')
YOUTUBE_TOKEN_FILE = os.path.join(CONFIG_DIR, 'yt_token.json')