# 🍳 Emoji Kitchen

> Mix two emojis. Cook one delicious mashup.

A Django-powered emoji combiner. Pick any two emojis, watch them sizzle together, then download or copy your one-of-a-kind sticker.

## Quick Start

```bash
# 1. Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations
python manage.py migrate

# 4. Run the dev server
python manage.py runserver

# 5. Open http://127.0.0.1:8000
```

## Project Structure

```
emoji_kitchen_project/
├── manage.py
├── requirements.txt
├── emoji_kitchen/          # Django project config
│   ├── settings.py
│   └── urls.py
└── kitchen/                # Main app
    ├── views.py            # Home + API views
    ├── models.py           # FAQ & BlogPost models
    ├── urls.py
    ├── templates/kitchen/
    │   └── home.html       # Full single-page template
    └── static/kitchen/
        ├── css/style.css   # All styling (no frameworks)
        └── js/main.js      # Emoji picker + combo logic
```

## How It Works

1. **Emoji Picker** — Custom JavaScript modal with 8 categories and search
2. **Combo Lookup** — Django API returns candidate Google Emoji Kitchen URLs; JS tries each until one loads
3. **Download** — Proxied through Django (`/api/download/`) to bypass CORS
4. **Copy** — Fetched via proxy and written to clipboard with the Clipboard API

Mashup artwork courtesy of [Google Emoji Kitchen](https://blog.google/products/android/emoji-kitchen-new-mashups-mixing-experience/).
