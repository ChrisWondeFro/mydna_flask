# Mydna Flask Application
Flask application to allow users to upload their AncestryDNA.txt file and get detailed variant summary data from NCBI database. Incorporates Google Sign-in.

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
- Fill in the PostgreSQL database connection details in the `.env` file:
  ```
  POSTGRES_URL=
  POSTGRES_USER=
  POSTGRES_PW=
  POSTGRES_DB="variant_summary"  

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


