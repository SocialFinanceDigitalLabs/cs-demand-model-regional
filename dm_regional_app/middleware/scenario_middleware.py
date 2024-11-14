import re

from django.contrib import messages
from django.shortcuts import redirect

from dm_regional_app.models import DataSource, SessionScenario


class SessionScenarioMiddleware:
    PATHS_TO_IGNORE = re.compile(
        r"(/admin.*)|(/accounts.*)|(/upload_data.*)|(/$)",
        re.IGNORECASE,
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialise a SessionScenario
        session_scenario_id = request.session.get("session_scenario_id", None)
        current_user = request.user

        if not current_user.is_authenticated:
            return self.get_response(request)

        if DataSource.objects.exists():
            historic_filters = {
                "la": [],
                "ethnicity": [],
                "sex": "all",
                "uasc": "all",
            }

            data = DataSource.objects.latest("uploaded")
            prediction_parameters = {
                "reference_start_date": data.start_date,
                "reference_end_date": data.end_date,
                "prediction_start_date": None,
                "prediction_end_date": None,
            }
            historic_stock = {
                "population": {},
                "base_rates": [],
            }
            inflation_parameters = {
                "inflation": False,
                "inflation_rate": 0.1,
            }

            # default_values should define the model default parameters
            session_scenario, created = SessionScenario.objects.get_or_create(
                id=session_scenario_id,
                defaults={
                    "user_id": current_user.id,
                    "historic_filters": historic_filters,
                    "prediction_parameters": prediction_parameters,
                    "historic_stock": historic_stock,
                    "adjusted_costs": None,
                    "adjusted_rates": None,
                    "adjusted_proportions": None,
                    "inflation_parameters": inflation_parameters,
                },
            )

            request.session["session_scenario_id"] = session_scenario.pk
        else:
            if self.PATHS_TO_IGNORE.match(request.path_info):
                return self.get_response(request)

            messages.error(
                request,
                "There is no data available. If you are an admin, please upload data via Data Source Upload. Otherwise, "
                "please contact your local admin.",
            )
            return redirect("home")

        return self.get_response(request)
