import requests
from flask import Flask, request, jsonify, render_template
from typing import Type, Dict, Any, Optional, List
from pydantic import BaseModel 

# Import FHIR resources individually
from fhir.resources.bundle import Bundle
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.condition import Condition
from fhir.resources.appointment import Appointment
from fhir.resources.patient import Patient
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.procedure import Procedure


app = Flask(__name__)

# A public test server
DEFAULT_FHIR_SERVER_URL = "http://hapi.fhir.org/baseR4"

# Map resource type strings to their model classes for dynamic parsing
RESOURCE_MAP: dict[str, Type[BaseModel]] = {
    "Bundle": Bundle,
    "Patient": Patient,
    "MedicationRequest": MedicationRequest,
    "Condition": Condition,
    "Appointment": Appointment,
    "DiagnosticReport": DiagnosticReport,
    "Procedure": Procedure,
}

# --- NEW HELPER FUNCTION FOR FHIR REQUESTS ---
def get_fhir_data(fhir_server_url: str, resource_type: str, params: Optional[Dict[str, Any]] = None):
    """
    Makes a GET request to the FHIR server and returns the JSON response.
    """
    url = f"{fhir_server_url}/{resource_type}"
    app.logger.info(f"Attempting to fetch FHIR data from: {url} with params: {params}")
    headers = {"Accept": "application/fhir+json"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status() # Raise an exception for HTTP errors
        app.logger.info(f"Successfully fetched data, status: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching FHIR data from {url}: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Error parsing JSON response from {url}: {e}")
        return None

@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html", fhir_server_url=DEFAULT_FHIR_SERVER_URL)

@app.route("/patients", methods=["GET"])
def get_patients():
    """
    Fetches a list of sample patients to populate the dropdown.
    """
    params = {"_count": 20} # Get up to 20 patients
    bundle = get_fhir_data(DEFAULT_FHIR_SERVER_URL, "Patient", params)

    if not bundle or not bundle.get("entry"):
        return jsonify([]), 200

    patients: List[Dict[str, Any]] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            patient_id = resource.get("id")
            
            name_data = resource.get("name", [{}])[0]
            given_name = " ".join(name_data.get("given", []))
            family_name = name_data.get("family", "")
            
            display_name = f"{given_name} {family_name}".strip()
            if not display_name:
                display_name = f"Patient/{patient_id}"
            else:
                display_name = f"{display_name} (ID: {patient_id})"

            patients.append({"id": patient_id, "name": display_name})
            
    return jsonify(patients), 200

@app.route("/fhir-proxy", methods=["POST"])
def fhir_proxy():
    """
    A proxy to forward FHIR requests to the target server.
    This is used to avoid CORS issues in the browser and add detailed logging.
    It now aims to return FHIR resources as parsed by fhir.resources when possible.
    """
    try:
        data = request.json
        if data is None:
            app.logger.error("Proxy request received without a JSON body.")
            return jsonify({"error": "A JSON body is required for this request."}), 400
            
        fhir_url = data.get("url")
        method = data.get("method", "GET").upper()
        payload = data.get("payload") # This would be used for POST/PUT
        resource_type_param = data.get("resource_type") # e.g., 'Patient', 'MedicationRequest'
        params = data.get("params") # For GET requests

        if not fhir_url and not resource_type_param: # Need at least one way to specify target
             app.logger.error("Proxy request received without a fhir_url or resource_type.")
             return jsonify({"error": "FHIR server URL or resource_type is required"}), 400

        # If a resource_type and params are provided, use the new helper function for GET
        if method == "GET" and resource_type_param:
            app.logger.info(f"Proxy using get_fhir_data for {resource_type_param} with params {params}")
            bundle = get_fhir_data(DEFAULT_FHIR_SERVER_URL, resource_type_param, params)
            if bundle:
                return jsonify(bundle), 200 # Just return the JSON
            else:
                return jsonify({"error": "Failed to fetch or parse FHIR data"}), 500


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
            return jsonify(response_json), resp.status_code
        else:
            # If not JSON, return the raw text.
            response_text = resp.text
            app.logger.warning(f"Response from FHIR server was not JSON. Content-Type: {resp.headers.get('Content-Type')}")
            error_payload: Dict[str, Any] = {
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

# --- ROUTES FOR SPECIFIC FHIR DATA ---


@app.route("/patient/<string:patient_id>/medications", methods=["GET"])
def get_patient_medications(patient_id: str):
    """
    Fetches medication requests for a given patient.
    """
    params = {"patient": patient_id}
    bundle = get_fhir_data(DEFAULT_FHIR_SERVER_URL, "MedicationRequest", params)

    if not bundle or not bundle.get("entry"):
        return jsonify({"message": f"No medication requests found for patient {patient_id}"}), 200

    medications: List[Dict[str, Any]] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "MedicationRequest":
            medication_name = resource.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "Unknown Medication")
            medications.append({
                "id": resource.get("id"),
                "status": resource.get("status"),
                "medication": medication_name,
                "intent": resource.get("intent"),
                "authoredOn": resource.get("authoredOn"),
                "requester": resource.get("requester", {}).get("display")
            })
    return jsonify(medications), 200

@app.route("/patient/<string:patient_id>/problems", methods=["GET"])
def get_patient_problems(patient_id: str):
    """
    Fetches problems (conditions) for a given patient.
    """
    params = {"patient": patient_id}
    bundle = get_fhir_data(DEFAULT_FHIR_SERVER_URL, "Condition", params)

    if not bundle or not bundle.get("entry"):
        return jsonify({"message": f"No problems found for patient {patient_id}"}), 200

    problems: List[Dict[str, Any]] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Condition":
            problem_name = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Condition")
            
            clinical_status = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("display")
            verification_status = resource.get("verificationStatus", {}).get("coding", [{}])[0].get("display")

            problems.append({
                "id": resource.get("id"),
                "clinicalStatus": clinical_status,
                "verificationStatus": verification_status,
                "problem": problem_name,
                "recordedDate": resource.get("recordedDate")
            })
    return jsonify(problems), 200


@app.route("/patient/<string:patient_id>/appointments", methods=["GET"])
def get_patient_appointments(patient_id: str):
    """
    Fetches appointments for a given patient.
    """
    params = {"actor": f"Patient/{patient_id}"}
    bundle = get_fhir_data(DEFAULT_FHIR_SERVER_URL, "Appointment", params)

    if not bundle or not bundle.get("entry"):
        return jsonify({"message": f"No appointments found for patient {patient_id}"}), 200

    appointments: List[Dict[str, Any]] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Appointment":
            appointment_type = resource.get("serviceType", [{}])[0].get("coding", [{}])[0].get("display", "Unknown Type")
            
            practitioners: List[str] = []
            for participant in resource.get("participant", []):
                actor = participant.get("actor", {})
                if "Practitioner" in actor.get("reference", ""):
                    practitioners.append(actor.get("display", actor.get("reference")))

            appointments.append({
                "id": resource.get("id"),
                "status": resource.get("status"),
                "type": appointment_type,
                "start": resource.get("start"),
                "end": resource.get("end"),
                "description": resource.get("description"),
                "practitioners": practitioners
            })
    return jsonify(appointments), 200

@app.route("/patient/<string:patient_id>/diagnostic-reports", methods=["GET"])
def get_patient_diagnostic_reports(patient_id: str):
    """
    Fetches diagnostic reports (radiology, pathology, etc.) for a given patient.
    """
    params = {"patient": patient_id}
    bundle = get_fhir_data(DEFAULT_FHIR_SERVER_URL, "DiagnosticReport", params)

    if not bundle or not bundle.get("entry"):
        return jsonify({"message": f"No diagnostic reports found for patient {patient_id}"}), 200

    reports: List[Dict[str, Any]] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "DiagnosticReport":
            report_type = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Type")
            
            performers: List[str] = []
            for performer in resource.get("performer", []):
                performers.append(performer.get("display", performer.get("reference")))

            reports.append({
                "id": resource.get("id"),
                "status": resource.get("status"),
                "type": report_type,
                "effectiveDateTime": resource.get("effectiveDateTime"),
                "conclusion": resource.get("conclusion"),
                "performers": performers
            })
    return jsonify(reports), 200

@app.route("/patient/<string:patient_id>/procedures", methods=["GET"])
def get_patient_procedures(patient_id: str):
    """
    Fetches procedures (surgery, colonoscopy, etc.) for a given patient.
    """
    params = {"patient": patient_id}
    bundle = get_fhir_data(DEFAULT_FHIR_SERVER_URL, "Procedure", params)

    if not bundle or not bundle.get("entry"):
        return jsonify({"message": f"No procedures found for patient {patient_id}"}), 200

    procedures: List[Dict[str, Any]] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Procedure":
            procedure_type = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Procedure")
            
            performers: List[str] = []
            for performer in resource.get("performer", []):
                actor = performer.get("actor", {})
                performers.append(actor.get("display", actor.get("reference")))

            reason = resource.get("reasonCode", [{}])[0].get("coding", [{}])[0].get("display")

            procedures.append({
                "id": resource.get("id"),
                "status": resource.get("status"),
                "type": procedure_type,
                "performedDateTime": resource.get("performedDateTime"),
                "reasonCode": reason,
                "performers": performers
            })
    return jsonify(procedures), 200


@app.route("/patient/<string:patient_id>/labs", methods=["GET"])
def get_patient_labs(patient_id: str):
    """
    Fetches lab reports for a given patient by searching for
    DiagnosticReports with the category 'LAB'.
    """
    params = {"patient": patient_id, "category": "LAB"}
    bundle = get_fhir_data(DEFAULT_FHIR_SERVER_URL, "DiagnosticReport", params)

    if not bundle or not bundle.get("entry"):
        return jsonify({"message": f"No lab reports found for patient {patient_id}"}), 200

    reports: List[Dict[str, Any]] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "DiagnosticReport":
            report_type = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Lab Report")
            
            performers: List[str] = []
            for performer in resource.get("performer", []):
                performers.append(performer.get("display", performer.get("reference")))

            # Also extract the Observation results if they are present
            results: List[str] = []
            for result_ref in resource.get("result", []):
                 results.append(result_ref.get("display", result_ref.get("reference")))

            reports.append({
                "id": resource.get("id"),
                "status": resource.get("status"),
                "type": report_type,
                "effectiveDateTime": resource.get("effectiveDateTime"),
                "conclusion": resource.get("conclusion"),
                "performers": performers,
                "results": results, # Add the results to the response
            })
    return jsonify(reports), 200





if __name__ == "__main__":
    app.run(debug=True, port=5000)


