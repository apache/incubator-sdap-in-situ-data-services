from flask import Blueprint
from flask_restx import Api
from .ingest_json_file import api as ingest_parquet_json_file
from .ingest_json_s3 import api as ingest_parquet_json_s3
from .query_data import api as query_data
_version = "1.0"

blueprint = Blueprint('parquet_flask', __name__, url_prefix='/{}'.format(_version))


api = Api(blueprint,
          title='Parquet ingestion & query',
          version=_version,
          description='API to support the Parquet ingestion & query data',
          doc='/doc/'
          )

# Register namespaces
api.add_namespace(ingest_parquet_json_file)
api.add_namespace(ingest_parquet_json_s3)
api.add_namespace(query_data)
