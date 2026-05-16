"""Tests for reply parser module."""

import pytest

from src.models import Lead, ReplyIntent
from src.reply_parser import ParsedReply, ReplyParser


class TestReplyParser:
    def test_interested_keywords(self) -> None:
        texts = ["I'm interested", "sounds good", "tell me more", "yes please", "call me"]
        for text in texts:
            result = ReplyParser.parse(text)
            assert result.intent == ReplyIntent.INTERESTED, f"Failed for: {text}"
            assert result.confidence > 0

    def test_price_inquiry_keywords(self) -> None:
        texts = ["how much?", "what's the price", "cost?", "quote please", "budget is tight"]
        for text in texts:
            result = ReplyParser.parse(text)
            assert result.intent == ReplyIntent.PRICE_INQUIRY, f"Failed for: {text}"

    def test_not_now_keywords(self) -> None:
        texts = ["not now", "maybe later", "too busy", "contact me next month"]
        for text in texts:
            result = ReplyParser.parse(text)
            assert result.intent == ReplyIntent.NOT_NOW, f"Failed for: {text}"

    def test_not_interested_keywords(self) -> None:
        texts = ["not interested", "no thanks", "unsubscribe", "stop", "don't contact me"]
        for text in texts:
            result = ReplyParser.parse(text)
            assert result.intent == ReplyIntent.NOT_INTERESTED, f"Failed for: {text}"

    def test_booked_keywords(self) -> None:
        texts = ["call me on Monday", "meet at 3pm", "available tomorrow", "free on Tuesday"]
        for text in texts:
            result = ReplyParser.parse(text)
            assert result.intent == ReplyIntent.BOOKED, f"Failed for: {text}"

    def test_empty_reply(self) -> None:
        result = ReplyParser.parse("")
        assert result.intent == ReplyIntent.UNKNOWN
        assert result.confidence == 0.0

    def test_unknown_reply(self) -> None:
        result = ReplyParser.parse("xyz abc 123")
        assert result.intent == ReplyIntent.UNKNOWN

    def test_extracts_phone(self) -> None:
        result = ReplyParser.parse("Call me at +91 98765 43210")
        assert "phone" in result.extracted_info

    def test_extracts_email(self) -> None:
        result = ReplyParser.parse("Reach me at test@example.com")
        assert "email" in result.extracted_info

    def test_auto_reply_for_price_inquiry(self) -> None:
        lead = Lead(business_name="Test Cafe", business_type="cafe", city="Mumbai", address="x", google_maps_url="x")
        parsed = ReplyParser.parse("How much does it cost?")
        reply = ReplyParser.auto_reply(parsed, lead)
        assert reply is not None
        assert "Test Cafe" in reply
        assert "pricing" in reply.lower() or "price" in reply.lower()

    def test_auto_reply_for_interested(self) -> None:
        lead = Lead(business_name="Test Cafe", business_type="cafe", city="Mumbai", address="x", google_maps_url="x")
        parsed = ReplyParser.parse("I'm interested")
        reply = ReplyParser.auto_reply(parsed, lead)
        assert reply is not None
        assert "15 minutes" in reply or "chat" in reply.lower()
