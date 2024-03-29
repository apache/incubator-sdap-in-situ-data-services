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

from parquet_flask.io_logic.parquet_paths_es_retriever import ParquetPathsEsRetriever
from parquet_flask.io_logic.partitioned_parquet_path import PartitionedParquetPath
from parquet_flask.io_logic.cdms_constants import CDMSConstants
from parquet_flask.io_logic.query_v2 import QueryProps

LOGGER = logging.getLogger(__name__)


class ParquetQueryConditionManagementV4:
    def __init__(self, parquet_name: str, missing_depth_value, es_config: dict, props=QueryProps()):
        self.__conditions = []
        self.__parquet_name = parquet_name if not parquet_name.endswith('/') else parquet_name[:-1]
        self.__columns = [CDMSConstants.time_col, CDMSConstants.depth_col, CDMSConstants.lat_col, CDMSConstants.lon_col]
        self.__query_props = props
        self.__missing_depth_value = missing_depth_value
        self.__parquet_names: [PartitionedParquetPath] = []
        self.__es_config = es_config

    def stringify_parquet_names(self):
        return [k.generate_path() for k in self.__parquet_names]

    @property
    def parquet_names(self):
        return self.__parquet_names

    @parquet_names.setter
    def parquet_names(self, val):
        """
        :param val:
        :return: None
        """
        self.__parquet_names = val
        return

    @property
    def conditions(self):
        return self.__conditions

    @conditions.setter
    def conditions(self, val):
        """
        :param val:
        :return: None
        """
        self.__conditions = val
        return

    @property
    def parquet_name(self):
        return self.__parquet_name

    @parquet_name.setter
    def parquet_name(self, val):
        """
        :param val:
        :return: None
        """
        self.__parquet_name = val
        return

    @property
    def columns(self):
        return self.__columns

    @columns.setter
    def columns(self, val):
        """
        :param val:
        :return: None
        """
        self.__columns = val
        return

    def __generate_time_partition_list(self, min_time, max_time):
        if min_time.year == max_time.year: # same year
            new_parquet_names = []
            for each_month in range(min_time.month, max_time.month + 1):
                new_parquet_names.extend([k.duplicate().set_year(min_time.year).set_month(each_month) for k in self.parquet_names])
            self.parquet_names = new_parquet_names
            return
        # different year
        new_parquet_names = []
        for each_whole_year in range(min_time.year + 1, max_time.year):  # for whole years
            new_parquet_names.extend([k.duplicate().set_year(each_whole_year) for k in self.parquet_names])
        if min_time.month == 1:
            new_parquet_names.extend([k.duplicate().set_year(min_time.year) for k in self.parquet_names])
        else:
            for each_month in range(min_time.month, 13):  # months for beginning year
                new_parquet_names.extend([k.duplicate().set_year(min_time.year).set_month(each_month) for k in self.parquet_names])
        if max_time.month == 12:
            new_parquet_names.extend([k.duplicate().set_year(max_time.year) for k in self.parquet_names])
        else:
            for each_month in range(1, max_time.month + 1):  # months for ending year
                new_parquet_names.extend([k.duplicate().set_year(max_time.year).set_month(each_month) for k in self.parquet_names])
        self.parquet_names = new_parquet_names
        return

    def __check_time_range(self):
        if self.__query_props.min_datetime is None and self.__query_props.max_datetime is None:
            return None
        min_time = max_time = None
        if self.__query_props.min_datetime is not None:
            LOGGER.debug(f'setting datetime min condition as sql: {self.__query_props.min_datetime}')
            self.__conditions.append(f"{CDMSConstants.time_obj_col} >= '{self.__query_props.min_datetime}'")
        if self.__query_props.max_datetime is not None:
            LOGGER.debug(f'setting datetime max condition as sql: {self.__query_props.max_datetime}')
            self.__conditions.append(f"{CDMSConstants.time_obj_col} <= '{self.__query_props.max_datetime}'")
        return

    def __check_bbox(self):
        if self.__query_props.min_lat_lon is not None:
            LOGGER.debug(f'setting Lat-Lon min condition as sql: {self.__query_props.min_lat_lon}')
            self.__conditions.append(f"{CDMSConstants.lat_col} >= {self.__query_props.min_lat_lon[0]}")
            self.__conditions.append(f"{CDMSConstants.lon_col} >= {self.__query_props.min_lat_lon[1]}")
        if self.__query_props.max_lat_lon is not None:
            LOGGER.debug(f'setting Lat-Lon max condition as sql: {self.__query_props.max_lat_lon}')
            self.__conditions.append(f"{CDMSConstants.lat_col} <= {self.__query_props.max_lat_lon[0]}")
            self.__conditions.append(f"{CDMSConstants.lon_col} <= {self.__query_props.max_lat_lon[1]}")
        return

    def __check_depth(self):
        if self.__query_props.min_depth is None and self.__query_props.max_depth is None:
            return
        depth_conditions = []
        include_subsurface = None
        if self.__query_props.min_depth is not None:
            LOGGER.debug(f'setting depth min condition: {self.__query_props.min_depth}')
            depth_conditions.append(f"{CDMSConstants.depth_col} >= {self.__query_props.min_depth}")
            include_subsurface = True if self.__query_props.min_depth <= 0 else False
        if self.__query_props.max_depth is not None:
            LOGGER.debug(f'setting depth max condition: {self.__query_props.max_depth}')
            depth_conditions.append(f"{CDMSConstants.depth_col} <= {self.__query_props.max_depth}")
            if include_subsurface is None or include_subsurface is True:
                include_subsurface = True if self.__query_props.max_depth >= 0 else False
        append_conditions = f"({' AND '.join(depth_conditions) })"
        if include_subsurface is True:
            append_conditions = f"( {append_conditions} OR {CDMSConstants.depth_col} == {self.__missing_depth_value} )"
        self.__conditions.append(append_conditions)
        return

    def __add_variables_filter(self):
        if len(self.__query_props.variable) < 1:
            return None
        variables_filter = []
        for each in self.__query_props.variable:
            LOGGER.debug(f'setting not null variable: {each}')
            variables_filter.append(f"{each} IS NOT NULL")
        self.__conditions.append(f"({' OR '.join(variables_filter)})")
        return

    def __check_columns(self):
        if len(self.__query_props.columns) < 1:
            self.__columns = []
            return
        variable_columns = []
        for each in self.__query_props.variable:
            variable_columns.append(each)
            if self.__query_props.quality_flag is True:
                LOGGER.debug(f'adding quality flag for : {each}')
                variable_columns.append(f'{each}_quality')
        self.__columns = self.__query_props.columns + variable_columns + self.__columns
        return

    def manage_query_props(self):
        self.__check_bbox()
        self.__check_time_range()
        self.__check_depth()
        self.__add_variables_filter()
        self.__check_columns()
        es_retriever = ParquetPathsEsRetriever(self.__parquet_name, self.__query_props).load_es_from_config(self.__es_config['es_url'], self.__es_config['es_index'], self.__es_config.get('es_port', 443))
        self.__parquet_names = es_retriever.start()
        return
