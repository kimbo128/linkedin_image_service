from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import os
import logging
import uuid
import base64
import urllib.request
from io import BytesIO
from datetime import datetime

app = Flask(__name__)

# Configure logging with handler that captures logs
import sys
from logging.handlers import MemoryHandler

# Create a custom handler that stores logs
log_buffer = []
class ListHandler(logging.Handler):
    def emit(self, record):
        log_buffer.append(self.format(record))
        # Also print to stdout/stderr for Railway logs
        print(self.format(record), file=sys.stdout)
        sys.stdout.flush()

# Configure logging
handler = ListHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
app.logger.setLevel(logging.INFO)
app.logger.addHandler(handler)

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

# Pre-download fonts on startup to ensure they're available
def ensure_fonts_available():
    """Download fonts if not available locally"""
    fonts_to_download = [
        ("https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf", "Roboto-Regular.ttf"),
        ("https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf", "Roboto-Bold.ttf"),
    ]
    
    for url, filename in fonts_to_download:
        font_path = os.path.join(FONTS_DIR, filename)
        if not os.path.exists(font_path):
            try:
                app.logger.info(f"Downloading font: {filename}")
                urllib.request.urlretrieve(url, font_path)
                app.logger.info(f"Successfully downloaded {filename}")
            except Exception as e:
                app.logger.warning(f"Could not download {filename}: {str(e)}")

# Download fonts on startup
try:
    ensure_fonts_available()
except Exception as e:
    app.logger.error(f"Error downloading fonts on startup: {str(e)}")

def download_font(url, filename):
    """Download font file if not exists"""
    font_path = os.path.join(FONTS_DIR, filename)
    if os.path.exists(font_path):
        return font_path
    
    try:
        app.logger.info(f"Downloading font from {url}")
        urllib.request.urlretrieve(url, font_path)
        app.logger.info(f"Downloaded font to {font_path}")
        return font_path
    except Exception as e:
        app.logger.error(f"Failed to download font: {str(e)}")
        return None

def find_font_file(filename):
    """Search for font file in common system directories and local fonts directory"""
    # First check local fonts directory
    local_font = os.path.join(FONTS_DIR, filename)
    if os.path.exists(local_font):
        try:
            test_font = ImageFont.truetype(local_font, 12)
            app.logger.info(f"Found font in local directory: {local_font}")
            return local_font
        except:
            pass
    
    search_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        "/System/Library/Fonts",
        "/Library/Fonts",
        "~/.fonts",
        "/opt/homebrew/share/fonts"
    ]
    
    for search_dir in search_dirs:
        expanded_dir = os.path.expanduser(search_dir)
        if not os.path.exists(expanded_dir):
            continue
        
        # Search recursively
        for root, dirs, files in os.walk(expanded_dir):
            if filename in files:
                font_path = os.path.join(root, filename)
                try:
                    # Test if we can actually load it
                    test_font = ImageFont.truetype(font_path, 12)
                    app.logger.info(f"Found font: {font_path}")
                    return font_path
                except:
                    continue
    
    return None

def get_font(size, bold=False):
    """Get font, fallback to default if custom font not available"""
    app.logger.info(f"get_font called: size={size}, bold={bold}")
    
    # Priority 1: Try Roboto fonts (downloaded on startup)
    if bold:
        font_file = find_font_file("Roboto-Bold.ttf")
        app.logger.info(f"Looking for Roboto-Bold.ttf: {font_file}")
    else:
        font_file = find_font_file("Roboto-Regular.ttf")
        app.logger.info(f"Looking for Roboto-Regular.ttf: {font_file}")
    
    # Priority 2: Try DejaVu Sans fonts (system fonts)
    if not font_file:
        if bold:
            font_file = find_font_file("DejaVuSans-Bold.ttf")
            app.logger.info(f"Looking for DejaVuSans-Bold.ttf: {font_file}")
        else:
            font_file = find_font_file("DejaVuSans.ttf")
            if not font_file:
                font_file = find_font_file("DejaVuSans-Regular.ttf")
            app.logger.info(f"Looking for DejaVuSans: {font_file}")
    
    # Priority 3: Try Liberation Sans as fallback
    if not font_file:
        if bold:
            font_file = find_font_file("LiberationSans-Bold.ttf")
        else:
            font_file = find_font_file("LiberationSans-Regular.ttf")
        app.logger.info(f"Looking for LiberationSans: {font_file}")
    
    # Priority 4: Try Arial or Helvetica
    if not font_file:
        font_file = find_font_file("Arial.ttf")
        app.logger.info(f"Looking for Arial.ttf: {font_file}")
    if not font_file:
        font_file = find_font_file("Helvetica.ttc")
        app.logger.info(f"Looking for Helvetica.ttc: {font_file}")
    
    # Priority 5: Direct paths as last resort
    if not font_file:
        direct_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
        for path in direct_paths:
            if os.path.exists(path):
                font_file = path
                app.logger.info(f"Found font via direct path: {font_file}")
                break
    
    if font_file:
        try:
            app.logger.info(f"Attempting to load font from {font_file} at size {size}")
            font = ImageFont.truetype(font_file, size)
            app.logger.info(f"SUCCESS: Loaded font from {font_file} at size {size}, font type: {type(font)}")
            return font
        except Exception as e:
            app.logger.error(f"FAILED to load font from {font_file}: {str(e)}", exc_info=True)
    
    # Last resort: Try to use ImageFont.load_default() but warn
    app.logger.error(f"CRITICAL: No suitable font found! Using default font at size {size} (will be VERY small - ~8px)")
    app.logger.error("This will result in unreadable text. Please ensure system fonts are available.")
    default_font = ImageFont.load_default()
    app.logger.error(f"Default font type: {type(default_font)}")
    return default_font

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
    app.logger.info(f"=== GENERATING SLIDE IMAGE ===")
    app.logger.info(f"slide_data: {slide_data}")
    
    slide_number = slide_data.get('slideNumber', 1)
    main_text_raw = slide_data.get('mainText', '')
    sub_text_raw = slide_data.get('subText', '')
    
    app.logger.info(f"Slide {slide_number} - RAW INPUT: mainText='{main_text_raw}', subText='{sub_text_raw}'")
    app.logger.info(f"Slide {slide_number} - mainText type: {type(main_text_raw)}, subText type: {type(sub_text_raw)}")
    
    main_text = main_text_raw or ''
    sub_text = sub_text_raw or ''
    main_text = main_text.strip() if isinstance(main_text, str) else ''
    sub_text = sub_text.strip() if isinstance(sub_text, str) else ''
    slide_type = slide_data.get('type', 'content')
    
    app.logger.info(f"Slide {slide_number} - PROCESSED: mainText='{main_text}' (len={len(main_text)}), subText='{sub_text}' (len={len(sub_text)})")
    
    # Determine which template to use
    if slide_number == 1:
        template_name = '1.png'
    elif slide_type == 'cta':
        template_name = '3.png'
    else:
        template_name = '2.png'
    
    template_path = os.path.join(TEMPLATE_DIR, template_name)
    app.logger.info(f"Slide {slide_number} - Using template: {template_name} from {template_path}")
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template {template_name} not found in {TEMPLATE_DIR}")
    
    img = Image.open(template_path).convert('RGBA')
    draw = ImageDraw.Draw(img)
    app.logger.info(f"Slide {slide_number} - Image loaded: {img.size}")
    
    # Increased font sizes for better visibility - much larger for readability
    # Use bold for main text
    app.logger.info(f"Slide {slide_number} - Loading fonts...")
    main_font = get_font(100, bold=True)
    sub_font = get_font(60, bold=False)
    app.logger.info(f"Slide {slide_number} - Fonts loaded: main_font={type(main_font)}, sub_font={type(sub_font)}")
    
    # Only process text if it exists and is not empty
    app.logger.info(f"Slide {slide_number} - Wrapping text...")
    app.logger.info(f"Slide {slide_number} - main_text is truthy: {bool(main_text)}, sub_text is truthy: {bool(sub_text)}")
    
    main_lines = []
    sub_lines = []
    
    if main_text:
        try:
            app.logger.info(f"Slide {slide_number} - Wrapping main_text: '{main_text}'")
            main_lines = wrap_text(main_text, main_font, MAX_TEXT_WIDTH, draw)
            app.logger.info(f"Slide {slide_number} - Main text wrapped into {len(main_lines)} lines: {main_lines}")
        except Exception as e:
            app.logger.error(f"Slide {slide_number} - ERROR wrapping main_text: {str(e)}", exc_info=True)
            main_lines = []
    
    if sub_text:
        try:
            app.logger.info(f"Slide {slide_number} - Wrapping sub_text: '{sub_text}'")
            sub_lines = wrap_text(sub_text, sub_font, MAX_TEXT_WIDTH, draw)
            app.logger.info(f"Slide {slide_number} - Sub text wrapped into {len(sub_lines)} lines: {sub_lines}")
        except Exception as e:
            app.logger.error(f"Slide {slide_number} - ERROR wrapping sub_text: {str(e)}", exc_info=True)
            sub_lines = []
    
    # Debug: Log text information
    app.logger.info(f"Slide {slide_number} - FINAL: main_lines={len(main_lines)}, sub_lines={len(sub_lines)}")
    
    # Debug: Log if no text to draw
    if not main_lines and not sub_lines:
        app.logger.warning(f"Slide {slide_number} - WARNING: No text lines to draw! mainText: '{main_text}', subText: '{sub_text}'")
    
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
    app.logger.info(f"Slide {slide_number} - Starting to draw text. start_y={start_y}, total_height={total_height}")
    current_y = start_y
    
    if main_lines:
        app.logger.info(f"Slide {slide_number} - Drawing {len(main_lines)} main text lines starting at y={current_y}")
        for idx, line in enumerate(main_lines):
            try:
                bbox = draw.textbbox((0, 0), line, font=main_font)
                line_height = bbox[3] - bbox[1]
                app.logger.info(f"Slide {slide_number} - Drawing main line {idx+1}: '{line}' at y={current_y}, bbox={bbox}, height={line_height}")
                draw_centered_text(draw, line, main_font, current_y, color=(0, 0, 0))
                app.logger.info(f"Slide {slide_number} - Successfully drew main line {idx+1}")
                current_y += int(line_height * 1.5)
            except Exception as e:
                app.logger.error(f"Slide {slide_number} - ERROR drawing main line {idx+1}: {str(e)}", exc_info=True)
    else:
        app.logger.warning(f"Slide {slide_number} - No main_lines to draw!")
    
    if main_lines and sub_lines:
        current_y += spacing_between
        app.logger.info(f"Slide {slide_number} - Added spacing, current_y={current_y}")
    
    # Draw sub text
    if sub_lines:
        app.logger.info(f"Slide {slide_number} - Drawing {len(sub_lines)} sub text lines starting at y={current_y}")
        for idx, line in enumerate(sub_lines):
            try:
                bbox = draw.textbbox((0, 0), line, font=sub_font)
                line_height = bbox[3] - bbox[1]
                app.logger.info(f"Slide {slide_number} - Drawing sub line {idx+1}: '{line}' at y={current_y}, bbox={bbox}, height={line_height}")
                draw_centered_text(draw, line, sub_font, current_y, color=(60, 60, 60))
                app.logger.info(f"Slide {slide_number} - Successfully drew sub line {idx+1}")
                current_y += int(line_height * 1.5)
            except Exception as e:
                app.logger.error(f"Slide {slide_number} - ERROR drawing sub line {idx+1}: {str(e)}", exc_info=True)
    else:
        app.logger.warning(f"Slide {slide_number} - No sub_lines to draw!")
    
    # Verify that text was actually drawn
    if main_lines or sub_lines:
        app.logger.info(f"Slide {slide_number} - Completed drawing text. Total lines drawn: main={len(main_lines) if main_lines else 0}, sub={len(sub_lines) if sub_lines else 0}")
    else:
        app.logger.warning(f"Slide {slide_number} - WARNING: No text was drawn at all!")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    # Save image atomically using a temporary file first
    temp_path = output_path + '.tmp'
    try:
        img.save(temp_path, 'PNG')
        
        # Atomic rename (works on Unix/Linux, Railway)
        if os.path.exists(temp_path):
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(temp_path, output_path)
        
        # Verify file was saved
        if not os.path.exists(output_path):
            raise IOError(f"Failed to save image to {output_path}")
        
        app.logger.info(f"Successfully saved image to {output_path}")
        
    except Exception as e:
        # Clean up temp file if it exists
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        raise IOError(f"Failed to save image: {str(e)}")
    
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
        
        # Generate unique identifier for this request to avoid collisions
        request_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
        
        for idx, slide in enumerate(slides, 1):
            output_filename = f"image_{timestamp}_{request_id}_{idx}.png"
            output_path = os.path.join(GENERATED_DIR, output_filename)
            
            try:
                generate_slide_image(slide, output_path)
                
                # Verify file exists after generation
                if not os.path.exists(output_path):
                    raise FileNotFoundError(f"Generated file not found: {output_path}")
                
                # Get file size for logging
                file_size = os.path.getsize(output_path)
                app.logger.info(f"Generated slide {idx}: {output_filename} ({file_size} bytes)")
                
                base_url = request.url_root.rstrip('/')
                
                generated_images.append({
                    'slideNumber': slide.get('slideNumber', idx),
                    'url': f'{base_url}/download/{output_filename}',
                    'filename': output_filename
                })
            except Exception as e:
                # Log error but continue with other slides
                app.logger.error(f"Error generating slide {idx}: {str(e)}")
                raise
        
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
        # Sanitize filename to prevent directory traversal
        filename = os.path.basename(filename)
        file_path = os.path.join(GENERATED_DIR, filename)
        
        # Use absolute path
        file_path = os.path.abspath(file_path)
        
        # Verify file is in the generated directory (security check)
        generated_dir_abs = os.path.abspath(GENERATED_DIR)
        if not file_path.startswith(generated_dir_abs):
            return jsonify({'error': 'Invalid file path'}), 403
        
        if not os.path.exists(file_path):
            app.logger.error(f"File not found: {file_path} (GENERATED_DIR: {generated_dir_abs})")
            # List available files for debugging
            if os.path.exists(GENERATED_DIR):
                available_files = os.listdir(GENERATED_DIR)
                app.logger.info(f"Available files in {GENERATED_DIR}: {available_files}")
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, mimetype='image/png')
    
    except Exception as e:
        app.logger.error(f"Error downloading file {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Test font loading
    test_font = get_font(100, bold=True)
    font_info = {
        'font_type': str(type(test_font)),
        'is_default': 'default' in str(type(test_font)).lower()
    }
    
    # Check available fonts
    available_fonts = []
    font_paths_to_check = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for path in font_paths_to_check:
        if os.path.exists(path):
            available_fonts.append(path)
    
    return jsonify({
        'status': 'healthy',
        'templates': os.listdir(TEMPLATE_DIR) if os.path.exists(TEMPLATE_DIR) else [],
        'font_info': font_info,
        'available_fonts': available_fonts,
        'fonts_dir_exists': os.path.exists(FONTS_DIR),
        'fonts_dir_contents': os.listdir(FONTS_DIR) if os.path.exists(FONTS_DIR) else []
    })

@app.route('/debug/fonts', methods=['GET'])
def debug_fonts():
    """Debug endpoint to check font availability"""
    results = {
        'fonts_dir': FONTS_DIR,
        'fonts_dir_exists': os.path.exists(FONTS_DIR),
        'fonts_dir_contents': [],
        'test_fonts': {},
        'recent_logs': log_buffer[-50:] if len(log_buffer) > 0 else []
    }
    
    if os.path.exists(FONTS_DIR):
        results['fonts_dir_contents'] = os.listdir(FONTS_DIR)
    
    # Test loading fonts
    test_sizes = [60, 100]
    for size in test_sizes:
        for bold in [True, False]:
            key = f"{size}px_{'bold' if bold else 'regular'}"
            try:
                font = get_font(size, bold=bold)
                results['test_fonts'][key] = {
                    'loaded': True,
                    'type': str(type(font)),
                    'is_default': 'default' in str(type(font)).lower()
                }
            except Exception as e:
                results['test_fonts'][key] = {
                    'loaded': False,
                    'error': str(e)
                }
    
    return jsonify(results)

@app.route('/debug/logs', methods=['GET'])
def debug_logs():
    """Get recent logs"""
    return jsonify({
        'total_logs': len(log_buffer),
        'recent_logs': log_buffer[-100:] if len(log_buffer) > 0 else [],
        'message': 'Logs are being captured. Check /debug/fonts for font-specific logs.'
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
            'GET /health': 'Health check',
            'GET /debug/fonts': 'Debug font availability'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
