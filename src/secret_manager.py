import boto3
from botocore.exceptions import ClientError
import structlog
from .log import configure_logging


def get_secret(secret_name: str, region_name: str = "us-east-1"):
    configure_logging()
    logger = structlog.get_logger()
    logger.debug(f"Getting secret for: {secret_name}")

    # secret_name = "DATABASE_URL"
    # region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    logger.debug(f"Credential for: {secret_name} acquired")
    return get_secret_value_response['SecretString']