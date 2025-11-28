from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

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

def get_font(size):
    """Get font, fallback to default if custom font not available"""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    ]
    
    for font_path in font_paths:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except:
            continue
    
    # Fallback: Use default font (will be small but better than nothing)
    # Note: Default font is typically 8-10px, so we'll use it as-is
    return ImageFont.load_default()

def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width"""
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
            else:
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def calculate_text_height(lines, font, draw, line_spacing=1.5):
    """Calculate total height of text block"""
    if not lines:
        return 0
    
    bbox = draw.textbbox((0, 0), lines[0], font=font)
    line_height = bbox[3] - bbox[1]
    
    return line_height * len(lines) * line_spacing

def draw_centered_text(draw, text, font, y_position, color=(0, 0, 0)):
    """Draw text centered horizontally"""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (IMAGE_WIDTH - text_width) // 2
    draw.text((x, y_position), text, font=font, fill=color)
    return bbox[3] - bbox[1]

def generate_slide_image(slide_data, output_path):
    """Generate a single slide image"""
    slide_number = slide_data.get('slideNumber', 1)
    main_text = slide_data.get('mainText', '').strip()
    sub_text = slide_data.get('subText', '').strip()
    slide_type = slide_data.get('type', 'content')
    
    # Determine which template to use
    if slide_number == 1:
        template_name = '1.png'
    elif slide_type == 'cta':
        template_name = '3.png'
    else:
        template_name = '2.png'
    
    template_path = os.path.join(TEMPLATE_DIR, template_name)
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template {template_name} not found in {TEMPLATE_DIR}")
    
    img = Image.open(template_path).convert('RGBA')
    draw = ImageDraw.Draw(img)
    
    # Increased font sizes for better visibility
    main_font = get_font(80)
    sub_font = get_font(48)
    
    # Only process text if it exists
    main_lines = wrap_text(main_text, main_font, MAX_TEXT_WIDTH, draw) if main_text else []
    sub_lines = wrap_text(sub_text, sub_font, MAX_TEXT_WIDTH, draw) if sub_text else []
    
    # Calculate heights
    main_height = calculate_text_height(main_lines, main_font, draw) if main_lines else 0
    sub_height = calculate_text_height(sub_lines, sub_font, draw) if sub_lines else 0
    spacing_between = 50 if main_lines and sub_lines else 0
    
    total_height = main_height + spacing_between + sub_height
    
    # Center vertically, or start from top if no text
    if total_height > 0:
        start_y = (IMAGE_HEIGHT - total_height) // 2
    else:
        start_y = IMAGE_HEIGHT // 2
    
    # Draw main text
    current_y = start_y
    if main_lines:
        for line in main_lines:
            bbox = draw.textbbox((0, 0), line, font=main_font)
            line_height = bbox[3] - bbox[1]
            draw_centered_text(draw, line, main_font, current_y, color=(0, 0, 0))
            current_y += int(line_height * 1.5)
    
    if main_lines and sub_lines:
        current_y += spacing_between
    
    # Draw sub text
    if sub_lines:
        for line in sub_lines:
            bbox = draw.textbbox((0, 0), line, font=sub_font)
            line_height = bbox[3] - bbox[1]
            draw_centered_text(draw, line, sub_font, current_y, color=(60, 60, 60))
            current_y += int(line_height * 1.5)
    
    img.save(output_path, 'PNG')
    return output_path

@app.route('/generate-carousel', methods=['POST'])
def generate_carousel():
    """Generate carousel images from JSON data"""
    try:
        data = request.get_json()
        
        if not data or 'slides' not in data:
            return jsonify({'error': 'Invalid request. Expected JSON with "slides" array'}), 400
        
        slides = data['slides']
        generated_images = []
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for idx, slide in enumerate(slides, 1):
            output_filename = f"image_{timestamp}_{idx}.png"
            output_path = os.path.join(GENERATED_DIR, output_filename)
            
            generate_slide_image(slide, output_path)
            
            base_url = request.url_root.rstrip('/')
            
            generated_images.append({
                'slideNumber': slide.get('slideNumber', idx),
                'url': f'{base_url}/download/{output_filename}',
                'filename': output_filename
            })
        
        return jsonify({
            'success': True,
            'images': generated_images,
            'count': len(generated_images)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_image(filename):
    """Download generated image"""
    try:
        file_path = os.path.join(GENERATED_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, mimetype='image/png')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'templates': os.listdir(TEMPLATE_DIR) if os.path.exists(TEMPLATE_DIR) else []
    })

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API documentation"""
    return jsonify({
        'service': 'LinkedIn Image Generator',
        'version': '1.0.0',
        'endpoints': {
            'POST /generate-carousel': 'Generate carousel images from JSON',
            'GET /download/<filename>': 'Download generated image',
            'GET /health': 'Health check'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
