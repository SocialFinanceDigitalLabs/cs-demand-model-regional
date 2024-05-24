from django import template

register = template.Library()


def convert_data_frame_to_html_table_headers(df):
    html = "<tr>"
    for value in df.columns:
        html += f'<th><p style="font-size:14px;">{value}</p></th>'
    html += "</tr>"
    return html


def convert_data_frame_to_html_table_headers_form(df):
    html = "<tr>"
    for value in df.columns:
        html += f"<th><p>{value.capitalize()}</p></th>"
    html += "<th><p>New rate</p></th></tr>"
    return html


def convert_data_frame_to_html_table_rows_form(df, form):
    html = ""
    for index, row in df.iterrows():
        row_html = "<tr>"
        for i, value in enumerate(row):
            if isinstance(value, str):
                row_html += f"<th><p>{value}</p></th>"
            else:
                row_html += f"<td><p>{value}</p></td>"
            if i == 2:  # Insert the input field in the fourth column
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
