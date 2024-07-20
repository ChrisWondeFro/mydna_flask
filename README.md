# Mydna Flask Application
Upload your AncestryDNA.txt file and get detailed variant summary data from NCBI database.

## Prerequisites

- Python 3.8+
- PostgreSQL
- Firebase project (for Google Sign-In)

## Installation

1. Clone the repository:

2. Set up a virtual environment (recommended):
    python -m venv venv
    source venv/bin/activate  # On Windows, use venv\Scripts\activate

3. Install the required packages:
    pip install -r requirements.txt

4. Set up the environment variables:
- Copy the `.env.example` file to `.env`
- Fill in the PostgreSQL database connection details and Firebase credentials in the `.env` file:
  ```
  POSTGRES_URL=
  POSTGRES_USER=
  POSTGRES_PW=
  POSTGRES_DB="variant_summary"  
  
  FIREBASE_TYPE=
  FIREBASE_PROJECT_ID=
  FIREBASE_PRIVATE_KEY_ID=
  FIREBASE_PRIVATE_KEY=
  FIREBASE_CLIENT_EMAIL=
  FIREBASE_CLIENT_ID=
  FIREBASE_AUTH_URI=
  FIREBASE_TOKEN_URI=
  FIREBASE_AUTH_PROVIDER_X509_CERT_URL=
  FIREBASE_CLIENT_X509_CERT_URL=
  FIREBASE_UNIVERSE_DOMAIN=

  FIREBASE_AUTH_DOMAIN=
  FIREBASE_PROJECT_ID=
  FIREBASE_STORAGE_BUCKET=
  FIREBASE_MESSAGING_SENDER_ID=
  FIREBASE_APP_ID=

  ```
5. Run the scripts in  app/models/variant_summary_process_and_upload folder, 
   first create_table.py then process_upload.py, this is the core of this application.

## Running the Application

### For Production

Use Hypercorn to run the application in production: 
    python run.py   

This will start the server on `localhost:8000`.

### For Testing

For development and testing purposes, use:
    python test_run.py

This will start the Flask development server on `localhost:8000` with debug mode enabled.

## Usage

1. Navigate to `http://localhost:8000` in your web browser.
2. Sign in using Google authentication.
3. Upload your AncestryDNA file.
4. View your personalized DNA health assessment.

## Contributing

## License


