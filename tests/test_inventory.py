import unittest

from netops_sentinel.validate_inventory import validate_inventory


class InventoryTests(unittest.TestCase):
    def test_inventory_passes_validation(self):
        report = validate_inventory()
        self.assertIn("Inventory validation: PASS", report)

    def test_expected_inventory_counts(self):
        report = validate_inventory()
        self.assertIn("Devices checked: 8", report)
        self.assertIn("Networks checked: 7", report)
        self.assertIn("Endpoints checked: 5", report)
        self.assertIn("Interfaces checked: 4", report)


if __name__ == "__main__":
    unittest.main()
