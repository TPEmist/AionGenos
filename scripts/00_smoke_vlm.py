"""M0 Smoke Test: VLM base64 grounding sanity.

Feeds a synthetic image to the teacher VLM and verifies it returns
valid integer coordinates in the expected format.

Usage:
    python scripts/00_smoke_vlm.py
"""

import asyncio
import io
import logging
import sys

from PIL import Image, ImageDraw

from aiongenos.config import AionGenosConfig
from aiongenos.vlm.client import call_vlm, encode_image_bytes_base64
from aiongenos.vlm.parser import parse_stage1
from aiongenos.vlm.prompts import get_stage1_system_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def create_synthetic_scene() -> bytes:
    """Create a 128x128 synthetic scene with colored cubes."""
    img = Image.new("RGB", (128, 128), color=(200, 200, 200))
    draw = ImageDraw.Draw(img)

    # Red cube (left side) — represents left target
    draw.rectangle([20, 40, 50, 70], fill=(255, 0, 0))

    # Blue cube (right side) — represents right target
    draw.rectangle([78, 40, 108, 70], fill=(0, 0, 255))

    # Green ground plane indicator
    draw.rectangle([0, 100, 128, 128], fill=(0, 150, 0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def main():
    config = AionGenosConfig()
    logger.info(f"Teacher URL: {config.teacher_url}")

    # Create synthetic image
    img_bytes = create_synthetic_scene()
    img_b64 = encode_image_bytes_base64(img_bytes)
    logger.info(f"Synthetic image: 128x128 PNG, {len(img_b64)} chars base64")

    # Build prompt
    system_prompt = get_stage1_system_prompt()
    user_prompt = (
        "TASK: Move both end-effectors to the colored targets. "
        "Left arm should reach the red target, right arm should reach the blue target.\n"
        "CONTROL_MODE: end_effector_position_only\n\n"
        "CURRENT STATE:\n"
        "  LEFT_EE_POS  = (X=0, Y=0, Z=50)\n"
        "  RIGHT_EE_POS = (X=0, Y=0, Z=50)\n\n"
        "THOUGHT: <one paragraph physics reasoning>\n"
        "LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
        "RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
        "STOP: <true|false>"
    )

    # Call VLM
    logger.info("Calling teacher VLM...")
    try:
        response = await call_vlm(
            url=config.teacher_url,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            image_base64=img_b64,
            temperature=0.3,
            max_tokens=512,
            timeout=120.0,
        )
        logger.info(f"VLM response:\n{response}")
    except Exception as e:
        logger.error(f"VLM call failed: {e}")
        sys.exit(1)

    # Parse response
    try:
        result = parse_stage1(response)
        logger.info(f"Parsed LEFT:  ({result.left.position.x}, {result.left.position.y}, {result.left.position.z})")
        logger.info(f"Parsed RIGHT: ({result.right.position.x}, {result.right.position.y}, {result.right.position.z})")
        logger.info(f"STOP: {result.stop}")
        logger.info(f"THOUGHT: {result.thought[:100]}...")
        logger.info("✅ VLM smoke test PASSED — valid integer coordinates returned")
    except ValueError as e:
        logger.error(f"Parse failed: {e}")
        logger.error("❌ VLM smoke test FAILED — could not parse coordinates")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
