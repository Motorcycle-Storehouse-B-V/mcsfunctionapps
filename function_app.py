import azure.functions as func
import datetime
import json
import logging
import os
import requests
import base64

app = func.FunctionApp()

@app.route(route="HttpTrigger", auth_level=func.AuthLevel.ANONYMOUS)
def HttpTrigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    # Authentication check
    client_principal = req.headers.get("x-ms-client-principal")
    if not client_principal:
        return func.HttpResponse("Unauthorized", status_code=401)

    # Decode user info from base64
    client_principal_decoded = json.loads(base64.b64decode(client_principal))
    user_name = client_principal_decoded.get("userDetails", "User")

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. Welcome, {user_name}!")
    else:
        return func.HttpResponse(
             f"Welcome, {user_name}. This HTTP triggered function executed successfully.",
             status_code=200
        )

@app.route(route="abn_insights", methods=["GET"])
def abn_insights(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing request for ABN AMRO Account Insights API.")

    # Ensure the request is authenticated
    client_principal = req.headers.get("x-ms-client-principal")
    if not client_principal:
        return func.HttpResponse("Unauthorized. Please sign in via Azure Entra ID.", status_code=401)

    # Fetch client credentials and endpoint
    abn_api_url = "https://api.abnamro.com/v2/account-insights"
    client_id = os.environ.get("ABN_CLIENT_ID")
    client_secret = os.environ.get("ABN_CLIENT_SECRET")
    certificate_path = os.environ.get("CERTIFICATE_PATH")
    key_path = os.environ.get("KEY_PATH")

    if not all([client_id, client_secret, certificate_path, key_path]):
        return func.HttpResponse(
            "Missing ABN API credentials or certificates in environment variables.",
            status_code=500,
        )

    try:
        # mTLS request to ABN AMRO API
        response = requests.get(
            abn_api_url,
            cert=(certificate_path, key_path),
            headers={"Authorization": f"Basic {base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()}"},
        )

        # Handle API response
        if response.status_code == 200:
            account_data = response.json()
            return func.HttpResponse(
                json.dumps(account_data, indent=4),
                mimetype="application/json",
                status_code=200,
            )
        else:
            logging.error(f"ABN API Error: {response.status_code} - {response.text}")
            return func.HttpResponse(
                f"ABN AMRO API returned an error: {response.text}",
                status_code=response.status_code,
            )
    except Exception as e:
        logging.error(f"Error connecting to ABN AMRO API: {e}")
        return func.HttpResponse(
            "An error occurred while connecting to the ABN AMRO API.",
            status_code=500,
        )  

@app.route(route="abn_page", methods=["GET"])
def abn_page(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing request for ABN AMRO Insights page.")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ABN Insights API</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{
                padding: 20px;
                font-family: Arial, sans-serif;
            }}
            .container {{
                margin-top: 50px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ABN AMRO Account Insights</h1>
            <p>Click the button below to fetch account insights from ABN AMRO.</p>
            <button id="fetchInsights" class="btn btn-primary">Fetch Insights</button>
            <div id="insightsData" class="mt-4"></div>
        </div>

        <script>
            document.getElementById("fetchInsights").addEventListener("click", async () => {{
                try {{
                    const response = await fetch("/api/abn_insights");
                    if (response.ok) {{
                        const data = await response.json();
                        document.getElementById("insightsData").innerHTML =
                            `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    }} else {{
                        document.getElementById("insightsData").innerHTML =
                            `<p>Error fetching data: ${response.status} - ${response.statusText}</p>`;
                    }}
                }} catch (error) {{
                    console.error("Error:", error);
                    document.getElementById("insightsData").innerHTML =
                        `<p>There was an error fetching the insights.</p>`;
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return func.HttpResponse(
        html_content,
        mimetype="text/html",
    )

@app.route(route="upload_audio", methods=["POST"])
def upload_audio(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed an audio upload request.')

    try:
        audio_file = req.files['audio']
        file_name = f"audio_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.webm"
        file_path = os.path.join("/path/to/save", file_name)

        with open(file_path, "wb") as f:
            f.write(audio_file.read())

        return func.HttpResponse(f"Audio file saved as {file_name}", status_code=200)
    except Exception as e:
        logging.error(f"Error saving audio file: {e}")
        return func.HttpResponse("Error saving audio file", status_code=500)

@app.route(route="audio_recorder", methods=["GET"])
def audio_recorder(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing request for audio recorder page.')

    # Check for authenticated user
    client_principal = req.headers.get("x-ms-client-principal")
    if not client_principal:
        return func.HttpResponse(
            "Unauthorized. Please sign in via Azure Entra ID.",
            status_code=401
        )

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Audio Recorder</title>
        <link rel="icon" href="/api/favicon.ico">
        <!-- Bootstrap CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{
                background-color: #f8f9fa;
                padding-top: 50px;
                text-align: center;
            }}
            .container-custom {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}
            h1 {{
                margin-bottom: 30px;
                text-align: center;
                color: #343a40;
            }}
            .btn-custom {{
                background-color: #ffe900; /* Yellow background */
                color: #000000; /* Black text */
                border: none; /* Remove border */
            }}
            .btn-custom:hover {{
                background-color: #e6c200; /* Darker yellow on hover */
                color: #000000; /* Black text */
            }}
            .footer {{
                margin-top: 20px;
                text-align: center;
                color: #6c757d;
                font-size: 0.9rem;
            }}
        </style>
    </head>
    <body>
        <div class="container container-custom">
            <h1>Audio Recorder</h1>
            <button id="recordButton" class="btn btn-custom">Record</button>
            <button id="stopButton" class="btn btn-custom" disabled>Stop</button>
            <audio id="audioPlayback" controls></audio>
            <form id="uploadForm" method="post" action="/api/upload_audio" enctype="multipart/form-data">
                <input type="file" name="audio" accept="audio/*" required>
                <button type="submit" class="btn btn-custom">Upload Audio</button>
            </form>
            <div class="footer">
                &copy; {datetime.datetime.now().year} Motorcycle Storehouse B.V.
            </div>
            <script>
                let mediaRecorder;
                let audioChunks = [];

                document.getElementById('recordButton').addEventListener('click', async () => {{
                    const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                    mediaRecorder = new MediaRecorder(stream);
                    mediaRecorder.start();

                    mediaRecorder.ondataavailable = event => {{
                        audioChunks.push(event.data);
                    }};

                    mediaRecorder.onstop = async () => {{
                        const audioBlob = new Blob(audioChunks, {{ type: 'audio/webm' }});
                        const audioUrl = URL.createObjectURL(audioBlob);
                        document.getElementById('audioPlayback').src = audioUrl;

                        const formData = new FormData();
                        formData.append('audio', audioBlob, 'audio.webm');

                        await fetch('/api/upload_audio', {{
                            method: 'POST',
                            body: formData
                        }});

                        audioChunks = [];
                    }};

                    document.getElementById('recordButton').disabled = true;
                    document.getElementById('stopButton').disabled = false;
                }});

                document.getElementById('stopButton').addEventListener('click', () => {{
                    mediaRecorder.stop();
                    document.getElementById('recordButton').disabled = false;
                    document.getElementById('stopButton').disabled = true;
                }});
            </script>
        </div>
        
        <!-- Bootstrap JS and dependencies -->
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

    return func.HttpResponse(
        html_content,
        mimetype="text/html",
    )