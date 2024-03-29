# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from parquet_flask.utils.file_utils import FileUtils
from pyspark.sql import SparkSession
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.utils import AnalysisException

from parquet_flask.io_logic.cdms_schema import CdmsSchema
from parquet_flask.parquet_stat_extractor.statistics_retriever import StatisticsRetriever
from parquet_flask.utils.config import Config

LOGGER = logging.getLogger(__name__)


class StatisticsRetrieverWrapper:
    def __init__(self):
        config = Config()
        self.__app_name = config.get_spark_app_name()
        self.__master_spark = config.get_value('master_spark_url')
        self.__parquet_name = config.get_value('parquet_file_name')
        self.__parquet_name = self.__parquet_name if not self.__parquet_name.endswith('/') else self.__parquet_name[:-1]

    def start(self, parquet_path):
        from parquet_flask.io_logic.retrieve_spark_session import RetrieveSparkSession
        spark: SparkSession = RetrieveSparkSession().retrieve_spark_session(self.__app_name, self.__master_spark)
        full_parquet_path = f"{self.__parquet_name}/{parquet_path}"
        LOGGER.debug(f'searching for full_parquet_path: {full_parquet_path}')
        try:
            insitu_schema = FileUtils.read_json(Config().get_value(Config.in_situ_schema))
            cdms_spark_struct = CdmsSchema().get_schema_from_json(insitu_schema)
            read_df: DataFrame = spark.read.schema(cdms_spark_struct).parquet(full_parquet_path)
        except AnalysisException as analysis_exception:
            if analysis_exception.desc is not None and analysis_exception.desc.startswith('Path does not exist'):
                LOGGER.debug(f'no such full_parquet_path: {full_parquet_path}')
                return None
            LOGGER.exception(f'error while retrieving full_parquet_path: {full_parquet_path}')
            raise analysis_exception
        stats = StatisticsRetriever(read_df, CdmsSchema().get_observation_names(insitu_schema)).start()
        return stats.to_json()
