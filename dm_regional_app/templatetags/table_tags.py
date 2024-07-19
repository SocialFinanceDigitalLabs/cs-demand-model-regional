import pandas as pd
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def convert_data_frame_to_html_table(df):
    """
    This takes a dataframe and converts it to a table
    As this is not used for showing base rates, checks if "base" is in value and removes it
    """
    html = "<thead><tr>"
    for value in df.columns:
        modified_value = value
        if "base" in value.lower():
            modified_value = value.lower().replace("base", "").strip().capitalize()
        html += f'<th scope="col" style="padding-top: 8px; padding-bottom: 8px;">{modified_value}</th>'
    html += "</tr></thead><tbody>"
    for row in df.values:
        row_html = "<tr>"
        for value in row:
            if isinstance(value, str):
                row_html += f'<th scope="row" style="font-size: 15px; padding-top: 8px; padding-bottom: 8px;">{value}</th>'
            else:
                row_html += f'<td scope="row" style="font-size: 15px; padding-top: 8px; padding-bottom: 8px;">{value}</td>'
        row_html += "</tr>"
        html += row_html
    html += "</tbody>"
    return html


@register.simple_tag
def convert_data_frame_to_html_table_plus_form(df, form, header="Rate multiplication"):
    """
    This takes both dataframe and form
    It will create a row for each item that shares an index
    The form input field will be at the end of each row
    """

    html = "<thead><tr>"
    for value in df.columns:
        html += f'<th scope="col">{value.capitalize()}</th>'
    html += f'<th scope="col">{header}</th></tr></thead><tbody>'
    for index, row in df.iterrows():
        row_html = "<tr>"
        for value in row:
            if isinstance(value, str):
                row_html += f'<th scope="row" style="font-size: 15px; padding-top: 8px;">{value}</th>'
            else:
                row_html += f'<td scope="row" style="font-size: 15px; padding-top: 8px;">{value}</td>'
        field_html = str(form[str(index)])
        row_html += f'<td scope="row">{field_html}</td>'
        row_html += "</tr>"
        html += row_html
    html += "</tbody>"
    return mark_safe(html)
