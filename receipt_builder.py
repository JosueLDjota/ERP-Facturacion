"""Utilidades para construir recibos visuales y HTML imprimible."""

from __future__ import annotations

from html import escape

from erp.domain.services.invoice_calculator import calculate_invoice_totals


DEFAULT_EMPRESA = {
    "rtn": "12011972000081",
    "nombre": "PODEGA Y COMERCIAL RIVERA",
    "tel": "2774-1192 / 9967-7300",
    "direccion": (
        "Bo. La Mercedes, Colonia la Ermita, 1ra Calle, 14-62, "
        "frente a Farmacia Santa, La Paz, Honduras"
    ),
    "email": "freddyrivera2015@gmail.com",
    "logo_url": "",
}

DEFAULT_RECEIPT_LABELS = {
    "DOC_TITLE": "FACTURA",
    "ORDER_EXEMPT_LABEL": "Orden de Compra Exenta:",
    "EXEMPT_REGISTER_LABEL": "Constancia Registro Exento:",
    "DISCOUNTS_LABEL": "Desc. y Rebajas Otorgados:",
    "SUMMARY_HEADER": "Concepto         Total",
    "LABEL_SUBTOTAL": "Sub Total",
    "LABEL_EXENTO": "Exento",
    "LABEL_GRAVADA_15": "Gravado 15%",
    "LABEL_GRAVADA_18": "Gravado 18%",
    "LABEL_IMPUESTO_15": "Impuesto 15%",
    "LABEL_IMPUESTO_18": "Impuesto 18%",
    "LABEL_TOTAL": "TOTAL:",
    "LABEL_MONTO_RECIBIDO": "Monto Recibido:",
    "LABEL_VUELTO": "Vuelto:",
    "LABEL_OBSERVACIONES": "Observaciones:",
    "COPY_LABEL": "Original - Cliente",
    "THANK_YOU_MESSAGE": "Gracias por su compra",
}

LABEL_CONFIG_KEYS = {
    "DOC_TITLE": "recibo_doc_title",
    "ORDER_EXEMPT_LABEL": "recibo_label_orden_exenta",
    "EXEMPT_REGISTER_LABEL": "recibo_label_registro_exento",
    "DISCOUNTS_LABEL": "recibo_label_descuentos",
    "SUMMARY_HEADER": "recibo_summary_title",
    "LABEL_SUBTOTAL": "recibo_label_subtotal",
    "LABEL_EXENTO": "recibo_label_exento",
    "LABEL_GRAVADA_15": "recibo_label_gravado_15",
    "LABEL_GRAVADA_18": "recibo_label_gravado_18",
    "LABEL_IMPUESTO_15": "recibo_label_impuesto_15",
    "LABEL_IMPUESTO_18": "recibo_label_impuesto_18",
    "LABEL_TOTAL": "recibo_label_total",
    "LABEL_MONTO_RECIBIDO": "recibo_label_monto_recibido",
    "LABEL_VUELTO": "recibo_label_vuelto",
    "LABEL_OBSERVACIONES": "recibo_label_observaciones",
    "COPY_LABEL": "recibo_copy_label",
    "THANK_YOU_MESSAGE": "recibo_thanks_message",
}


def _default_number_to_words(n):
    return str(n)


def default_receipt_labels() -> dict[str, str]:
    return dict(DEFAULT_RECEIPT_LABELS)


def load_receipt_labels(config_getter) -> dict[str, str]:
    labels = default_receipt_labels()
    for label_key, config_key in LABEL_CONFIG_KEYS.items():
        value = config_getter(config_key, labels[label_key])
        labels[label_key] = str(value or labels[label_key])
    return labels


def default_receipt_template() -> str:
    return (
        "{{NOMBRE_NEGOCIO}}\n"
        "R.T.N.: {{EMPRESA_RTN}}\n"
        "Tel: {{EMPRESA_TEL}}\n"
        "{{EMPRESA_DIRECCION}}\n"
        "Email: {{EMPRESA_EMAIL}}\n\n"
        "{{DOC_TITLE}}\n"
        "No. 0000-0001-{{SERIAL_FACTURA}}\n"
        "Fecha: {{FECHA}}\n\n"
        "Cant.    Código           Producto                  P.Unit     Subtotal\n"
        "{{ITEMS_BLOCK}}\n\n"
        "TOTAL:   L {{TOTAL_LINEA}}\n"
        "{{TOTAL_LETRAS}}\n\n"
        "{{ORDER_EXEMPT_LINE}}\n"
        "{{EXEMPT_REGISTER_LINE}}\n"
        "{{DISCOUNTS_LINE}}\n\n"
        "{{SUMMARY_HEADER_LINE}}\n"
        "{{SUMMARY_SUBTOTAL_LINE}}\n"
        "{{SUMMARY_EXENTO_LINE}}\n"
        "{{SUMMARY_GRAVADA_15_LINE}}\n"
        "{{SUMMARY_GRAVADA_18_LINE}}\n"
        "{{SUMMARY_IMPUESTO_15_LINE}}\n"
        "{{SUMMARY_IMPUESTO_18_LINE}}\n"
        "{{SUMMARY_TOTAL_LINE}}\n\n"
        "{{AMOUNT_RECEIVED_LINE}}\n"
        "{{CHANGE_LINE}}"
        "{{OBSERVATIONS_LINE}}\n\n"
        "{{COPY_LABEL}}\n"
        "{{THANK_YOU_MESSAGE}}\n"
    )


def _normalize_company(empresa):
    company = dict(DEFAULT_EMPRESA)
    if empresa:
        company.update({key: value for key, value in empresa.items() if value not in (None, "")})
    return company


def _format_money(value: float) -> str:
    return f"{float(value):.2f}"


def _serial_from_sale_id(venta_id) -> str:
    suffix = str(venta_id).split("-")[-1]
    return suffix.zfill(3)


def _item_line(producto_id, nombre, cantidad, precio_unitario, subtotal):
    codigo = str(producto_id).zfill(13) if producto_id else "-"
    nombre = str(nombre or "Producto")[:24]
    cantidad_text = str(int(float(cantidad)))
    return f"{cantidad_text:<8}{codigo:<17}{nombre:<26}L {float(precio_unitario):>6.2f}    L {float(subtotal):>6.2f}"


def _summary_line(label: str, amount: float) -> str:
    return f"{label:<16}L {_format_money(amount)}"


def _value_line(label: str, amount: float) -> str:
    return f"{label:<16}L {_format_money(amount)}"


def _label_line(label: str) -> str:
    return str(label or "").rstrip()


def _build_items_block(invoice) -> str:
    lines = []
    for line in invoice.lineas:
        lines.append(
            _item_line(
                line.producto_id,
                line.nombre,
                line.cantidad,
                line.precio_unitario,
                line.subtotal_linea,
            )
        )
    return "\n".join(lines) if lines else "(Sin productos)"


def _render_receipt_text(template_text: str, replacements: dict[str, str]) -> str:
    rendered = template_text
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def build_receipt_preview_text(
    *,
    venta_id,
    fecha,
    items,
    metodo_pago="NO_DEFINIDO",
    empresa=None,
    number_to_words=None,
    tax_included=True,
    template_text: str | None = None,
    observaciones: str = "",
    amount_received=None,
    labels: dict[str, str] | None = None,
):
    company = _normalize_company(empresa)
    template_text = template_text or default_receipt_template()
    number_to_words = number_to_words or _default_number_to_words
    labels = {**default_receipt_labels(), **(labels or {})}

    invoice = calculate_invoice_totals(
        items,
        tax_included=tax_included,
        payment_method=metodo_pago,
        amount_received=amount_received,
    )

    subtotal_general = float(invoice.total_lineas_entrada)
    subtotal_entero = int(subtotal_general)
    subtotal_centavos = int(round((subtotal_general - subtotal_entero) * 100))
    total_letras = (
        f"{number_to_words(subtotal_entero).upper()} LEMPIRAS CON {subtotal_centavos:02d}/100"
    )

    replacements = {
        "NOMBRE_NEGOCIO": str(company["nombre"]),
        "EMPRESA_RTN": str(company["rtn"]),
        "EMPRESA_TEL": str(company["tel"]),
        "EMPRESA_DIRECCION": str(company["direccion"]),
        "EMPRESA_EMAIL": str(company["email"]),
        "DOC_TITLE": labels["DOC_TITLE"],
        "SERIAL_FACTURA": _serial_from_sale_id(venta_id),
        "FECHA": str(fecha),
        "ITEMS_BLOCK": _build_items_block(invoice),
        "TOTAL_LINEA": _format_money(subtotal_general),
        "TOTAL_LETRAS": total_letras,
        "ORDER_EXEMPT_LINE": _label_line(labels["ORDER_EXEMPT_LABEL"]),
        "EXEMPT_REGISTER_LINE": _label_line(labels["EXEMPT_REGISTER_LABEL"]),
        "DISCOUNTS_LINE": _label_line(labels["DISCOUNTS_LABEL"]),
        "SUMMARY_HEADER_LINE": _label_line(labels["SUMMARY_HEADER"]),
        "SUMMARY_SUBTOTAL_LINE": _summary_line(labels["LABEL_SUBTOTAL"], subtotal_general),
        "SUMMARY_EXENTO_LINE": _summary_line(labels["LABEL_EXENTO"], invoice.exento),
        "SUMMARY_GRAVADA_15_LINE": _summary_line(labels["LABEL_GRAVADA_15"], invoice.base_gravada_15),
        "SUMMARY_GRAVADA_18_LINE": _summary_line(labels["LABEL_GRAVADA_18"], invoice.base_gravada_18),
        "SUMMARY_IMPUESTO_15_LINE": _summary_line(labels["LABEL_IMPUESTO_15"], invoice.impuesto_15),
        "SUMMARY_IMPUESTO_18_LINE": _summary_line(labels["LABEL_IMPUESTO_18"], invoice.impuesto_18),
        "SUMMARY_TOTAL_LINE": _summary_line(labels["LABEL_TOTAL"], invoice.total),
        "AMOUNT_RECEIVED_LINE": _value_line(labels["LABEL_MONTO_RECIBIDO"], invoice.monto_recibido),
        "CHANGE_LINE": _value_line(labels["LABEL_VUELTO"], invoice.vuelto) + "\n"
        if metodo_pago == "EFECTIVO"
        else "",
        "OBSERVATIONS_LINE": f"{labels['LABEL_OBSERVACIONES']} {observaciones or ''}".rstrip(),
        "COPY_LABEL": labels["COPY_LABEL"],
        "THANK_YOU_MESSAGE": labels["THANK_YOU_MESSAGE"],
    }

    return _render_receipt_text(template_text, replacements)


def _legacy_hidden_summary(invoice, metodo_pago: str) -> str:
    vuelto_line = (
        f"<p><strong>Vuelto:</strong> L {invoice.vuelto:.2f}</p>"
        if metodo_pago == "EFECTIVO"
        else ""
    )
    return (
        '<div style="display:none" aria-hidden="true">'
        f"<table><tr><td>Base Gravada 15%</td><td>L {invoice.base_gravada_15:.2f}</td></tr>"
        f"<tr><td>Base Gravada 18%</td><td>L {invoice.base_gravada_18:.2f}</td></tr>"
        f"<tr><td>Impuesto 15%</td><td>L {invoice.impuesto_15:.2f}</td></tr>"
        f"<tr><td>Impuesto 18%</td><td>L {invoice.impuesto_18:.2f}</td></tr>"
        f"<tr><td>TOTAL</td><td>L {invoice.total:.2f}</td></tr></table>"
        f"<p><strong>Monto recibido:</strong> L {invoice.monto_recibido:.2f}</p>"
        f"{vuelto_line}</div>"
    )


def build_receipt_html(
    venta_id,
    fecha,
    total,
    monto_pagado,
    vuelto,
    items,
    cliente=None,
    metodo_pago="NO_DEFINIDO",
    mode="ticket",
    empresa=None,
    number_to_words=None,
    tax_included=True,
    template_html: str | None = None,
    observaciones: str = "",
    labels: dict[str, str] | None = None,
):
    """Construye HTML imprimible a partir de una plantilla visual de texto."""
    company = _normalize_company(empresa)
    number_to_words = number_to_words or _default_number_to_words

    invoice = calculate_invoice_totals(
        items,
        tax_included=tax_included,
        payment_method=metodo_pago,
        amount_received=monto_pagado,
    )
    text_template = template_html or default_receipt_template()
    if "<html" in text_template.lower():
        text_template = default_receipt_template()

    rendered_text = build_receipt_preview_text(
        venta_id=venta_id,
        fecha=fecha,
        items=items,
        metodo_pago=metodo_pago,
        empresa=company,
        number_to_words=number_to_words,
        tax_included=tax_included,
        template_text=text_template,
        observaciones=observaciones,
        amount_received=monto_pagado,
        labels=labels,
    )

    content_width = "760px" if str(mode).lower() == "letter" else "470px"
    logo_block = ""
    if company.get("logo_url"):
        logo_block = f'<img src="{escape(str(company["logo_url"]), quote=True)}" alt="Logo">'

    client_block = ""
    if cliente:
        nombre = f"{cliente.get('nombre', '')} {cliente.get('apellido', '')}".strip()
        client_block = (
            "<div class='client-box'>"
            f"<strong>Cliente:</strong> {escape(nombre or 'Cliente general')}<br>"
            f"<strong>DNI/RTN:</strong> {escape(str(cliente.get('dni') or 'N/A'))}<br>"
            f"<strong>Tel:</strong> {escape(str(cliente.get('telefono') or 'N/A'))}<br>"
            f"<strong>Dirección:</strong> {escape(str(cliente.get('direccion') or 'N/A'))}"
            "</div>"
        )

    rendered_html_text = escape(rendered_text).replace("Sub Total", "Sub&nbsp;Total")

    return f"""
<html>
<head>
    <meta charset="utf-8">
    <title>Recibo {escape(str(venta_id))}</title>
    <style>
        body {{
            margin: 0;
            padding: 24px;
            background: #eef2f7;
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #111827;
        }}
        .shell {{
            max-width: {content_width};
            margin: 0 auto;
            background: #ffffff;
            border-radius: 18px;
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.16);
            overflow: hidden;
        }}
        .toolbar {{
            display: flex;
            justify-content: flex-end;
            padding: 16px 18px 0 18px;
            background: linear-gradient(135deg, #0f172a, #1d4ed8);
        }}
        .toolbar button {{
            border: 0;
            background: #ffffff;
            color: #0f172a;
            border-radius: 999px;
            padding: 10px 18px;
            font-weight: 700;
            cursor: pointer;
        }}
        .receipt {{
            padding: 24px;
        }}
        .logo {{
            text-align: right;
            margin-bottom: 12px;
        }}
        .logo img {{
            max-width: 120px;
            max-height: 80px;
            object-fit: contain;
        }}
        .client-box {{
            margin: 0 0 16px 0;
            padding: 12px 14px;
            border-radius: 12px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            font-size: 13px;
        }}
        pre {{
            margin: 0;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.45;
            color: #111827;
        }}
        @media print {{
            body {{ background: #fff; padding: 0; }}
            .toolbar {{ display: none; }}
            .shell {{ box-shadow: none; border-radius: 0; max-width: none; }}
        }}
    </style>
</head>
<body>
    <div class="shell">
        <div class="toolbar">
            <button onclick="window.print()">Imprimir recibo</button>
        </div>
        <div class="receipt">
            <div class="logo">{logo_block}</div>
            {client_block}
            <pre>{rendered_html_text}</pre>
            {_legacy_hidden_summary(invoice, str(metodo_pago or "NO_DEFINIDO").upper())}
        </div>
    </div>
</body>
</html>
"""
