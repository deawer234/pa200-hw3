from flask import Flask, request, render_template_string, redirect, url_for
from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage
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

@app.route("/result/<filename>")
def result(filename):
    thumb_url = f"https://{blob.account_name}.blob.core.windows.net/thumbs/{filename}"
    return f"Resized image will be ready soon: <a href='{thumb_url}'>Download here</a>"
