# Leaflambda  

Control your Nissan Leaf with your Amazon Alexa or Echo Dot via AWS Lambda

Special thanks to https://github.com/ScottHelme/AlexaNissanLeaf.  I borrowed heavily, but really wanted everything to be in python.

# What's in this repo

Intent Schema & utterances for setting up an Alexa Skill (this is a manual step).

`service.py` - the actual AWS lambda function that (1) gathers data from your Leaf every hour and (2) answers specific synchronous questions & performs actions.

`deploy.zip` - a package of the lambda function + dependencies suitable for uploading to AWS lambda

`build.sh` - a script for building `deploy.zip`.  Get onto an AWS EC2 instance to create the package appropriately

`leaflambda.tf` and `variables.tf` - terraform script for easy deploy onto AWS (still a work in progress)

# Installation

There are a few manual steps to get this working, but I've created a terraform script to make it easier.

1. Get yourself an AWS account and get your AWS credentials in env vars.
2. Get terraform (https://learn.hashicorp.com/terraform/getting-started/install.html)
3. Edit the `variables.tf` file with your nissan username & password, and the name of a new S3 bucket to be created.

...(The S3 bucket is used as both a cache for current leaf state so latency is low on requests, as well as saving a log of your Nissan Leaf status every hour)

4. Run `./terraform apply`.  This will setup several things in AWS:
..* Create an S3 bucket for the cache
..* Create an IAM role for lambda execution with several permissions that it needs
..* Create a lambda function and upload `deploy.zip` into it
..* Create a cloudwatch event that triggers the lambda to run every hour

At this point the lambda will be collecting data from your Leaf every hour (stored as logfiles in S3), and you can analyze it for example with AWS Athena (see `aws_athena_hive_query.txt` for how to set that up).

# Further Manual Steps you need to do

Create an Alexa Skill and configure it to run this lambda.  The intents and utterances in this repo match what the lambda is expecting as input, and the lambda returns output json that Alexa understands.

It's also nice to create an API Gateway to trigger the lambda.  With this you can trigger it with a google home device (via https://dialogflow.com/) or your own integration.  TODO: get API gateway into terraform for easy setup.