"""Shared Azure Blob Storage helpers."""

import mydocs.config as C


def create_blob_service_client():
    """Create an async Azure BlobServiceClient using configured credentials.

    Authentication priority:
    1. Connection string (AZURE_STORAGE_CONNECTION_STRING)
    2. Account name + key (AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY)
    3. Account name + DefaultAzureCredential (managed identity, Azure CLI, etc.)

    Returns:
        azure.storage.blob.aio.BlobServiceClient instance.

    Raises:
        ValueError: If neither connection string nor account name is configured.
    """
    from azure.storage.blob.aio import BlobServiceClient

    if C.AZURE_STORAGE_CONNECTION_STRING:
        return BlobServiceClient.from_connection_string(C.AZURE_STORAGE_CONNECTION_STRING)

    if C.AZURE_STORAGE_ACCOUNT_NAME:
        account_url = f"https://{C.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
        if C.AZURE_STORAGE_ACCOUNT_KEY:
            return BlobServiceClient(account_url, credential=C.AZURE_STORAGE_ACCOUNT_KEY)
        from azure.identity.aio import DefaultAzureCredential
        return BlobServiceClient(account_url, credential=DefaultAzureCredential())

    raise ValueError(
        "Azure Blob Storage requires either AZURE_STORAGE_CONNECTION_STRING "
        "or AZURE_STORAGE_ACCOUNT_NAME to be set."
    )
