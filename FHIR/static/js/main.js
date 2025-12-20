document.addEventListener('DOMContentLoaded', () => {
    const fhirServerInput = document.getElementById('fhir-server');
    const responseArea = document.getElementById('response-area');
    const formattedResponseArea = document.getElementById('formatted-response-area');

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
            case 'Bundle':
                return formatBundle(resource);
            case 'OperationOutcome':
                 return `<div class="p-2 border rounded mb-2"><h5>Operation Outcome</h5><p class="text-danger">${escapeHtml(resource.issue[0].diagnostics)}</p></div>`;
            default:
                return `<div class="p-2 border rounded mb-2"><strong>Formatted view not yet supported for:</strong> ${escapeHtml(resource.resourceType)}</div>`;
        }
    }
    
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
