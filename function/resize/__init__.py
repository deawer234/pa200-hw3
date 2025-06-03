import json, logging, io, os
from azure.storage.blob import BlobServiceClient
from PIL import Image
import azure.functions as func

# Connection string k Storage účtu dostane funkce z Application settings
BLOB_CONN = os.environ["AzureWebJobsStorage"]
blob_client = BlobServiceClient.from_connection_string(BLOB_CONN)

def main(msg: func.ServiceBusMessage):
    """Service Bus Queue trigger: zmenší obrázek a uloží thumbnail."""
    logging.info("Processing message: %s", msg.get_body().decode())
    body = json.loads(msg.get_body().decode())
    url = body["blobUrl"]
    width, height = body.get("targetWidth", 1024), body.get("targetHeight", 768)

    # -------- stáhni originál --------
    path = url.split(".net/")[1]
    container, blob_name = path.split("/", 1)
    raw_blob = blob_client.get_blob_client(container, blob_name)
    stream = io.BytesIO()
    stream.write(raw_blob.download_blob().readall())
    stream.seek(0)

    # -------- převzorkuj --------
    img = Image.open(stream)
    img.thumbnail((width, height))
    out = io.BytesIO()
    img.save(out, format=img.format)
    out.seek(0)

    # -------- ulož thumbnail --------
    thumb_blob = blob_client.get_blob_client("thumbs", blob_name)
    thumb_blob.upload_blob(out, overwrite=True)
    logging.info("Thumbnail saved to thumbs/%s", blob_name)
