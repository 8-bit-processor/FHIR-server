import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from typing import Dict, Any, Optional, List
import os 
import time
from dotenv import load_dotenv

load_dotenv()

# Import FHIR resources individually
from fhir.resources.bundle import Bundle
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.condition import Condition
from fhir.resources.appointment import Appointment
from fhir.resources.patient import Patient
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.procedure import Procedure


app = Flask(__name__)
CORS(app)

# VA OAuth2 settings
CLIENT_ID = os.getenv("VA_CLIENT_ID")
CLIENT_SECRET = os.getenv("VA_CLIENT_SECRET")
TOKEN_URL = "https://sandbox-api.va.gov/oauth2/health/system/v1/token"

# Cache the access token and its expiration time
token_cache = {
    "access_token": None,
    "expires_at": 0
}

def get_access_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        app.logger.warning("VA_CLIENT_ID or VA_CLIENT_SECRET not set. Using mock data for development.")
        return None
    
    global token_cache
    current_time = time.time()
    
    # Check if we have a valid token that isn't expired (with a 60s buffer)
    if token_cache["access_token"] and token_cache["expires_at"] > current_time + 60:
        return token_cache["access_token"]
        
    app.logger.info("Fetching new access token...")
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    try:
        response = requests.post(TOKEN_URL, data=data, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        
        token_cache["access_token"] = token_data["access_token"]
        # expires_in is usually in seconds
        expires_in = token_data.get("expires_in", 3600)
        token_cache["expires_at"] = current_time + expires_in
        
        return token_cache["access_token"]
    except Exception as e:
        app.logger.error(f"Failed to fetch access token: {e}")
        return None

# A VA sandbox FHIR server
DEFAULT_FHIR_SERVER_URL = "https://sandbox-api.va.gov/services/fhir/v0/r4"

# --- NEW HELPER FUNCTION FOR FHIR REQUESTS ---
def get_fhir_data(fhir_server_url: str, resource_type: str, params: Optional[Dict[str, Any]] = None):
    """
    Makes a GET request to the FHIR server and returns the JSON response.
    """
    url = f"{fhir_server_url}/{resource_type}"
    app.logger.info(f"Attempting to fetch FHIR data from: {url} with params: {params}")
    headers = {"Accept": "application/fhir+json"}
    token = get_access_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
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

@app.route("/progress-note-studio")
def progress_note_studio():
    """Render the Progress Note Studio page."""
    return render_template("progressNoteStudio.html")

@app.route("/patients", methods=["GET"])
def get_patients():
    """
    Returns a list of sample test patients for the VA sandbox.
    Note: VA API requires specific patient IDs; this is a hardcoded list for demo.
    """
    # Hardcoded test patients from VA sandbox test data
    test_patients = [
        {"id": "32000225", "name": "Sheba703 Harris789"},
        {"id": "5000335", "name": "Mariano761 Ruelas156"},
        {"id": "25000126", "name": "Lorenzo669 Valentín837"},
        {"id": "2000190", "name": "Luis923 Mayer370"},
        {"id": "25000285", "name": "Dorian295 Friesen796"},
    ]
    return jsonify(test_patients), 200

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
        token = get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        app.logger.info("="*50)
        app.logger.info(f"Received proxy request for method: {method}")
        app.logger.info(f"Target FHIR URL: {fhir_url}")
        if payload:
            app.logger.info(f"Request Payload: {payload}")
        
        app.logger.info("Forwarding request to FHIR server...")
        
        # Using a timeout is a good practice
        resp = requests.request(method, fhir_url, headers=headers, json=payload, timeout=20)

        app.logger.info(f"Received response from FHIR server with Status: {resp.status_code}")
        
        # If the response is JSON, return it as JSON
        content_type = resp.headers.get('Content-Type', '')
        if 'application/fhir+json' in content_type or 'application/json' in content_type:
            return jsonify(resp.json()), resp.status_code
        
        # If it's a Binary resource or plain text, return the raw data/text
        return resp.text, resp.status_code

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
    token = get_access_token()
    if not token:
        # Return mock data for development
        mock_medications = [
            {
                "id": "med1",
                "medication": "Lisinopril 10mg",
                "status": "active",
                "intent": "order",
                "authoredOn": "2024-01-15"
            },
            {
                "id": "med2", 
                "medication": "Metformin 500mg",
                "status": "active",
                "intent": "order",
                "authoredOn": "2024-01-15"
            }
        ]
        return jsonify(mock_medications), 200
    
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
    token = get_access_token()
    if not token:
        # Return mock data for development
        mock_problems = [
            {
                "id": "prob1",
                "clinicalStatus": "active",
                "verificationStatus": "confirmed",
                "problem": "Hypertension",
                "recordedDate": "2023-06-01"
            },
            {
                "id": "prob2",
                "clinicalStatus": "active",
                "verificationStatus": "confirmed", 
                "problem": "Type 2 Diabetes",
                "recordedDate": "2023-08-15"
            }
        ]
        return jsonify(mock_problems), 200
    
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
    token = get_access_token()
    if not token:
        # Return mock data for development
        mock_appointments = [
            {
                "id": "appt1",
                "status": "booked",
                "type": "Primary Care Visit",
                "start": "2024-02-15T10:00:00Z",
                "end": "2024-02-15T10:30:00Z",
                "description": "Routine checkup",
                "practitioners": ["Dr. Smith"]
            },
            {
                "id": "appt2",
                "status": "booked",
                "type": "Cardiology Consultation", 
                "start": "2024-02-20T14:00:00Z",
                "end": "2024-02-20T14:30:00Z",
                "description": "Follow-up on hypertension",
                "practitioners": ["Dr. Johnson"]
            }
        ]
        return jsonify(mock_appointments), 200
    
    params = {"patient": patient_id}
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
    token = get_access_token()
    if not token:
        # Return mock data for development
        mock_reports = [
            {
                "id": "diag1",
                "status": "final",
                "type": "Chest X-Ray",
                "effectiveDateTime": "2024-01-10T08:00:00Z",
                "conclusion": "No acute findings",
                "performers": ["Dr. Radiology"]
            },
            {
                "id": "diag2",
                "status": "final",
                "type": "EKG",
                "effectiveDateTime": "2024-01-12T09:30:00Z", 
                "conclusion": "Normal sinus rhythm",
                "performers": ["Dr. Cardiology"]
            }
        ]
        return jsonify(mock_reports), 200
    
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
    token = get_access_token()
    if not token:
        # Return mock data for development
        mock_procedures = [
            {
                "id": "proc1",
                "status": "completed",
                "type": "Colonoscopy",
                "performedDateTime": "2024-01-05T10:00:00Z",
                "reasonCode": "Screening",
                "performers": ["Dr. Gastroenterology"]
            },
            {
                "id": "proc2",
                "status": "completed",
                "type": "Cardiac Catheterization",
                "performedDateTime": "2024-01-08T14:00:00Z",
                "reasonCode": "Chest pain evaluation",
                "performers": ["Dr. Cardiology"]
            }
        ]
        return jsonify(mock_procedures), 200
    
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
    token = get_access_token()
    if not token:
        # Return mock data for development
        mock_labs = [
            {
                "id": "lab1",
                "status": "final",
                "type": "Complete Blood Count",
                "effectiveDateTime": "2024-01-15T07:00:00Z",
                "conclusion": "Within normal limits",
                "performers": ["Lab Corp"],
                "results": ["WBC: 7.2 K/uL", "Hgb: 14.5 g/dL", "Plt: 285 K/uL"]
            },
            {
                "id": "lab2",
                "status": "final",
                "type": "Comprehensive Metabolic Panel",
                "effectiveDateTime": "2024-01-15T07:00:00Z",
                "conclusion": "Mild hyperglycemia",
                "performers": ["Lab Corp"],
                "results": ["Glucose: 145 mg/dL", "Creatinine: 0.9 mg/dL", "eGFR: 85 mL/min"]
            }
        ]
        return jsonify(mock_labs), 200
    
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


@app.route("/patient/<string:patient_id>/allergies", methods=["GET"])
def get_patient_allergies(patient_id: str):
    """
    Fetches allergies for a given patient.
    """
    token = get_access_token()
    if not token:
        mock_allergies = [
            {"id": "alg1", "substance": "Penicillin", "status": "active", "criticality": "high", "type": "allergy"},
            {"id": "alg2", "substance": "Peanuts", "status": "active", "criticality": "unable-to-assess", "type": "intolerance"}
        ]
        return jsonify(mock_allergies), 200

    params = {"patient": patient_id}
    bundle = get_fhir_data(DEFAULT_FHIR_SERVER_URL, "AllergyIntolerance", params)

    if not bundle or not bundle.get("entry"):
        return jsonify({"message": f"No allergies found for patient {patient_id}"}), 200

    allergies: List[Dict[str, Any]] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "AllergyIntolerance":
            substance = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Substance")
            allergies.append({
                "id": resource.get("id"),
                "substance": substance,
                "status": resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("display", "active"),
                "criticality": resource.get("criticality"),
                "type": resource.get("type")
            })
    return jsonify(allergies), 200

@app.route("/patient/<string:patient_id>/vitals", methods=["GET"])
def get_patient_vitals(patient_id: str):
    """
    Fetches vital signs for a given patient.
    """
    token = get_access_token()
    if not token:
        mock_vitals = [
            {"id": "vit1", "code": "Blood Pressure", "value": "120/80", "unit": "mmHg", "date": "2024-01-15"},
            {"id": "vit2", "code": "Heart Rate", "value": "72", "unit": "bpm", "date": "2024-01-15"}
        ]
        return jsonify(mock_vitals), 200

    # Searching for observations with category 'vital-signs'
    params = {"patient": patient_id, "category": "vital-signs"}
    bundle = get_fhir_data(DEFAULT_FHIR_SERVER_URL, "Observation", params)

    if not bundle or not bundle.get("entry"):
        return jsonify({"message": f"No vitals found for patient {patient_id}"}), 200

    vitals: List[Dict[str, Any]] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Observation":
            code_text = resource.get("code", {}).get("text") or resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Vital")

            value = ""
            unit = ""
            if "valueQuantity" in resource:
                value = resource["valueQuantity"].get("value")
                unit = resource["valueQuantity"].get("unit")
            elif "valueCodeableConcept" in resource:
                value = resource["valueCodeableConcept"].get("coding", [{}])[0].get("display", "")
            elif "component" in resource: # Handle BP which is often in components
                parts = []
                for comp in resource["component"]:
                    c_val = comp.get("valueQuantity", {}).get("value")
                    c_unit = comp.get("valueQuantity", {}).get("unit", "")
                    parts.append(f"{c_val}{c_unit}")
                value = " / ".join(parts)

            vitals.append({
                "id": resource.get("id"),
                "code": code_text,
                "value": value,
                "unit": unit,
                "date": resource.get("effectiveDateTime") or resource.get("issued")
            })
    return jsonify(vitals), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)


