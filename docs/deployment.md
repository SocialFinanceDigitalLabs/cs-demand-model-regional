# Deployment Guide

Currently, the web application is deployed on Heroku and connects to an S3 bucket in AWS. This guide
will help you set up a new instance using the same technical stack. Please refer to 
the [architecture guide](architecture.md) for more details on how the application pieces 
fit together.

## Prerequisites
- Heroku account and [team](https://devcenter.heroku.com/articles/heroku-teams)
- Heroku CLI installed and configured
- DNS provider
- AWS account with appropriate permissions to create S3 buckets and IAM roles
- Azure account with appropriate permissions to create an app registration and enterprise application (if using Microsoft SSO)

## Steps to Deploy
1. Create required AWS infrastructure following the [infrastructure guide](../infrastructure/README.md#new-deployment).
2. If using Microsoft for SSO, follow the [SSO configuration guide](SSO.md).
3. Create a new Heroku app
   - Log in to your Heroku account
   - Create a new app in the desired team
   - Set the app name and region - ensure you choose a region in line with any IG requirements
2. Add resources in the Overview tab -> Configure Add-ons
    - Add the [Heroku Postgres](https://elements.heroku.com/addons/heroku-postgresql) add-on 
    - Add the [Heroku Papertrail](https://elements.heroku.com/addons/papertrail) add-on
3. Configure automatic deployments
   - Connect the Heroku app to this Github repository - you will need admin rights on the repository.
   - Enable automatic deployments from the main branch and tick the "Wait for CI to pass before deploying" option
3. Configure app settings
   - Go to the Settings tab of your Heroku app
   - Under "Buildpacks" add the following buildpacks in this order:
     - `https://github.com/SocialFinanceDigitalLabs/python-poetry-buildpack.git`
     - `heroku/python`
   - Under Config Vars, add the following environment variables:
     - `ALLOWED_HOSTS`: A comma separated list of any domain names you will use for the app (e.g., `csdemandmodel.org.uk`)
     - `AWS_ACCESS_KEY_ID`: AWS access key ID created during `terraform apply`
     - `AWS_SECRET_ACCESS_KEY`: AWS secret access key created during `terraform apply` and retrieved with `terraform output secret_access_key`
     - `AWS_STORAGE_BUCKET_NAME`: The name of your S3 bucket created during `terraform apply`
     - `DATABASE_URL`: This should have been automatically set by the Heroku Postgres add-on. It will look something like `postgres://username:password@hostname:port/dbname`.
     - `DATA_STORAGE_LOCATION`: The location within the S3 bucket where the data will be stored - leave blank to point to root location
     - `DISABLE_POETRY_CREATE_RUNTIME_FILE`: 1
     - `DJANGO_SECRET_KEY`: A [secret key](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-SECRET_KEY) for the Django application
     - `DJANGO_SETTINGS_MODULE`: `dm_regional_site.settings.production`
     - `MICROSOFT_CLIENT_ID`: Your Microsoft OAuth client ID for authentication (from step 2, if applicable)
     - `MICROSOFT_CLIENT_SECRET`: Your Microsoft OAuth client secret for authentication (from step 2, if applicable)
     - `MICROSOFT_TENANT_ID`: Your Microsoft OAuth tenant ID for authentication (from step 2, if applicable)
     - `POETRY_VERSION`: At least 1.8.3
     - `SENTRY_DSN`: The DSN for the associated Sentry project
     - `SENTRY_ENVIRONMENT`: The environment name for Sentry (e.g., `production-{region}`)
   - Configure SSL -> Automatic Certificate Management (ACM) to provision an SSL certificate for your domain
   - Domains -> Configure your custom domain and add it to your DNS provider
4. Deploy the application
   - Trigger a manual deployment from the Deploy -> Manual deploy.
5. Create a superuser
   - Run the following command in the Heroku console (or via the CLI) to create a superuser:
     ```bash
     python manage.py createsuperuser
     ```
   - Follow the prompts to set up the superuser account

### Delete Session Scenarios

To manage data transfer between views, users are assigned a session scenario. These scenarios should be deleted regularly,
perhaps through the Heroku Scheduler.
To delete session scenarios:

```
python manage.py erase_session_scenarios
```