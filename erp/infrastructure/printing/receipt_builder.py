"""Utilidades para construir facturas HTML reutilizables."""

# Contexto del archivo:
# Adaptador de impresion y renderizado HTML para recibos del ERP. Este modulo
# transforma datos ya calculados por dominio en una salida imprimible
# reutilizable por POS, reimpresion de ventas y pruebas automatizadas.

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
    tax_included=True,
):
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

    invoice = calculate_invoice_totals(
        items,
        tax_included=tax_included,
        payment_method=metodo_pago,
        amount_received=monto_pagado,
    )

    items_rows = []
    for line in invoice.lineas:
        cantidad = float(line.cantidad)
        precio_unitario = float(line.precio_unitario)
        descuento_pct = float(line.descuento_porcentaje)

        if descuento_pct > 0:
            subtotal = float(line.subtotal_linea)
            desc_text = f" (-{int(descuento_pct * 100)}%)"
        else:
            subtotal = float(line.subtotal_linea)
            desc_text = ""

        product_id = line.producto_id
        codigo = str(product_id).zfill(8 if mode == "ticket" else 13) if product_id else "-"
        nombre = str(line.nombre or "Producto")

        items_rows.append(
            "<tr>"
            f"<td>{int(cantidad) if cantidad.is_integer() else cantidad}</td>"
            f"<td>{escape(codigo)}</td>"
            f"<td>{escape(nombre)}{escape(desc_text)}</td>"
            f"<td>L {precio_unitario:.2f}</td>"
            f"<td>L {subtotal:.2f}</td>"
            "</tr>"
        )

    total = float(invoice.total)
    metodo_pago = str(metodo_pago or "NO_DEFINIDO").upper()
    total_entero = int(total)
    total_centavos = int(round((total - total_entero) * 100))
    monto_letras = f"{number_to_words(total_entero).upper()} LEMPIRAS CON {total_centavos:02d}/100"

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
        <tr><td>Exento</td><td>L {invoice.exento:.2f}</td></tr>
        <tr><td>Base Gravada 15%</td><td>L {invoice.base_gravada_15:.2f}</td></tr>
        <tr><td>Base Gravada 18%</td><td>L {invoice.base_gravada_18:.2f}</td></tr>
        <tr><td>Impuesto 15%</td><td>L {invoice.impuesto_15:.2f}</td></tr>
        <tr><td>Impuesto 18%</td><td>L {invoice.impuesto_18:.2f}</td></tr>
        <tr><td>TOTAL</td><td>L {invoice.total:.2f}</td></tr>
    </table>

    <div><strong>Total cobrado:</strong> L {invoice.total:.2f}</div>
    <div><strong>Monto recibido:</strong> L {invoice.monto_recibido:.2f}</div>
    {"<div><strong>Vuelto:</strong> L %.2f</div>" % invoice.vuelto if metodo_pago == "EFECTIVO" else ""}

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
