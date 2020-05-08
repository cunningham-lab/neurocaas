#!/bin/bash

cd ncap_iac/ncap_blueprints/

bash iac_utils/build.sh epi_web_stack
bash iac_utils/test_main.sh epi_web_stack
