import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# A public test server
DEFAULT_FHIR_SERVER_URL = "http://hapi.fhir.org/baseR4"

@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html", fhir_server_url=DEFAULT_FHIR_SERVER_URL)

@app.route("/fhir-proxy", methods=["POST"])
def fhir_proxy():
    """
    A proxy to forward FHIR requests to the target server.
    This is used to avoid CORS issues in the browser and add detailed logging.
    """
    try:
        data = request.json
        if data is None:
            app.logger.error("Proxy request received without a JSON body.")
            return jsonify({"error": "A JSON body is required for this request."}), 400
            
        fhir_url = data.get("url")
        method = data.get("method", "GET").upper()
        payload = data.get("payload")

        if not fhir_url:
            app.logger.error("Proxy request received without a fhir_url.")
            return jsonify({"error": "FHIR server URL is required"}), 400

        headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
        
        app.logger.info("="*50)
        app.logger.info(f"Received proxy request for method: {method}")
        app.logger.info(f"Target FHIR URL: {fhir_url}")
        if payload:
            app.logger.info(f"Request Payload: {payload}")
        
        app.logger.info("Forwarding request to FHIR server...")
        
        # Using a timeout is a good practice
        resp = requests.request(method, fhir_url, headers=headers, json=payload, timeout=20)

        app.logger.info(f"Received response from FHIR server with Status: {resp.status_code}")
        app.logger.info(f"Response Headers: {resp.headers}")

        # Check if the response content type is JSON before trying to parse it
        if 'application/fhir+json' in resp.headers.get('Content-Type', '') or 'application/json' in resp.headers.get('Content-Type', ''):
            response_json = resp.json()
            app.logger.info("Response is JSON, returning to client.")
            return jsonify(response_json), resp.status_code
        else:
            # If not JSON, return the raw text. This helps debug non-JSON error responses (e.g., HTML from a gateway).
            response_text = resp.text
            app.logger.warning(f"Response from FHIR server was not JSON. Content-Type: {resp.headers.get('Content-Type')}")
            app.logger.warning(f"Returning raw text response to client. Response Text: {response_text[:500]}...") # Log first 500 chars
            # Return it as part of a JSON error object so the frontend can handle it consistently
            error_payload = {
                "error": "The FHIR server returned a non-JSON response.",
                "status_code": resp.status_code,
                "content_type": resp.headers.get('Content-Type', 'unknown'),
                "response_body": response_text
            }
            return jsonify(error_payload), resp.status_code

    except requests.exceptions.Timeout:
        app.logger.error("Request to FHIR server timed out.")
        return jsonify({"error": "The request to the FHIR server timed out."}), 504 # Gateway Timeout
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error proxying request: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)

