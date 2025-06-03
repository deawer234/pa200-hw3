from flask import Flask, request, render_template_string, redirect, url_for, jsonify
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from datetime import datetime, timedelta
import os, uuid, json


app = Flask(__name__)

blob = BlobServiceClient.from_connection_string(os.getenv("AZURE_STORAGE_CONN"))
bus  = ServiceBusClient.from_connection_string(os.getenv("SERVICEBUS_CONNECTION"))
queue_sender = bus.get_queue_sender("resize-requests")

FORM = """
<h1>Upload and Resize Image</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file required><br>
  Width: <input type=number name=width value=1024 required><br>
  Height: <input type=number name=height value=768 required><br>
  <button type=submit>Upload and Resize</button>
</form>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.files["file"]
        ext = os.path.splitext(f.filename)[1].lower()
        filename = f"{uuid.uuid4()}{ext}"
        width = int(request.form["width"])
        height = int(request.form["height"])

        # Save original image
        blob.get_blob_client("raw", filename).upload_blob(f)

        # Send resize request to Service Bus
        msg = {
            "blobUrl": f"https://{blob.account_name}.blob.core.windows.net/raw/{filename}",
            "targetWidth": width,
            "targetHeight": height,
            "resultBlobName": filename
        }
        queue_sender.send_messages(ServiceBusMessage(json.dumps(msg)))

        return redirect(url_for('result', filename=filename))

    return render_template_string(FORM)

RESULT_PAGE = """
<script>
function checkStatus() {
  fetch('/check/{{ filename }}')
    .then(response => response.json())
    .then(data => {
      if (data.ready) {
        document.getElementById('status').innerHTML = `<a href='${data.url}'>Download resized image</a>`;
      } else {
        setTimeout(checkStatus, 3000);
      }
    });
}
checkStatus();
</script>

<div id='status'>Checking status...</div>
"""

@app.route("/result/<filename>")
def result(filename):
    return render_template_string(RESULT_PAGE, filename=filename)

@app.route("/check/<filename>")
def check(filename):
    thumb_blob = blob.get_blob_client("thumbs", filename)
    if thumb_blob.exists():
        sas_token = generate_blob_sas(
            account_name=blob.account_name,
            container_name="thumbs",
            blob_name=filename,
            account_key=blob.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )

        thumb_url = f"https://{blob.account_name}.blob.core.windows.net/thumbs/{filename}?{sas_token}"
        return jsonify({"ready": True, "url": thumb_url})
    
    return jsonify({"ready": False})
