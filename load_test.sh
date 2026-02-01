#!/bin/bash
for i in {1..5}
do
   curl -X POST "http://localhost:8000/fetch" -H "Content-Type: application/json" -d '{"url": "https://example.com"}' &
done
wait
echo "Done"
