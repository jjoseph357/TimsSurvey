print("Starting app.py...")
from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
print("Importing SurveyAutomator...")
from survey_automator import SurveyAutomator
import threading

print("Initializing Flask app...")
app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

print("Initializing Automator...")
automator = SurveyAutomator()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def scan_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            code, method = automator.scan_image(filepath)
            os.remove(filepath)
            
            if code:
                return jsonify({'success': True, 'code': code, 'method': method})
            else:
                return jsonify({'success': False, 'error': 'Could not detect code'}), 404
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_survey():
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    if automator.is_running:
        return jsonify({'error': 'Survey already running'}), 400
        
    # Run in background thread
    thread = threading.Thread(target=automator.start_survey, args=(code,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Survey started in background'})

@app.route('/api/status', methods=['GET'])
def get_status():
    # Extract just the filename from the full path
    image_filename = None
    if automator.result_image_path:
        image_filename = os.path.basename(automator.result_image_path)
    
    return jsonify({
        'status': automator.status,
        'progress': automator.progress,
        'logs': automator.logs,
        'image': image_filename,  # Just the filename
        'result_code': automator.result_code,
        'is_running': automator.is_running
    })

@app.route('/api/screenshot/<filename>', methods=['GET'])
def get_screenshot(filename):
    """Serve screenshot from temp directory"""
    import tempfile
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/png')
    else:
        return jsonify({'error': 'Screenshot not found'}), 404

if __name__ == '__main__':
    # Run on 0.0.0.0 to be accessible from other devices (mobile)
    # Disable debug mode to prevent reloader issues on Windows
    # Using port 5001 instead of 5000 due to zombie process on 5000
    print("Starting server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=False)
