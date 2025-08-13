# Infrastructure

Demand Modelling needs to have a location for uploaded files. For this, we
use S3. The files contained here create a terraformed stack in AWS.

[A remote backend](https://developer.hashicorp.com/terraform/language/state/remote) 
has been implemented to allow developers to work on and 
adjust the same terraform state without committing it to version control.
In order to keep deployments separate and allow for the future handover of
deployments to clients, we keep terraform state in an S3 bucket in the
target AWS account. Then these modules can be applied to different accounts
by using `-backup-config` flag when running `terraform init`.

## Prerequisites
- AWS account and [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
- If using AWS CLI v2, [configure your CLI to use SSO](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html#sso-configure-profile-token-auto-sso):

```bash
aws configure sso
```
The start URL can be found in IAM Identity Centre

- Set the environment variable `AWS_PROFILE` to the relevant profile


## How to use (existing deployment)
1. Initialise terraform within this directory, including the relevant backend configuration.
```bash
terraform init -backend-config="./backend_config/staging.config"
```
2. Make appropriate changes to terraform files 
3. Run and verify the accuracy of a terraform plan
```bash
terraform plan -var-file="variables/staging.tfvars"
```
5. Apply the plan
```bash
terraform apply -var-file="variables/staging.tfvars"
```
6. Confirm via AWS Console that the resources look as expected
7. If you need the AWS secret access key to set an environment variable, 
you can run the following command to retrieve it:
```bash
terraform output secret_access_key
````

## New Deployment
1. Login via the AWS CLI.
2. Create an S3 bucket for the terraform state ([recommended instructions](https://spacelift.io/blog/terraform-s3-backend)). 
The bucket name will need to unique in the entire region - this is the suggested convention:
`{application}-tfstate-{environment}`
For instance, the terraform state bucket for this application and client GM would be called
`demand-model-tfstate-production-gm`
3. Create a DynamoDB table (from the above instructions).
4. Add a new `config` file with the appropriate details to `backend_config` folder.
Add a new `tfvars` file with the appropriate details to `variables` folder.
5. Initialise terraform 
```bash
terraform init -backend-config="./backend_config/staging.config"
```
If an error appears titled "Backend configuration changed" and you have initialised/applied
this infrastructure to a different account/backend previously, add the `-reconfigure` flag
to the `terraform init` command.

## Gotchas
If you are initialising terraform providers (with `terraform init`), ensure
you run:
```bash
terraform providers lock -platform=windows_amd64 -platform=linux_amd64
```
This will write checksums for both Windows and Linux to the lock file
which ensures developers (and any CI) working across platforms can 
plan and apply changes.

If you are switching between backends in order to apply changes to more than one
deployment, this command will show you available profiles:
```bash
aws configure list-profiles
```
And this command will log you in appropriately (first set the `AWS_PROFILE` environment
variable):
```bash
aws sso login
```