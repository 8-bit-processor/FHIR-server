document.addEventListener('DOMContentLoaded', () => {
    const fhirServerInput = document.getElementById('fhir-server');
    const responseArea = document.getElementById('response-area');
    const formattedResponseArea = document.getElementById('formatted-response-area');
    const patientIdInput = document.getElementById('patient-id-input');
    const patientIdDatalist = document.getElementById('patient-id-list');

    /**
     * Fetches patients and populates the datalist for autocomplete.
     */
    async function populatePatientDatalist() {
        try {
            const response = await fetch('/patients');
            if (!response.ok) {
                throw new Error(`Failed to fetch patients with status: ${response.status}`);
            }
            const patients = await response.json();

            patientIdDatalist.innerHTML = ''; // Clear existing options
            patients.forEach(patient => {
                const option = document.createElement('option');
                option.value = patient.id;
                option.textContent = patient.name;
                patientIdDatalist.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to populate patient list:', error);
        }
    }

    // Call the function to populate the list on page load
    populatePatientDatalist();
    
    /**
     * A helper function to safely escape HTML to prevent XSS.
     * @param {string} str - The string to escape.
     * @returns {string} The escaped string.
     */
    const escapeHtml = (str) => {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    };

    /**
     * Formats a Patient resource into readable HTML.
     * @param {object} patient - The FHIR Patient resource.
     * @returns {string} HTML string.
     */
    function formatPatient(patient) {
        let html = '<div class="p-2 border rounded mb-2">';
        html += `<h5>Patient Details (ID: ${escapeHtml(patient.id)})</h5>`;
        const name = patient.name && patient.name[0];
        if (name) {
            const given = (name.given || []).join(' ');
            html += `<p><strong>Name:</strong> ${escapeHtml(given)} ${escapeHtml(name.family || '')}</p>`;
        }
        if (patient.gender) {
            html += `<p><strong>Gender:</strong> ${escapeHtml(patient.gender)}</p>`;
        }
        if (patient.birthDate) {
            html += `<p><strong>Birth Date:</strong> ${escapeHtml(patient.birthDate)}</p>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Formats an Observation resource into readable HTML.
     * @param {object} observation - The FHIR Observation resource.
     * @returns {string} HTML string.
     */
    function formatObservation(observation) {
        let html = '<div class="p-2 border rounded mb-2">';
        html += `<h5>Observation (ID: ${escapeHtml(observation.id)})</h5>`;

        if (observation.code && observation.code.text) {
             html += `<p><strong>Code:</strong> ${escapeHtml(observation.code.text)}</p>`;
        }
        if (observation.status) {
            html += `<p><strong>Status:</strong> ${escapeHtml(observation.status)}</p>`;
        }
        if (observation.valueQuantity) {
            const value = observation.valueQuantity;
            html += `<p><strong>Value:</strong> ${escapeHtml(value.value)} ${escapeHtml(value.unit)}</p>`;
        }
        if (observation.subject && observation.subject.reference) {
            html += `<p><strong>Subject:</strong> ${escapeHtml(observation.subject.reference)}</p>`;
        }
        if (observation.effectiveDateTime) {
            html += `<p><strong>Effective Date:</strong> ${escapeHtml(new Date(observation.effectiveDateTime).toLocaleString())}</p>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Formats a MedicationRequest resource into readable HTML.
     * @param {object} mr - The FHIR MedicationRequest resource.
     * @returns {string} HTML string.
     */
    function formatMedicationRequest(mr) {
        let html = '<div class="p-2 border rounded mb-2">';
        html += `<h5>Medication Request (ID: ${escapeHtml(mr.id)})</h5>`;
        html += `<p><strong>Status:</strong> ${escapeHtml(mr.status)}</p>`;
        const medicationName = mr.medicationCodeableConcept && mr.medicationCodeableConcept.coding && mr.medicationCodeableConcept.coding[0] && mr.medicationCodeableConcept.coding[0].display;
        if (medicationName) {
            html += `<p><strong>Medication:</strong> ${escapeHtml(medicationName)}</p>`;
        }
        if (mr.intent) {
            html += `<p><strong>Intent:</strong> ${escapeHtml(mr.intent)}</p>`;
        }
        if (mr.authoredOn) {
            html += `<p><strong>Authored On:</strong> ${escapeHtml(new Date(mr.authoredOn).toLocaleString())}</p>`;
        }
        if (mr.requester && mr.requester.display) {
            html += `<p><strong>Requester:</strong> ${escapeHtml(mr.requester.display)}</p>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Formats a Condition resource into readable HTML.
     * @param {object} condition - The FHIR Condition resource.
     * @returns {string} HTML string.
     */
    function formatCondition(condition) {
        let html = '<div class="p-2 border rounded mb-2">';
        html += `<h5>Condition (ID: ${escapeHtml(condition.id)})</h5>`;
        const problemName = condition.code && condition.code.coding && condition.code.coding[0] && condition.code.coding[0].display;
        if (problemName) {
            html += `<p><strong>Problem:</strong> ${escapeHtml(problemName)}</p>`;
        }
        if (condition.clinicalStatus && condition.clinicalStatus.coding && condition.clinicalStatus.coding[0] && condition.clinicalStatus.coding[0].display) {
            html += `<p><strong>Clinical Status:</strong> ${escapeHtml(condition.clinicalStatus.coding[0].display)}</p>`;
        }
        if (condition.verificationStatus && condition.verificationStatus.coding && condition.verificationStatus.coding[0] && condition.verificationStatus.coding[0].display) {
            html += `<p><strong>Verification Status:</strong> ${escapeHtml(condition.verificationStatus.coding[0].display)}</p>`;
        }
        if (condition.recordedDate) {
            html += `<p><strong>Recorded Date:</strong> ${escapeHtml(new Date(condition.recordedDate).toLocaleString())}</p>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Formats an Appointment resource into readable HTML.
     * @param {object} appointment - The FHIR Appointment resource.
     * @returns {string} HTML string.
     */
    function formatAppointment(appointment) {
        let html = '<div class="p-2 border rounded mb-2">';
        html += `<h5>Appointment (ID: ${escapeHtml(appointment.id)})</h5>`;
        if (appointment.status) {
            html += `<p><strong>Status:</strong> ${escapeHtml(appointment.status)}</p>`;
        }
        const serviceType = appointment.serviceType && appointment.serviceType[0] && appointment.serviceType[0].coding && appointment.serviceType[0].coding[0] && appointment.serviceType[0].coding[0].display;
        if (serviceType) {
            html += `<p><strong>Type:</strong> ${escapeHtml(serviceType)}</p>`;
        }
        if (appointment.start) {
            html += `<p><strong>Start:</strong> ${escapeHtml(new Date(appointment.start).toLocaleString())}</p>`;
        }
        if (appointment.end) {
            html += `<p><strong>End:</strong> ${escapeHtml(new Date(appointment.end).toLocaleString())}</p>`;
        }
        if (appointment.description) {
            html += `<p><strong>Description:</strong> ${escapeHtml(appointment.description)}</p>`;
        }
        if (appointment.practitioners && appointment.practitioners.length > 0) {
            html += `<p><strong>Practitioners:</strong> ${escapeHtml(appointment.practitioners.join(', '))}</p>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Formats a DiagnosticReport resource into readable HTML.
     * @param {object} dr - The FHIR DiagnosticReport resource.
     * @returns {string} HTML string.
     */
    function formatDiagnosticReport(dr) {
        let html = '<div class="p-2 border rounded mb-2">';
        html += `<h5>Diagnostic Report (ID: ${escapeHtml(dr.id)})</h5>`;
        const reportType = dr.code && dr.code.coding && dr.code.coding[0] && dr.code.coding[0].display;
        if (reportType) {
            html += `<p><strong>Type:</strong> ${escapeHtml(reportType)}</p>`;
        }
        if (dr.status) {
            html += `<p><strong>Status:</strong> ${escapeHtml(dr.status)}</p>`;
        }
        if (dr.effectiveDateTime) {
            html += `<p><strong>Effective Date:</strong> ${escapeHtml(new Date(dr.effectiveDateTime).toLocaleString())}</p>`;
        }
        if (dr.conclusion) {
            html += `<p><strong>Conclusion:</strong> ${escapeHtml(dr.conclusion)}</p>`;
        }
        if (dr.performer && dr.performer.length > 0) {
            const performers = dr.performer.map(p => escapeHtml(p.display || p.reference)).join(', ');
            html += `<p><strong>Performers:</strong> ${performers}</p>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Formats a Procedure resource into readable HTML.
     * @param {object} proc - The FHIR Procedure resource.
     * @returns {string} HTML string.
     */
    function formatProcedure(proc) {
        let html = '<div class="p-2 border rounded mb-2">';
        html += `<h5>Procedure (ID: ${escapeHtml(proc.id)})</h5>`;
        const procedureType = proc.code && proc.code.coding && proc.code.coding[0] && proc.code.coding[0].display;
        if (procedureType) {
            html += `<p><strong>Type:</strong> ${escapeHtml(procedureType)}</p>`;
        }
        if (proc.status) {
            html += `<p><strong>Status:</strong> ${escapeHtml(proc.status)}</p>`;
        }
        if (proc.performedDateTime) {
            html += `<p><strong>Performed Date:</strong> ${escapeHtml(new Date(proc.performedDateTime).toLocaleString())}</p>`;
        }
        if (proc.reasonCode && proc.reasonCode.length > 0) {
            const reason = proc.reasonCode[0].coding[0].display;
            html += `<p><strong>Reason:</strong> ${escapeHtml(reason)}</p>`;
        }
        if (proc.performer && proc.performer.length > 0) {
            const performers = proc.performer.map(p => escapeHtml(p.actor.display || p.actor.reference)).join(', ');
            html += `<p><strong>Performers:</strong> ${performers}</p>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Formats a Bundle resource into readable HTML by formatting each entry.
     * @param {object} bundle - The FHIR Bundle resource.
     * @returns {string} HTML string.
     */
    function formatBundle(bundle) {
        let html = `<h4>Bundle containing ${bundle.total || (bundle.entry ? bundle.entry.length : 0)} results</h4>`;
        if (bundle.entry && bundle.entry.length > 0) {
            bundle.entry.forEach(entry => {
                if (entry.resource) {
                    html += formatFhirResource(entry.resource); // Recursively format
                }
            });
        } else {
            html += '<p>No results found in this bundle.</p>';
        }
        return html;
    }

    /**
     * Main dispatcher function to format any FHIR resource.
     * @param {object} resource - A FHIR resource.
     * @returns {string} HTML string.
     */
    function formatFhirResource(resource) {
        if (!resource || !resource.resourceType) {
            return '<span class="text-muted">Not a valid FHIR resource or resource is empty.</span>';
        }

        switch (resource.resourceType) {
            case 'Patient':
                return formatPatient(resource);
            case 'Observation':
                return formatObservation(resource);
            case 'MedicationRequest':
                return formatMedicationRequest(resource);
            case 'Condition':
                return formatCondition(resource);
            case 'Appointment':
                return formatAppointment(resource);
            case 'DiagnosticReport':
                return formatDiagnosticReport(resource);
            case 'Procedure':
                return formatProcedure(resource);
            case 'Bundle':
                return formatBundle(resource);
            case 'OperationOutcome':
                 return `<div class="p-2 border rounded mb-2"><h5>Operation Outcome</h5><p class="text-danger">${escapeHtml(resource.issue[0].diagnostics)}</p></div>`;
            default:
                return `<div class="p-2 border rounded mb-2"><strong>Formatted view not yet supported for:</strong> ${escapeHtml(resource.resourceType)}</div>`;
        }
    }
    
    // Get references to new Patient Data tab elements
    const patientDataResponseArea = document.getElementById('patient-data-response');

    /**
     * Fetches patient-specific data from the custom Flask routes.
     * @param {string} patientId - The ID of the patient.
     * @param {string} dataType - The type of data to fetch ('medications', 'problems', 'appointments', 'diagnostic-reports', 'procedures', 'labs').
     */
    async function fetchPatientSpecificData(patientId, dataType) {
        if (!patientId) {
            alert('Please enter a Patient ID.');
            return;
        }

        const loadingMsg = '<span class="text-muted">Loading...</span>';
        patientDataResponseArea.innerHTML = loadingMsg;
        formattedResponseArea.innerHTML = loadingMsg;
        responseArea.textContent = 'Loading...';

        try {
            const response = await fetch(`/patient/${patientId}/${dataType}`);
            const data = await response.json();

            // Display raw JSON in main area
            responseArea.textContent = JSON.stringify(data, null, 2);

            if (response.ok) {
                let formattedHtml = `<h4>${dataType.charAt(0).toUpperCase() + dataType.slice(1).replace('-', ' ')} for Patient ${escapeHtml(patientId)}</h4>`;
                
                if (data.message) { 
                    formattedHtml += `<p>${escapeHtml(data.message)}</p>`;
                } else if (Array.isArray(data) && data.length > 0) {
                    data.forEach(item => {
                        if (item.resourceType) {
                            formattedHtml += formatFhirResource(item);
                        } else {
                            formattedHtml += `<div class="p-2 border rounded mb-2"><pre>${escapeHtml(JSON.stringify(item, null, 2))}</pre></div>`;
                        }
                    });
                } else if (data && typeof data === 'object' && Object.keys(data).length > 0) {
                    if (data.resourceType) {
                         formattedHtml += formatFhirResource(data);
                    } else {
                        formattedHtml += `<div class="p-2 border rounded mb-2"><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></div>`;
                    }
                } else {
                    formattedHtml += '<p>No data found.</p>';
                }
                
                patientDataResponseArea.innerHTML = formattedHtml;
                // Also update the main formatted area for consistency
                formattedResponseArea.innerHTML = formattedHtml;
            } else {
                const errorHtml = `<p class="text-danger">Error fetching ${dataType}: ${escapeHtml(JSON.stringify(data))}</p>`;
                patientDataResponseArea.innerHTML = errorHtml;
                formattedResponseArea.innerHTML = errorHtml;
            }

        } catch (error) {
            console.error(`Error fetching ${dataType}:`, error);
            const errorMsg = `Request failed: ${error.message}`;
            const errorHtml = `<p class="text-danger">${errorMsg}</p>`;
            patientDataResponseArea.innerHTML = errorHtml;
            formattedResponseArea.innerHTML = errorHtml;
            responseArea.textContent = errorMsg;
        }
    }

    // DRY Event Listeners for Patient Data buttons
    const patientButtons = [
        { id: 'btn-get-vitals', type: 'vitals' },
        { id: 'btn-get-allergies', type: 'allergies' },
        { id: 'btn-get-medications', type: 'medications' },
        { id: 'btn-get-problems', type: 'problems' },
        { id: 'btn-get-appointments', type: 'appointments' },
        { id: 'btn-get-diagnostic-reports', type: 'diagnostic-reports' },
        { id: 'btn-get-procedures', type: 'procedures' },
        { id: 'btn-get-labs', type: 'labs' }
    ];

    patientButtons.forEach(btnInfo => {
        const btn = document.getElementById(btnInfo.id);
        if (btn) {
            btn.addEventListener('click', () => {
                const patientId = patientIdInput.value.trim();
                fetchPatientSpecificData(patientId, btnInfo.type);
            });
        }
    });

    /**
     * A helper function to make requests to our backend proxy.
     * @param {string} method - The HTTP method (GET, POST, PUT, DELETE).
     * @param {string} path - The resource path (e.g., "Patient/123").
     * @param {object|null} payload - The JSON payload for POST/PUT requests.
     */
    async function makeFhirRequest(method, path, payload = null) {
        const baseUrl = fhirServerInput.value.trim();
        if (!baseUrl) {
            alert('Please enter a FHIR Server Base URL.');
            return;
        }

        const fullUrl = `${baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
        
        responseArea.textContent = 'Loading...';
        formattedResponseArea.innerHTML = '<span class="text-muted">Loading...</span>';

        try {
            const response = await fetch('/fhir-proxy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ method, url: fullUrl, payload }),
            });

            const responseData = await response.json();
            
            // Display raw JSON
            responseArea.textContent = JSON.stringify(responseData, null, 2);

            // Display formatted view
            if (response.ok) {
                formattedResponseArea.innerHTML = formatFhirResource(responseData);
            } else {
                 // Even if not "ok", the body might be a useful OperationOutcome
                formattedResponseArea.innerHTML = formatFhirResource(responseData);
            }

        } catch (error) {
            console.error('Request failed:', error);
            const errorMsg = `Request failed: ${error.message}`;
            responseArea.textContent = errorMsg;
            formattedResponseArea.innerHTML = `<p class="text-danger">${errorMsg}</p>`;
        }
    }

    // Event Listeners for buttons
    document.getElementById('btn-read').addEventListener('click', () => {
        const path = document.getElementById('read-path').value.trim();
        if (path) makeFhirRequest('GET', path);
        else alert('Please enter a resource path for Read (e.g., Patient/123).');
    });

    document.getElementById('btn-search').addEventListener('click', () => {
        const path = document.getElementById('search-path').value.trim();
        if (path) makeFhirRequest('GET', path);
        else alert('Please enter a resource and search parameters (e.g., Patient?name=John).');
    });

    document.getElementById('btn-create').addEventListener('click', () => {
        const path = document.getElementById('create-path').value.trim();
        const payloadStr = document.getElementById('create-payload').value;
        if (!path) {
            alert('Please enter a resource type for Create (e.g., Patient).');
            return;
        }
        try {
            const payload = JSON.parse(payloadStr);
            makeFhirRequest('POST', path, payload);
        } catch (e) {
            alert('Invalid JSON in payload for Create.');
        }
    });
    
    document.getElementById('btn-update').addEventListener('click', () => {
        const path = document.getElementById('update-path').value.trim();
        const payloadStr = document.getElementById('update-payload').value;
        if (!path) {
            alert('Please enter a resource path for Update (e.g., Patient/123).');
            return;
        }
        try {
            const payload = JSON.parse(payloadStr);
            makeFhirRequest('PUT', path, payload);
        } catch (e) {
            alert('Invalid JSON in payload for Update.');
        }
    });

    document.getElementById('btn-delete').addEventListener('click', () => {
        const path = document.getElementById('delete-path').value.trim();
        if (path) makeFhirRequest('DELETE', path);
        else alert('Please enter a resource path for Delete (e.g., Patient/123).');
    });
});
