from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping


TWOPLACES = Decimal("0.01")
ZERO = Decimal("0.00")
TAX_RATE_15 = Decimal("0.15")
TAX_RATE_18 = Decimal("0.18")
DEFAULT_TAX_RATE = TAX_RATE_15


def _to_decimal(value) -> Decimal:
    if value in (None, ""):
        return ZERO
    return Decimal(str(value))


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass(slots=True)
class InvoiceLineTotals:
    producto_id: int | None
    nombre: str
    cantidad: int
    precio_unitario: float
    descuento_porcentaje: float
    subtotal_linea: float
    subtotal_base: float
    exento: float
    base_gravada_15: float
    base_gravada_18: float
    impuesto_15: float
    impuesto_18: float
    total_linea: float

    @property
    def gravado_15(self) -> float:
        return self.base_gravada_15

    @property
    def gravado_18(self) -> float:
        return self.base_gravada_18


@dataclass(slots=True)
class InvoiceTotals:
    total_lineas_entrada: float
    exento: float
    base_gravada_15: float
    base_gravada_18: float
    impuesto_15: float
    impuesto_18: float
    total: float
    monto_recibido: float
    vuelto: float
    lineas: list[InvoiceLineTotals]
    validation_errors: list[str]

    @property
    def gravado_15(self) -> float:
        return self.base_gravada_15

    @property
    def gravado_18(self) -> float:
        return self.base_gravada_18


def _resolve_tax_rate(item: Mapping) -> Decimal:
    if item.get("tax_exempt") or item.get("is_exempt"):
        return ZERO

    raw_rate = item.get("tax_rate", DEFAULT_TAX_RATE)
    rate = _to_decimal(raw_rate)
    if rate > Decimal("1"):
        rate = rate / Decimal("100")

    if rate < ZERO:
        return ZERO
    return rate


def calculate_invoice_totals(
    items: Iterable[Mapping],
    tax_included: bool,
    payment_method: str,
    amount_received=None,
) -> InvoiceTotals:
    total_lineas_entrada = ZERO
    base_imponible_total = ZERO
    exento = ZERO
    base_gravada_15 = ZERO
    base_gravada_18 = ZERO
    impuesto_15 = ZERO
    impuesto_18 = ZERO
    expected_total = ZERO
    lineas: list[InvoiceLineTotals] = []

    for item in items:
        cantidad = int(item.get("cantidad", 0) or 0)
        precio_unitario = _to_decimal(item.get("precio_unitario", 0))
        descuento_pct = _to_decimal(item.get("descuento_porcentaje", 0))
        if descuento_pct > Decimal("1"):
            descuento_pct = descuento_pct / Decimal("100")

        total_linea_entrada = precio_unitario * cantidad * (Decimal("1") - descuento_pct)
        tax_rate = _resolve_tax_rate(item)

        line_exento = ZERO
        line_base_gravada_15 = ZERO
        line_base_gravada_18 = ZERO
        line_impuesto_15 = ZERO
        line_impuesto_18 = ZERO
        subtotal_base_linea = ZERO
        total_linea = total_linea_entrada

        if tax_rate == ZERO:
            line_exento = total_linea_entrada
            subtotal_base_linea = total_linea_entrada
        elif tax_rate == TAX_RATE_15:
            if tax_included:
                # Cuando el precio ya incluye ISV, se separa la base imponible
                # dividiendo el total entre 1.15 y la diferencia queda como impuesto.
                line_base_gravada_15 = total_linea_entrada / (Decimal("1") + TAX_RATE_15)
                line_impuesto_15 = total_linea_entrada - line_base_gravada_15
                subtotal_base_linea = line_base_gravada_15
            else:
                line_base_gravada_15 = total_linea_entrada
                line_impuesto_15 = line_base_gravada_15 * TAX_RATE_15
                subtotal_base_linea = line_base_gravada_15
                total_linea = line_base_gravada_15 + line_impuesto_15
        elif tax_rate == TAX_RATE_18:
            if tax_included:
                # Cuando el precio ya incluye ISV, se separa la base imponible
                # dividiendo el total entre 1.18 y la diferencia queda como impuesto.
                line_base_gravada_18 = total_linea_entrada / (Decimal("1") + TAX_RATE_18)
                line_impuesto_18 = total_linea_entrada - line_base_gravada_18
                subtotal_base_linea = line_base_gravada_18
            else:
                line_base_gravada_18 = total_linea_entrada
                line_impuesto_18 = line_base_gravada_18 * TAX_RATE_18
                subtotal_base_linea = line_base_gravada_18
                total_linea = line_base_gravada_18 + line_impuesto_18
        else:
            if tax_included:
                base = total_linea_entrada / (Decimal("1") + tax_rate)
                impuesto = total_linea_entrada - base
                line_base_gravada_15 = base
                line_impuesto_15 = impuesto
                subtotal_base_linea = base
            else:
                line_base_gravada_15 = total_linea_entrada
                line_impuesto_15 = line_base_gravada_15 * tax_rate
                subtotal_base_linea = line_base_gravada_15
                total_linea = line_base_gravada_15 + line_impuesto_15

        total_lineas_entrada += total_linea_entrada
        base_imponible_total += subtotal_base_linea + line_exento
        exento += line_exento
        base_gravada_15 += line_base_gravada_15
        base_gravada_18 += line_base_gravada_18
        impuesto_15 += line_impuesto_15
        impuesto_18 += line_impuesto_18
        expected_total += total_linea

        lineas.append(
            InvoiceLineTotals(
                producto_id=item.get("producto_id"),
                nombre=str(item.get("nombre", "Producto")),
                cantidad=cantidad,
                precio_unitario=float(_round_money(precio_unitario)),
                descuento_porcentaje=float(descuento_pct),
                subtotal_linea=float(_round_money(total_linea_entrada)),
                subtotal_base=float(_round_money(subtotal_base_linea + line_exento)),
                exento=float(line_exento),
                base_gravada_15=float(_round_money(line_base_gravada_15)),
                base_gravada_18=float(_round_money(line_base_gravada_18)),
                impuesto_15=float(_round_money(line_impuesto_15)),
                impuesto_18=float(_round_money(line_impuesto_18)),
                total_linea=float(_round_money(total_linea)),
            )
        )

    total_lineas_entrada = _round_money(total_lineas_entrada)
    base_imponible_total = _round_money(base_imponible_total)
    exento = _round_money(exento)
    base_gravada_15 = _round_money(base_gravada_15)
    base_gravada_18 = _round_money(base_gravada_18)
    impuesto_15 = _round_money(impuesto_15)
    impuesto_18 = _round_money(impuesto_18)
    total = _round_money(base_imponible_total + impuesto_15 + impuesto_18)
    expected_total = _round_money(expected_total)

    payment_method = str(payment_method or "NO_DEFINIDO").upper()
    amount_received_decimal = None if amount_received in (None, "") else _round_money(_to_decimal(amount_received))

    if payment_method == "EFECTIVO":
        amount_received_decimal = amount_received_decimal if amount_received_decimal is not None else ZERO
        vuelto = _round_money(amount_received_decimal - total) if amount_received_decimal >= total else ZERO
    elif payment_method == "TRANSFERENCIA":
        amount_received_decimal = total if amount_received_decimal in (None, ZERO) else total
        vuelto = ZERO
    else:
        amount_received_decimal = total if amount_received_decimal in (None, ZERO) else amount_received_decimal
        vuelto = ZERO

    validation_errors: list[str] = []
    base_total = _round_money(exento + base_gravada_15 + base_gravada_18)
    if base_total != base_imponible_total:
        validation_errors.append("La base imponible total no coincide con la suma de bases gravadas y exentas.")

    line_entry_total = _round_money(sum((_to_decimal(line.subtotal_linea) for line in lineas), ZERO))
    if tax_included and line_entry_total != total:
        validation_errors.append("La suma de lineas con ISV incluido no coincide con el total.")

    if not tax_included and line_entry_total != base_imponible_total:
        validation_errors.append("La suma de lineas sin ISV no coincide con la base imponible total.")

    component_total = _round_money(base_imponible_total + impuesto_15 + impuesto_18)
    if component_total != total:
        validation_errors.append("El total no coincide con la suma de bases e impuestos.")

    if expected_total != total:
        validation_errors.append("El total esperado por lineas no coincide con el total fiscal.")

    if base_gravada_15 > ZERO and impuesto_15 == ZERO:
        validation_errors.append("Hay base gravada al 15% sin impuesto calculado.")

    if base_gravada_18 > ZERO and impuesto_18 == ZERO:
        validation_errors.append("Hay base gravada al 18% sin impuesto calculado.")

    if payment_method == "EFECTIVO" and amount_received_decimal < total:
        validation_errors.append("El monto recibido en efectivo no puede ser menor al total.")

    if payment_method == "TRANSFERENCIA" and vuelto != ZERO:
        validation_errors.append("Las transferencias no deben generar vuelto.")

    return InvoiceTotals(
        total_lineas_entrada=float(total_lineas_entrada),
        exento=float(exento),
        base_gravada_15=float(base_gravada_15),
        base_gravada_18=float(base_gravada_18),
        impuesto_15=float(impuesto_15),
        impuesto_18=float(impuesto_18),
        total=float(total),
        monto_recibido=float(amount_received_decimal),
        vuelto=float(vuelto),
        lineas=lineas,
        validation_errors=validation_errors,
    )


def calculateInvoiceTotals(payload: Mapping) -> dict:
    totals = calculate_invoice_totals(
        items=payload.get("items", []),
        tax_included=bool(payload.get("taxIncluded", False)),
        payment_method=str(payload.get("paymentMethod", "NO_DEFINIDO")),
        amount_received=payload.get("amountReceived"),
    )
    return {
        "baseGravada15": totals.base_gravada_15,
        "baseGravada18": totals.base_gravada_18,
        "impuesto15": totals.impuesto_15,
        "impuesto18": totals.impuesto_18,
        "exento": totals.exento,
        "total": totals.total,
        "montoRecibido": totals.monto_recibido,
        "vuelto": totals.vuelto,
        "validationErrors": list(totals.validation_errors),
    }
