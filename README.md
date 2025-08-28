# Children's Social Care Demand Model - Regional Webapp

This repository contains the code for the webapp that accompanies the [Children's Social Care Demand Model](https://github.com/data-to-insight/cs-demand-model).

## Why?

The [existing live application](https://github.com/data-to-insight/cs-demand-model) runs on pyodide and requires the user to upload the 903 files. 
This tool is expected to read the data from a remote source (an S3 bucket or similar) and create similar analysis as before, with the following benefits:

- A new user interface with a focus on user experience
- It uses the [new generic demand model](https://github.com/SocialFinanceDigitalLabs/demand-model) which, besides predicting the number of children, also includes a confidence interval.
- Since it's a standard webapp, it now has a database, which makes it possible to save user preferences and scenarios, as well as handle authentication and permissions.

## Getting Started

See the [local development guide](docs/local_development.md) for instructions on how to set up the project locally.

See the [deployment guide](docs/deployment.md) for instructions on how to deploy the application.

See the [architecture guide](docs/architecture.md) for an overview of the application's architecture.