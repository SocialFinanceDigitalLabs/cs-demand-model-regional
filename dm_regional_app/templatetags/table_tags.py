from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def convert_data_frame_to_html_table(df):
    """
    This takes a dataframe and converts it to a table.
    As this is not used for showing base rates, checks if "base" is in value and removes it.
    """

    def format_value(value):
        """Formats the value to add commas for large numbers."""
        if isinstance(value, (int, float)) and (value > 1 or value < -1):
            return f"{value:,.2f}"
        return value

    html = "<thead><tr>"
    for value in df.columns:
        if isinstance(value, str):
            if "base" in value.lower():
                value = value.lower().replace("base", "").strip().capitalize()
            html += f'<th scope="col" style="padding-top: 8px; padding-bottom: 8px;">{value}</th>'
    html += "</tr></thead><tbody>"

    for row in df.values:
        row_html = "<tr>"
        for value in row:
            if isinstance(value, str):
                row_html += f'<th scope="row" style="font-size: 15px; padding-top: 8px; padding-bottom: 8px;">{value}</th>'
            else:
                formatted_value = format_value(value)
                row_html += f'<td scope="row" style="font-size: 15px; padding-top: 8px; padding-bottom: 8px;">{formatted_value}</td>'
        row_html += "</tr>"
        html += row_html

    html += "</tbody>"
    return html


@register.simple_tag
def convert_df_plus_dynamicform_to_html_table(df, form, header):
    """
    This takes both dataframe and DynamicForm
    It will create a row for each item that shares an index
    The form input field will be at the end of each row
    """

    # Start building the HTML table
    html = "<thead><tr>"

    # Create headers for each column in the dataframe
    for value in df.columns:
        html += f'<th scope="col">{value.capitalize()}</th>'

    # Add header for form input column
    html += f'<th scope="col">{header}</th></tr></thead><tbody>'

    # Iterate over the dataframe rows and add the form fields
    for index, row in df.iterrows():
        row_html = "<tr>"
        for value in row:
            if isinstance(value, str):
                row_html += f'<th scope="row" style="font-size: 15px; padding-top: 8px;">{value}</th>'
            else:
                row_html += f'<td scope="row" style="font-size: 15px; padding-top: 8px;">{value}</td>'

        # Create form field and add to row
        field_html = str(form[str(index)])
        row_html += (
            f'<td scope="row" style="font-size: 15px; padding-top: 8px;">{field_html}'
        )

        # Add error messages for field if they exist
        if form[f"{index}"].errors:
            row_html += '<div class="text-danger">'
            for error in form[f"{index}"].errors:
                row_html += f"<p>{error}</p>"
            row_html += "</div>"

        # Close cell and row
        row_html += "</td></tr>"

        html += row_html

    # Close table body
    html += "</tbody>"
    return mark_safe(html)


@register.filter
def convert_summary_tables_to_html_table(df):
    """
    This takes a dataframe and converts it to a table.
    As this is not used for showing base rates, checks if "base" is in value and removes it.
    """

    def format_value(value):
        """Formats the value to add commas for large numbers."""
        if isinstance(value, (int, float)) and (value > 1 or value < -1):
            return f"{value:,.2f}"
        return value

    html = f'<thead><tr><th scope="col" style="padding-top: 8px; padding-bottom: 8px;">Placement</th>'
    for value in df.columns:
        if isinstance(value, str):
            if "base" in value.lower():
                value = value.lower().replace("base", "").strip().capitalize()
            html += f'<th scope="col" style="padding-top: 8px; padding-bottom: 8px;">{value}</th>'
    html += "</tr></thead><tbody>"

    for index, row in df.iterrows():
        row_html = f'<tr><th scope="row" style="font-size: 15px; padding-top: 8px; padding-bottom: 8px;">{index}</th>'
        for value in row:
            if isinstance(value, str):
                row_html += f'<th scope="row" style="font-size: 15px; padding-top: 8px; padding-bottom: 8px;">{value}</th>'
            else:
                formatted_value = format_value(value)
                row_html += f'<td scope="row" style="font-size: 15px; padding-top: 8px; padding-bottom: 8px;">{formatted_value}</td>'
        row_html += "</tr>"
        html += row_html

    html += "</tbody>"
    return html


@register.filter
def convert_df_and_dynamicrateform_to_table(df, form):
    """
    This takes both dataframe and DynamicRateForm.
    It will create a row for each item that shares an index.
    The form input fields (multiply and add) will be at the end of each row,
    and any errors will be displayed under the corresponding input fields.
    """

    # Start building the HTML table
    html = "<thead><tr>"

    # Create headers for each column in the dataframe
    for value in df.columns:
        html += f'<th scope="col">{value.capitalize()}</th>'

    # Add headers for multiplication and addition
    html += '<th scope="col">Multiply Rate</th>'
    html += '<th scope="col">Add to Rate</th>'
    html += "</tr></thead><tbody>"

    # Iterate over the dataframe rows and add the form fields
    for index, row in df.iterrows():
        row_html = "<tr>"

        # For each value in the row, create a table cell
        for value in row:
            if isinstance(value, str):
                row_html += f'<th scope="row" style="font-size: 15px; padding-top: 8px;">{value}</th>'
            else:
                row_html += f'<td scope="row" style="font-size: 15px; padding-top: 8px;">{value}</td>'

        # Create form fields for multiply and add rates
        multiply_field_html = str(form[f"multiply_{index}"])
        add_field_html = str(form[f"add_{index}"])

        # Add form fields to the row
        row_html += f'<td scope="row" style="font-size: 15px; padding-top: 8px;">{multiply_field_html}'

        # Add error messages for multiply field if they exist
        if form[f"multiply_{index}"].errors:
            row_html += '<div class="text-danger">'
            for error in form[f"multiply_{index}"].errors:
                row_html += f"<p>{error}</p>"
            row_html += "</div>"

        row_html += "</td>"

        # Add form fields for add rate and include error messages
        row_html += f'<td scope="row" style="font-size: 15px; padding-top: 8px;">{add_field_html}'

        # Add error messages for add field if they exist
        if form[f"add_{index}"].errors:
            row_html += '<div class="text-danger">'
            for error in form[f"add_{index}"].errors:
                row_html += f"<p>{error}</p>"
            row_html += "</div>"

        row_html += "</td>"

        # Close the table row
        row_html += "</tr>"
        html += row_html

    # Close the table body
    html += "</tbody>"

    return html
