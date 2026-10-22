import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import update, build, run

class UpdateTests(unittest.TestCase):
    def test_empty_feed_preserves_history(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(update, "DATA", temp):
            path=Path(temp)/"wti.csv"
            original="date,open,high,low,close\n2026-09-24,1,2,1,2\n"
            path.write_text(original,encoding="utf-8")
            with self.assertRaises(ValueError): update.merge_ohlc("wti", [])
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_merge_keeps_source_dates_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(update, "DATA", temp):
            row=dict(date="2026-09-24",open=1,high=2,low=1,close=2)
            update.merge_ohlc("wti",[row])
            update.merge_ohlc("wti",[dict(row,close=1.5)])
            self.assertEqual(len(update.read_rows("wti")),1)
            self.assertEqual(update.read_rows("wti")[0]["date"],"2026-09-24")

    def test_outcome_and_stale_warning(self):
        for ok,fail,expected in [(0,2,1),(1,1,2),(2,0,0)]:
            with self.subTest(ok=ok,fail=fail), tempfile.TemporaryDirectory() as temp:
                item=dict(id="wti", name="WTI",cat="Energy",unit="USD",source="test",note="",type="line", dates=["2026-09-24"],values=[2],last=2,last_date="2026-09-24",change=None)
                with patch.object(update,"DATA",temp), patch.object(build,"DATA",temp), patch.object(build,"HERE",temp), patch.object(build,"CATEGORIES",["Energy"]), patch.object(build,"build_payload",return_value=[item]), patch.object(update,"main",return_value=dict(ok=ok,fail=fail,skipped=1)):
                    self.assertEqual(run.main(),expected)
                    status=json.loads((Path(temp)/"update_status.json").read_text(encoding="utf-8"))
                    self.assertTrue(status["items"][0]["stale"])
                    page=(Path(temp)/"index.html").read_text(encoding="utf-8")
                    self.assertIn("2026-09-24",page)
                    self.assertIn("최신 데이터 미확인",page)
                    self.assertNotIn("__HEALTH__",page)

if __name__=="__main__": unittest.main()
