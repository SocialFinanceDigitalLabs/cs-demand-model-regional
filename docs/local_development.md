# Local Development
You need to have [python](https://www.python.org/) and [poetry](https://python-poetry).

1. Create an `.env` file by copying the `.env.example` one and editing the variables as needed.
2. Set environment variable `DJANGO_SETTINGS_MODULE=dm_regional_site.settings.development` in relevant places. 
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

To manage data transfer between views, users are assigned a session scenario. These scenarios should be deleted weekly through a recurrent job wherever the app is deployed.
To run this command:

```
python manage.py erase_session_scenarios
```

## Run

Run `python manage.py runserver` to access the regional demand model platform. it will be live at http://localhost:8000.