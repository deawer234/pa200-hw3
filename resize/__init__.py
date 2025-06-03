import json, logging, io, os
from azure.storage.blob import BlobServiceClient
from PIL import Image
import azure.functions as func

BLOB_CONN = os.environ["AzureWebJobsStorage"]
blob_client = BlobServiceClient.from_connection_string(BLOB_CONN)

def main(msg: func.ServiceBusMessage):
    logging.info("Received message: %s", msg.get_body().decode())
    body = json.loads(msg.get_body().decode())
    url = body["blobUrl"]
    width = body["targetWidth"]
    height = body["targetHeight"]
    result_blob_name = body["resultBlobName"]

    path = url.split(".net/")[1]
    container, blob_name = path.split("/", 1)

    # Download original
    raw_blob = blob_client.get_blob_client(container, blob_name)
    stream = io.BytesIO()
    stream.write(raw_blob.download_blob().readall())
    stream.seek(0)

    # Resize image
    img = Image.open(stream)
    img.thumbnail((width, height))
    out = io.BytesIO()
    img.save(out, format=img.format)
    out.seek(0)

    # Upload resized image
    thumb_blob = blob_client.get_blob_client("thumbs", result_blob_name)
    thumb_blob.upload_blob(out, overwrite=True)
    logging.info("Resized image uploaded as thumbs/%s", result_blob_name)
