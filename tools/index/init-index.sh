#!/bin/sh

if [ $# -ne 1 ]
then
    echo usage: $0 http://combined.yoda.test:9200
    exit 2
fi

opensearch=$1

echo -n 'DELETE: '
curl -s -XDELETE $opensearch/yoda
echo ''
echo -n 'CREATE: '
curl -s -XPUT --header 'Content-Type: application/json' $opensearch/yoda -d '{
  "mappings": {
    "properties": {
      "absolutePath": { "type": "text" },
      "dataSize": { "type": "long" },
      "fileName": { "type": "text" },
      "isFile": { "type": "boolean" },
      "lastModifiedDate": { "type": "long" },
      "metadataEntries": {
        "type": "nested",
        "properties": {
          "attribute": {
            "type": "text",
            "fields": { "raw": { "type": "keyword" } }
          },
          "unit": {
            "type": "text",
            "fields": { "raw": { "type": "keyword" } }
          },
          "value": {
            "type": "text",
            "fields": {
              "raw": { "type": "keyword" },
              "number": {
                "type": "long",
                "ignore_malformed": true
              }
            }
          }
        }
      },
      "mimeType": { "type":  "text" },
      "parentPath": { "type": "text" },
      "url": { "type": "text" },
      "zoneName": { "type": "text" }
    }
  }
}'
echo ''
