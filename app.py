print("Starting app.py...")
from flask import Flask, render_template, request, jsonify, send_file
import os
import uuid
import threading
import time
from werkzeug.utils import secure_filename
print("Importing SurveyAutomator...")
from survey_automator import SurveyAutomator

print("Initializing Flask app...")
app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['UPLOAD_FOLDER'] = 'uploads'
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Removed: scan upload not needed

# Counter Logic
COUNTER_FILE = 'counter.txt'
SUCCESS_COUNTER = 10

def load_counter():
    global SUCCESS_COUNTER
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, 'r') as f:
                val = int(f.read().strip())
                SUCCESS_COUNTER = val
        except:
            pass
    else:
        save_counter()

def save_counter():
    with open(COUNTER_FILE, 'w') as f:
        f.write(str(SUCCESS_COUNTER))

def increment_counter():
    global SUCCESS_COUNTER
    SUCCESS_COUNTER += 1
    save_counter()
    print(f"Global Success Counter: {SUCCESS_COUNTER}")

load_counter()

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

# Session Store: session_id -> SurveyAutomator instance
active_sessions = {}

def cleanup_sessions():
    """Background task to remove old sessions"""
    while True:
        try:
            time.sleep(300) # Check every 5 minutes
            # Logic to remove old sessions could go here
            # For now, we'll just keep them in memory as they are small objects
            # Real implementation would check last_activity timestamp
        except:
            pass

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

# /api/scan endpoint removed

@app.route('/api/start', methods=['POST'])
def start_survey():
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    # Create new session
    session_id = str(uuid.uuid4())
    automator = SurveyAutomator()
    active_sessions[session_id] = automator
    
    # Run in background thread
    thread = threading.Thread(target=automator.start_survey, args=(code,), kwargs={'on_success': increment_counter})
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True, 
        'message': 'Survey started',
        'session_id': session_id
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    session_id = request.args.get('session_id')
    
    if session_id == 'init_check':
         return jsonify({
            'status': 'Idle',
            'progress': 0,
            'logs': [],
            'image': None,
            'result_code': None,
            'is_running': False,
            'global_counter': SUCCESS_COUNTER
        })

    if not session_id or session_id not in active_sessions:
        return jsonify({'error': 'Invalid session'}), 404
        
    automator = active_sessions[session_id]
    
    # Extract just the filename from the full path
    image_filename = None
    if automator.result_image_path:
        image_filename = os.path.basename(automator.result_image_path)
    
    return jsonify({
        'status': automator.status,
        'progress': automator.progress,
        'logs': automator.logs,
        'image': image_filename,
        'result_code': automator.result_code,
        'result_code': automator.result_code,
        'is_running': automator.is_running,
        'global_counter': SUCCESS_COUNTER
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
    print("Starting server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=False)
