# function_app.py  (root of your Function App)
import json, io, logging, os
from urllib.parse import urlparse, unquote

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from PIL import Image

app = func.FunctionApp()

BLOB_CONN = os.environ["AzureWebJobsStorage"]
blob_client = BlobServiceClient.from_connection_string(BLOB_CONN)

@app.function_name("ResizeThumbnail")
@app.service_bus_queue_trigger(
        arg_name="msg",
        queue_name="resize-requests",
        connection="SERVICEBUS_CONNECTION")
def resize(msg: func.ServiceBusMessage):
    logging.info("Processing message: %s", msg.get_body().decode())
    body   = json.loads(msg.get_body().decode())
    url    = body["blobUrl"]
    width  = body.get("targetWidth", 1024)
    height = body.get("targetHeight", 768)

    # --- download original ---
    u = urlparse(url)
    container, blob_name = u.path.lstrip("/").split("/", 1)
    raw_blob = blob_client.get_blob_client(container, blob_name)
    stream   = io.BytesIO(raw_blob.download_blob().readall())

    # --- resize ---
    img = Image.open(stream)
    img.thumbnail((width, height))
    out = io.BytesIO()
    img.save(out, format=img.format)
    out.seek(0)

    # --- upload thumb ---
    thumb_blob = blob_client.get_blob_client("thumbs", blob_name)
    thumb_blob.upload_blob(out, overwrite=True)
    logging.info("Thumbnail saved to thumbs/%s", blob_name)