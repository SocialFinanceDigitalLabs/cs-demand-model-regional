# Local Development
You need to have [python](https://www.python.org/) and [poetry](https://python-poetry.org).

1. Create an `.env` file by copying the `.env.example` one and editing the variables as needed.
2. Set environment variable `DJANGO_SETTINGS_MODULE=dm_regional_site.settings.development` wherever you will be
running django commands (e.g. terminal or Configurations). 
3. Install dependencies with `poetry install`; 
4. Activate the poetry environment
5. Run `python manage.py migrate` to create the databases tables; 
6. Add the pre-commit hook by running `pre-commit install`. This will ensure your code is formatted before you commit something;

## Load fixtures
To flush the entire database and load some dummy data, run:

```
python manage.py load-fixtures
```
>Note: This will delete all existing data in the database!

This will load some users that can be used to log in to the application:
**Regular users**
- email: john.smith@bromley.gov.uk
- password: test


- email: annie.smith@bromley.gov.uk
- password: test


- email: john.smith@southwark.gov.uk
- password: test

**Admin user**
- email: admin@example.test
- password: test

## Run

Run `python manage.py runserver` to access the regional demand model platform. it will be live at http://localhost:8000.