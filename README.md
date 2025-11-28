# LinkedIn Carousel Image Generator

Flask service that generates LinkedIn carousel images from JSON data using custom templates.

## Features

- Accepts JSON with slide data from n8n workflow
- Uses template images (1.png, 2.png, 3.png)
- Generates 1200x1500px images optimized for LinkedIn
- Automatically wraps and centers text
- Returns downloadable URLs
- Ready for Railway deployment

## Quick Start

### Deploy to Railway

1. Go to [Railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select this repository
4. Railway auto-detects and deploys
5. Get your URL: `https://your-app.railway.app`

### API Usage

**POST** `/generate-carousel`

```bash
curl -X POST https://your-app.railway.app/generate-carousel \
  -H "Content-Type: application/json" \
  -d '{
    "slides": [
      {
        "slideNumber": 1,
        "type": "cover",
        "mainText": "Your headline here",
        "subText": "Supporting text"
      }
    ]
  }'
```

**Response:**
```json
{
  "success": true,
  "images": [
    {
      "slideNumber": 1,
      "url": "https://your-app.railway.app/download/image_20241128_120000_1.png",
      "filename": "image_20241128_120000_1.png"
    }
  ],
  "count": 1
}
```

## Template Requirements

Place in `templates/` directory:
- **1.png** - First slide (cover)
- **2.png** - Middle slides (content)
- **3.png** - Last slide (CTA)

All templates: **1200x1500px PNG**

## n8n Integration

**HTTP Request Node:**
- Method: POST
- URL: `https://your-app.railway.app/generate-carousel`
- Body: JSON
- Content: `{ "slides": {{ $json.slides }} }`

**Access URLs:**
```javascript
{{ $json.images[0].url }}
{{ $json.images[1].url }}
```

## Local Development

```bash
pip install -r requirements.txt
python app.py
```

## Text Styling

- Main Text: 60px, black, bold
- Sub Text: 36px, dark gray
- Alignment: Centered horizontally and vertically
- Padding: 100px from edges
- Auto-wrapping enabled

## Endpoints

- `POST /generate-carousel` - Generate images
- `GET /download/<filename>` - Download image
- `GET /health` - Health check
- `GET /` - API documentation

## License

MIT
