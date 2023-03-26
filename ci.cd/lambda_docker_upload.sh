#!/bin/bash

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


aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 848373852523.dkr.ecr.us-west-2.amazonaws.com
docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} 848373852523.dkr.ecr.us-west-2.amazonaws.com/cdms:${DOCKER_TAG}
docker push 848373852523.dkr.ecr.us-west-2.amazonaws.com/cdms:${DOCKER_TAG}