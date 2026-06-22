from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import logging
from io import BytesIO

# Local conversion libraries
try:
    from docx2pdf import convert
    HAS_DOCX2PDF = True
except ImportError:
    HAS_DOCX2PDF = False

try:
    from pdf2docx import Converter
    HAS_PDF2DOCX = True
except ImportError:
    HAS_PDF2DOCX = False

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pikepdf
    HAS_PIKEPDF = True
except ImportError:
    HAS_PIKEPDF = False

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
ILOVEPDF_PUBLIC_KEY = os.getenv("ILOVEPDF_PUBLIC_KEY")
ILOVEPDF_SECRET_KEY = os.getenv("ILOVEPDF_SECRET_KEY")
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt', 'jpg', 'jpeg', 'png'}
API_REQUEST_TIMEOUT = 60  # seconds

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ========== LOCAL CONVERSION FUNCTIONS ==========

import os
import subprocess

def convert_word_to_pdf_local(input_path, output_path):
    """Convert Word document to PDF locally using LibreOffice"""
    try:
        # Get absolute paths
        abs_input = os.path.abspath(input_path)
        abs_output = os.path.abspath(output_path)
        output_dir = os.path.dirname(abs_output)
        
        # 1. Run the LibreOffice conversion
        subprocess.run(
            ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', output_dir, abs_input],
            check=True,
            capture_output=True,
            text=True
        )
        
        # 2. Figure out what LibreOffice actually named the file
        # It takes the original file name and just changes the extension to .pdf
        base_name = os.path.splitext(os.path.basename(abs_input))[0]
        libreoffice_generated_file = os.path.join(output_dir, f"{base_name}.pdf")
        
        # 3. Rename it to match the requested output_path if they are different
        if libreoffice_generated_file != abs_output and os.path.exists(libreoffice_generated_file):
            os.replace(libreoffice_generated_file, abs_output)
            
        # 4. Final verification
        if os.path.exists(abs_output):
            logger.info(f"Local conversion successful: {input_path} -> {output_path}")
            return True, None
        else:
            return False, "Conversion seemed to run, but the PDF file was not found."

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        logger.error(f"Local Word to PDF conversion error: {error_msg}")
        return False, f"LibreOffice error: {error_msg}"
    except Exception as e:
        logger.error(f"Local Word to PDF conversion error: {str(e)}")
        return False, str(e)

def convert_pdf_to_word_local(input_path, output_path):
    """Convert PDF to Word locally using pdf2docx"""
    try:
        if not HAS_PDF2DOCX:
            return False, "pdf2docx library not available"
        
        cv = Converter(input_path)
        cv.convert(output_path)
        cv.close()
        logger.info(f"Local conversion: {input_path} -> {output_path}")
        return True, None
    except Exception as e:
        logger.error(f"Local PDF to Word conversion error: {str(e)}")
        return False, str(e)

def compress_pdf_local(input_path, output_path):
    """Compress PDF locally using pikepdf"""
    try:
        if not HAS_PIKEPDF:
            return False, "pikepdf library not available"
        
        with pikepdf.open(input_path) as pdf:
            pdf.save(output_path, compress_streams=True)
        
        logger.info(f"Local compression: {input_path} -> {output_path}")
        return True, None
    except Exception as e:
        logger.error(f"Local PDF compression error: {str(e)}")
        return False, str(e)

#Home Page

@app.route("/")
def home():
    return render_template("index.html")

#Word to PDF Page

@app.route("/word-to-pdf")
def word_to_pdf():
    return render_template("word_to_pdf.html")

#PDF to Word Page

@app.route("/pdf-to-word")
def pdf_to_word():
    return render_template("pdf_to_word.html")

#Compress PDF Page

@app.route("/compress-pdf")
def compress_pdf():
    return render_template("compress_pdf.html")

# ========== DEBUG ENDPOINT ==========

@app.route("/api/health", methods=['GET'])
def health_check():
    """Health check endpoint to verify API configuration"""
    return jsonify({
        "status": "ok",
        "has_public_key": bool(ILOVEPDF_PUBLIC_KEY),
        "has_secret_key": bool(ILOVEPDF_SECRET_KEY),
        "api_timeout": API_REQUEST_TIMEOUT,
        "message": "FileMorph API is running"
    }), 200

@app.route("/api/test-connection", methods=['POST'])
def test_api_connection():
    """Test connection to iLoveAPI"""
    if not ILOVEPDF_PUBLIC_KEY:
        return jsonify({"error": "API key not configured"}), 400
    
    try:
        logger.info("Testing iLoveAPI connection...")
        
        # Test the task creation endpoint
        url = f"{ILOVEPDF_BASE_URL}/start"
        headers = {
            "Authorization": f"Bearer {ILOVEPDF_PUBLIC_KEY}",
            "User-Agent": "FileMorph/1.0"
        }
        data = {"tool": "officepdf"}
        
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=API_REQUEST_TIMEOUT
        )
        
        logger.debug(f"API Response Status: {response.status_code}")
        logger.debug(f"API Response: {response.text[:200]}")
        
        return jsonify({
            "status": response.status_code,
            "url": url,
            "message": response.text[:300],
            "test": "API connection test completed"
        }), 200
        
    except Exception as e:
        logger.error(f"API connection test failed: {str(e)}")
        return jsonify({
            "error": str(e),
            "message": "API connection test failed"
        }), 500

# ========== FORM SUBMISSION ROUTES (for HTML form compatibility) ==========

@app.route("/convert-word-to-pdf", methods=['POST'])
def convert_word_to_pdf_form():
    """Handle Word to PDF conversion using local libraries"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"Converting Word to PDF (local): {filename}")
        
        # Generate output filename
        output_filename = f"converted_{filename.rsplit('.', 1)[0]}.pdf"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # Perform local conversion
        success, error = convert_word_to_pdf_local(filepath, output_path)
        
        if success:
            # Clean up original file
            os.remove(filepath)
            logger.info(f"Successfully converted: {filename} -> {output_filename}")
            return send_file(output_path, as_attachment=True, download_name=output_filename)
        else:
            if os.path.exists(filepath):
                os.remove(filepath)
            logger.error(f"Conversion error: {error}")
            return jsonify({"error": f"Conversion failed: {error}"}), 500
        
    except Exception as e:
        logger.error(f"Error in word-to-pdf conversion: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/convert-pdf-to-word", methods=['POST'])
def convert_pdf_to_word_form():
    """Handle PDF to Word conversion using local libraries"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.endswith('.pdf'):
            return jsonify({"error": "Please upload a PDF file"}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"Converting PDF to Word (local): {filename}")
        
        # Generate output filename
        output_filename = f"converted_{filename.rsplit('.', 1)[0]}.docx"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # Perform local conversion
        success, error = convert_pdf_to_word_local(filepath, output_path)
        
        if success:
            os.remove(filepath)
            logger.info(f"Successfully converted: {filename} -> {output_filename}")
            return send_file(output_path, as_attachment=True, download_name=output_filename)
        else:
            if os.path.exists(filepath):
                os.remove(filepath)
            logger.error(f"Conversion error: {error}")
            return jsonify({"error": f"Conversion failed: {error}"}), 500
        
    except Exception as e:
        logger.error(f"Error in pdf-to-word conversion: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/compress-pdf-file", methods=['POST'])
def compress_pdf_file_form():
    """Handle PDF compression using local libraries"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.endswith('.pdf'):
            return jsonify({"error": "Please upload a PDF file"}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"Compressing PDF (local): {filename}")
        
        # Get original file size
        original_size = os.path.getsize(filepath)
        
        # Generate output filename
        output_filename = f"compressed_{filename}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # Perform local compression
        success, error = compress_pdf_local(filepath, output_path)
        
        if success:
            compressed_size = os.path.getsize(output_path)
            reduction_percent = round((1 - compressed_size / original_size) * 100, 2) if original_size > 0 else 0
            
            os.remove(filepath)
            logger.info(f"Successfully compressed: {filename} -> {output_filename} ({reduction_percent}% reduction)")
            
            # Return file with compression stats
            response = send_file(output_path, as_attachment=True, download_name=output_filename)
            response.headers['X-Original-Size'] = str(original_size)
            response.headers['X-Compressed-Size'] = str(compressed_size)
            response.headers['X-Reduction-Percent'] = str(reduction_percent)
            return response
        else:
            if os.path.exists(filepath):
                os.remove(filepath)
            logger.error(f"Compression error: {error}")
            return jsonify({"error": f"Compression failed: {error}"}), 500
        
    except Exception as e:
        logger.error(f"Error in compress-pdf conversion: {str(e)}")
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )