import os
import tempfile
import threading

from flask import Flask, render_template, request, jsonify, send_file

from jobs import JobManager


def create_app(job_manager, counter_file='counter.txt'):
    app = Flask(__name__)
    counter = {'value': 10}
    counter_lock = threading.Lock()

    if counter_file and os.path.exists(counter_file):
        try:
            with open(counter_file) as f:
                counter['value'] = int(f.read().strip())
        except (OSError, ValueError):
            pass

    def increment_counter():
        with counter_lock:
            counter['value'] += 1
            if counter_file:
                with open(counter_file, 'w') as f:
                    f.write(str(counter['value']))

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/start', methods=['POST'])
    def start_survey():
        data = request.json or {}
        codes = data.get('codes') or ([data['code']] if data.get('code') else [])
        codes = [c for c in codes if c and c.strip()]
        if not codes:
            return jsonify({'error': 'No code provided'}), 400

        job_ids, errors = [], []
        for code in codes:
            try:
                job_ids.append(job_manager.submit(code, on_success=increment_counter).id)
            except ValueError as e:
                errors.append(str(e))

        if not job_ids:
            return jsonify({'error': '; '.join(errors)}), 400
        return jsonify({'success': True, 'job_ids': job_ids, 'errors': errors})

    @app.route('/api/jobs', methods=['GET'])
    def list_jobs():
        return jsonify({
            'jobs': [j.to_dict() for j in job_manager.list()],
            'global_counter': counter['value'],
        })

    @app.route('/api/jobs/<job_id>', methods=['DELETE'])
    def dismiss_job(job_id):
        return jsonify({'success': job_manager.remove(job_id)})

    @app.route('/api/screenshot/<filename>', methods=['GET'])
    def get_screenshot(filename):
        filepath = os.path.join(tempfile.gettempdir(), os.path.basename(filename))
        if os.path.exists(filepath):
            return send_file(filepath, mimetype='image/png')
        return jsonify({'error': 'Screenshot not found'}), 404

    return app


if __name__ == '__main__':
    from survey_automator import make_automator
    max_browsers = int(os.environ.get('MAX_BROWSERS', '10'))
    app = create_app(JobManager(make_automator, max_concurrent=max_browsers))
    print(f"Starting server on port 5001 (up to {max_browsers} surveys at once)...")
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
