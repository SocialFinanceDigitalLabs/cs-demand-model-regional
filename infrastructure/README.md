# Infrastructure

Demand Modelling needs to have a location for uploaded files. For this, we
use S3. The files contained here create a terraformed stack in AWS.

[A remote backend](https://developer.hashicorp.com/terraform/language/state/remote) 
has been implemented to allow developers to work on and 
adjust the same terraform state without committing it to version control.

[Workspaces](https://developer.hashicorp.com/terraform/cli/workspaces) are used 
to separate the resources created for different environments. When planning and
applying for `staging` and `prod` environments, ensure you are in the right
workspace first.

## Prerequisites
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
- If using AWS CLI v2, [configure your CLI to use SSO](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html#sso-configure-profile-token-auto-sso):

```bash
aws configure sso
```
- Set the environment variable `AWS_PROFILE` to the relevant profile


## How to use
1. Initialise terraform within this directory
```bash
terraform init
```
2. Connect to the `staging` workspace
```bash
terraform workspace list
terraform workspace select staging
```
3. Make appropriate changes to terraform files
4. Run and verify the accuracy of a terraform plan
```bash
terraform plan -var-file="staging.tfvars"
```
5. Apply the plan
```bash
terraform apply -var-file="staging.tfvars"
```
6. Confirm via AWS Console that the resources look as expected

## Gotchas
If you are initialising terraform providers (with `terraform init`), ensure
you run:
```bash
terraform providers lock -platform=windows_amd64 -platform=linux_amd64
```
This will write checksums for both Windows and Linux to the lock file
which ensures developers (and any CI) working across platforms can 
plan and apply changes.