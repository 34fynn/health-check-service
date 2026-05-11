'''
Health Check Service

A service that monitors 3 endpoints in the background and exposes their health status and metrics via /health
'''

from flask import Flask, jsonify
import requests
import threading
import time
from datetime import datetime, timezone






#The 3 enpoints to be monitored
endpoints = [
    {"name":"Google", "url":"https://www.google.com" },
    {"name": "Netflix", "url" : "https://www.netflix.com"},
    {"name": "Apple", "url": "https://www.apple.com"}
]

#how long to wait for a response before declaring failure
request_timeout = 5 #seconds

#how often the background worker re-checks each endpoint
check_interval = 30 #seconds


#Creating a dictionary to store the latest health data for each endpoint which is updated by the background thread and read by the /health route
health_state = {
    endpoint['name']: {
        "url": endpoint["url"],
        "status": "unknown",
        "status_code":None,
        "response_time_ms":None,
        "last_checked": None,
        "consecutive_failures":0,
        "error":None,
    }
    for endpoint in endpoints
}

#Using a lock to prevent the background thread and the web request thread from reading/writing the dictionary at the same time(preventing race conditions)
state_lock = threading.Lock()


def check_endpoint(endpoint):
    """
    Sends a GET request to a single endpoint and measures whether it responded, how fast it responded and what HTTP status code it returned
    :param endpoint: one of the three endpoints to be monitored
    :return: a dictionary describing the result
    """
    name = endpoint["name"]
    url = endpoint["url"]

    start_time = time.time()
    result = {
        "url": url,
        "last_checked": datetime.now(timezone.utc).isoformat()
    }

    try:
        response = requests.get(url, timeout=request_timeout)
        elapsed_ms = round((time.time() - start_time) * 1000,2)

        #A 2xx response means the service is healthy.
        if 200<=response.status_code and response.status_code<300:
            result["status"] = "up"
        else:
            result["status"] = "degraded"

        result["status_code"] = response.status_code
        result["response_time_ms"] = elapsed_ms
        result ["error"] = None

    except requests.exceptions.Timeout:
        result["status"] = "down"
        result["status_code"] = None
        result["response_time_ms"] = None
        result["error"] = f"Timeout after {request_timeout} seconds"

    #Catching all other requests errors like refused connection etc
    except requests.exceptions.RequestException as e:
        result["status"] = "down"
        result["status_code"] = None
        result["response_time_ms"] = None
        result["error"] = str(e)

    return name, result

def update_state(name, new_result):
    """
    Safely update the shared health_state dictionary using the lock to prevent race conditions
    :param name: name of the endpoint
    :param new_result: dictionary containing the latest health check results
    :return:None
    """
    with state_lock:
        previous = health_state[name]

        #Tracking how many this specific endpoint has failed in a row.
        if new_result["status"] == "down":
            new_result["consecutive_failures"] = previous["consecutive_failures"] + 1
        else:
            new_result["consecutive_failures"] = 0

        health_state[name].update(new_result)

def background_worker():
    """
    Runs forever in a separate thread.At every check_interval second, it checks all endpoints
    :return: None
    """
    while True:
        #threading allows us to check all endpoints in parallel so a slow endpoint does not delay the others
        threads = []
        results = []

        def worker(endpoint):
            name, result = check_endpoint(endpoint)
            results.append((name, result))

        for endpoint in endpoints:
            t = threading.Thread(target=worker, args=(endpoint,))
            t.start()
            threads.append(t)

        #Waiting for all checks to complete before updating state.
        for t in threads:
            t.join()

        for name, result in results:
            update_state(name, result)

        time.sleep(check_interval)

#The Web Server
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    """
    The overall status is computed as:
    1. 'healthy' if all endpoints are up
    2. 'degraded' if some are up and some are down
    3. 'unhealthy' if all endpoints are down
    :return: The latest snapshot of all monitored enpoints
    """
    with state_lock:
        #Taking a thread-safe copy of the current state
        snapshot = {name:dict(data) for name, data in health_state.items()}

    statuses = [info["status"] for info in snapshot.values()]
    up_count = statuses.count("up")
    down_count = statuses.count("down")
    total = len(statuses)

    if up_count == total:
        overall = "healthy"
        http_code = 200
    elif down_count == total:
        overall = "unhealthy"
        http_code = 503  #Service unavailable
    else:
        overall = "degraded"
        http_code = 207 #Partial success

    response = {
        "service": "health-check-service",
        "overall_status": overall,
        "summary": {
            "total": total,
            "up":up_count,
            "down":down_count,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": snapshot,
    }

    return jsonify(response), http_code

@app.route("/", methods=["GET"])
def root():
    """
    A friendly root route so its obvious the service is running
    :return: json response containing service name and a help message along with the status code 200
    """
    return  jsonify({
        "service": "health-check-service",
        "message": "Visit /health to view the status of monitored endpoints."
    }), 200


#Startup
if __name__ == "__main__":
    #Starting the background worker as a daemon thread which will shut down automatically with the main app
    worker_thread = threading.Thread(target=background_worker, daemon=True)
    worker_thread.start()

    #Running the Flask web server
    app.run(host="0.0.0.0", port = 5000, debug = False)







