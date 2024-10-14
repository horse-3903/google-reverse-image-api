import asyncio
from flask import Flask, jsonify, request
from api_util import google_reverse_search_task
from celery import Celery

app = Flask(__name__)

# Configure Celery to use Redis as the message broker
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@app.route("/")
def index():
    return "Hello, world!"

# API route: Create a task for the Google reverse search
@app.route("/api-route/google-reverse-search/search-query")
def search_query():
    query = request.args.get("query")
    num = int(request.args.get("num"))

    # Call the background task
    task = google_reverse_search_task.apply_async(args=[query, num])

    # Return the task ID so the user can check the status
    return jsonify({'task_id': task.id}), 202

# API route: Get the status of the Celery task
@app.route("/api-route/task-status/<task_id>")
def get_task_status(task_id):
    task = google_reverse_search_task.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Pending...'}
    elif task.state == 'SUCCESS':
        response = {'state': task.state, 'result': task.result}
    elif task.state == 'FAILURE':
        response = {'state': task.state, 'status': 'Task failed.'}
    else:
        response = {'state': task.state, 'status': 'Task in progress...'}
    
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)