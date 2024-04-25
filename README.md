# Children's Social Care Demand Model - Regional Webapp

This repository contains the code for the webapp that accompanies the [Children's Social Care Demand Model](https://github.com/data-to-insight/cs-demand-model).

## Why?

The [existing live application](https://github.com/data-to-insight/cs-demand-model) runs on pyodide and requires the user to upload the 903 files. 
This tool is expected to read the data from a remote source (an S3 bucket or similar) and create similar analysis as before, with the following beneficts:

- A new user interface with a focus on user experience
- It uses the [new generic demand model](https://github.com/SocialFinanceDigitalLabs/demand-model) which, besides predicting the number of children, also includes a confidence interval.
- Since it's a standard webapp, it now has a database, which makes it possible to save user preferences and scenarios, as well as handle authentication and permissions.


# Local Setup
You need to have [python](https://www.python.org/) and [poetry](https://python-poetry).


3. Install dependencies with `poetry install`;
4. Launch a poetry shell so the virtual environment is active: `poetry shell`;
5. Run `python manage.py migrate` to create the databases tables;
6. Add the pre-commit hook by running `pre-commit install`. This will ensure your code is formatted before you commit something;

## Load fixtures
To load some dummy data, run:

```
python manage.py load-fixtures
```

This will load some users:

**Regular user**
- email: john.smith@bromley.gov.uk
- password: test

**Admin user**
- email: admin@example.test
- password: test


## Delete Session Scenarios

To manage data transfer between views, users are assigned a session scenario. These scenarios should be deleted weekly through a recurrant job wherever the app is deployed.
To run this command:

```
python manage.py erase_session_scenarios
```

## Run

Run `python manage.py runserver` to access the regional demand model platform. it will be live at http://localhost:8000.