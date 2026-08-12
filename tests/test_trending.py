import unittest

from github_hot.trending import parse_trending_html


TRENDING_FIXTURE = """
<html><body>
<div class="Box">
  <article class="Box-row">
    <h2 class="h3 lh-condensed"><a href="/openai/whisper"><span class="text-normal">openai /</span> whisper</a></h2>
    <p class="col-9 color-fg-muted my-1 pr-4">Robust speech recognition via large-scale weak supervision</p>
    <div class="f6 color-fg-muted mt-2">
      <a class="Link--muted d-inline-block mr-3" href="/openai/whisper/stargazers">68,000</a>
      <a class="Link--muted d-inline-block mr-3" href="/openai/whisper/forks">8,000</a>
      <span class="d-inline-block mr-3"><span>Python</span></span>
      <span class="d-inline-block float-sm-right"><span class="Link--muted d-inline-block mr-3">1,234 stars this week</span></span>
    </div>
  </article>
  <article class="Box-row">
    <h2 class="h3 lh-condensed"><a href="/vercel/ai"><span class="text-normal">vercel /</span> ai</a></h2>
    <p class="col-9 color-fg-muted my-1 pr-4">TypeScript toolkit for AI apps</p>
    <div class="f6 color-fg-muted mt-2">
      <a class="Link--muted d-inline-block mr-3" href="/vercel/ai/stargazers">12,345</a>
      <a class="Link--muted d-inline-block mr-3" href="/vercel/ai/forks">1,111</a>
      <span class="d-inline-block mr-3">Built by</span>
      <a class="d-inline-block mr-3" href="/vercel/ai/contributors">4</a>
      <span class="tmp-mr-3 d-inline-block ml-0 tmp-ml-0">
        <span class="repo-language-color" style="background-color: #3178c6"></span>
        <span itemprop="programmingLanguage">TypeScript</span>
      </span>
      <span class="d-inline-block float-sm-right"><span class="Link--muted d-inline-block mr-3">567 stars this week</span></span>
    </div>
  </article>
</div>
</body></html>
"""


class TrendingParserTests(unittest.TestCase):
    def test_parse_articles(self):
        repos = parse_trending_html(TRENDING_FIXTURE)
        self.assertEqual(len(repos), 2)

    def test_first_article_fields(self):
        repo = parse_trending_html(TRENDING_FIXTURE)[0]
        self.assertEqual(repo.full_name, "openai/whisper")
        self.assertEqual(repo.stars, 68000)
        self.assertEqual(repo.forks, 8000)
        self.assertEqual(repo.weekly_stars, 1234)
        self.assertEqual(repo.language, "Python")
        self.assertEqual(
            repo.description,
            "Robust speech recognition via large-scale weak supervision",
        )

    def test_built_by_does_not_pollute_language(self):
        repo = parse_trending_html(TRENDING_FIXTURE)[1]
        self.assertEqual(repo.full_name, "vercel/ai")
        self.assertEqual(repo.language, "TypeScript")
        self.assertEqual(repo.weekly_stars, 567)
