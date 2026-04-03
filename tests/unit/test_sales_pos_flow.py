import unittest

from frames.sales import UnifiedPOSFrame


class DummyVar:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class SalesPOSFlowTests(unittest.TestCase):
    def test_validate_checkout_payment_rejects_incomplete_payment(self):
        frame = object.__new__(UnifiedPOSFrame)
        frame.total_var = DummyVar(150.0)
        frame.monto_pagado_var = DummyVar("100")
        warnings = []
        frame._parse_float = lambda value: float(value)
        frame._show_warning = lambda title, message: warnings.append((title, message))

        ok = UnifiedPOSFrame._validate_checkout_payment(frame)

        self.assertFalse(ok)
        self.assertEqual(warnings[0][0], "Pago incompleto")

    def test_go_to_confirmation_step_now_starts_processing_after_validation(self):
        frame = object.__new__(UnifiedPOSFrame)
        frame.pending_sale = None
        frame._validate_checkout_payment = lambda: True
        frame._build_sale_snapshot = lambda: {"venta_id": "POS-1"}
        started = []
        frame._start_processing_sale = lambda: started.append(True)

        UnifiedPOSFrame._go_to_confirmation_step(frame)

        self.assertEqual(frame.pending_sale, {"venta_id": "POS-1"})
        self.assertEqual(started, [True])

    def test_render_confirmation_step_redirects_to_payment_step(self):
        frame = object.__new__(UnifiedPOSFrame)
        calls = []
        frame._render_workflow_payment_step = lambda: calls.append("payment")

        UnifiedPOSFrame._render_confirmation_step(frame)

        self.assertEqual(calls, ["payment"])

    def test_render_success_step_returns_directly_to_cart(self):
        frame = object.__new__(UnifiedPOSFrame)
        frame.workflow_progress = type("Progress", (), {"configure": lambda self, **kwargs: None})()

        cleared = []
        frame._clear_workflow_content = lambda: cleared.append("content")
        frame._clear_workflow_footer = lambda: cleared.append("footer")

        finished = []
        frame._finish_checkout_success = lambda: finished.append("done")

        result = type("Result", (), {"sale_id": "POS-10", "total": 123.45})()

        UnifiedPOSFrame._render_success_step(frame, result)

        self.assertEqual(cleared, ["content", "footer"])
        self.assertEqual(frame.last_sale_result, result)
        self.assertEqual(finished, ["done"])

    def test_finish_checkout_success_returns_to_cart_and_clears_context(self):
        frame = object.__new__(UnifiedPOSFrame)
        frame.pending_sale = {"venta_id": "POS-11"}
        frame.last_sale_result = {"sale_id": "POS-11"}

        shown = []
        frame._show_sales_stage = lambda: shown.append("cart")

        UnifiedPOSFrame._finish_checkout_success(frame)

        self.assertIsNone(frame.pending_sale)
        self.assertIsNone(frame.last_sale_result)
        self.assertEqual(shown, ["cart"])


if __name__ == "__main__":
    unittest.main()
