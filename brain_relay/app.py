"""Local-only Flask assembly and JSON API."""
import hashlib
import json
import os
from pathlib import Path
import secrets
from flask import Flask, jsonify, render_template, request, session, url_for
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from .jobs import Jobs, QueueFull
from .model_client import ModelClient
from .relay import validate_capsule, render_handoff, ValidationError, BudgetExceeded
from .storage import Storage


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=secrets.token_hex(32), MAX_CONTENT_LENGTH=500000,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                      TRUSTED_HOSTS=['localhost','127.0.0.1','[::1]'],
                      DATA_DIR=os.getenv('RELAY_DATA_DIR', str(Path.home()/'.local/share/brain-relay')),
                      MODEL_URL=os.getenv('BRAIN_MODEL_URL',''), MODEL_NAME=os.getenv('BRAIN_MODEL_NAME',''),
                      MODEL_KEY=os.getenv('BRAIN_MODEL_KEY',''))
    app.config.update(config or {})
    store = Storage(app.config['DATA_DIR'])
    model = ModelClient(app.config['MODEL_URL'], app.config['MODEL_NAME'], app.config['MODEL_KEY'])
    jobs = Jobs()
    app.extensions.update(relay_store=store, relay_jobs=jobs)
    example_path = Path(__file__).parent/'examples'/'park-map.json'
    def example():
        return validate_capsule(json.loads(example_path.read_text(encoding='utf-8')))

    @app.before_request
    def guard():
        # Host validation occurs before issuing CSRF tokens (DNS rebinding).
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin = request.headers.get('Origin')
            if request.headers.get('Sec-Fetch-Site') == 'cross-site' or (origin and origin != request.host_url.rstrip('/')):
                return jsonify(code='cross_site', error='Cross-site requests are blocked.'), 403
            token = session.get('csrf_token')
            if not token or not secrets.compare_digest(token, request.headers.get('X-CSRF-Token','')):
                return jsonify(code='csrf', error='Refresh the page, then retry this action.'), 403

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable' if request.path.startswith('/static/') and request.args.get('v') else 'no-store'
        return response

    @app.context_processor
    def assets():
        def asset(filename):
            digest = hashlib.sha256((Path(app.static_folder)/filename).read_bytes()).hexdigest()[:12]
            return url_for('static', filename=filename, v=digest)
        return {'asset': asset}

    @app.errorhandler(ValidationError)
    def invalid(error):
        return jsonify(code='validation', error=str(error)), 400

    @app.errorhandler(BadRequest)
    def bad_json(error):
        return jsonify(code='invalid_request', error='Invalid JSON or untrusted Host. Open the loopback URL and retry.'), 400

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(error):
        return jsonify(code='too_large', error='Request exceeds 500,000 bytes.'), 413

    @app.errorhandler(OSError)
    @app.errorhandler(json.JSONDecodeError)
    def storage_error(error):
        return jsonify(code='storage_error', error='Local data could not be read or saved. Check the data directory and restore a backup if needed.'), 500

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/styleguide')
    def styleguide():
        return render_template('styleguide.html')

    @app.get('/healthz')
    def health():
        return jsonify(status='ok')

    @app.get('/api/bootstrap')
    def bootstrap():
        session.setdefault('csrf_token', secrets.token_hex(32))
        return jsonify(csrf_token=session['csrf_token'], capsules=store.all(), model_configured=model.configured)

    @app.get('/api/example')
    def get_example():
        return jsonify(example())

    @app.post('/api/capsules')
    @app.post('/api/import')
    def save():
        return jsonify(store.save(request.get_json()))

    @app.get('/api/capsules/<capsule_id>/export')
    def export(capsule_id):
        value = store.get(capsule_id)
        if value is None:
            return jsonify(code='not_found', error='Capsule not found.'), 404
        response = jsonify(value)
        response.headers['Content-Disposition'] = f'attachment; filename="capsule-{value["id"]}.json"'
        return response

    @app.post('/api/handoff')
    def handoff():
        body = request.get_json()
        if not isinstance(body, dict) or set(body) != {'capsule','max_chars'}:
            raise ValidationError('Expected capsule and max_chars fields.')
        try:
            text = render_handoff(body['capsule'], body['max_chars'])
        except BudgetExceeded as error:
            return jsonify(code='budget_too_small', error=str(error), required_chars=error.required_chars, max_chars=error.max_chars, omitted=error.omitted), 422
        return jsonify(text=text, chars=len(text))

    @app.post('/api/extract')
    def extract():
        if not model.configured:
            return jsonify(code='model_not_configured', error='No model configured. Create and edit a capsule manually, or use the synthetic example.'), 503
        body = request.get_json()
        if not isinstance(body, dict) or set(body) != {'conversation','title'}:
            raise ValidationError('Expected conversation and title fields.')
        if not isinstance(body['conversation'], str) or not 1 <= len(body['conversation'].strip()) <= 60000:
            raise ValidationError('conversation: use 1–60,000 characters.')
        if not isinstance(body['title'], str) or not 1 <= len(body['title'].strip()) <= 200:
            raise ValidationError('title: use 1–200 characters.')
        try:
            task_id = jobs.submit(lambda: model.extract(body['conversation'], body['title'], example()))
        except QueueFull:
            response = jsonify(code='queue_full', error='Model queue is full. Try again after a running job finishes.')
            response.headers['Retry-After'] = '5'
            return response, 503
        return jsonify(task_id=task_id), 202

    @app.get('/api/jobs/<task_id>')
    def job(task_id):
        item = jobs.get(task_id)
        if item is None:
            return jsonify(code='job_not_found', error='Job expired or server restarted. Run extraction again.'), 404
        return jsonify(item)

    return app
