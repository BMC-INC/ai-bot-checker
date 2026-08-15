#!/usr/bin/env python3
"""Offline unit tests for the AI Bot Blocker Checker core. No network access."""

import socket
import unittest
from unittest import mock

from app import (
    AI_BOTS,
    assert_public_host,
    build_recommendations,
    compute_posture,
    evaluate_bots,
    find_unscored_agents,
    normalize_url,
    resolve_public_ip,
)


def _addrinfo(*ips):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 0)) for ip in ips]

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


def _block(*uas):
    """robots.txt that blocks exactly the given user-agents."""
    return "\n".join(f"User-agent: {ua}\nDisallow: /\n" for ua in uas)


def _training_uas():
    return [b["ua"] for b in AI_BOTS if b["category"] == "Training"]


class TestComputePosture(unittest.TestCase):
    def _posture(self, robots):
        return compute_posture(evaluate_bots(robots, BASE))

    def test_shape(self):
        p = self._posture("")
        for key in ("verdict", "label", "detail"):
            self.assertIn(key, p)

    def test_open_when_nothing_blocked(self):
        self.assertEqual(self._posture("")["verdict"], "open")

    def test_locked_down_when_everything_blocked(self):
        self.assertEqual(self._posture("User-agent: *\nDisallow: /\n")["verdict"], "locked_down")

    def test_balanced_requires_all_training_bots_blocked(self):
        p = self._posture(_block(*_training_uas()))
        self.assertEqual(p["verdict"], "balanced")

    def test_partial_training_block_is_selective_not_balanced(self):
        # The execlayer.io case: 5 of 12 training bots blocked must NOT
        # be reported as "balanced" — it's an incomplete blocklist.
        p = self._posture(_block("GPTBot", "Google-Extended", "Bytespider", "CCBot", "FacebookBot"))
        self.assertEqual(p["verdict"], "selective")

    def test_selective_detail_names_blocked_and_allowed_operators(self):
        p = self._posture(_block("GPTBot", "Google-Extended"))
        self.assertIn("OpenAI", p["detail"])
        self.assertIn("Anthropic", p["detail"])

    def test_visibility_risk_when_search_bots_blocked(self):
        p = self._posture(_block("OAI-SearchBot", "PerplexityBot", "Claude-SearchBot", "Applebot"))
        self.assertEqual(p["verdict"], "visibility_risk")


class TestFindUnscoredAgents(unittest.TestCase):
    def test_flags_agents_the_grid_does_not_score(self):
        robots = "User-agent: Bingbot\nDisallow: /\n\nUser-agent: GPTBot\nDisallow: /\n"
        self.assertEqual(find_unscored_agents(robots), ["Bingbot"])

    def test_case_insensitive_match_against_scored_list(self):
        # Claude-Web is scored as "claude-web"; must not be flagged.
        robots = "User-agent: Claude-Web\nDisallow: /\n"
        self.assertEqual(find_unscored_agents(robots), [])

    def test_ignores_wildcard_and_dedupes(self):
        robots = "User-agent: *\nAllow: /\n\nUser-agent: Bingbot\nUser-agent: bingbot\nDisallow: /\n"
        self.assertEqual(find_unscored_agents(robots), ["Bingbot"])

    def test_empty_robots(self):
        self.assertEqual(find_unscored_agents(""), [])


class TestRecommendationAudience(unittest.TestCase):
    def test_every_recommendation_declares_an_audience(self):
        recs = build_recommendations(evaluate_bots("", BASE))
        self.assertTrue(recs)
        for r in recs:
            self.assertIn("audience", r)
            self.assertIn(r["audience"], ("vendor", "publisher", "strict"))


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

    def test_rejects_missing_hostname(self):
        with self.assertRaises(ValueError):
            resolve_public_ip("")

    def test_rejects_mixed_public_and_private_records(self):
        # A host with even one private record must be refused entirely,
        # otherwise a malicious DNS answer can smuggle a private target in.
        with mock.patch("app.socket.getaddrinfo", return_value=_addrinfo("93.184.216.34", "10.0.0.5")):
            with self.assertRaises(ValueError):
                resolve_public_ip("evil.example")

    def test_returns_pinned_ip_for_public_host(self):
        with mock.patch("app.socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
            self.assertEqual(resolve_public_ip("example.com"), "93.184.216.34")

    def test_rejects_metadata_endpoint_ip(self):
        # 169.254.169.254 is link-local; the cloud metadata classic.
        with mock.patch("app.socket.getaddrinfo", return_value=_addrinfo("169.254.169.254")):
            with self.assertRaises(ValueError):
                resolve_public_ip("metadata.internal")


if __name__ == "__main__":
    unittest.main()
