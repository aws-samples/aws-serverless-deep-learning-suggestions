# Deployment Instructions

The solution is package as an automated deployment via the [AWS Serverless Application Model (SAM)](https://aws.amazon.com/serverless/sam/) CLI. The static website configuration will then be modified and uploaded to the static website Amazon S3 bucket.

The following sections guide you through the following process:

- Download the sample code to your local machine
- Deploy the serverless application via the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- Adjust the config file in the static website source-code based on deployment values
- Upload the static website to the Amazon S3 bucket
- Submit a sample maintenance report to test the citizen workflow
- View the map and resolve a maintenance item to test the government workflow

## Prerequisites

For this walkthrough, you need to have the following prerequisites:

- An [AWS account](https://signin.aws.amazon.com/signin?redirect_uri=https%3A%2F%2Fportal.aws.amazon.com%2Fbilling%2Fsignup%2Fresume&client_id=signup)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html) installed and set up with [credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html#cli-configure-files-methods)
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

The AWS SAM CLI is an open source command line tool used to locally build, test, debug, and deploy serverless applications defined with [AWS SAM templates](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-specification-template-anatomy.html).

Download the sample app source code and extract locally.

## Build and Deploy the Stack

1. In a terminal and navigate to the `./sam/` directory
2. Run the following command to build and package the project for deployment:

   `sam build`
3. Verify template formatting and deployability:

   `sam validate`
4. Deploy the SAM template to your account. The wizard will step through the process of deploying the SAM CloudFormation stack. Details on this process are found in the [sam build](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-build.html) documentation.
   1. Run the following command:

      `sam deploy --guided --capabilities CAPABILITY_NAMED_IAM`
   2. Select the supported region you chose in the Prerequisites section.
   3. Choose `Y` to all Y/N items.
5. Once the build completes, note the entries in the Outputs section, they'll be needed in the following sections:
   1. `SubmissionURL`
   2. `ViewingURL`

This concludes the deployment of the back-end infrastructure. Optionally, you can view the deployed resources by logging into the AWS Management Console, navigating to the CloudFormation service, selecting the relevant CloudFormation stack and choosing the Resources tab.

This concludes the deployment of the static website front-end. The
entire application is deployed.

## Updating Website Contents

The website contents are automatically deployed into the Static S3 bucket via the `seed_s3_data` function. The contents come from `sam/seed_s3_data/website.zip`. The contents are NOT updated after the first deployment of the stack.

When you modify the website code in `website/` the contents will NOT apply to new stacks automatically. You must zip the contents before the `sam build` step.

Run the following from the root of the repository:

```bash
> zip -r ./sam/seed_s3_data/website.zip website
```

If you wish to update the website contents of a previously deployed stack, use the following sequence:

1. Update the contents of `website/` with new functionality or bug fixes
2. Upload the contents of `website/` to the static website S3 bucket (`dl-suggest-blog-static-website-[...]`)
3. Create a CloudFront Invalidation on the CloudFront Distribution for `/*` to clear the CloudFront caches globally
4. When ready to package the website for new deployments, run the following from the root of the repository: `zip -r ./sam/seed_s3_data/website.zip website`