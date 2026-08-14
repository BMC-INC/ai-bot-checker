#!/usr/bin/env python3
"""Offline unit tests for the AI Bot Blocker Checker core. No network access."""

import unittest

from app import (
    AI_BOTS,
    assert_public_host,
    build_recommendations,
    evaluate_bots,
    normalize_url,
)

BASE = "https://example.com"


class TestNormalizeUrl(unittest.TestCase):
    def test_adds_https_scheme(self):
        self.assertEqual(normalize_url("example.com"), "https://example.com")

    def test_keeps_http_scheme(self):
        self.assertEqual(normalize_url("http://example.com/path?q=1"), "http://example.com")

    def test_strips_path_and_query(self):
        self.assertEqual(normalize_url("https://example.com/a/b?c=d"), "https://example.com")

    def test_rejects_garbage(self):
        with self.assertRaises(ValueError):
            normalize_url("https://")


class TestEvaluateBots(unittest.TestCase):
    def test_empty_robots_allows_everything(self):
        results = evaluate_bots("", BASE)
        self.assertEqual(len(results), len(AI_BOTS))
        self.assertTrue(all(b["status"] == "allowed" for b in results))

    def test_blanket_disallow_blocks_everything(self):
        results = evaluate_bots("User-agent: *\nDisallow: /\n", BASE)
        self.assertTrue(all(b["status"] == "blocked" for b in results))

    def test_targeted_block_only_hits_named_bot(self):
        robots = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
        results = {b["ua"]: b["status"] for b in evaluate_bots(robots, BASE)}
        self.assertEqual(results["GPTBot"], "blocked")
        self.assertEqual(results["ClaudeBot"], "allowed")
        self.assertEqual(results["PerplexityBot"], "allowed")

    def test_result_shape(self):
        bot = evaluate_bots("", BASE)[0]
        for key in ("ua", "name", "operator", "category", "desc", "status"):
            self.assertIn(key, bot)


class TestBotList(unittest.TestCase):
    def test_no_duplicate_user_agents(self):
        uas = [b["ua"] for b in AI_BOTS]
        self.assertEqual(len(uas), len(set(uas)))

    def test_categories_are_known(self):
        allowed = {"Search", "User Fetch", "Training"}
        self.assertTrue(all(b["category"] in allowed for b in AI_BOTS))


class TestRecommendations(unittest.TestCase):
    def test_three_templates_with_snippets(self):
        recs = build_recommendations([])
        self.assertEqual(len(recs), 3)
        for rec in recs:
            self.assertTrue(rec["title"])
            self.assertTrue(rec["description"])
            self.assertIn("User-agent:", rec["snippet"])

    def test_balanced_template_splits_search_and_training(self):
        balanced = build_recommendations([])[1]["snippet"]
        self.assertIn("User-agent: OAI-SearchBot\nAllow: /", balanced)
        self.assertIn("User-agent: GPTBot\nDisallow: /", balanced)


class TestSsrfGuard(unittest.TestCase):
    def test_rejects_loopback(self):
        with self.assertRaises(ValueError):
            assert_public_host("https://127.0.0.1")

    def test_rejects_private_range(self):
        with self.assertRaises(ValueError):
            assert_public_host("https://192.168.1.1")

    def test_rejects_localhost_name(self):
        with self.assertRaises(ValueError):
            assert_public_host("https://localhost")


if __name__ == "__main__":
    unittest.main()
