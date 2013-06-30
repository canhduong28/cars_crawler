#!bin/bash
# pending a job of lead_spider to scrapyd service
curl http://localhost:6800/schedule.json -d project=fatech_production -d spider=cars_recon