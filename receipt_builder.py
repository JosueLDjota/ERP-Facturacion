"""Utilidades para construir facturas HTML reutilizables."""

from html import escape


DEFAULT_EMPRESA = {
    "rtn": "12011972000081",
    "nombre": "PODEGA Y COMERCIAL RIVERA",
    "tel": "2774-1192 / 9967-7300",
    "direccion": (
        "Bo. La Mercedes, Colonia la Ermita, 1ra Calle, 14-62, "
        "frente a Farmacia Santa, La Paz, Honduras"
    ),
    "email": "freddyrivera2015@gmail.com",
}


def _default_number_to_words(n):
    return str(n)


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
):
    """Construye HTML de factura en formato ticket o carta."""
    company = dict(DEFAULT_EMPRESA)
    if empresa:
        company.update(empresa)

    number_to_words = number_to_words or _default_number_to_words
    mode = "letter" if str(mode).lower() == "letter" else "ticket"

    if mode == "ticket":
        width = "350px"
        font_size = "12px"
    else:
        width = "700px"
        font_size = "15px"

    total = float(total or 0)
    monto_pagado = float(monto_pagado or 0)
    vuelto = float(vuelto or 0)

    subtotal_gravado = 0.0
    items_rows = []
    for item in items:
        cantidad = float(item.get("cantidad", 0))
        precio_unitario = float(item.get("precio_unitario", 0))
        descuento_pct = float(item.get("descuento_porcentaje", 0))
        descuento_monto = float(item.get("descuento_monto", 0))

        if descuento_pct > 0:
            subtotal = (precio_unitario * cantidad) * (1 - descuento_pct)
            desc_text = f" (-{int(descuento_pct * 100)}%)"
        else:
            subtotal = float(item.get("subtotal", (precio_unitario * cantidad) - descuento_monto))
            desc_text = ""

        subtotal_gravado += subtotal
        product_id = item.get("producto_id")
        codigo = str(product_id).zfill(8 if mode == "ticket" else 13) if product_id else "-"
        nombre = str(item.get("nombre", "Producto"))[: (10 if mode == "ticket" else 28)]

        items_rows.append(
            "<tr>"
            f"<td>{int(cantidad) if cantidad.is_integer() else cantidad}</td>"
            f"<td>{escape(codigo)}</td>"
            f"<td>{escape(nombre)}{escape(desc_text)}</td>"
            f"<td>L {precio_unitario:.2f}</td>"
            f"<td>L {subtotal:.2f}</td>"
            "</tr>"
        )

    impuesto_15 = subtotal_gravado * 0.15
    total_con_impuesto = subtotal_gravado + impuesto_15
    total_entero = int(total)
    total_centavos = int(round((total - total_entero) * 100))
    monto_letras = (
        f"{number_to_words(total_entero).upper()} LEMPIRAS CON {total_centavos:02d}/100"
    )

    cliente_html = ""
    if cliente:
        nombre = f"{cliente.get('nombre', '')} {cliente.get('apellido', '')}".strip()
        dni = cliente.get("dni") or "N/A"
        telefono = cliente.get("telefono") or "N/A"
        direccion = cliente.get("direccion") or "N/A"
        cliente_html = f"""
        <div style="margin: 15px 0; padding: 8px; border: 1px solid #ddd; background: #f9f9f9;">
            <div style="font-weight: bold; margin-bottom: 5px;">DATOS DEL CLIENTE:</div>
            <div><strong>Nombre:</strong> {escape(nombre)}</div>
            <div><strong>DNI/RTN:</strong> {escape(str(dni))}</div>
            <div><strong>Tel:</strong> {escape(str(telefono))}</div>
            <div><strong>Dirección:</strong> {escape(str(direccion))}</div>
        </div>
        """

    return f"""
<html>
<head>
    <meta charset="utf-8">
    <title>Recibo de Venta {escape(str(venta_id))}</title>
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
        <div class="title">FACTURA</div>
        <div>No. 0000-0001-{escape(str(venta_id).split('-')[-1])}</div>
        <div>Fecha: {escape(str(fecha))}</div>
        <div>Metodo de pago: {escape(str(metodo_pago or 'NO_DEFINIDO'))}</div>
    </div>

    {cliente_html}

    <table>
        <thead>
            <tr>
                <th>Cant.</th>
                <th>Código</th>
                <th>Producto</th>
                <th>P. Unit</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            {''.join(items_rows)}
        </tbody>
    </table>

    <table class="totals">
        <tr><td>Sub Total</td><td>L {subtotal_gravado:.2f}</td></tr>
        <tr><td>Exento</td><td>L 0.00</td></tr>
        <tr><td>Gravado 15%</td><td>L {subtotal_gravado:.2f}</td></tr>
        <tr><td>Gravado 18%</td><td>L 0.00</td></tr>
        <tr><td>Impuesto 15%</td><td>L {impuesto_15:.2f}</td></tr>
        <tr><td>Impuesto 18%</td><td>L 0.00</td></tr>
        <tr><td>TOTAL</td><td>L {total_con_impuesto:.2f}</td></tr>
    </table>

    <div><strong>Total cobrado:</strong> L {total:.2f}</div>
    <div><strong>Monto recibido:</strong> L {monto_pagado:.2f}</div>
    <div><strong>Vuelto:</strong> L {vuelto:.2f}</div>

    <div class="observaciones">
        <p><strong>SON:</strong> {escape(monto_letras)}</p>
        <p>Orden de Compra Exenta:</p>
        <p>Constancia Registro Exento:</p>
        <p>Desc. y Rebajas Otorgados:</p>
    </div>

    <div class="footer">
        <hr>
        <div>Original - Cliente</div>
        <div>Gracias por su compra</div>
    </div>
</body>
</html>
"""
