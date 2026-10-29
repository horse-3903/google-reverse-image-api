import os
import tempfile

from flask import Flask, jsonify, request
from api_util import celery, google_reverse_image_task, google_reverse_search_task

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello, world!"

# API route: Create a task for the Google reverse search
@app.route("/api-route/google-reverse-search/search-query")
def search_query():
    query = request.args.get("query")
    if not query:
        return jsonify({'error': 'query is required'}), 400
    try:
        num = int(request.args.get("num", 10))
    except ValueError:
        return jsonify({'error': 'num must be an integer'}), 400
    if num < 0:
        return jsonify({'error': 'num must be 0 (all results) or greater'}), 400

    # Call the background task
    task = google_reverse_search_task.apply_async(args=[query, num])

    # Return the task ID so the user can check the status
    return jsonify({'task_id': task.id}), 202

# API route: Create a task for a Google Lens reverse image search
@app.route("/api-route/google-reverse-search/search-image", methods=["POST"])
def search_image():
    image = request.files.get("image")
    if not image:
        return jsonify({'error': 'image file is required'}), 400
    try:
        num = int(request.form.get("num", 10))
    except ValueError:
        return jsonify({'error': 'num must be an integer'}), 400
    if num < 0:
        return jsonify({'error': 'num must be 0 (all results) or greater'}), 400

    fd, path = tempfile.mkstemp(suffix=os.path.splitext(image.filename or "")[1])
    os.close(fd)
    image.save(path)

    task = google_reverse_image_task.apply_async(args=[path, num])
    return jsonify({'task_id': task.id}), 202

# API route: Get the status of the Celery task
@app.route("/api-route/task-status/<task_id>")
def get_task_status(task_id):
    task = celery.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Pending...'}
    elif task.state == 'SUCCESS':
        response = {'state': task.state, 'result': task.result}
    elif task.state == 'FAILURE':
        response = {'state': task.state, 'status': 'Task failed.', 'error': str(task.result)}
    else:
        response = {'state': task.state, 'status': 'Task in progress...'}
    
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)