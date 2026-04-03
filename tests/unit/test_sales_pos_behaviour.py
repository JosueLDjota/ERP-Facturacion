import unittest

from frames.sales import ProductSearchModal, UnifiedPOSFrame


class DummyVar:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class DummyCombo:
    def __init__(self, index=0, value="Sin descuento"):
        self.index = index
        self.value = value

    def current(self):
        return self.index

    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        self.index = 0 if value == "Sin descuento" else self.index


class FakeWindow:
    def __init__(self):
        self.bound = {}
        self.unbound = []
        self.after_idle_callbacks = []

    def bind(self, key, callback):
        self.bound[key] = callback

    def unbind(self, key):
        self.unbound.append(key)

    def after_idle(self, callback):
        self.after_idle_callbacks.append(callback)

    def winfo_exists(self):
        return True

    def destroy(self):
        self.bound["destroyed"] = True


class FakeWidget:
    def __init__(self, widget_class="TButton"):
        self.widget_class = widget_class
        self.focused = False
        self.selection_calls = []
        self.config = {}

    def focus_set(self):
        self.focused = True

    def selection_range(self, start, end):
        self.selection_calls.append((start, end))

    def winfo_class(self):
        return self.widget_class

    def configure(self, **kwargs):
        self.config.update(kwargs)


class FakeEvent:
    def __init__(self, widget):
        self.widget = widget


class SalesPOSBehaviourTests(unittest.TestCase):
    def test_bind_shortcuts_uses_toplevel_owner(self):
        frame = object.__new__(UnifiedPOSFrame)
        owner = FakeWindow()
        frame.winfo_toplevel = lambda: owner
        frame.checkout_mode = DummyVar("cart")
        events = []
        frame.open_product_search = lambda: events.append("f1")
        frame.open_payment_modal = lambda: events.append("f2")
        frame.clear_cart = lambda: events.append("f3")
        frame._shortcut_owner = None

        UnifiedPOSFrame._bind_shortcuts(frame)

        self.assertIn("<F1>", owner.bound)
        self.assertIn("<F2>", owner.bound)
        self.assertIn("<F3>", owner.bound)
        self.assertIn("<F4>", owner.bound)
        self.assertIn("<Escape>", owner.bound)
        self.assertIn("<Return>", owner.bound)
        self.assertEqual(owner.bound["<F1>"](), "break")
        self.assertEqual(owner.bound["<F2>"](), "break")
        self.assertEqual(owner.bound["<F3>"](), "break")
        self.assertEqual(events, ["f1", "f2", "f3"])

    def test_add_product_from_modal_applies_wholesale_discount_automatically(self):
        frame = object.__new__(UnifiedPOSFrame)
        frame.product_index = {
            1: {"nombre": "Monitor", "precio": 100.0, "stock": 20}
        }
        frame.cart = {}
        frame.sale_mode_var = DummyVar("ESPECIAL")
        frame.selected_client_is_wholesale = False
        frame.discount_by_type = {"MAYORISTA": [{"porcentaje": 0.2}]}
        frame.status_var = DummyVar("")
        frame.preview_window = None
        frame.update_cart_display = lambda: None
        frame.refresh_preview = lambda: None
        frame._show_error = lambda *args, **kwargs: self.fail("No esperaba error de stock")

        UnifiedPOSFrame.add_product_from_modal(frame, 1, 1, 0.0, "Sin descuento")

        self.assertEqual(frame.cart[1]["cantidad"], 1)
        self.assertAlmostEqual(frame.cart[1]["descuento_porcentaje"], 0.2)
        self.assertEqual(frame.cart[1]["auto_label"], "Mayorista")

    def test_add_product_from_modal_applies_docena_discount_in_normal_mode(self):
        frame = object.__new__(UnifiedPOSFrame)
        frame.product_index = {
            1: {"nombre": "Monitor", "precio": 100.0, "stock": 20}
        }
        frame.cart = {}
        frame.sale_mode_var = DummyVar("NORMAL")
        frame.selected_client_is_wholesale = False
        frame.discount_by_type = {"DOCENA": [{"porcentaje": 0.12}]}
        frame.status_var = DummyVar("")
        frame.preview_window = None
        frame.update_cart_display = lambda: None
        frame.refresh_preview = lambda: None
        frame._show_error = lambda *args, **kwargs: self.fail("No esperaba error de stock")

        UnifiedPOSFrame.add_product_from_modal(frame, 1, 12, 0.0, "Sin descuento")

        self.assertEqual(frame.cart[1]["cantidad"], 12)
        self.assertAlmostEqual(frame.cart[1]["descuento_porcentaje"], 0.12)
        self.assertEqual(frame.cart[1]["auto_label"], "Docena")

    def test_modal_submit_guard_avoids_duplicate_add_on_consecutive_submit_events(self):
        modal = object.__new__(ProductSearchModal)
        modal.selected_product = {"id": 1, "stock": 5}
        modal.product_lookup = {}
        modal.window = FakeWindow()
        modal.qty_var = DummyVar(1)
        modal.discount_combo = DummyCombo()
        modal._submit_locked = False

        calls = []
        modal.callback = lambda product_id, quantity, discount_pct, discount_name: calls.append(
            (product_id, quantity, discount_pct, discount_name)
        )
        modal._show_notification = lambda _message: None
        modal._get_selected_product = lambda: modal.selected_product

        first = ProductSearchModal._add_and_continue(modal)
        second = ProductSearchModal._add_and_continue(modal)

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(len(calls), 1)

        for callback in modal.window.after_idle_callbacks:
            callback()

        third = ProductSearchModal._add_and_continue(modal)
        self.assertTrue(third)
        self.assertEqual(len(calls), 2)

    def test_checkout_shortcuts_focus_expected_controls_in_payment_step(self):
        frame = object.__new__(UnifiedPOSFrame)
        frame.checkout_mode = DummyVar("payment")
        frame.checkout_payment_combo = FakeWidget("TCombobox")
        frame.checkout_amount_entry = FakeWidget("TEntry")
        frame.checkout_secondary_button = FakeWidget("TButton")
        frame.checkout_details_visible = False

        toggles = []
        frame._toggle_checkout_details = lambda: toggles.append(True) or setattr(frame, "checkout_details_visible", True) or True

        self.assertEqual(UnifiedPOSFrame._handle_f2_shortcut(frame), "break")
        self.assertTrue(frame.checkout_payment_combo.focused)

        self.assertEqual(UnifiedPOSFrame._handle_f3_shortcut(frame), "break")
        self.assertTrue(frame.checkout_amount_entry.focused)

        self.assertEqual(UnifiedPOSFrame._handle_f4_shortcut(frame), "break")
        self.assertEqual(toggles, [True])
        self.assertTrue(frame.checkout_secondary_button.focused)

    def test_enter_and_escape_follow_contextual_primary_action(self):
        frame = object.__new__(UnifiedPOSFrame)
        frame.checkout_mode = DummyVar("payment")
        frame.cart = {1: {"cantidad": 1}}

        started = []
        returned = []
        finished = []
        searched = []
        charged = []

        frame._start_processing_sale = lambda: started.append(True)
        frame._show_sales_stage = lambda: returned.append(True)
        frame._finish_checkout_success = lambda: finished.append(True)
        frame.open_product_search = lambda: searched.append(True)
        frame.open_payment_modal = lambda: charged.append(True)

        self.assertEqual(UnifiedPOSFrame._handle_enter_shortcut(frame), "break")
        self.assertEqual(started, [True])
        self.assertEqual(UnifiedPOSFrame._handle_escape_shortcut(frame), "break")
        self.assertEqual(returned, [True])

        frame.checkout_mode.set("success")
        self.assertEqual(UnifiedPOSFrame._handle_enter_shortcut(frame), "break")
        self.assertEqual(UnifiedPOSFrame._handle_escape_shortcut(frame), "break")
        self.assertEqual(finished, [True, True])

        frame.checkout_mode.set("cart")
        editable_event = FakeEvent(FakeWidget("TEntry"))
        self.assertIsNone(UnifiedPOSFrame._handle_enter_shortcut(frame, editable_event))
        self.assertEqual(charged, [])
        self.assertEqual(searched, [])

        primary_event = FakeEvent(FakeWidget("TButton"))
        self.assertEqual(UnifiedPOSFrame._handle_enter_shortcut(frame, primary_event), "break")
        self.assertEqual(charged, [True])

        frame.cart = {}
        self.assertEqual(UnifiedPOSFrame._handle_enter_shortcut(frame, primary_event), "break")
        self.assertEqual(searched, [True])


if __name__ == "__main__":
    unittest.main()
