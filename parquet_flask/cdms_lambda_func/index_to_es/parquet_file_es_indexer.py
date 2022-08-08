import os

from parquet_flask.aws.aws_s3 import AwsS3
from parquet_flask.aws.es_abstract import ESAbstract

from parquet_flask.aws.es_factory import ESFactory
from parquet_flask.cdms_lambda_func.cdms_lambda_constants import CdmsLambdaConstants
from parquet_flask.cdms_lambda_func.index_to_es.parquet_stat_extractor import ParquetStatExtractor
from parquet_flask.cdms_lambda_func.index_to_es.s3_stat_extractor import S3StatExtractor
from parquet_flask.cdms_lambda_func.lambda_logger_generator import LambdaLoggerGenerator
from parquet_flask.cdms_lambda_func.s3_records.s3_2_sqs import S3ToSqs

LOGGER = LambdaLoggerGenerator.get_logger(__name__, log_level=LambdaLoggerGenerator.get_level_from_env())


class ParquetFileEsIndexer:
    def __init__(self):
        self.__s3_url = None
        self.__es_url = os.environ.get(CdmsLambdaConstants.es_url, None)
        self.__es_index = os.environ.get(CdmsLambdaConstants.es_index, None)
        self.__es_port = int(os.environ.get(CdmsLambdaConstants.es_port, '443'))
        if any([k is None for k in [self.__es_url, self.__es_index]]):
            raise ValueError(f'invalid env. must have {[CdmsLambdaConstants.es_url, CdmsLambdaConstants.es_index]}')
        self.__es: ESAbstract = ESFactory().get_instance('AWS', index=self.__es_index, base_url=self.__es_url, port=self.__es_port)

    def ingest_file(self):
        if self.__s3_url is None:
            raise ValueError('s3 url is null. Set it first')
        s3_stat = S3StatExtractor(self.__s3_url).start()
        s3_bucket, s3_key = AwsS3().split_s3_url(self.__s3_url)
        parquet_stat = ParquetStatExtractor().start(s3_key)
        LOGGER.debug(f's3_stat: {s3_stat.to_json()}')
        LOGGER.debug(f'parquet_stat: {parquet_stat}')
        self.__es.index_one({'s3_url': self.__s3_url, **s3_stat.to_json(), **parquet_stat}, s3_stat.s3_url)
        return

    def remove_file(self):
        if self.__s3_url is None:
            raise ValueError('s3 url is null. Set it first')
        delete_result = self.__es.delete_by_id(self.__s3_url)
        return f'deletion result: {delete_result}. id: self'

    def start(self, event):
        # LOGGER.warning(self.__es.query({
        #     'size': 10,
        #     'query': {
        #         'match_all': {}
        #     }
        # }))
        s3_records = S3ToSqs(event)
        ignoring_phrases = ['spark-staging', '_temporary']
        for i in range(s3_records.size()):
            self.__s3_url = s3_records.get_s3_url(i)
            if any([k in self.__s3_url for k in ignoring_phrases]):
                LOGGER.debug(f'skipping temp file: {self.__s3_url}')
                return
            LOGGER.debug(f'executing: self.__s3_url')
            s3_event = s3_records.get_event_name(i).strip().lower()
            if s3_event.startswith('objectcreated'):
                LOGGER.debug('executing index')
                self.ingest_file()
            elif s3_event.startswith('objectremoved'):
                LOGGER.debug('executing to remove index')
                self.remove_file()
            else:
                raise ValueError(f'invalid s3_event: {s3_event}')
        return
