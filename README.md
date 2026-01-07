# LinkedIn Carousel Image Generator

Flask service that generates LinkedIn carousel images from JSON data using custom templates.

## Features

* Accepts JSON with slide data from n8n workflow
* Uses template images (1.png, 2.png, 3.png)
* Generates 1200x1500px images optimized for LinkedIn
* Automatically wraps and centers text
* **NEW: Featured image support for cover slides (Template 1)**
* **NEW: Optimized text positioning for better LinkedIn preview display**
* Returns downloadable URLs or base64 encoded images
* Ready for Railway deployment

## Template Optimization

### Template 1 (Cover Slide)
- AM Logo moved **UP** to avoid LinkedIn crop
- QR Code and "SWIPE TO READ" moved **DOWN**
- **Middle area reserved for featured blog image** (800x600px max)
- Text remains centered above featured image

### Template 2 & 3 (Content & CTA Slides)
- AM Logo moved **DOWN** slightly to prevent LinkedIn preview cutoff
- Text positioning adjusted **100px lower** to accommodate logo
- Maintains optimal readability

## Quick Start

### Deploy to Railway

1. Go to Railway.app
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
        "subText": "Supporting text",
        "featuredImage": "https://example.com/image.jpg"
      },
      {
        "slideNumber": 2,
        "mainText": "Content slide",
        "subText": "Details here"
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

### Featured Image Support (NEW!)

For **Slide 1 (Cover)** only, you can add a featured image:

#### Option 1: Image URL
```json
{
  "slideNumber": 1,
  "mainText": "Title",
  "subText": "Subtitle",
  "featuredImage": "https://your-blog.com/featured.jpg"
}
```

#### Option 2: Base64 Encoded
```json
{
  "slideNumber": 1,
  "mainText": "Title",
  "subText": "Subtitle",
  "featuredImageBase64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Image Specs:**
- Auto-resized to max 800px width
- Max height: 600px (maintains aspect ratio)
- Positioned at Y=650 (center of slide)
- Horizontally centered

## Base64 Endpoint (for n8n network bypass)

**POST** `/generate-carousel-base64`

Returns images as base64 strings instead of URLs - perfect for n8n workflows that can't access Railway URLs.

```bash
curl -X POST https://your-app.railway.app/generate-carousel-base64 \
  -H "Content-Type: application/json" \
  -d '{
    "slides": [
      {
        "slideNumber": 1,
        "mainText": "Title",
        "featuredImage": "https://example.com/image.jpg"
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
      "filename": "image_20241128_120000_1.png",
      "base64": "iVBORw0KGgoAAAANSUhEUgAA..."
    }
  ],
  "count": 1
}
```

## Template Requirements

Place in `templates/` directory:

* **1.png** - First slide (cover) - Logo TOP, QR BOTTOM, middle for featured image
* **2.png** - Middle slides (content) - Logo slightly LOWER
* **3.png** - Last slide (CTA) - Logo slightly LOWER

All templates: **1200x1500px PNG**

## n8n Integration

**HTTP Request Node:**

* Method: POST
* URL: `https://your-app.railway.app/generate-carousel`
* Body: JSON
* Content:
```json
{
  "slides": [
    {
      "slideNumber": 1,
      "mainText": "{{ $json.title }}",
      "subText": "{{ $json.subtitle }}",
      "featuredImage": "{{ $json.featuredImageUrl }}"
    }
  ]
}
```

**Access URLs:**
```
{{ $json.images[0].url }}
{{ $json.images[1].url }}
```

**Or use base64 endpoint:**
```
POST /generate-carousel-base64
→ Access via {{ $json.images[0].base64 }}
```

## Local Development

```bash
pip install -r requirements.txt
python app.py
```

Server runs on `http://localhost:5000`

## Text Styling

* **Main Text:** 90px (cover), 83px (content), 86px (CTA)
* **Sub Text:** 49px (cover), 45px (content), 47px (CTA)
* **Alignment:** Centered horizontally and vertically
* **Padding:** 100px from edges
* **Auto-wrapping enabled**
* **Y-Offset:** +0px (Template 1), +100px (Template 2&3)

## Endpoints

* `POST /generate-carousel` - Generate images, return URLs
* `POST /generate-carousel-base64` - Generate images, return base64
* `GET /download/<filename>` - Download image
* `GET /health` - Health check
* `GET /debug/config` - Show current configuration
* `GET /` - API documentation

## Changelog

### Version 2.2.0
- ✅ Added featured image support for Template 1
- ✅ Optimized logo positions for LinkedIn preview
- ✅ Adjusted text Y-offset for Templates 2 & 3 (+100px)
- ✅ Support for both URL and base64 featured images

### Version 2.1.0
- Added base64 endpoint for n8n compatibility
- Improved debug output

### Version 2.0.0
- Optimized font sizes (25% reduction)
- Better text wrapping

## License

MIT
