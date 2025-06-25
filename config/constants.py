import os.path

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSETS_DIR = os.path.join(APP_DIR, 'assets')
FONTS_DIR = os.path.join(ASSETS_DIR, 'fonts')
DATA_DIR = os.path.join(APP_DIR, 'data')
CONFIG_DIR = os.path.join(APP_DIR, 'config')

FALLBACK_STORIES = [
    {
    "title": "The Reflection",
    "story": "The old woman insisted her mirror was evil. \"It shows things not there,\" she'd croak. Her niece, visiting after years, scoffed, polishing the ornate frame. As she admired her reflection, a gaunt, smiling face appeared over her shoulder in the glass. The niece froze. It wasn't the old woman. She turned slowly. The room behind her was empty."
    },
    {
    "title": "The Lullaby",
    "story": "A young father recorded his baby daughter's first words, whispering sweet encouragement. Later, reviewing the clip, he heard her tiny voice, clear as day, finishing the lullaby he'd been singing. But he'd stopped singing halfway through, moments before she spoke."
    },
    {
    "title": "The Last Light",
    "story": "The power died, plunging the apartment into darkness. My phone, at 1%, was my only light. I navigated to the bedroom, the beam dancing across the walls. Then, a second light flickered on from the far corner of the room, held by someone, or something, I couldn't quite see."
    },
    {
    "title": "The Persistent Knock",
    "story": "I heard it last night, three sharp knocks on my apartment door. No one was there. This morning, I found a small, hand-carved wooden bird on my doormat. It had three tiny, raised bumps on its head, perfectly matching the rhythm of the knocks."
    },
    {
    "title": "The Static Friend",
    "story": "My old radio only picks up static now. But lately, when I turn it on, I hear faint whispers within the white noise. Yesterday, amidst the crackle, I distinctly heard my name, followed by a child's giggle right beside my ear. The radio was across the room."
    },
    {
    "title": "The Wrong Reflection",
    "story": "I was practicing dance moves in front of my full-length mirror. My reflection moved perfectly in sync. Then, I stopped. My reflection didn't. It just kept dancing, eyes wide and unblinking, a slow, terrifying smile spreading across its face."
    },
    {
    "title": "The Last Message",
    "story": "My grandfather's old flip phone rang. It was his number, but he died last year. Hesitantly, I answered. All I heard was heavy breathing, then a garbled voice whisper, \"They're still here,\" before the line went dead."
    },
    {
    "title": "The Unseen Guest",
    "story": "I live alone. So when I woke up this morning to find a second, perfectly placed toothbrush in the holder next to mine, a fresh, unused bar of soap in the shower, and the distinct scent of a perfume I don't own lingering in the air, I knew I wasn't alone anymore."
    },
    {
        "title": "The Whispering Walls",
        "story": "Every night, the old house whispers my name. I dismissed it as wind, then pipes, but last night, it sounded like a dozen voices, all my own, echoing from behind the wallpaper. I pressed my ear against it, and they all screamed."
    },
    {
        "title": "The Glitch in the Photo",
        "story": "I took a selfie, smiling. Later, reviewing it, I noticed a distortion. My face was there, but my eyes were *different*, too wide, too black. And in the background, just visible, was a figure that definitely wasn't there when I took the shot."
    },
    {
        "title": "The Missing Step",
        "story": "Walking up my familiar stairs in the dark, I always count the steps. Sixteen. Last night, I counted fifteen, and my foot kept going. I caught myself just before falling into empty air where the sixteenth step should have been."
    },
    {
        "title": "The Child's Drawing",
        "story": "I found an old drawing tucked into a library book. A child's crude stick figures: a family holding hands. Below it, scrawled in shaky letters, 'Don't let the man in the hat in.' My reflection in the window showed a man in a hat standing directly behind me."
    },
    {
        "title": "The Wrong Call",
        "story": "My phone rang, displaying 'Mom.' I answered, 'Hey, Mom!' A voice replied, deep and gravelly, 'She's not here right now.' Then a click. My real mom called a second later, asking why *I* had just called *her*."
    },
    {
        "title": "The Shadow in the Frame",
        "story": "I inherited an antique mirror. It’s beautiful, ornate. But sometimes, in my peripheral vision, I catch a shadow moving *within* the glass itself, not a reflection. It’s always just a glimpse, like someone pacing behind the surface."
    },
    {
        "title": "The Basement Door",
        "story": "We moved into an old house with a locked basement door. The previous owners said they lost the key. One night, I heard a faint scratching from behind it. The next morning, the door was slightly ajar, a single, rusty key lying on the floor."
    },
    {
        "title": "The Static Broadcast",
        "story": "My car radio kept tuning to a station that was pure static. But then, a child's voice broke through, counting slowly. 'One... two... three...' It kept counting, getting clearer, until it reached 'ten,' and my engine sputtered and died."
    },
    {
        "title": "The Familiar Stranger",
        "story": "I saw her reflection in a shop window. A woman who looked *exactly* like me, same clothes, same hairstyle. We both stopped, staring. Then she smiled, but I hadn't. Her smile was too wide, too knowing."
    },
    {
        "title": "The Unplugged Device",
        "story": "I unplugged every smart device in my house after hearing strange noises at night. The next morning, my smart speaker, sitting dark and unplugged on the counter, suddenly lit up. A robotic voice said, 'Good morning. Did you sleep well?'"
    },
    {
        "title": "The Persistent Humming",
        "story": "There’s a low hum coming from beneath my bed, always. I’ve checked, nothing's there. Last night, the humming pulsed, and something cold brushed my ankle from under the covers. It hummed louder, like it was happy."
    },
    {
        "title": "The Open Window",
        "story": "I always lock my windows before bed. Always. So when I woke to a chill and found the bedroom window wide open, flapping curtains, I felt a knot of dread. On the sill, a single, wet footprint pointed *inward*."
    },
    {
        "title": "The Mimic",
        "story": "My cat, Mittens, loves to play. I tossed her toy, and she pounced. But then I heard a familiar 'meow' from behind me, and turned to see Mittens still curled up, asleep on the couch. The 'cat' in front of me slowly stood on two legs."
    },
    {
        "title": "The Forgotten Face",
        "story": "I was sketching faces from memory. My best friend, my mom, my dog. Then, without thinking, I drew a face I didn't recognize. It was gaunt, with huge, black eyes. As I finished, I felt cold breath on my neck, and a whisper, 'You forgot me?'"
    },
    {
        "title": "The Backyard Swing",
        "story": "The swing set in my backyard always moves a little in the wind. But this morning, every swing was twisted, ropes stretched taut, facing the house. And the smallest swing, the baby one, was slowly, deliberately rocking, back and forth, back and forth."
    }
]

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = os.path.join(CONFIG_DIR, 'client_secret.json')
YOUTUBE_TOKEN_FILE = os.path.join(CONFIG_DIR, 'yt_token.json')