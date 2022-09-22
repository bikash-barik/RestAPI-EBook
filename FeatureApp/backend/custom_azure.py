from storages.backends.azure_storage import AzureStorage
import re
from django.utils.encoding import force_str
from django.utils.functional import keep_lazy_text
from config.config import fileshare_connectionString, container_name_var, account_name, account_key
from azure.storage.blob import BlobServiceClient


@keep_lazy_text
def get_valid_filename(s):
    s = force_str(s).strip()
    return re.sub(r'(?u)[^-\w. ]', '', s)


def azure_connection():
    connstr = fileshare_connectionString
    container = container_name_var
    blob_service_client = BlobServiceClient.from_connection_string(connstr)
    container_client = blob_service_client.get_container_client(container)
    return container_client


class AzureMediaStorage(AzureStorage):
    account_name = account_name
    account_key = account_key
    azure_container = container_name_var
    expiration_secs = None

    def get_valid_name(self, name):
        return get_valid_filename(name)


class AzureStaticStorage(AzureStorage):
    account_name = account_name
    account_key = account_key
    azure_container = container_name_var
    expiration_secs = None
