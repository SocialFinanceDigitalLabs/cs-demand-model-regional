import datetime

from django import template

register = template.Library()


@register.filter
def add_days(date, days):
    try:
        days = int(days)
        if date:
            return date + datetime.timedelta(days=days)
    except (ValueError, TypeError):
        # Handle the error if days cannot be converted to an integer
        return date
    return date


@register.filter
def filter_text(dict):
    html = "<p>You have applied the following filters to your historic population:<ul>"

    # Check for 'la' and ensure it has non-empty values
    if dict.get("la"):
        html += "LA:<ul>"
        for la in dict["la"]:
            html += f"<li>{la}</li>"
        html += "</ul>"

    # Check for 'ethnicity' and ensure it has non-empty values
    if dict.get("ethnicity"):
        html += "Ethnicity:<ul>"
        for age_bin in dict["ethnicity"]:
            html += f"<li>{age_bin}</li>"
        html += "</ul>"

    # Only include 'sex' if its value is not 'all' and not empty
    if dict.get("sex") and dict["sex"] != "all":
        html += "Sex:<ul>"
        # Check the value of dict["sex"]
        if dict["sex"] == "1":
            html += "<li>Male</li>"
        else:
            html += "<li>Female</li>"
        html += "</ul>"

    # Only include 'uasc' if its value is not 'all' and not empty
    if dict.get("uasc") and dict["uasc"] != "all":
        html += "UASC:<ul>"
        html += f"<li>{dict['uasc']}</li></ul>"

    if (
        html
        == "<p>You have applied the following filters to your historic population:<ul>"
    ):
        html = "<p>You have not applied any filters to your historic population.</p>"
    else:
        html += "</p></ul>"

    return html
