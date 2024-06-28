from django import template

register = template.Library()


def convert_data_frame_to_html_table_headers(df):
    """
    This takes a dataframe
    As this is not used for showing base rates, checks if "base" is in value and removes it
    """
    html = "<tr>"
    for value in df.columns:
        modified_value = value
        if "base" in value.lower():
            modified_value = value.lower().replace("base", "").strip().capitalize()
        html += f'<th><p style="font-size:14px;">{modified_value}</p></th>'
    html += "</tr>"
    return html


def convert_data_frame_to_html_table_headers_form(df):
    """
    This takes only the dataframe but adds an additional column to allow for the form to be integrated
    """
    html = "<tr>"
    for value in df.columns:
        html += f"<th><p>{value.capitalize()}</p></th>"
    html += "<th><p>Rate multiplication</p></th></tr>"
    return html


def convert_data_frame_to_html_table_rows_form(df, form):
    """
    This takes both dataframe and form
    It will create a row for each item that shares an index
    The form input field will be at the end of each row
    """
    html = ""
    for index, row in df.iterrows():
        row_html = "<tr>"
        for value in row:
            if isinstance(value, str):
                row_html += f"<th><p>{value}</p></th>"
            else:
                row_html += f"<td><p>{value}</p></td>"
                field_html = str(form[str(index)])
                row_html += f"<td>{field_html}</td>"
        row_html += "</tr>"
        html += row_html
    return html


def convert_data_frame_to_html_table_rows(df):
    html = ""
    for row in df.values:
        row_html = "<tr>"
        for value in row:
            if isinstance(value, str):
                row_html += f'<th><p style="font-size:14px;">{value}</p></th>'
            else:
                row_html += f'<td><p style="font-size:14px;">{value}</p></td>'
        row_html += "</tr>"
        html += row_html
    return html


register.filter(
    "convert_data_frame_to_html_table_rows", convert_data_frame_to_html_table_rows
)

register.filter(
    "convert_data_frame_to_html_table_rows_form",
    convert_data_frame_to_html_table_rows_form,
)

register.filter(
    "convert_data_frame_to_html_table_headers", convert_data_frame_to_html_table_headers
)

register.filter(
    "convert_data_frame_to_html_table_headers_form",
    convert_data_frame_to_html_table_headers_form,
)
