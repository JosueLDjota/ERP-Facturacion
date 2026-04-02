"""Utilidades centralizadas para construir y previsualizar recibos."""

# Contexto del archivo:
# Adaptador de impresion y renderizado para recibos del ERP. Este modulo
# concentra la plantilla activa, textos visibles y conversion a HTML/texto
# para que Configuracion, Ventas y Reimpresion compartan la misma fuente
# de verdad sin duplicar logica.

from __future__ import annotations

from html import escape, unescape
import re

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
    "SUMMARY_HEADER": "RESUMEN DE IMPUESTOS",
    "LABEL_MONTO_RECIBIDO": "Monto recibido",
    "LABEL_VUELTO": "Vuelto",
    "LABEL_OBSERVACIONES": "Observaciones",
    "COPY_LABEL": "Original - Cliente",
    "THANK_YOU_MESSAGE": "Gracias por su compra",
}


LABEL_CONFIG_KEYS = {
    "DOC_TITLE": "recibo_doc_title",
    "ORDER_EXEMPT_LABEL": "recibo_label_orden_exenta",
    "EXEMPT_REGISTER_LABEL": "recibo_label_registro_exento",
    "DISCOUNTS_LABEL": "recibo_label_descuentos",
    "SUMMARY_HEADER": "recibo_summary_title",
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


def load_receipt_labels(get_config) -> dict[str, str]:
    labels = default_receipt_labels()
    if not callable(get_config):
        return labels

    for label_key, config_key in LABEL_CONFIG_KEYS.items():
        stored_value = get_config(config_key, labels[label_key])
        text = str(stored_value or "").strip()
        if text:
            labels[label_key] = text
    return labels


def load_receipt_company(get_config) -> dict[str, str]:
    company = dict(DEFAULT_EMPRESA)
    if not callable(get_config):
        return company

    field_map = {
        "nombre": "empresa_nombre",
        "rtn": "empresa_rtn",
        "tel": "empresa_tel",
        "email": "empresa_email",
        "direccion": "empresa_direccion",
        "logo_url": "empresa_logo_url",
    }
    for field_name, config_key in field_map.items():
        stored_value = str(get_config(config_key, company[field_name]) or "").strip()
        if stored_value:
            company[field_name] = stored_value
    return company


def load_receipt_render_settings(get_config) -> dict[str, object]:
    template_html = None
    observations = ""
    if callable(get_config):
        template_value = str(get_config("recibo_template", "") or "").strip()
        if template_value:
            template_html = template_value
        observations = str(get_config("recibo_observaciones", "") or "").strip()

    return {
        "empresa": load_receipt_company(get_config),
        "labels": load_receipt_labels(get_config),
        "template_html": template_html,
        "observaciones": observations,
    }


def _line_discount_text(line) -> str:
    discount_pct = float(line.descuento_porcentaje)
    if discount_pct <= 0:
        return ""
    return f" (-{int(round(discount_pct * 100))}%)"


def _build_item_rows(invoice, mode: str) -> tuple[str, str]:
    html_rows = []
    text_rows = []

    for line in invoice.lineas:
        quantity = float(line.cantidad)
        unit_price = float(line.precio_unitario)
        subtotal = float(line.subtotal_linea)
        product_id = line.producto_id
        code_width = 8 if mode == "ticket" else 13
        code = str(product_id).zfill(code_width) if product_id else "-"
        product_name = str(line.nombre or "Producto")
        discount_text = _line_discount_text(line)
        quantity_text = str(int(quantity)) if quantity.is_integer() else f"{quantity:g}"
        name_with_discount = f"{product_name}{discount_text}"

        html_rows.append(
            "<tr>"
            f"<td>{escape(quantity_text)}</td>"
            f"<td>{escape(code)}</td>"
            f"<td>{escape(name_with_discount)}</td>"
            f"<td>L {unit_price:.2f}</td>"
            f"<td>L {subtotal:.2f}</td>"
            "</tr>"
        )
        text_rows.append(
            f"<div class=\"item\"><span>{escape(quantity_text)} x {escape(name_with_discount)}</span>"
            f"<span>L {subtotal:.2f}</span></div>"
        )

    return "".join(html_rows), "".join(text_rows)


def _build_receipt_context(
    *,
    venta_id,
    fecha,
    monto_pagado,
    items,
    cliente,
    metodo_pago,
    mode,
    empresa,
    number_to_words,
    tax_included,
    labels,
    observaciones,
):
    company = dict(DEFAULT_EMPRESA)
    if empresa:
        company.update(empresa)

    merged_labels = default_receipt_labels()
    if labels:
        merged_labels.update({key: str(value) for key, value in labels.items() if value is not None})

    invoice = calculate_invoice_totals(
        items,
        tax_included=tax_included,
        payment_method=metodo_pago,
        amount_received=monto_pagado,
    )

    mode = "letter" if str(mode).lower() == "letter" else "ticket"
    item_rows_html, item_rows_text = _build_item_rows(invoice, mode)

    total = float(invoice.total)
    total_integer = int(total)
    total_cents = int(round((total - total_integer) * 100))
    words_fn = number_to_words or _default_number_to_words
    amount_in_words = f"{words_fn(total_integer).upper()} LEMPIRAS CON {total_cents:02d}/100"

    client_name = ""
    client_html = ""
    if cliente:
        client_name = f"{cliente.get('nombre', '')} {cliente.get('apellido', '')}".strip()
        dni = cliente.get("dni") or "N/A"
        phone = cliente.get("telefono") or "N/A"
        address = cliente.get("direccion") or "N/A"
        client_html = f"""
        <div style="margin: 15px 0; padding: 8px; border: 1px solid #ddd; background: #f9f9f9;">
            <div style="font-weight: bold; margin-bottom: 5px;">DATOS DEL CLIENTE:</div>
            <div><strong>Nombre:</strong> {escape(client_name)}</div>
            <div><strong>DNI/RTN:</strong> {escape(str(dni))}</div>
            <div><strong>Tel:</strong> {escape(str(phone))}</div>
            <div><strong>Direccion:</strong> {escape(str(address))}</div>
        </div>
        """
    else:
        dni = phone = address = ""

    payment_method = str(metodo_pago or "NO_DEFINIDO").upper()
    observations = str(observaciones or "").strip()

    return {
        "company": company,
        "labels": merged_labels,
        "invoice": invoice,
        "subtotal_base": float(invoice.exento) + float(invoice.base_gravada_15) + float(invoice.base_gravada_18),
        "mode": mode,
        "venta_id": str(venta_id),
        "fecha": str(fecha),
        "metodo_pago": payment_method,
        "cliente_html": client_html,
        "cliente_nombre": client_name,
        "cliente_dni": str(dni),
        "cliente_telefono": str(phone),
        "cliente_direccion": str(address),
        "items_rows_html": item_rows_html,
        "items_rows_text": item_rows_text,
        "monto_letras": amount_in_words,
        "observaciones": observations,
    }


def build_receipt_view_model(
    *,
    venta_id,
    fecha,
    items,
    cliente=None,
    metodo_pago="NO_DEFINIDO",
    mode="ticket",
    empresa=None,
    number_to_words=None,
    tax_included=True,
    labels=None,
    observaciones="",
    amount_received=None,
):
    """Devuelve un modelo estructurado para previews visuales sin HTML crudo."""
    context = _build_receipt_context(
        venta_id=venta_id,
        fecha=fecha,
        monto_pagado=amount_received if amount_received is not None else 0,
        items=items,
        cliente=cliente,
        metodo_pago=metodo_pago,
        mode=mode,
        empresa=empresa,
        number_to_words=number_to_words,
        tax_included=tax_included,
        labels=labels,
        observaciones=observaciones,
    )
    invoice = context["invoice"]

    return {
        "company": context["company"],
        "labels": context["labels"],
        "venta_id": context["venta_id"],
        "fecha": context["fecha"],
        "metodo_pago": context["metodo_pago"],
        "cliente_nombre": context["cliente_nombre"],
        "monto_letras": context["monto_letras"],
        "observaciones": context["observaciones"],
        "subtotal_base": float(context["subtotal_base"]),
        "items": [
            {
                "cantidad": float(line.cantidad),
                "codigo": str(line.producto_id).zfill(8 if context["mode"] == "ticket" else 13) if line.producto_id else "-",
                "producto": f"{line.nombre or 'Producto'}{_line_discount_text(line)}",
                "precio_unitario": float(line.precio_unitario),
                "subtotal": float(line.subtotal_linea),
            }
            for line in invoice.lineas
        ],
        "summary_rows": [
            ("Exento", float(invoice.exento)),
            ("Gravado 15%", float(invoice.base_gravada_15)),
            ("Gravado 18%", float(invoice.base_gravada_18)),
            ("Impuesto 15%", float(invoice.impuesto_15)),
            ("Impuesto 18%", float(invoice.impuesto_18)),
            ("TOTAL", float(invoice.total)),
        ],
        "payment_rows": [
            (context["labels"]["LABEL_MONTO_RECIBIDO"], float(invoice.monto_recibido)),
            (context["labels"]["LABEL_VUELTO"], float(invoice.vuelto)),
        ],
    }


def _render_template(template_html: str, context: dict[str, object]) -> str:
    company = context["company"]
    labels = context["labels"]
    invoice = context["invoice"]
    items_rows_html = str(context["items_rows_html"])

    placeholders = {
        "NOMBRE_NEGOCIO": escape(company["nombre"]),
        "RTN": escape(company["rtn"]),
        "TELEFONO": escape(company["tel"]),
        "EMAIL": escape(company["email"]),
        "DIRECCION": escape(company["direccion"]),
        "LOGO_URL": escape(company.get("logo_url", "")),
        "ID_VENTA": escape(context["venta_id"]),
        "FECHA": escape(context["fecha"]),
        "METODO_PAGO": escape(context["metodo_pago"]),
        "DOC_TITLE": escape(labels["DOC_TITLE"]),
        "TITULO_DOCUMENTO": escape(labels["DOC_TITLE"]),
        "CLIENTE_NOMBRE": escape(context["cliente_nombre"]),
        "CLIENTE_DNI": escape(context["cliente_dni"]),
        "CLIENTE_TELEFONO": escape(context["cliente_telefono"]),
        "CLIENTE_DIRECCION": escape(context["cliente_direccion"]),
        "TOTAL": f"{float(invoice.total):.2f}",
        "SUBTOTAL": f"{float(context['subtotal_base']):.2f}",
        "MONTO_PAGADO": f"{float(invoice.monto_recibido):.2f}",
        "VUELTO": f"{float(invoice.vuelto):.2f}",
        "EXENTO": f"{float(invoice.exento):.2f}",
        "BASE_GRAVADA_15": f"{float(invoice.base_gravada_15):.2f}",
        "BASE_GRAVADA_18": f"{float(invoice.base_gravada_18):.2f}",
        "IMPUESTO_15": f"{float(invoice.impuesto_15):.2f}",
        "IMPUESTO_18": f"{float(invoice.impuesto_18):.2f}",
        "MONTO_LETRAS": escape(context["monto_letras"]),
        "OBSERVACIONES": escape(context["observaciones"]),
        "ORDER_EXEMPT_LABEL": escape(labels["ORDER_EXEMPT_LABEL"]),
        "EXEMPT_REGISTER_LABEL": escape(labels["EXEMPT_REGISTER_LABEL"]),
        "DISCOUNTS_LABEL": escape(labels["DISCOUNTS_LABEL"]),
        "SUMMARY_HEADER": escape(labels["SUMMARY_HEADER"]),
        "LABEL_MONTO_RECIBIDO": escape(labels["LABEL_MONTO_RECIBIDO"]),
        "LABEL_VUELTO": escape(labels["LABEL_VUELTO"]),
        "LABEL_OBSERVACIONES": escape(labels["LABEL_OBSERVACIONES"]),
        "COPY_LABEL": escape(labels["COPY_LABEL"]),
        "THANK_YOU_MESSAGE": escape(labels["THANK_YOU_MESSAGE"]),
        "ITEMS_PLACEHOLDER": items_rows_html,
        "ITEMS_ROWS": items_rows_html,
        "MONTO_RECIBIDO": f"{float(invoice.monto_recibido):.2f}",
        "SUB_TOTAL": f"{float(context['subtotal_base']):.2f}",
    }

    rendered = template_html
    rendered = rendered.replace("<!-- ITEMS_PLACEHOLDER -->", items_rows_html)
    for key, value in placeholders.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _default_receipt_html(context: dict[str, object]) -> str:
    company = context["company"]
    invoice = context["invoice"]
    labels = context["labels"]
    mode = context["mode"]
    title = labels["DOC_TITLE"]

    width = "350px" if mode == "ticket" else "700px"
    font_size = "12px" if mode == "ticket" else "15px"
    copy_label = labels["COPY_LABEL"]
    thanks = labels["THANK_YOU_MESSAGE"]
    observations = context["observaciones"]

    return f"""
<html>
<head>
    <meta charset="utf-8">
    <title>{escape(title)} {escape(context["venta_id"])}</title>
    <style>
        body {{
            width: {width};
            font-family: 'Courier New', Courier, monospace;
            font-size: {font_size};
            margin: 0 auto;
            background: #fff;
            color: #222;
        }}
        .header, .footer {{
            text-align: center;
            margin-bottom: 10px;
        }}
        .title {{
            font-size: 1.2em;
            font-weight: bold;
            color: #dc3545;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
        }}
        th, td {{
            border-bottom: 1px solid #ddd;
            padding: 4px 6px;
            text-align: left;
        }}
        th {{
            background: #f8f8f8;
        }}
        .totals td {{
            font-weight: bold;
        }}
        .observaciones {{
            margin-top: 10px;
            font-size: 0.95em;
            color: #555;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>{escape(company["nombre"])}</div>
        <div>R.T.N.: {escape(company["rtn"])}</div>
        <div>Tel: {escape(company["tel"])}</div>
        <div>{escape(company["direccion"])}</div>
        <div>Email: {escape(company["email"])}</div>
        <hr>
        <div class="title">{escape(title)}</div>
        <div>No. 0000-0001-{escape(context["venta_id"].split('-')[-1])}</div>
        <div>Fecha: {escape(context["fecha"])}</div>
        <div>Metodo de pago: {escape(context["metodo_pago"])}</div>
    </div>

    {context["cliente_html"]}

    <table>
        <thead>
            <tr>
                <th>Cant.</th>
                <th>Codigo</th>
                <th>Producto</th>
                <th>P. Unit</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            {context["items_rows_html"]}
        </tbody>
    </table>

    <div style="font-weight: bold; margin: 10px 0 6px 0;">{escape(labels["SUMMARY_HEADER"])}</div>
    <table class="totals">
        <tr><td>Exento</td><td>L {invoice.exento:.2f}</td></tr>
        <tr><td>Base Gravada 15%</td><td>L {invoice.base_gravada_15:.2f}</td></tr>
        <tr><td>Base Gravada 18%</td><td>L {invoice.base_gravada_18:.2f}</td></tr>
        <tr><td>Impuesto 15%</td><td>L {invoice.impuesto_15:.2f}</td></tr>
        <tr><td>Impuesto 18%</td><td>L {invoice.impuesto_18:.2f}</td></tr>
        <tr><td>TOTAL</td><td>L {invoice.total:.2f}</td></tr>
    </table>

    <div><strong>Total cobrado:</strong> L {invoice.total:.2f}</div>
    <div><strong>{escape(labels["LABEL_MONTO_RECIBIDO"])}:</strong> L {invoice.monto_recibido:.2f}</div>
    {"<div><strong>%s:</strong> L %.2f</div>" % (escape(labels["LABEL_VUELTO"]), invoice.vuelto) if context["metodo_pago"] == "EFECTIVO" else ""}

    <div class="observaciones">
        <p><strong>SON:</strong> {escape(context["monto_letras"])}</p>
        <p>{escape(labels["ORDER_EXEMPT_LABEL"])}</p>
        <p>{escape(labels["EXEMPT_REGISTER_LABEL"])}</p>
        <p>{escape(labels["DISCOUNTS_LABEL"])}</p>
        <p><strong>{escape(labels["LABEL_OBSERVACIONES"])}:</strong> {escape(observations or "-")}</p>
    </div>

    <div class="footer">
        <hr>
        <div>{escape(copy_label)}</div>
        <div>{escape(thanks)}</div>
    </div>
</body>
</html>
"""


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
    template_html=None,
    labels=None,
    observaciones="",
):
    context = _build_receipt_context(
        venta_id=venta_id,
        fecha=fecha,
        monto_pagado=monto_pagado,
        items=items,
        cliente=cliente,
        metodo_pago=metodo_pago,
        mode=mode,
        empresa=empresa,
        number_to_words=number_to_words,
        tax_included=tax_included,
        labels=labels,
        observaciones=observaciones,
    )

    template = str(template_html or "").strip()
    if template and "{{" in template:
        return _render_template(template, context)
    return _default_receipt_html(context)


def _html_to_plain_text(html: str) -> str:
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<head.*?>.*?</head>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|table|h1|h2|h3|li)>", "\n", text)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_receipt_preview_text(
    venta_id,
    fecha,
    items,
    cliente=None,
    metodo_pago="NO_DEFINIDO",
    mode="ticket",
    empresa=None,
    number_to_words=None,
    tax_included=True,
    template_text=None,
    labels=None,
    observaciones="",
    amount_received=None,
):
    html = build_receipt_html(
        venta_id=venta_id,
        fecha=fecha,
        total=0,
        monto_pagado=amount_received if amount_received is not None else 0,
        vuelto=0,
        items=items,
        cliente=cliente,
        metodo_pago=metodo_pago,
        mode=mode,
        empresa=empresa,
        number_to_words=number_to_words,
        tax_included=tax_included,
        template_html=template_text,
        labels=labels,
        observaciones=observaciones,
    )
    return _html_to_plain_text(html)


__all__ = [
    "DEFAULT_EMPRESA",
    "DEFAULT_RECEIPT_LABELS",
    "build_receipt_html",
    "build_receipt_preview_text",
    "build_receipt_view_model",
    "default_receipt_labels",
    "load_receipt_company",
    "load_receipt_labels",
    "load_receipt_render_settings",
]
