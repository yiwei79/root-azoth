"""BL-014: kernel governance docs stay cross-consistent (drift, gates, promotion)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


class TestKernelChecksumBlock:
    def test_governance_integrity_lists_four_explicit_paths(self) -> None:
        gov = _read("kernel/GOVERNANCE.md")
        assert "sha256sum kernel/BOOTLOADER.md kernel/GOVERNANCE.md" in gov
        assert "kernel/PROMOTION_RUBRIC.md kernel/TRUST_CONTRACT.md" in gov
        assert "kernel/*.md" not in gov.split("### Integrity Check Mechanism")[1].split("```")[1]

    def test_trust_section3_points_to_governance(self) -> None:
        trust = _read("kernel/TRUST_CONTRACT.md")
        s3 = trust.split("## 3. Drift Detection")[1].split("## 4.")[0]
        assert "kernel/GOVERNANCE.md" in s3
        assert "Section 4" in s3 or "§4" in s3 or "Drift Detection Contract" in s3
        assert "sha256sum kernel/BOOTLOADER.md" not in s3


class TestGateCrossRefs:
    def test_trust_section2_points_to_governance_gates(self) -> None:
        trust = _read("kernel/TRUST_CONTRACT.md")
        s2 = trust.split("## 2. Alignment Protocol")[1].split("## 3.")[0]
        assert "kernel/GOVERNANCE.md" in s2
        assert "Section 2" in s2

    def test_bootloader_activate_lists_governance_section2_gates(self) -> None:
        boot = _read("kernel/BOOTLOADER.md")
        act = boot.split("## Phase 1: ACTIVATE")[1].split("## Phase 2:")[0]
        assert "GOVERNANCE.md" in act
        assert "Section 2" in act

    def test_bootloader_operate_points_to_governance_section2(self) -> None:
        boot = _read("kernel/BOOTLOADER.md")
        op = boot.split("## Phase 3: OPERATE")[1].split("## Phase 4:")[0]
        assert "GOVERNANCE.md" in op
        assert "Section 2" in op


class TestPromotionRubric:
    def test_single_promotion_checklists_section(self) -> None:
        rubric = _read("kernel/PROMOTION_RUBRIC.md")
        assert "### Promotion checklists (by destination)" in rubric
        assert "#### M3 → M2" in rubric
        assert "#### M2 → M1" in rubric
        assert "2+ source episodes" in rubric
        assert "m2_candidate" in rubric


class TestGovernanceM2M1Process:
    def test_process_points_to_promotion_rubric(self) -> None:
        gov = _read("kernel/GOVERNANCE.md")
        m2m1 = gov.split("### M2 → M1 Promotion")[1].split("### Promotion Anti-Patterns")[0]
        assert "PROMOTION_RUBRIC.md" in m2m1
        assert "Promotion checklists" in m2m1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
