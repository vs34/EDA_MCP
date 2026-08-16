import unittest
from virtuoso_client import VirtuosoClient

class TestVirtuosoSanitization(unittest.TestCase):
    def setUp(self):
        # Instantiate VirtuosoClient with a dummy session for testing _clean_skill_command
        self.client = VirtuosoClient(session=None)

    def test_multiline_string_with_newlines(self):
        cmd = 'let((cv)\n  printf("Checking cellview:\nLine2\n")\n)'
        cleaned = self.client._clean_skill_command(cmd)
        self.assertEqual(
            cleaned,
            'let((cv) printf("Checking cellview:\\nLine2\\n") )'
        )

    def test_semicolons_inside_strings(self):
        cmd = 'printf("URL: http://site.com;;test")'
        cleaned = self.client._clean_skill_command(cmd)
        self.assertEqual(
            cleaned,
            'printf("URL: http://site.com;;test")'
        )

    def test_comments_outside_strings(self):
        cmd = 'printf("Hello") ;; this is a comment\nprintf("World")'
        cleaned = self.client._clean_skill_command(cmd)
        self.assertEqual(
            cleaned,
            'printf("Hello") printf("World")'
        )

    def test_escaped_quotes_inside_strings(self):
        cmd = 'printf("He said \\"Hello\\" ;; inside quote") ;; comment'
        cleaned = self.client._clean_skill_command(cmd)
        self.assertEqual(
            cleaned,
            'printf("He said \\"Hello\\" ;; inside quote")'
        )

    def test_empty_and_whitespace_command(self):
        self.assertEqual(self.client._clean_skill_command(""), "")
        self.assertEqual(self.client._clean_skill_command("   \n\n ;; comment \n"), "")

if __name__ == "__main__":
    unittest.main()
