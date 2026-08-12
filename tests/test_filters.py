import unittest

from github_hot.filters import annotate_ai_repos, match_repo
from github_hot.models import TrendingRepo


class FilterTests(unittest.TestCase):
    def test_llm_project(self):
        repo = TrendingRepo(
            full_name="ollama/ollama",
            url="https://github.com/ollama/ollama",
            description="Run large language models locally",
        )
        is_ai, reasons = match_repo(repo)
        self.assertTrue(is_ai)
        self.assertTrue(
            any(
                ("llm" in reason or "ollama" in reason or "large language model" in reason)
                for reason in reasons
            )
        )

    def test_non_ai_project(self):
        repo = TrendingRepo(
            full_name="microsoft/vscode",
            url="https://github.com/microsoft/vscode",
            description="Code editor",
        )
        self.assertFalse(match_repo(repo)[0])

    def test_chinese_keyword(self):
        repo = TrendingRepo(
            full_name="acme/framework",
            url="https://github.com/acme/framework",
            description="开源大模型推理框架",
        )
        self.assertTrue(match_repo(repo)[0])

    def test_topic_match(self):
        repo = TrendingRepo(
            full_name="acme/tool",
            url="https://github.com/acme/tool",
            description="Developer tool",
            topics=["machine-learning"],
        )
        self.assertTrue(match_repo(repo)[0])

    def test_annotate_keeps_all_repos(self):
        repos = [
            TrendingRepo(
                full_name="microsoft/vscode",
                url="https://github.com/microsoft/vscode",
                description="Code editor",
            ),
            TrendingRepo(
                full_name="ollama/ollama",
                url="https://github.com/ollama/ollama",
                description="Run LLMs locally",
            ),
        ]
        annotated = annotate_ai_repos(repos)
        self.assertEqual(len(annotated), 2)
        self.assertFalse(annotated[0].ai_reasons)
        self.assertTrue(annotated[1].ai_reasons)
