import unittest

from api.api_util import extract

MAIN_PAGE = (
    r'[0,"I-JLtexrxtJD7M",["https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS7b9WLrGujJDkaV9HDRO6h2-7VqRpH_gkXBDLbMRLSkw&s=10",452,678],'
    r'["https://oxfordlearning.com/wp-content/uploads/2025/03/types-of-test-takers-study-tips-scaled.jpeg",1000,1500],null,0]'
    r'[0,"XcAn7v4CsPc12M",["https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTL_FNE6cX5dZ7bAyNic7dqjAFsHTQxngjuf93poaMX_g&s=10",452,678],'
    r'["https://www.thoughtco.com/thmb/tVaPl-XUEXp32eYG9Ql50vYah7Q=/1500x0/filters:no_upscale()/GettyImages-79253051.jpg",1000,1500],null,0]'
)

SCROLL_RESPONSE = (
    r'[0,\"XNyniTXgXuqRXM\",[\"https://encrypted-tbn0.gstatic.com/images?q\\u003dtbn:ANd9GcRWQJvcTe_w6_HJ7y4nl6a6meUEjvgGT71EWl29zGHIAA\\u0026s\\u003d10\",480,638],'
    r'[\"https://media.post.rvohealth.io/wp-content/uploads/2023/02/2715013-At-Home-Drug-Tests-732x549-Feature.jpg\",549,732],null,0]'
)

LENS_RECORD = (
    r'["AwjjaumQNfrf2roP2oLwyQI59":[0,"5uY30m5LTnbwCM",["https://encrypted-tbn2.gstatic.com/images?q=tbn:ANd9GcRAwW3L_PyV_wWkyLTYl2xVgaKAS9JlVQMRqWaMFiC_FHZBlyJm",221,228],'
    r'["https://static.wikia.nocookie.net/valorant/images/e/e6/Bind_minimap.png/revision/latest?cb=20260203205623",2048,2048],null,0,'
    r'{"22":0,"2003":[null,"fVy21i1Ks6NUYM","https://valorant.fandom.com/wiki/Map:Bind","Map:Bind | Valorant Wiki | Fandom",null,null]}]'
)


class ExtractTest(unittest.TestCase):
    def test_main_page_format(self):
        results = extract(MAIN_PAGE)
        self.assertEqual(len(results), 2)
        self.assertEqual(
            results[0],
            {
                "url": "https://oxfordlearning.com/wp-content/uploads/2025/03/types-of-test-takers-study-tips-scaled.jpeg",
                "width": 1500,
                "height": 1000,
            },
        )

    def test_unicode_escapes_are_decoded(self):
        url = extract(MAIN_PAGE)[1]["url"]
        self.assertIn("tVaPl-XUEXp32eYG9Ql50vYah7Q=/1500x0", url)
        self.assertNotIn("\\", url)

    def test_scroll_response_format(self):
        results = extract(SCROLL_RESPONSE)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["width"], 732)
        self.assertEqual(results[0]["height"], 549)
        self.assertTrue(results[0]["url"].endswith("Drug-Tests-732x549-Feature.jpg"))

    def test_duplicates_collapse_and_thumbnails_are_excluded(self):
        results = extract(MAIN_PAGE + MAIN_PAGE + SCROLL_RESPONSE)
        self.assertEqual(len(results), 3)
        self.assertFalse(any("encrypted-tbn" in r["url"] for r in results))

    def test_lens_record_includes_source_page(self):
        result = extract(LENS_RECORD)[0]
        self.assertEqual(result["url"], "https://static.wikia.nocookie.net/valorant/images/e/e6/Bind_minimap.png/revision/latest?cb=20260203205623")
        self.assertEqual((result["width"], result["height"]), (2048, 2048))
        self.assertEqual(result["page_url"], "https://valorant.fandom.com/wiki/Map:Bind")
        self.assertEqual(result["title"], "Map:Bind | Valorant Wiki | Fandom")

    def test_no_results(self):
        self.assertEqual(extract("<html>Please enable JavaScript</html>"), [])


if __name__ == "__main__":
    unittest.main()
