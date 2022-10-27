# Deployment Instructions

The solution is package as an automated deployment via the [AWS Serverless Application Model (SAM)](https://aws.amazon.com/serverless/sam/) CLI.

The following sections guide you through the following process:

- Download the sample code to your local machine
- Deploy the serverless application via the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- Adjust the config file in the static website source-code based on deployment values
- Upload the static website to the Amazon S3 bucket
- Submit a sample maintenance report to test the citizen workflow
- View the map and resolve a maintenance item to test the government workflow

## Prerequisites

For this walkthrough, you need to have the following prerequisites:

- An [AWS account](https://portal.aws.amazon.com/billing/signup)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) installed and set up with [credentials](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-getting-started-set-up-credentials.html)
- Python 3.9 Installed and in your PATH variable
- A smart phone with location services enabled for testing
- Select one of the supported regions:
  - US East (N. Virginia)
  - US East (Ohio)
  - US West (Oregon)
  - Europe (Frankfurt)
  - Europe (Ireland)
  - Europe (Stockholm)
  - Asia Pacific (Singapore)
  - Asia Pacific (Sydney)
  - Asia Pacific (Tokyo)

## Deployment

For this walkthrough, you must have the following prerequisites:

The AWS SAM CLI is an open-source command line tool used to locally build, test, debug, and deploy serverless applications defined with [AWS SAM templates](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-specification-template-anatomy.html).

[Download](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) the source code and extract locally: [AWS Samples -- AWS Serverless Deep Learning Suggestions](https://github.com/aws-samples/aws-serverless-deep-learning-suggestions)

#### Build and deploy the stack

1. In a terminal, navigate to the ./sam/ directory
2. Run the following command to build and package the project for deployment:\
`sam build`
3. Deploy the SAM template to your account. The wizard will guide you through the process of deploying the SAM CloudFormation stack. Details on this process are found in the [sam build documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-build.html).
   1. Run the following command: \
      `sam deploy --guided --capabilities CAPABILITY_NAMED_IAM`
   2. Select the supported AWS Region you chose in the prerequisites section.
   3. The default parameters are suggested.
   4. Choose "Y" for all Yes or No items.
4. Wait for the deployment to complete. This process takes approximately five minutes.
5. Once the build completes, note the entries in the Outputs section. These are the URLs for the two pages of the Deep Learning Suggestion application.
   1. SubmissionURL -- Citizen UI for submitting reports of damage
   2. MapViewURL -- Government UI for viewing the submitted damage reports on a map

This concludes the deployment of the Deep Learning Suggestion application. AWS SAM CLI uses [AWS CloudFormation](https://aws.amazon.com/cloudformation/) to orchestrate the deployment of both the backend API, image processing infrastructure, and the front-end static website. The entire application is deployed.
