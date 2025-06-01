from flask import Flask, request, render_template_string
from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage
import os, uuid, json

app = Flask(__name__)

blob = BlobServiceClient.from_connection_string(os.getenv("AZURE_STORAGE_CONN"))
bus  = ServiceBusClient.from_connection_string(os.getenv("SERVICEBUS_CONNECTION"))
queue_sender = bus.get_queue_sender("resize-requests")

FORM = """
<h1>Upload obrázku</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file required>
  <button>Upload</button>
</form>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.files["file"]
        ext = os.path.splitext(f.filename)[1].lower()
        filename = f"{uuid.uuid4()}{ext}"
        # --- uložit originál ---
        blob.get_blob_client("raw", filename).upload_blob(f)
        # --- poslat zprávu ---
        msg = {"blobUrl": f"https://{blob.account_name}.blob.core.windows.net/raw/{filename}"}
        queue_sender.send_messages(ServiceBusMessage(json.dumps(msg)))
        return "Nahráno, thumbnail se brzy objeví!"
    return render_template_string(FORM)
