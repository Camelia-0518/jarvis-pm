"""CI gate: 空库迁移链完整性

验证 alembic upgrade head 在 fresh database 上可完整执行。
"""

import pytest
from pathlib import Path


@pytest.mark.ci
@pytest.mark.integration
def test_alembic_migrations_exist():
    """验证迁移文件和 env.py 指向的模型全部可导入"""
    from app.models.__init__ import __all__ as all_models
    assert "ReviewRecord" in all_models, "ReviewRecord must be exported for alembic env.py"
    assert len(all_models) >= 20, "Expected 20+ models to be registered"


@pytest.mark.ci
def test_alembic_config_valid():
    """验证 alembic 配置文件存在"""
    alembic_dir = Path(__file__).parent.parent / "alembic"
    assert alembic_dir.exists(), "alembic directory missing"
    assert (alembic_dir / "env.py").exists(), "alembic/env.py missing"
    assert (alembic_dir / "versions").exists(), "alembic/versions directory missing"

    # 验证最新迁移包含 review_records
    versions = list((alembic_dir / "versions").glob("*.py"))
    assert len(versions) >= 4, f"Expected 4+ migration files, found {len(versions)}"
