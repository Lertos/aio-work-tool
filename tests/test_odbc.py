import sys
import types
import unittest

from src.services.odbc import best_driver


class BestDriverTests(unittest.TestCase):
    def pick(self, installed):
        fake = types.ModuleType("pyodbc")
        fake.drivers = lambda: installed
        real = sys.modules.get("pyodbc")
        sys.modules["pyodbc"] = fake
        best_driver.cache_clear()
        try:
            return best_driver()
        finally:
            if real is None:
                sys.modules.pop("pyodbc")
            else:
                sys.modules["pyodbc"] = real
            best_driver.cache_clear()

    def test_prefers_newest_installed(self):
        self.assertEqual(self.pick(["SQL Server", "ODBC Driver 17 for SQL Server",
                                    "ODBC Driver 18 for SQL Server"]),
                         "{ODBC Driver 18 for SQL Server}")
        self.assertEqual(self.pick(["SQL Server", "ODBC Driver 17 for SQL Server"]),
                         "{ODBC Driver 17 for SQL Server}")

    def test_falls_back_to_built_in_driver(self):
        self.assertEqual(self.pick(["SQL Server", "Microsoft Access Driver (*.mdb)"]), "{SQL Server}")

    def test_nothing_known_installed_asks_for_18(self):
        self.assertEqual(self.pick([]), "{ODBC Driver 18 for SQL Server}")


if __name__ == "__main__":
    unittest.main()
