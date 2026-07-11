from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)


def generate_pdf(username, websites):

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    elements = []

    title = Paragraph("<b>WebWatch Monitoring Report</b>", styles["Title"])

    elements.append(title)

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph(
            f"<b>User:</b> {username}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"<b>Generated:</b> {datetime.now()}",
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 20))

    data = [[
        "Website",
        "Status",
        "SSL Warning",
        "SSL Expiry"
    ]]

    for website in websites:

        status = "Online" if website.status else "Offline"

        ssl_warning = "Yes" if website.ssl_warning else "No"

        expiry = (
            website.ssl_expiry.strftime("%Y-%m-%d")
            if website.ssl_expiry
            else "-"
        )

        data.append([
            website.website_name,
            status,
            ssl_warning,
            expiry
        ])

    table = Table(data)

    table.setStyle(

        TableStyle([

            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),

            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

            ("GRID", (0, 0), (-1, -1), 1, colors.black),

            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),

            ("ALIGN", (0, 0), (-1, -1), "CENTER"),

            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),

        ])

    )

    elements.append(table)

    elements.append(Spacer(1, 25))

    elements.append(

        Paragraph(

            "Generated automatically by WebWatch",

            styles["Italic"]

        )

    )

    doc.build(elements)

    buffer.seek(0)

    return buffer