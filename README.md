# Deep Learning Suggestion Example

An interactive mobile website and backend to create a fluid experience for citizens reporting issues in their area.

For deployment instructions see [DEPLOYMENT](./docs/DEPLOYMENT.md).

## Architecture

![Overall Architecture Diagram](./docs/arch-overview.png "Overall Architecture Diagram")

## Workflows

This example application has two general workflows:

1. Citizen Workflow - A citizen loads a mobile web page, takes a picture, submits picture for suggestion processing, makes a selection on the report type, then submits the report.
2. Government Workflow - A government worker loads desktop web page, retrieves the submitted reports and renders those as pins on a map with details, which can then be dismissed/resolved.

## Citizen Workflow

![Citizen Workflow Diagram](./docs/arch-citizen-flow.png "Citizen Workflow Diagram")

1. Mobile User accesses static website via CloudFront CDN
2. CloudFront CDN returns cached content, or retrieves the static site from the origin (S3 Bucket)
3. Static website loads and browser obtains temporary credentials from Cognito (used for S3 upload)
4. User uploads image to S3 bucket
5. S3 event triggers Process Image Lambda function
6. Lambda function requests Rekognition processes image, receives list of labels in the image
7. Lambda function retrieves list of possible reports from DynamoDB Report Table, compares that to Rekognition results, determines the recommendations, and saves it to the Reports Table
8. Immediately after step #3, the browser begins checking for the processed image results every 500ms via API Gateway.
9. Each API Gateway request calls a Lambda function to get report types or results from a processed image.
10. Lambda function retrieves the relevant data from the DynamoDB table. User makes a selection on the type of report they want to submit, and it is submitted via second 8-10 sequence.


## Government Workflow

![Government Workflow Diagram](./docs/arch-govt-flow.png "Government Workflow Diagram")

1. Desktop User accesses static website via CloudFront CDN
2. CloudFront CDN returns cached content, or retrieves the static site from the origin (S3 Bucket)
3. Static website loads and browser obtains temporary credentials from Cognito (used for Map/Location Rendering)
4. Browser renders map from the Amazon Location Service
5. Browser requests all open submissions and report types from API Gateway
6. Each API Gateway request calls a Lambda function to get report types and open reports
7. Lambda function retrieves the relevant data from the DynamoDB table and passes it back to the browser. The worker eventually chooses to resolve the report, whose request follows the 5-7 steps marking the report resolved in the database.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
