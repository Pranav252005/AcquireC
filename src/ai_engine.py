"""AI generation engine with grammar constraints, validation, caching, and fallback chain.

Provides consistent, high-quality pitch generation through structured output control.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models import Lead, PitchCache, _utc_now

logger = logging.getLogger(__name__)

# GBNF grammar for guaranteed valid JSON output
PITCH_GRAMMAR = r'''
root ::= "{" ws "\"pitch_text\"" ":" ws string "," ws "\"context_summary\"" ":" ws string "," ws "\"membership_idea\"" ":" ws string "," ws "\"website_benefits\"" ":" ws string "}"
ws ::= [ \t\n]*
string ::= "\"" ([^"\\] | "\\" ["\\/bfnrt] | "\\u" [0-9a-fA-F]{4})* "\""
'''


@dataclass
class BusinessContext:
    """Rich context for pitch generation."""

    name: str
    city: str
    business_type: str
    years_in_business: int | None
    has_website: bool
    website_score: str
    website_issues: list[str]
    linkedin_summary: str
    offerings: str
    rating: float | None = None
    review_count: int | None = None
    price_level: str | None = None
    maturity_stage: str | None = None
    biggest_pain_point: str | None = None
    membership_concept: str | None = None
    website_benefit_lines: list[str] | None = None


class TemperatureScheduler:
    """Map generation stage to optimal temperature."""

    _STAGES: dict[str, float] = {
        "analysis": 0.1,
        "draft": 0.3,
        "refinement": 0.5,
        "creative": 0.4,
    }

    @classmethod
    def get(cls, stage: str) -> float:
        return cls._STAGES.get(stage, 0.3)


class PitchValidator:
    """Validate AI-generated pitch structure and content."""

    SCHEMA: dict[str, dict[str, Any]] = {
        "pitch_text": {"type": "string", "min_length": 100, "max_length": 1200},
        "context_summary": {"type": "string", "min_length": 20, "max_length": 300},
        "membership_idea": {"type": "string", "min_length": 50, "max_length": 600},
        "website_benefits": {"type": "string", "min_length": 50, "max_length": 600},
    }

    def validate(self, output: dict[str, Any]) -> list[str]:
        """Return list of validation errors; empty list means pass."""
        errors: list[str] = []
        for key, rules in self.SCHEMA.items():
            val = output.get(key, "")
            if not isinstance(val, str):
                errors.append(f"{key} is not a string")
                continue
            min_len = rules.get("min_length", 0)
            max_len = rules.get("max_length", 9999)
            if len(val) < min_len:
                errors.append(f"{key} too short ({len(val)} chars, need {min_len})")
            if len(val) > max_len:
                errors.append(f"{key} too long ({len(val)} chars, max {max_len})")

        # Content guards
        pitch_lower = output.get("pitch_text", "").lower()
        if "website" not in pitch_lower and "site" not in pitch_lower:
            errors.append("pitch_text missing website/site reference")
        if len(pitch_lower) < 200:
            errors.append("pitch_text seems too brief for a business pitch")

        return errors


class PromptRenderer:
    """Render Jinja2 prompt templates for different business types."""

    def __init__(self, templates_dir: str | None = None) -> None:
        if templates_dir is None:
            templates_dir = str(Path(__file__).parent / "prompts" / "v1")
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(),
        )
        self._system_template = self.env.get_template("system_pitch.txt")

    def render_system(self) -> str:
        return self._system_template.render()

    def render_user(self, ctx: BusinessContext) -> str:
        template_name = self._template_for_type(ctx.business_type)
        try:
            tmpl = self.env.get_template(template_name)
        except Exception:
            try:
                tmpl = self.env.get_template("user_generic.txt")
            except Exception:
                return self._inline_generic_prompt(ctx)
        return tmpl.render(
            name=ctx.name,
            city=ctx.city,
            business_type=ctx.business_type,
            years=ctx.years_in_business or "unknown",
            has_website=ctx.has_website,
            website_score=ctx.website_score,
            website_issues=ctx.website_issues,
            linkedin_summary=ctx.linkedin_summary or "Not available",
            offerings=ctx.offerings or "Not available",
            rating=ctx.rating,
            review_count=ctx.review_count,
            price_level=ctx.price_level,
            maturity_stage=ctx.maturity_stage or "unknown",
            biggest_pain_point=ctx.biggest_pain_point or "Not analyzed",
            membership_concept=ctx.membership_concept or "Not available",
            website_benefit_lines=ctx.website_benefit_lines or [],
        )

    @staticmethod
    def _inline_generic_prompt(ctx: BusinessContext) -> str:
        lines = [
            f"Business: {ctx.name} in {ctx.city}",
            f"Type: {ctx.business_type}",
            f"Years in business: {ctx.years_in_business or 'unknown'}",
            f"Has website: {ctx.has_website}",
            f"Website score: {ctx.website_score}",
            f"Website issues: {', '.join(ctx.website_issues) or 'none'}",
            f"Rating: {ctx.rating or 'N/A'}",
            f"Review count: {ctx.review_count or 'N/A'}",
            f"Maturity stage: {ctx.maturity_stage or 'unknown'}",
            f"Biggest pain point: {ctx.biggest_pain_point or 'Not analyzed'}",
            f"Membership concept: {ctx.membership_concept or 'Not available'}",
            f"Offerings: {ctx.offerings or 'Not available'}",
            "",
            "Generate a personalized business pitch.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _template_for_type(business_type: str) -> str:
        mapping = {
            "cafe": "user_cafe.txt",
            "coffee": "user_cafe.txt",
            "restaurant": "user_restaurant.txt",
            "salon": "user_salon.txt",
            "spa": "user_salon.txt",
            "retail": "user_retail.txt",
            "shop": "user_retail.txt",
            "clinic": "user_clinic.txt",
            "doctor": "user_clinic.txt",
            "medical": "user_clinic.txt",
            "gym": "user_gym.txt",
            "fitness": "user_gym.txt",
            "tuition": "user_tuition.txt",
            "coaching": "user_tuition.txt",
        }
        return mapping.get(business_type.lower(), "user_generic.txt")


class PitchCacheManager:
    """Manage cached pitches to avoid redundant AI calls."""

    @staticmethod
    def _hash_context(ctx: BusinessContext) -> str:
        """Create a deterministic hash of the context."""
        key_data = {
            "name": ctx.name,
            "city": ctx.city,
            "type": ctx.business_type,
            "stage": ctx.maturity_stage,
            "score": ctx.website_score,
            "years": ctx.years_in_business,
            "has_website": ctx.has_website,
            "issues": ctx.website_issues,
            "rating": ctx.rating,
        }
        raw = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, db: Session, ctx: BusinessContext) -> dict[str, str] | None:
        """Return cached pitch if available, else None."""
        h = self._hash_context(ctx)
        cache = (
            db.query(PitchCache)
            .filter_by(context_hash=h)
            .order_by(PitchCache.hit_count.desc())
            .first()
        )
        if cache:
            cache.hit_count += 1
            cache.last_used_at = _utc_now()
            # Do not commit here; let caller manage transaction
            db.flush()
            return {
                "pitch_text": cache.pitch_text,
                "membership_idea": cache.membership_idea,
                "website_benefits": cache.website_benefits,
                "context_summary": f"Cached pitch for {ctx.business_type} ({ctx.maturity_stage})",
            }
        return None

    def save(
        self,
        db: Session,
        ctx: BusinessContext,
        pitch_text: str,
        membership_idea: str,
        website_benefits: str,
        model_used: str,
    ) -> None:
        """Store a successful pitch in cache."""
        h = self._hash_context(ctx)
        existing = db.query(PitchCache).filter_by(context_hash=h).first()
        if existing:
            existing.pitch_text = pitch_text
            existing.membership_idea = membership_idea
            existing.website_benefits = website_benefits
            existing.model_used = model_used
            existing.last_used_at = _utc_now()
        else:
            cache = PitchCache(
                context_hash=h,
                business_type=ctx.business_type,
                maturity_stage=ctx.maturity_stage or "unknown",
                website_score=ctx.website_score,
                pitch_text=pitch_text,
                membership_idea=membership_idea,
                website_benefits=website_benefits,
                model_used=model_used,
            )
            db.add(cache)
        db.commit()


# Lazy-loaded model instances
_local_llama: Any = None
_local_text: Any = None


def _load_local_model(model_path: str, clip_model_path: str | None = None) -> Any:
    """Load local model via llama-cpp-python (cached)."""
    global _local_llama
    if _local_llama is not None:
        return _local_llama

    try:
        from llama_cpp import Llama
    except ImportError as exc:
        raise RuntimeError("llama-cpp-python is not installed") from exc

    path = Path(model_path)
    if not path.exists():
        raise RuntimeError(f"Local model not found: {path}")

    kwargs: dict[str, Any] = {"model_path": str(path), "n_ctx": 4096, "verbose": False}
    if clip_model_path and Path(clip_model_path).exists():
        kwargs["clip_model_path"] = clip_model_path

    try:
        _local_llama = Llama(**kwargs)
        return _local_llama
    except Exception as exc:
        raise RuntimeError(f"Failed to load local model: {exc}") from exc


def _load_text_model(model_path: str) -> Any:
    """Load a text-only local model (larger context, no vision)."""
    global _local_text
    if _local_text is not None:
        return _local_text

    try:
        from llama_cpp import Llama
    except ImportError as exc:
        raise RuntimeError("llama-cpp-python is not installed") from exc

    path = Path(model_path)
    if not path.exists():
        return None

    try:
        _local_text = Llama(
            model_path=str(path),
            n_ctx=8192,
            verbose=False,
        )
        return _local_text
    except Exception as exc:
        logger.warning("Failed to load text fallback model: %s", exc)
        return None


class AIPitchEngine:
    """Orchestrated pitch generation with validation, caching, and fallbacks."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.validator = PitchValidator()
        self.renderer = PromptRenderer()
        self.cache = PitchCacheManager()

    def generate(
        self,
        db: Session,
        ctx: BusinessContext,
        max_retries: int = 3,
    ) -> dict[str, str]:
        """Generate a pitch with full validation, caching, and fallback chain."""
        # 1. Check cache
        cached = self.cache.get(db, ctx)
        if cached:
            logger.info("Pitch cache hit for %s (%s)", ctx.name, ctx.business_type)
            return cached

        # 2. Try primary model with retries
        system_prompt = self.renderer.render_system()
        user_prompt = self.renderer.render_user(ctx)

        for attempt in range(1, max_retries + 1):
            try:
                result = self._try_primary(system_prompt, user_prompt)
                errors = self.validator.validate(result)
                if not errors:
                    self.cache.save(
                        db,
                        ctx,
                        result["pitch_text"],
                        result["membership_idea"],
                        result["website_benefits"],
                        model_used="primary",
                    )
                    return result
                logger.warning("Pitch validation failed (attempt %d): %s", attempt, errors)
                # Feed errors back for retry
                user_prompt += f"\n\nPrevious attempt had these issues: {errors}. Please fix them."
            except Exception as exc:
                logger.warning("Primary model failed (attempt %d): %s", attempt, exc)

        # 3. Try VLM fallback (same weights but with vision projector loaded)
        try:
            result = self._try_vlm_fallback(system_prompt, user_prompt)
            errors = self.validator.validate(result)
            if not errors:
                self.cache.save(
                    db,
                    ctx,
                    result["pitch_text"],
                    result["membership_idea"],
                    result["website_benefits"],
                    model_used="vlm_fallback",
                )
                return result
        except Exception as exc:
            logger.warning("VLM fallback failed: %s", exc)

        # 4. Try Ollama API fallback
        try:
            result = self._try_ollama_fallback(system_prompt, user_prompt)
            errors = self.validator.validate(result)
            if not errors:
                self.cache.save(
                    db,
                    ctx,
                    result["pitch_text"],
                    result["membership_idea"],
                    result["website_benefits"],
                    model_used="ollama_fallback",
                )
                return result
        except Exception as exc:
            logger.warning("Ollama fallback failed: %s", exc)

        # 5. Template fallback
        logger.info("All AI models failed; using template fallback for %s", ctx.name)
        return self._template_fallback(ctx)

    def _try_primary(self, system_prompt: str, user_prompt: str) -> dict[str, str]:
        """Generate using the primary local text model with grammar constraint."""
        llm = _load_local_model(self.settings.local_model_path)
        full_prompt = (
            f"<|im_start|>system\n{system_prompt}\n<|im_start|>user\n{user_prompt}\n<|im_start|>assistant\n"
        )
        output = llm(
            full_prompt,
            max_tokens=1024,
            stop=["<|im_start|>"],
            temperature=TemperatureScheduler.get("draft"),
            grammar=PITCH_GRAMMAR,
        )
        raw = output.get("choices", [{}])[0].get("text", "").strip()
        parsed = json.loads(raw)
        return {
            "pitch_text": parsed.get("pitch_text", ""),
            "context_summary": parsed.get("context_summary", ""),
            "membership_idea": parsed.get("membership_idea", ""),
            "website_benefits": parsed.get("website_benefits", ""),
        }

    def _try_vlm_fallback(self, system_prompt: str, user_prompt: str) -> dict[str, str]:
        """Fallback to the VLM model (with vision projector) if text model fails."""
        llm = _load_local_model(
            str(self.settings.vlm_model_path),
            clip_model_path=str(self.settings.vlm_mmproj_path),
        )
        full_prompt = (
            f"<|im_start|>system\n{system_prompt}\n<|im_start|>user\n{user_prompt}\n<|im_start|>assistant\n"
        )
        output = llm(
            full_prompt,
            max_tokens=1024,
            stop=["<|im_start|>"],
            temperature=TemperatureScheduler.get("draft"),
            grammar=PITCH_GRAMMAR,
        )
        raw = output.get("choices", [{}])[0].get("text", "").strip()
        parsed = json.loads(raw)
        return {
            "pitch_text": parsed.get("pitch_text", ""),
            "context_summary": parsed.get("context_summary", ""),
            "membership_idea": parsed.get("membership_idea", ""),
            "website_benefits": parsed.get("website_benefits", ""),
        }

    def _try_ollama_fallback(self, system_prompt: str, user_prompt: str) -> dict[str, str]:
        """Try Ollama HTTP API if running."""
        import urllib.request

        url = f"{self.settings.ollama_url}/api/generate"
        payload = json.dumps(
            {
                "model": self.settings.ollama_model,
                "prompt": f"{system_prompt}\n\n{user_prompt}\n\nReturn ONLY valid JSON.",
                "stream": False,
                "options": {"temperature": TemperatureScheduler.get("draft")},
            }
        ).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            raw = data.get("response", "").strip()
            parsed = json.loads(raw)
            return {
                "pitch_text": parsed.get("pitch_text", ""),
                "context_summary": parsed.get("context_summary", ""),
                "membership_idea": parsed.get("membership_idea", ""),
                "website_benefits": parsed.get("website_benefits", ""),
            }

    def _template_fallback(self, ctx: BusinessContext) -> dict[str, str]:
        """Last resort: structured template fallback."""
        from src.membership_ideas import MembershipLibrary
        from src.business_intelligence import MaturityAnalyzer

        lib = MembershipLibrary()
        concept = lib.get_concept(ctx.business_type)
        maturity = ctx.maturity_stage or MaturityAnalyzer.infer_stage(ctx.years_in_business)
        benefits = MaturityAnalyzer.get_website_benefits(maturity, ctx.business_type)

        pitch_lines = [
            f"Hi {ctx.name} team,",
            "",
            f"I came across your business in {ctx.city} and noticed you could benefit from a modern, mobile-friendly website.",
            "",
        ]

        if ctx.years_in_business:
            pitch_lines.append(
                f"With {ctx.years_in_business} years in business, you've built something real — now let a professional website work while you sleep."
            )
        else:
            pitch_lines.append(
                "A professional website helps new customers find you, learn what you offer, and get in touch easily."
            )

        if ctx.membership_concept:
            pitch_lines.extend([
                "",
                f"Here's an idea: {ctx.membership_concept}",
                "This runs entirely through your website — sign-ups, payments, and member tracking."
            ])

        pitch_lines.extend([
            "",
            "I build fast, beautiful websites tailored for local businesses like yours.",
            f"Would you be open to a quick chat about how a new site could drive more customers your way?",
            "",
            "Best regards",
        ])

        return {
            "pitch_text": "\n".join(pitch_lines),
            "context_summary": f"Template fallback for {ctx.business_type} ({maturity})",
            "membership_idea": ctx.membership_concept or (concept.description if concept else ""),
            "website_benefits": "\n".join(f"- {b}" for b in benefits),
        }
