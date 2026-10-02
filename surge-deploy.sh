#!/bin/bash
export https_proxy=http://127.0.0.1:19359 http_proxy=http://127.0.0.1:19359
echo "hok-heroes.surge.sh" | npx -y surge ./ 2>&1
