from django import template

register = template.Library()


def convert_data_frame_to_html_table_headers(df):
    html = ""
    for row in df.values:
        row_html = "<tr>"
        for value in row:
            row_html += f'<th><p style="font-size:14px;">{value.capitalize()}</p></th>'
        row_html += "</tr>"
        html += row_html
    return html


def convert_data_frame_to_html_table_rows(df):
    html = ""
    for row in df.values:
        row_html = "<tr>"
        for value in row:
            if isinstance(value, str):
                row_html += (
                    f'<th><p style="font-size:14px;">{value.capitalize()}</p></th>'
                )
            else:
                row_html += f'<td><p style="font-size:14px;">{value}</p></td>'
        row_html += "</tr>"
        html += row_html
    return html


def adjustment_buttons(df):
    html = "<tr><td></td><td></td>"
    column_id = 0
    row = df.iloc[0].values.flatten().tolist()
    row_len = len(row) - 2
    for value in range(row_len):
        html += f'<td><a class="btn btn-primary" href="#" id={column_id}>Edit this column</a></td>'
        column_id += 1
    html += "</tr>"
    return html


register.filter(
    "convert_data_frame_to_html_table_rows", convert_data_frame_to_html_table_rows
)

register.filter(
    "convert_data_frame_to_html_table_headers", convert_data_frame_to_html_table_headers
)

register.filter("adjustment_buttons", adjustment_buttons)
