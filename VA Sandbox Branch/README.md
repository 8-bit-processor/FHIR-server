# VA FHIR Dev Server & Progress Note Studio

A senior-tier clinical documentation suite and FHIR R4 middleware. This application is designed to help clinicians rapidly generate medical progress notes by bridging the gap between raw FHIR data and structured clinical documentation.

## 🚀 Key Clinical Features

### 🏥 Progress Note Studio (Clinician Interface)
- **Live Auto-Populate:** One-click retrieval of patient-specific data including:
    - **Subjective:** Allergies & active Medications.
    - **Objective:** Vital Signs (including Blood Pressure component parsing) and Lab Results.
    - **Context:** Diagnostic Reports (Radiology/Pathology) automatically appended to Labwork.
    - **History:** Past Medical History (Conditions) and Past Surgical History (Procedures).
- **Existing Note Retrieval:** Automatically discovers the most recent `DocumentReference`, fetches the associated `Binary` payload, and decodes the Base64 content directly into the editor.
- **AI-Ready Interface:** Purple "Process w/AI" buttons at both section and document levels, ready for LLM integration.
- **Dynamic Editor:** Drag-and-drop section reordering (SortableJS), "Copy Section" for quick charting, and a standard clinical order (SOAP/HPI).

### 🛠 FHIR Technical Client (Developer Interface)
- **OAuth2 Middleware:** Transparently handles VA Sandbox authentication with automatic token expiration/refresh (60s buffer).
- **Resource Dispatcher:** Dynamically formats complex FHIR resources into human-readable cards.
- **Full CRUD Proxy:** Supports GET (Read/Search), POST (Create), PUT (Update), and DELETE operations while bypassing CORS restrictions.

## 🛠 Technical Stack
- **Backend:** Python 3.9+ / Flask / Requests
- **FHIR Models:** `fhir.resources` (Pydantic-driven validation)
- **Frontend:** Vanilla JavaScript (ES6+), Bootstrap 5, SortableJS
- **Authentication:** OAuth 2.0 Client Credentials Grant

## 📋 Prerequisites
1.  **VA API Credentials:** Obtain a `Client ID` and `Client Secret` from the [VA API Developer Portal](https://developer.va.gov/).
2.  **Python Environment:** Ensure you have a virtual environment active.

## ⚙️ Installation & Configuration

1. **Setup Environment:**
   Update your `.env` file in the root directory:
   ```env
   VA_CLIENT_ID=your_client_id_here
   VA_CLIENT_SECRET=your_client_secret_here
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Application:**
   ```bash
   python app.py
   ```
   Access the dashboard at: `http://127.0.0.1:5000`

## 📂 Architecture Overview
- `app.py`: High-performance Flask server with token caching and clinical route mapping.
- `static/js/main.js`: Technical interface logic and FHIR resource formatting.
- `templates/progressNoteStudio.html`: A monolithic, high-efficiency clinical editor containing the data-fetching and Base64 decoding engines.
- `templates/index.html`: The technical playground for FHIR resource testing.

## 🔒 Security & Sandbox Note
This application is strictly optimized for the **VA Sandbox environment** using synthetic data.
- **ICNs (Patient IDs):** Use test ICNs like `32000225` or `5000335` to see live data.
- **Credentials:** Rigorously protect your `.env` file; it is listed in `.gitignore` by default.

---
*Developed for clinical documentation excellence and FHIR interoperability.*
