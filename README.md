# 🎬 Faceless — Create Viral Videos on Autopilot
### Open-Source Alternative to FacelessReels.com

A full-stack web platform that generates faceless videos with AI, posts them automatically to **YouTube Shorts, TikTok, and Instagram Reels** — while you sleep. Powered by **Google Gemini Pro**.

---

## 🆚 How We Compare to FacelessReels

| Feature | FacelessReels | **Faceless (This)** |
|---------|:---:|:---:|
| AI Script Generation | ✅ | ✅ Gemini Pro |
| Auto Video Creation | ✅ | ✅ MoviePy + Pillow |
| YouTube Shorts | ✅ | ✅ |
| TikTok Posting | ✅ | ✅ |
| Instagram Reels | ✅ | ✅ |
| Multiple Art Styles | ✅ | ✅ 8 styles |
| Multiple Niches | ✅ | ✅ 9 niches |
| Series / Auto-post | ✅ | ✅ |
| Web Dashboard | ✅ | ✅ |
| Analytics | ✅ | ✅ |
| Trending Discovery | ❌ | ✅ AI-powered |
| Self-Hosted | ❌ | ✅ Own your data |
| Open Source | ❌ | ✅ |
| Monthly Cost | $29-99/mo | **Free** |

---

## 🚀 Features

- **✨ One-Click Video Creation** — Pick niche, art style, and go. AI handles everything.
- **📱 Shorts/Reels Format** — 9:16 vertical video optimized for all platforms
- **🎨 8 Art Styles** — Cartoon, Anime, Watercolor, Neon, Retro, Minimalist, Pixel, Storybook
- **📺 9 Niches** — Kids Cartoon, Scary Stories, History, Motivation, Science, Mythology, Finance, Animals, Custom
- **🔊 8 AI Voices** — Natural-sounding narration via Edge-TTS
- **📅 Series & Auto-posting** — Create series, set schedule, auto-post daily
- **🔗 Multi-Platform** — YouTube, TikTok, Instagram in one click
- **📊 Analytics Dashboard** — Track views, likes, engagement
- **🔥 Trending Finder** — AI discovers viral topics in your niche
- **🔄 Real-time Progress** — WebSocket-powered generation tracking
- **🛡️ COPPA Compliant** — Built-in child safety for kids content

---

## ⚡ Quick Start (3 Steps)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your Gemini API key
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# 3. Launch the platform
python run.py
# Open http://localhost:8000
```

---

## 📦 Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
GEMINI_API_KEY=your_gemini_pro_api_key
YOUTUBE_API_KEY=your_youtube_data_api_key    # optional, for analytics
YOUTUBE_CHANNEL_ID=your_channel_id           # optional
YOUTUBE_CLIENT_ID=your_oauth_client_id       # optional, for auto-upload
YOUTUBE_CLIENT_SECRET=your_oauth_client_secret
```

> **Minimum requirement**: Just `GEMINI_API_KEY` to start creating videos!

### 3. Launch

```bash
# Web Dashboard (recommended)
python run.py
# → Open http://localhost:8000

# Or use CLI mode
python main.py plan
python main.py full 1
```

### 4. YouTube OAuth Setup (for auto-uploading)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **YouTube Data API v3**
3. Create **OAuth 2.0 credentials** (Desktop app type)
4. Copy `client_id` and `client_secret` to `.env`

---

## 🖥️ Web Dashboard

Launch with `python run.py` and open http://localhost:8000

### Pages:
- **Dashboard** — Stats overview, quick actions, recent videos
- **Create Video** — 3-step wizard: Niche → Art Style → Generate
- **My Series** — Create auto-posting series with schedules
- **My Videos** — View, download, delete generated videos
- **Schedule** — Calendar of upcoming auto-posts
- **Platforms** — Connect YouTube, TikTok, Instagram
- **Trending** — AI-powered viral content discovery
- **Analytics** — Performance tracking and insights

### API Documentation
Visit http://localhost:8000/docs for full Swagger/OpenAPI documentation.

---

## 🎮 Usage

### Quick Commands

```bash
# View status and help
python main.py

# Generate 30-day content plan
python main.py plan

# Generate script for Day 1
python main.py script 1

# Create video for Day 1
python main.py video 1

# Upload video for Day 1
python main.py upload 1

# Full pipeline (script → video → upload) for Day 1
python main.py full 1

# Batch process Days 1-7
python main.py batch 1 7

# Analyze your channel
python main.py analytics

# Find trending kids content
python main.py trending

# List available templates
python main.py templates

# Start auto-scheduler (runs daily)
python main.py scheduler

# Check pipeline status
python main.py status
```

### Typical Workflow

```bash
# Step 1: Generate your 30-day plan (or use the pre-built one)
python main.py plan

# Step 2: Generate scripts for the first week
python main.py batch 1 7

# Step 3: Or go fully automated
python main.py scheduler
```

---

## 📁 Project Structure

```
faceless/
├── run.py                     # 🚀 Start web server (recommended)
├── app.py                     # FastAPI web application
├── main.py                    # CLI orchestrator (alternative)
├── requirements.txt
├── .env.example
├── agent/
│   ├── config.py              # Configuration & constants
│   ├── database.py            # SQLAlchemy models (User, Series, Video, Platform)
│   ├── auth.py                # JWT authentication
│   ├── script_generator.py    # Gemini Pro script generation
│   ├── audio_generator.py     # Edge-TTS narration
│   ├── video_generator.py     # MoviePy video creation
│   ├── styles.py              # 8 art styles, 9 niches, voices, music
│   ├── platforms.py           # Multi-platform posting (YT, TikTok, IG)
│   ├── youtube_uploader.py    # YouTube OAuth upload & scheduling
│   ├── analytics.py           # Channel analytics
│   ├── trending.py            # Trending content discovery
│   └── templates.py           # Video templates
├── static/
│   └── index.html             # Web dashboard (Tailwind CSS)
├── output/
│   ├── scripts/
│   │   └── 30_day_plan.json   # Pre-built 30-day content plan
│   ├── videos/
│   ├── audio/
│   └── thumbnails/
└── assets/
```

---

## 📅 Pre-Built 30-Day Content Plan

The plan includes a diverse mix of categories:

| Day | Topic | Category |
|-----|-------|----------|
| 1 | The Little Elephant Who Learned to Share | Moral Stories |
| 2 | ABC Song with Funny Animals | ABC & 123 Learning |
| 3 | 5 Amazing Facts About Dinosaurs | Fun Facts for Kids |
| 4 | Twinkle Twinkle Little Star - Animated | Nursery Rhymes |
| 5 | The Brave Little Bunny | Bedtime Stories |
| 6 | Colors of the Rainbow | ABC & 123 Learning |
| 7 | Super Cat Saves the Day! | Superhero Stories |
| ... | ... | ... |
| 25 | Mother's Day Special | Holiday Specials |
| 30 | Thank You Celebration Compilation | Holiday Specials |

Full plan in `output/scripts/30_day_plan.json`

---

## 🎨 Art Styles

| Style | Look | Best For |
|-------|------|----------|
| **Cartoon** | Bright, bold with thick outlines | Kids, Comedy |
| **Anime** | Japanese anime-inspired vibrant | Stories, Fantasy |
| **Watercolor** | Soft painting aesthetic | Nature, Calm |
| **Neon** | Dark background, glowing elements | Scary, Mystery |
| **Retro** | Vintage pop with halftone | History, Facts |
| **Minimalist** | Clean modern design | Motivation, Finance |
| **Pixel** | 8-bit retro gaming | Gaming, Nostalgia |
| **Storybook** | Children's book illustration | Kids, Fairy Tales |

## 📺 Supported Niches

Kids Cartoon, Scary Stories, History, Motivation, Science & Space,
Mythology, Finance & Money, Animals & Nature, Custom (define your own)

## 🔊 Available Voices

| Voice | Accent | Best For |
|-------|--------|----------|
| Ana | US (young female) | Kids content |
| Jenny | US (female) | General |
| Guy | US (male) | Narration |
| Sonia | British (female) | Stories |
| Ryan | British (male) | Documentary |
| Natasha | Australian (female) | Fun content |
| Neerja | Indian (female) | Educational |
| Aria | US (female) | Professional |

---

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | **Required** — Google Gemini Pro API key |
| `YOUTUBE_API_KEY` | — | YouTube Data API for analytics/trending |
| `TTS_VOICE` | `en-US-AnaNeural` | Default narration voice |
| `VIDEO_FPS` | `24` | Frames per second |
| `UPLOAD_TIME` | `10:00` | Daily auto-post time |
| `UPLOAD_TIMEZONE` | `Asia/Kolkata` | Timezone for scheduling |

---

## 🖥️ CLI Mode (Alternative)

The original CLI interface is still available:

```bash
python main.py                    # Show help & status
python main.py plan              # Generate 30-day plan
python main.py script 1          # Generate Day 1 script
python main.py video 1           # Create Day 1 video
python main.py full 1            # Full pipeline Day 1
python main.py batch 1 7         # Batch Days 1-7
python main.py analytics         # Channel analytics
python main.py trending          # Trending content
python main.py scheduler         # Daily auto-runner
```

---

## 🛡️ Safety

- All kids content is **COPPA compliant** (`selfDeclaredMadeForKids = true`)
- Scripts prompted to avoid violence, scary content for kids niche
- `safeSearch: strict` for all YouTube API searches
- JWT auth with bcrypt password hashing
- No credentials stored in frontend

---

## 📊 Analytics

The analytics dashboard tracks:
- Total videos created & posted
- Views, likes, engagement rates across platforms
- Best/worst performing content
- AI-powered recommendations for growth
- Trending topic discovery with actionable ideas

---

## 🗺️ Roadmap

- [ ] AI-generated images (Gemini Vision / DALL-E)
- [ ] Background music library
- [ ] Custom font uploads
- [ ] Team collaboration
- [ ] Webhook integrations
- [ ] Mobile app
- [ ] A/B testing thumbnails

---

## ⚡ Quick Start

```bash
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key" > .env
python run.py
# → Open http://localhost:8000, create account, start making videos!
```

---

## License

MIT
