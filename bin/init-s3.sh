#!/bin/bash

if [[ "$LANCEDB_URI" =~ ^s3://[a-z0-9.-]{3,63}(/[^ ]*)?$ ]]; then
  awslocal s3 mb $LANCEDB_URI 
else
  awslocal s3 mb s3://willa
fi 
