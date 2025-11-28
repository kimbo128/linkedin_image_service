from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
import uuid

app = Flask(__name__)

# Configuration
TEMPLATE_DIR = 'templates'
GENERATED_DIR = 'generated'
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 1500
PADDING = 100
MAX_TEXT_WIDTH = IMAGE_WIDTH - (2 * PADDING)

# Ensure directories exist
os.makedirs(GENERATED_DIR, exist_ok=True)

# Font paths - try common locations
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]

def get_font(size, bold=False):
    """Get font - simple and direct"""
    font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    
    # Try direct paths
    for path in FONT_PATHS:
        if os.path.exists(path) and font_name in path:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    # Try to find in system
    for root, dirs, files in os.walk("/usr/share/fonts"):
        if font_name in files:
            try:
                return ImageFont.truetype(os.path.join(root, font_name), size)
            except:
                continue
    
    # Last resort: default font
    print(f"WARNING: Using default font for size {size}")
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
    main_text_raw = slide_data.get('mainText') or slide_data.get('title', '')
    sub_text_raw = slide_data.get('subText') or slide_data.get('subtitle', '')
    
    main_text = str(main_text_raw).strip() if main_text_raw else ''
    sub_text = str(sub_text_raw).strip() if sub_text_raw else ''
    
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
    
    # Load fonts - LARGE SIZES
    main_font = get_font(90, bold=True)
    sub_font = get_font(55, bold=False)
    
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
    
    # Calculate total height
    main_height = 0
    if main_lines:
        bbox = draw.textbbox((0, 0), main_lines[0], font=main_font)
        main_height = (bbox[3] - bbox[1]) * len(main_lines) * 1.3
    
    sub_height = 0
    if sub_lines:
        bbox = draw.textbbox((0, 0), sub_lines[0], font=sub_font)
        sub_height = (bbox[3] - bbox[1]) * len(sub_lines) * 1.3
    
    spacing = 40 if main_lines and sub_lines else 0
    total_height = main_height + spacing + sub_height
    
    # Center vertically
    start_y = (IMAGE_HEIGHT - total_height) // 2
    
    # Draw main text
    current_y = start_y
    for line in main_lines:
        line_height = draw_text_centered(draw, line, main_font, current_y, (0, 0, 0))
        current_y += int(line_height * 1.3)
    
    if main_lines and sub_lines:
        current_y += spacing
    
    # Draw sub text
    for line in sub_lines:
        line_height = draw_text_centered(draw, line, sub_font, current_y, (60, 60, 60))
        current_y += int(line_height * 1.3)
    
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
                if os.path.exists(output_path):
                    slide_debug['file_size'] = os.path.getsize(output_path)
                else:
                    slide_debug['status'] = 'error'
                    slide_debug['error'] = 'File not created'
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

@app.route('/', methods=['GET'])
def index():
    """API info"""
    return jsonify({
        'service': 'LinkedIn Image Generator',
        'version': '2.0.0',
        'endpoints': {
            'POST /generate-carousel': 'Generate images',
            'GET /download/<filename>': 'Download image',
            'GET /health': 'Health check'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
