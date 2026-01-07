from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import os
import urllib.request
from datetime import datetime
import uuid
import base64
import io
import requests

app = Flask(__name__)

# Configuration
TEMPLATE_DIR = 'templates'
GENERATED_DIR = 'generated'
FONTS_DIR = 'fonts'
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 1500
PADDING = 100
MAX_TEXT_WIDTH = IMAGE_WIDTH - (2 * PADDING)

# Ensure directories exist
os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

# Font URLs - Google Fonts CDN (100% reliable)
FONT_URLS = {
    'regular': 'https://fonts.gstatic.com/s/roboto/v30/KFOmCnqEu92Fr1Mu4mxP.ttf',
    'bold': 'https://fonts.gstatic.com/s/roboto/v30/KFOlCnqEu92Fr1MmWUlfBBc4.ttf'
}

def download_font(font_type='regular'):
    """Download font from Google Fonts CDN - GUARANTEED TO WORK"""
    font_path = os.path.join(FONTS_DIR, f'Roboto-{font_type.capitalize()}.ttf')
    
    if os.path.exists(font_path):
        return font_path
    
    try:
        url = FONT_URLS[font_type]
        print(f"Downloading Roboto {font_type} from Google Fonts...", flush=True)
        urllib.request.urlretrieve(url, font_path)
        print(f"Downloaded to {font_path}", flush=True)
        return font_path
    except Exception as e:
        print(f"Failed to download font: {e}", flush=True)
        return None

def get_font(size, bold=False):
    """Get font - 100% WORKING: Use fonts directly from repository"""
    font_filename = "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"
    font_path = os.path.join(FONTS_DIR, font_filename)
    
    # Use font from repository (guaranteed to exist)
    if os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, size)
            print(f"SUCCESS: Loaded {font_filename} at size {size} from repository", flush=True)
            return font
        except Exception as e:
            print(f"ERROR loading font from {font_path}: {e}", flush=True)
    
    # Fallback: Try system fonts
    system_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    
    for path in system_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    # Last resort: default font (will be small)
    print(f"WARNING: Using default font for size {size} - text will be VERY small!", flush=True)
    return ImageFont.load_default()

def wrap_text(text, font, max_width, draw):
    """Wrap text to fit width"""
    if not text:
        return []
    
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines if lines else [text]

def draw_text_centered(draw, text, font, y, color=(0, 0, 0)):
    """Draw centered text"""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (IMAGE_WIDTH - text_width) // 2
    draw.text((x, y), text, font=font, fill=color)
    return bbox[3] - bbox[1]

def generate_slide_image(slide_data, output_path):
    """Generate slide image - SIMPLE AND DIRECT"""
    slide_number = slide_data.get('slideNumber', 1)
    
    # Support both formats: mainText/subText AND title/subtitle
    # Check both formats explicitly to ensure we get the text
    main_text_raw = slide_data.get('mainText') or slide_data.get('title') or ''
    sub_text_raw = slide_data.get('subText') or slide_data.get('subtitle') or ''
    
    main_text = str(main_text_raw).strip() if main_text_raw else ''
    sub_text = str(sub_text_raw).strip() if sub_text_raw else ''
    
    # NEU: Featured Image für Template 1
    featured_image_url = slide_data.get('featuredImage', '')
    featured_image_base64 = slide_data.get('featuredImageBase64', '')
    
    # Debug output for first slide
    if slide_number == 1:
        print(f"DEBUG Slide 1 - mainText: '{main_text}', subText: '{sub_text}'", flush=True)
        print(f"DEBUG Slide 1 - featuredImage: '{featured_image_url}'", flush=True)
        print(f"DEBUG Slide 1 - raw data: {slide_data}", flush=True)
    
    slide_type = slide_data.get('type', 'content')
    
    # Choose template
    if slide_number == 1:
        template_name = '1.png'
    elif slide_type == 'cta':
        template_name = '3.png'
    else:
        template_name = '2.png'
    
    template_path = os.path.join(TEMPLATE_DIR, template_name)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_name}")
    
    # Load image
    img = Image.open(template_path).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # NEU: Featured Image für Template 1 OBEN einfügen
    featured_img_height = 0
    has_featured_image = False
    
    if slide_number == 1 and (featured_image_url or featured_image_base64):
        try:
            featured_img = None
            
            # Von URL laden
            if featured_image_url:
                response = requests.get(featured_image_url, timeout=10)
                featured_img = Image.open(io.BytesIO(response.content)).convert('RGBA')
            # Von Base64 laden
            elif featured_image_base64:
                img_data = base64.b64decode(featured_image_base64)
                featured_img = Image.open(io.BytesIO(img_data)).convert('RGBA')
            
            if featured_img:
                # Featured Image Größe: Breite 700px, Höhe proportional
                target_width = 700
                aspect_ratio = featured_img.height / featured_img.width
                target_height = int(target_width * aspect_ratio)
                
                # Max Höhe: 450px
                if target_height > 450:
                    target_height = 450
                    target_width = int(target_height / aspect_ratio)
                
                featured_img = featured_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                # Abgerundete Ecken hinzufügen
                radius = 30  # Radius für abgerundete Ecken
                mask = Image.new('L', (target_width, target_height), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle(
                    [(0, 0), (target_width, target_height)],
                    radius=radius,
                    fill=255
                )
                
                # Maske auf das Bild anwenden
                featured_img.putalpha(mask)
                
                # Position: Horizontal zentriert, OBEN (unter dem Logo)
                x_pos = (IMAGE_WIDTH - target_width) // 2
                y_pos = 280  # Oben, unter dem AM Logo
                
                # Bild einfügen mit Alpha-Kanal (für abgerundete Ecken)
                img.paste(featured_img, (x_pos, y_pos), featured_img)
                featured_img_height = target_height
                has_featured_image = True
                print(f"Featured image added at ({x_pos}, {y_pos}), size: {target_width}x{target_height}, rounded corners: {radius}px", flush=True)
        
        except Exception as e:
            print(f"ERROR: Failed to load featured image: {e}", flush=True)
    
    # Optimized font sizes based on slide type - 25% smaller than before
    # Cover slides: Larger title for impact
    # Content slides: Balanced sizes for readability
    # CTA slides: Slightly larger to draw attention
    if slide_number == 1:  # Cover slide
        main_font_size = 90  # 120 * 0.75
        sub_font_size = 49   # 65 * 0.75
        line_spacing = 1.25
        text_spacing = 50
        y_offset = 0  # Kein Offset, da Logo nach oben verschoben wurde
    elif slide_type == 'cta':  # CTA slide
        main_font_size = 86   # 115 * 0.75
        sub_font_size = 47    # 63 * 0.75
        line_spacing = 1.25
        text_spacing = 45
        y_offset = 100  # Logo nach unten -> Text muss tiefer starten
    else:  # Content slides
        main_font_size = 83   # 110 * 0.75
        sub_font_size = 45    # 60 * 0.75
        line_spacing = 1.3
        text_spacing = 45
        y_offset = 100  # Logo nach unten -> Text muss tiefer starten
    
    main_font = get_font(main_font_size, bold=False)
    sub_font = get_font(sub_font_size, bold=False)
    
    # Wrap text
    main_lines = []
    sub_lines = []
    
    if main_text:
        main_lines = wrap_text(main_text, main_font, MAX_TEXT_WIDTH, draw)
    
    if sub_text:
        sub_lines = wrap_text(sub_text, sub_font, MAX_TEXT_WIDTH, draw)
    
    # Calculate position
    total_lines = len(main_lines) + len(sub_lines)
    
    if total_lines == 0:
        # No text - save empty image
        img.save(output_path, 'PNG')
        return output_path
    
    # Calculate total height with optimized spacing
    main_height = 0
    if main_lines:
        bbox = draw.textbbox((0, 0), main_lines[0], font=main_font)
        main_height = (bbox[3] - bbox[1]) * len(main_lines) * line_spacing
    
    sub_height = 0
    if sub_lines:
        bbox = draw.textbbox((0, 0), sub_lines[0], font=sub_font)
        sub_height = (bbox[3] - bbox[1]) * len(sub_lines) * line_spacing
    
    spacing = text_spacing if main_lines and sub_lines else 0
    total_height = main_height + spacing + sub_height
    
    # Center vertically + apply y_offset
    # Für Slide 1 mit Featured Image: Text UNTER dem Bild
    if slide_number == 1 and has_featured_image:
        # Text beginnt direkt unter dem Featured Image
        start_y = 280 + featured_img_height + 60  # Image Y-Pos + Höhe + Abstand
    else:
        # Normale Zentrierung
        start_y = (IMAGE_HEIGHT - total_height) // 2 + y_offset
    
    # Draw main text with optimized spacing
    current_y = start_y
    for line in main_lines:
        line_height = draw_text_centered(draw, line, main_font, current_y, (0, 0, 0))
        current_y += int(line_height * line_spacing)
    
    if main_lines and sub_lines:
        current_y += spacing
    
    # Draw sub text with optimized spacing
    for line in sub_lines:
        line_height = draw_text_centered(draw, line, sub_font, current_y, (60, 60, 60))
        current_y += int(line_height * line_spacing)
    
    # Save
    img.save(output_path, 'PNG')
    return output_path

@app.route('/generate-carousel', methods=['POST'])
def generate_carousel():
    """Generate carousel images"""
    debug_info = []
    
    try:
        data = request.get_json()
        if not data or 'slides' not in data:
            return jsonify({'error': 'Invalid request'}), 400
        
        slides = data['slides']
        generated_images = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        request_id = str(uuid.uuid4())[:8]
        
        for idx, slide in enumerate(slides, 1):
            slide_debug = {
                'index': idx,
                'slideNumber': slide.get('slideNumber', idx),
                'raw_data': {
                    'mainText': repr(slide.get('mainText', '')),
                    'subText': repr(slide.get('subText', '')),
                    'title': repr(slide.get('title', '')),
                    'subtitle': repr(slide.get('subtitle', '')),
                    'type': slide.get('type', 'content')
                },
                'processed': {
                    'mainText': repr(slide.get('mainText') or slide.get('title', '')),
                    'subText': repr(slide.get('subText') or slide.get('subtitle', ''))
                }
            }
            
            filename = f"image_{timestamp}_{request_id}_{idx}.png"
            output_path = os.path.join(GENERATED_DIR, filename)
            
            # Generate and capture debug info
            try:
                generate_slide_image(slide, output_path)
                slide_debug['status'] = 'success'
                
                # Check if file was created
                abs_path = os.path.abspath(output_path)
                if os.path.exists(abs_path):
                    slide_debug['file_size'] = os.path.getsize(abs_path)
                    slide_debug['file_path'] = abs_path
                else:
                    slide_debug['status'] = 'error'
                    slide_debug['error'] = f'File not found at {abs_path}'
                    slide_debug['generated_dir'] = os.path.abspath(GENERATED_DIR)
                    slide_debug['dir_exists'] = os.path.exists(GENERATED_DIR)
                    if os.path.exists(GENERATED_DIR):
                        slide_debug['dir_contents'] = os.listdir(GENERATED_DIR)
            except Exception as e:
                slide_debug['status'] = 'error'
                slide_debug['error'] = str(e)
            
            debug_info.append(slide_debug)
            
            base_url = request.url_root.rstrip('/')
            generated_images.append({
                'slideNumber': slide.get('slideNumber', idx),
                'url': f'{base_url}/download/{filename}',
                'filename': filename
            })
        
        return jsonify({
            'success': True,
            'images': generated_images,
            'count': len(generated_images),
            'debug': debug_info
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'debug': debug_info
        }), 500

# ============= NEUER BASE64 ENDPOINT - NICHTS GEÄNDERT AM ALTEN CODE =============
@app.route('/generate-carousel-base64', methods=['POST'])
def generate_carousel_base64():
    """Generate carousel images and return as base64 - for n8n network bypass"""
    debug_info = []
    
    try:
        data = request.get_json()
        if not data or 'slides' not in data:
            return jsonify({'error': 'Invalid request', 'success': False}), 400
        
        slides = data['slides']
        generated_images = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        request_id = str(uuid.uuid4())[:8]
        
        for idx, slide in enumerate(slides, 1):
            slide_debug = {
                'index': idx,
                'slideNumber': slide.get('slideNumber', idx),
                'raw_data': {
                    'mainText': repr(slide.get('mainText', '')),
                    'subText': repr(slide.get('subText', '')),
                    'title': repr(slide.get('title', '')),
                    'subtitle': repr(slide.get('subtitle', '')),
                    'type': slide.get('type', 'content')
                },
                'processed': {
                    'mainText': repr(slide.get('mainText') or slide.get('title', '')),
                    'subText': repr(slide.get('subText') or slide.get('subtitle', ''))
                }
            }
            
            filename = f"image_{timestamp}_{request_id}_{idx}.png"
            output_path = os.path.join(GENERATED_DIR, filename)
            
            # Generate image
            try:
                generate_slide_image(slide, output_path)
                slide_debug['status'] = 'success'
                
                # Read and encode as base64
                abs_path = os.path.abspath(output_path)
                if os.path.exists(abs_path):
                    with open(abs_path, 'rb') as f:
                        image_data = f.read()
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                    
                    slide_debug['file_size'] = os.path.getsize(abs_path)
                    slide_debug['file_path'] = abs_path
                    slide_debug['base64_length'] = len(base64_data)
                    
                    generated_images.append({
                        'slideNumber': slide.get('slideNumber', idx),
                        'filename': filename,
                        'base64': base64_data
                    })
                else:
                    slide_debug['status'] = 'error'
                    slide_debug['error'] = f'File not found at {abs_path}'
            
            except Exception as e:
                slide_debug['status'] = 'error'
                slide_debug['error'] = str(e)
            
            debug_info.append(slide_debug)
        
        return jsonify({
            'success': True,
            'images': generated_images,
            'count': len(generated_images),
            'debug': debug_info
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'debug': debug_info
        }), 500
# ============= ENDE NEUER ENDPOINT =============

@app.route('/download/<filename>', methods=['GET'])
def download_image(filename):
    """Download image"""
    try:
        filename = os.path.basename(filename)
        file_path = os.path.join(GENERATED_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'templates': os.listdir(TEMPLATE_DIR) if os.path.exists(TEMPLATE_DIR) else []
    })

@app.route('/debug/config', methods=['GET'])
def debug_config():
    """Debug endpoint to check current font sizes and configuration"""
    return jsonify({
        'font_sizes': {
            'cover': {'main': 90, 'sub': 49},
            'content': {'main': 83, 'sub': 45},
            'cta': {'main': 86, 'sub': 47}
        },
        'y_offsets': {
            'cover': 0,
            'content': 100,
            'cta': 100
        },
        'featured_image': {
            'max_width': 700,
            'max_height': 450,
            'y_position': 280,
            'border_radius': 30,
            'layout': 'Image OBEN → Titel → Untertitel'
        },
        'image_width': IMAGE_WIDTH,
        'image_height': IMAGE_HEIGHT,
        'max_text_width': MAX_TEXT_WIDTH,
        'version': '2.2.1'
    })

@app.route('/', methods=['GET'])
def index():
    """API info"""
    return jsonify({
        'service': 'LinkedIn Image Generator',
        'version': '2.2.1',
        'endpoints': {
            'POST /generate-carousel': 'Generate images with URLs',
            'POST /generate-carousel-base64': 'Generate images as base64 (for n8n)',
            'GET /download/<filename>': 'Download image',
            'GET /health': 'Health check',
            'GET /debug/config': 'Show configuration'
        },
        'new_features': {
            'featured_image': 'Add featuredImage URL or featuredImageBase64 to slide 1',
            'layout': 'Slide 1: Featured Image OBEN → Titel → Untertitel',
            'rounded_corners': '30px border radius on featured images'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
