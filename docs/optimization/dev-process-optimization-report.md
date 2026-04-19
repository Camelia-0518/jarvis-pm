# Jarvis PM 开发流程全面优化报告

> 基于 Claude Skills 的开发流程优化方案
> 生成日期: 2026-04-10
> 适用项目: Jarvis PM (AI 驱动的产品管理协作平台)

---

## 目录

1. [执行摘要](#执行摘要)
2. [测试策略](#测试策略)
3. [代码规范](#代码规范)
4. [开发流程优化](#开发流程优化)
5. [CI/CD 建议](#cicd-建议)
6. [Git 工作流规范](#git-工作流规范)
7. [Code Review 指南](#code-review-指南)
8. [实施路线图](#实施路线图)

---

## 执行摘要

### 当前状态分析

Jarvis PM 项目已完成 Phase 1 开发，技术栈如下:

| 层级 | 技术栈 | 当前测试状况 |
|------|--------|-------------|
| 前端 | Next.js 15 + React 19 + TypeScript | 无系统化测试 |
| 后端 | FastAPI + Python 3.11 | pytest 基础配置 |
| 数据库 | PostgreSQL + Redis | 无集成测试 |
| AI 服务 | Claude API / Kimi API | 无 Mock 测试 |

### 关键问题识别

1. **测试覆盖率不足** - 仅有基础 pytest 配置，无前端测试
2. **缺乏代码规范** - ESLint 配置简单，无 Prettier 统一格式
3. **无 CI/CD 流程** - 手动部署，无自动化检查
4. **Code Review 流程缺失** - 无标准化审查清单
5. **Git 工作流不规范** - 直接在 main 分支开发风险高

### 优化目标

| 指标 | 当前 | 目标 (3个月) |
|------|------|-------------|
| 单元测试覆盖率 | < 10% | >= 80% |
| 集成测试覆盖率 | 0% | >= 60% |
| E2E 测试覆盖率 | 0% | 核心流程 100% |
| 代码规范检查 | 部分 | 100% 自动化 |
| CI/CD 自动化 | 无 | 完整流水线 |

---

## 测试策略

### 测试金字塔

```
        /\
       /  \    E2E Tests (10%)
      /____\      - 用户完整流程
     /      \     - 关键业务路径
    /________\    - 慢但全面
   /          \
  /------------\   Integration Tests (30%)
 /              \   - API 接口测试
/________________\  - 数据库集成
                    - AI 服务 Mock

  Unit Tests (60%)
  - 组件/函数单元测试
  - 快速执行 (< 100ms)
  - 高覆盖率目标
```

### 前端测试策略 (Next.js + React)

#### 1. 单元测试 - Jest + React Testing Library

**安装依赖:**
```bash
cd apps/web
npm install --save-dev jest @testing-library/react @testing-library/jest-dom @testing-library/user-event jest-environment-jsdom
```

**配置文件 `jest.config.js`:**
```javascript
const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,ts}',
  ],
  coverageThreshold: {
    global: {
      branches: 75,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
}

module.exports = createJestConfig(customJestConfig)
```

**测试示例 - 组件测试:**
```typescript
// src/components/common/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from './Button'

describe('Button', () => {
  it('should render with correct text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('should handle click events', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    fireEvent.click(screen.getByText('Click me'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('should be disabled when loading', () => {
    render(<Button loading>Loading</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })
})
```

**测试示例 - Hook 测试:**
```typescript
// src/hooks/useAuth.test.ts
import { renderHook, act } from '@testing-library/react'
import { useAuth } from './useAuth'

describe('useAuth', () => {
  it('should return unauthenticated state initially', () => {
    const { result } = renderHook(() => useAuth())
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('should update state on login', async () => {
    const { result } = renderHook(() => useAuth())
    
    await act(async () => {
      await result.current.login({ email: 'test@test.com', password: '123' })
    })
    
    expect(result.current.isAuthenticated).toBe(true)
  })
})
```

**测试示例 - Store 测试 (Zustand):**
```typescript
// src/stores/prdStore.test.ts
import { usePRDStore } from './prdStore'

describe('PRD Store', () => {
  beforeEach(() => {
    usePRDStore.setState({ prds: [], currentPRD: null })
  })

  it('should add PRD to store', () => {
    const prd = { id: '1', title: 'Test PRD', content: 'Content' }
    usePRDStore.getState().addPRD(prd)
    
    expect(usePRDStore.getState().prds).toContainEqual(prd)
  })
})
```

#### 2. 集成测试 - API + 组件

**测试示例 - API 路由测试:**
```typescript
// src/app/api/prds/route.test.ts
import { createMocks } from 'node-mocks-http'
import { GET, POST } from './route'

describe('/api/prds', () => {
  it('should return PRD list', async () => {
    const { req, res } = createMocks({ method: 'GET' })
    await GET(req)
    
    expect(res._getStatusCode()).toBe(200)
    expect(JSON.parse(res._getData())).toHaveProperty('prds')
  })
})
```

#### 3. E2E 测试 - Playwright

**安装:**
```bash
npm install --save-dev @playwright/test
npx playwright install
```

**配置文件 `playwright.config.ts`:**
```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
})
```

**E2E 测试示例:**
```typescript
// e2e/prd-flow.spec.ts
import { test, expect } from '@playwright/test'

test.describe('PRD Creation Flow', () => {
  test('user can create a new PRD', async ({ page }) => {
    // 登录
    await page.goto('/login')
    await page.fill('[data-testid="email"]', 'test@example.com')
    await page.fill('[data-testid="password"]', 'password')
    await page.click('[data-testid="login-button"]')
    
    // 创建 PRD
    await page.goto('/dashboard')
    await page.click('[data-testid="new-prd-button"]')
    await page.fill('[data-testid="prd-title"]', 'Test PRD')
    await page.fill('[data-testid="prd-description"]', 'Description')
    await page.click('[data-testid="create-prd-button"]')
    
    // 验证
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible()
    await expect(page.locator('h1')).toContainText('Test PRD')
  })
})
```

### 后端测试策略 (FastAPI)

#### 1. 单元测试 - pytest

**当前配置已存在，需要增强:**

```python
# apps/api/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db

# 测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**服务层单元测试:**
```python
# apps/api/tests/services/test_prd_service.py
import pytest
from unittest.mock import Mock, patch
from app.services.prd_service import PRDService
from app.models.prd import PRD

class TestPRDService:
    @pytest.fixture
    def service(self, db):
        return PRDService(db)
    
    def test_create_prd(self, service, db):
        # Arrange
        prd_data = {
            "title": "Test PRD",
            "content": "Content",
            "project_id": "proj-123"
        }
        
        # Act
        result = service.create_prd(prd_data)
        
        # Assert
        assert result.title == "Test PRD"
        assert result.id is not None
    
    @patch('app.services.prd_service.ClaudeClient')
    def test_generate_prd_with_ai(self, mock_claude, service):
        # Arrange
        mock_client = Mock()
        mock_client.generate.return_value = "Generated PRD content"
        mock_claude.return_value = mock_client
        
        # Act
        result = service.generate_prd_with_ai("Create login feature")
        
        # Assert
        assert result == "Generated PRD content"
        mock_client.generate.assert_called_once()
```

#### 2. API 集成测试

```python
# apps/api/tests/api/test_prd_endpoints.py
import pytest

class TestPRDEndpoints:
    def test_create_prd(self, client):
        response = client.post("/api/v1/prds", json={
            "title": "Test PRD",
            "content": "Content",
            "project_id": "proj-123"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test PRD"
        assert "id" in data
    
    def test_get_prd_list(self, client):
        # 先创建数据
        client.post("/api/v1/prds", json={
            "title": "PRD 1",
            "content": "Content 1",
            "project_id": "proj-123"
        })
        
        # 获取列表
        response = client.get("/api/v1/prds")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
    
    def test_update_prd(self, client):
        # 创建
        create_res = client.post("/api/v1/prds", json={
            "title": "Original",
            "content": "Content",
            "project_id": "proj-123"
        })
        prd_id = create_res.json()["id"]
        
        # 更新
        response = client.put(f"/api/v1/prds/{prd_id}", json={
            "title": "Updated"
        })
        
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"
```

#### 3. AI 服务 Mock 测试

```python
# apps/api/tests/services/test_ai_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.ai_service import AIService

class TestAIService:
    @pytest.fixture
    def ai_service(self):
        return AIService()
    
    @patch('app.services.ai_service.Anthropic')
    async def test_generate_prd_with_claude(self, mock_anthropic, ai_service):
        # Mock Claude 响应
        mock_message = Mock()
        mock_message.content = [Mock(text="Generated PRD content")]
        
        mock_client = Mock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client
        
        # 测试
        result = await ai_service.generate_prd("Create login feature")
        
        assert result == "Generated PRD content"
        mock_client.messages.create.assert_called_once()
    
    @patch('app.services.ai_service.AsyncOpenAI')
    async def test_generate_prd_with_kimi(self, mock_openai, ai_service):
        # Mock Kimi (OpenAI compatible) 响应
        mock_choice = Mock()
        mock_choice.message.content = "Generated PRD content"
        
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai.return_value = mock_client
        
        # 测试
        result = await ai_service.generate_prd_with_kimi("Create login feature")
        
        assert result == "Generated PRD content"
```

### 测试数据管理

#### Factory 模式 (Python - factory_boy)

```python
# apps/api/tests/factories.py
import factory
from app.models.prd import PRD
from app.models.project import Project

class ProjectFactory(factory.Factory):
    class Meta:
        model = Project
    
    id = factory.Sequence(lambda n: f"proj-{n}")
    name = factory.Faker('company')
    description = factory.Faker('text')

class PRDFactory(factory.Factory):
    class Meta:
        model = PRD
    
    id = factory.Sequence(lambda n: f"prd-{n}")
    title = factory.Faker('sentence')
    content = factory.Faker('text')
    project = factory.SubFactory(ProjectFactory)
```

#### TypeScript Factory (frontend)

```typescript
// apps/web/src/test/factories.ts
import { faker } from '@faker-js/faker'
import { PRD, Project } from '@/types'

export const createProject = (overrides?: Partial<Project>): Project => ({
  id: faker.string.uuid(),
  name: faker.company.name(),
  description: faker.lorem.paragraph(),
  createdAt: faker.date.past().toISOString(),
  updatedAt: faker.date.recent().toISOString(),
  ...overrides,
})

export const createPRD = (overrides?: Partial<PRD>): PRD => ({
  id: faker.string.uuid(),
  title: faker.lorem.sentence(),
  content: faker.lorem.paragraphs(3),
  projectId: faker.string.uuid(),
  status: 'draft',
  createdAt: faker.date.past().toISOString(),
  updatedAt: faker.date.recent().toISOString(),
  ...overrides,
})
```

### 测试脚本配置

**`apps/web/package.json`:**
```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

**`apps/api/pyproject.toml`:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests",
]

[tool.coverage.run]
source = ["app"]
omit = ["*/tests/*", "*/migrations/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

---

## 代码规范

### 前端代码规范 (TypeScript/React)

#### ESLint 配置增强

**`.eslintrc.json`:**
```json
{
  "extends": [
    "next/core-web-vitals",
    "@typescript-eslint/recommended",
    "@typescript-eslint/recommended-requiring-type-checking",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended",
    "plugin:import/recommended",
    "plugin:import/typescript",
    "prettier"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "project": "./tsconfig.json"
  },
  "plugins": [
    "@typescript-eslint",
    "react-hooks",
    "jsx-a11y",
    "import"
  ],
  "rules": {
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    "@typescript-eslint/explicit-function-return-type": "warn",
    "@typescript-eslint/no-floating-promises": "error",
    "import/order": [
      "error",
      {
        "groups": [
          "builtin",
          "external",
          "internal",
          "parent",
          "sibling",
          "index"
        ],
        "newlines-between": "always"
      }
    ],
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn"
  },
  "settings": {
    "import/resolver": {
      "typescript": {}
    }
  }
}
```

#### Prettier 配置

**`.prettierrc`:**
```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "bracketSpacing": true,
  "arrowParens": "avoid"
}
```

**`.prettierignore`:**
```
node_modules
.next
dist
coverage
*.md
```

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件 | PascalCase | `UserProfile.tsx` |
| Hooks | camelCase + use 前缀 | `useAuth.ts` |
| 工具函数 | camelCase | `formatDate.ts` |
| 常量 | SCREAMING_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 类型/接口 | PascalCase | `UserProps`, `PRDType` |
| 枚举 | PascalCase | `UserRole` |
| 文件 | camelCase (非组件) | `apiClient.ts` |

#### 组件规范

```typescript
// ✅ 好的组件示例
import React, { useState, useCallback } from 'react'
import { Button } from '@/components/common'
import { useAuth } from '@/hooks/useAuth'
import type { User } from '@/types'

interface UserProfileProps {
  user: User
  onUpdate?: (user: User) => void
  readonly?: boolean
}

export const UserProfile: React.FC<UserProfileProps> = ({
  user,
  onUpdate,
  readonly = false,
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const { currentUser } = useAuth()
  
  const handleEdit = useCallback(() => {
    setIsEditing(true)
  }, [])
  
  const handleSave = useCallback((updatedUser: User) => {
    onUpdate?.(updatedUser)
    setIsEditing(false)
  }, [onUpdate])
  
  return (
    <div className="user-profile">
      <h2>{user.name}</h2>
      {!readonly && currentUser?.id === user.id && (
        <Button onClick={handleEdit}>Edit</Button>
      )}
    </div>
  )
}
```

#### Import 顺序规范

```typescript
// 1. React/Next.js 核心
import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/router'

// 2. 第三方库
import { useQuery } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'

// 3. 内部绝对导入 (@/)
import { Button, Input } from '@/components/common'
import { useAuth } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api'
import type { User, Project } from '@/types'

// 4. 内部相对导入 (./)
import { UserCard } from './UserCard'
import { styles } from './styles.module.css'
```

### 后端代码规范 (Python/FastAPI)

#### Ruff 配置 (替代 flake8 + black + isort)

**`pyproject.toml`:**
```toml
[tool.ruff]
target-version = "py311"
line-length = 100
select = [
    "E",   # pycodestyle errors
    "F",   # Pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "W",   # pycodestyle warnings
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.ruff.pydocstyle]
convention = "google"

[tool.ruff.isort]
known-first-party = ["app"]
```

#### 项目结构规范

```
apps/api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库连接
│   │   └── security.py        # 安全相关
│   ├── api/                    # API 层
│   │   ├── __init__.py
│   │   ├── deps.py            # 依赖注入
│   │   └── v1/                # API v1
│   │       ├── __init__.py
│   │       ├── endpoints/     # 端点模块
│   │       │   ├── __init__.py
│   │       │   ├── auth.py
│   │       │   ├── prds.py
│   │       │   └── projects.py
│   │       └── router.py      # 路由聚合
│   ├── models/                 # 数据库模型
│   │   ├── __init__.py
│   │   ├── base.py            # 基础模型
│   │   ├── user.py
│   │   ├── prd.py
│   │   └── project.py
│   ├── schemas/                # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── prd.py
│   │   └── project.py
│   ├── services/               # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── prd_service.py
│   │   └── ai_service.py
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       └── helpers.py
├── tests/
│   ├── conftest.py
│   ├── api/
│   ├── services/
│   └── factories.py
└── pyproject.toml
```

#### 代码规范示例

```python
# ✅ 好的 Python 代码示例
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.schemas.base import BaseSchema


class PRD(Base):
    """PRD 数据库模型."""
    
    __tablename__ = "prds"
    
    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(String, nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="prds")
    
    def __repr__(self) -> str:
        return f"<PRD(id={self.id}, title={self.title})>"


class PRDCreate(BaseSchema):
    """PRD 创建请求模型."""
    
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    project_id: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "用户登录功能 PRD",
                "content": "## 需求描述...",
                "project_id": "proj-123"
            }
        }


class PRDService:
    """PRD 业务逻辑服务."""
    
    def __init__(self, db: Session) -> None:
        self.db = db
    
    async def create_prd(self, prd_data: PRDCreate) -> PRD:
        """创建新 PRD.
        
        Args:
            prd_data: PRD 创建数据
            
        Returns:
            创建的 PRD 对象
            
        Raises:
            ProjectNotFoundError: 项目不存在
        """
        # 验证项目存在
        project = await self.db.get(Project, prd_data.project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {prd_data.project_id} not found")
        
        # 创建 PRD
        prd = PRD(
            id=generate_uuid(),
            title=prd_data.title,
            content=prd_data.content,
            project_id=prd_data.project_id,
        )
        
        self.db.add(prd)
        await self.db.commit()
        await self.db.refresh(prd)
        
        return prd
```

#### 错误处理规范

```python
# app/core/exceptions.py
class JarvisPMException(Exception):
    """基础异常类."""
    
    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(JarvisPMException):
    """资源不存在异常."""
    
    def __init__(self, resource: str, resource_id: str) -> None:
        message = f"{resource} with id {resource_id} not found"
        super().__init__(message, status_code=404)


class ValidationError(JarvisPMException):
    """数据验证异常."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class AIError(JarvisPMException):
    """AI 服务异常."""
    
    def __init__(self, message: str = "AI service error") -> None:
        super().__init__(message, status_code=503)
```

### 代码质量检查脚本

**`scripts/lint.sh`:**
```bash
#!/bin/bash
set -e

echo "=== Running Frontend Lint ==="
cd apps/web
npm run lint
npm run format:check

echo "=== Running Backend Lint ==="
cd ../api
ruff check .
ruff format --check .
mypy app

echo "=== All checks passed ==="
```

**`package.json` 脚本:**
```json
{
  "scripts": {
    "lint": "eslint src/ --ext .ts,.tsx",
    "lint:fix": "eslint src/ --ext .ts,.tsx --fix",
    "format": "prettier --write \"src/**/*.{ts,tsx,json,css}\"",
    "format:check": "prettier --check \"src/**/*.{ts,tsx,json,css}\"",
    "type-check": "tsc --noEmit"
  }
}
```

---

## 开发流程优化

### 基于 Skills 的开发工作流

```
┌─────────────────────────────────────────────────────────────────┐
│                     Jarvis PM 开发工作流                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 需求分析阶段                                                  │
│     ├── /skill product-analyst (需求分析)                        │
│     ├── /skill ux-designer (UX设计)                              │
│     └── /skill business-model (商业模式)                         │
│                                                                 │
│  2. 规划阶段                                                      │
│     ├── /skill planning-with-files (创建计划文件)                │
│     ├── /skill milestone-planner (里程碑规划)                    │
│     └── /skill writing-plans (编写执行计划)                      │
│                                                                 │
│  3. 开发阶段                                                      │
│     ├── /skill using-git-worktrees (隔离工作区)                  │
│     ├── /skill subagent-driven-development (子Agent开发)         │
│     │   ├── Implementer SubAgent (实现)                         │
│     │   ├── Spec Reviewer (规范审查)                            │
│     │   └── Code Quality Reviewer (质量审查)                    │
│     └── /skill test-driven-development (TDD)                     │
│                                                                 │
│  4. 代码审查阶段                                                  │
│     ├── /skill requesting-code-review (请求审查)                 │
│     ├── /skill receiving-code-review (处理反馈)                  │
│     └── /skill coding-standards (规范检查)                       │
│                                                                 │
│  5. 测试阶段                                                      │
│     ├── /skill testing-qa (测试QA)                               │
│     ├── /skill auto-test (自动测试)                              │
│     └── /skill test-validator (测试验证)                         │
│                                                                 │
│  6. 调试阶段                                                      │
│     └── /skill systematic-debugging (系统调试)                   │
│                                                                 │
│  7. 完成阶段                                                      │
│     ├── /skill finishing-a-development-branch (分支完成)         │
│     └── /skill verification-before-completion (完成验证)         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 文件式规划 (Planning with Files)

每个功能开发前必须创建三个规划文件:

#### 1. task_plan.md

```markdown
# 功能: [功能名称]

## 目标
[清晰描述功能目标]

## 阶段

### Phase 1: 需求分析
- [ ] 用户故事梳理
- [ ] 竞品对标分析
- [ ] 验收标准定义

### Phase 2: 技术设计
- [ ] API 接口设计
- [ ] 数据库模型设计
- [ ] 组件结构设计

### Phase 3: 开发实现
- [ ] 后端 API 实现
- [ ] 前端组件实现
- [ ] 集成测试

### Phase 4: 代码审查
- [ ] 规范检查
- [ ] 测试覆盖率检查
- [ ] 性能检查

### Phase 5: 部署上线
- [ ] 环境配置
- [ ] 监控配置
- [ ] 文档更新

## 依赖
- [依赖项1]
- [依赖项2]

## 风险
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| [风险1] | 高 | [措施1] |
```

#### 2. findings.md

```markdown
# 研究发现

## 技术选型
### [决策1]
- **选项**: A vs B
- **选择**: A
- **理由**: ...

## 问题记录
| 问题 | 解决方案 | 状态 |
|------|----------|------|
| [问题1] | [方案1] | 已解决 |

## 参考链接
- [链接1]
- [链接2]
```

#### 3. progress.md

```markdown
# 开发日志

## 2026-04-10
### 完成
- [x] 任务1
- [x] 任务2

### 问题
- [问题描述]

### 下一步
- [ ] 任务3
```

### SubAgent 驱动开发流程

```
┌──────────────────────────────────────────────────────────────┐
│                   SubAgent 驱动开发流程                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Controller (主 Agent)                                        │
│  ├── 读取计划文件，提取所有任务                                │
│  ├── 为每个任务创建独立 SubAgent                              │
│  └── 协调审查流程                                            │
│                                                              │
│  Task N                                                      │
│  ├── Implementer SubAgent                                    │
│  │   ├── 实现功能                                            │
│  │   ├── 编写测试                                            │
│  │   ├── 自我审查                                            │
│  │   └── 提交代码                                            │
│  │                                                           │
│  ├── Spec Reviewer SubAgent                                  │
│  │   ├── 检查是否符合规范                                    │
│  │   └── 反馈问题 → Implementer 修复                         │
│  │                                                           │
│  └── Code Quality Reviewer SubAgent                          │
│      ├── 代码质量评估                                        │
│      └── 反馈问题 → Implementer 修复                         │
│                                                              │
│  循环直到所有任务完成                                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## CI/CD 建议

### GitHub Actions 工作流

#### 1. PR 检查工作流

**`.github/workflows/pr-check.yml`:**
```yaml
name: PR Check

on:
  pull_request:
    branches: [main, develop]

jobs:
  frontend-check:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/web
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: apps/web/package-lock.json
      
      - name: Install dependencies
        run: npm ci
      
      - name: Type check
        run: npm run type-check
      
      - name: Lint
        run: npm run lint
      
      - name: Format check
        run: npm run format:check
      
      - name: Unit tests
        run: npm run test:coverage
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./apps/web/coverage/lcov.info
          flags: frontend

  backend-check:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/api
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Lint with Ruff
        run: |
          pip install ruff
          ruff check .
          ruff format --check .
      
      - name: Type check with mypy
        run: |
          pip install mypy
          mypy app
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test
          REDIS_URL: redis://localhost:6379/0
        run: pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./apps/api/coverage.xml
          flags: backend
```

#### 2. E2E 测试工作流

**`.github/workflows/e2e.yml`:**
```yaml
name: E2E Tests

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'  # 每天运行

jobs:
  e2e:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: |
          cd apps/web && npm ci
          cd ../api && pip install -r requirements.txt
      
      - name: Install Playwright
        run: |
          cd apps/web
          npx playwright install --with-deps
      
      - name: Start backend
        run: |
          cd apps/api
          python main.py &
          sleep 5
      
      - name: Run E2E tests
        run: |
          cd apps/web
          npm run test:e2e
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: apps/web/playwright-report/
```

#### 3. 部署工作流

**`.github/workflows/deploy.yml`:**
```yaml
name: Deploy

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Vercel
        uses: vercel/action-deploy@v1
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}

  deploy-backend:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Railway
        run: |
          npm install -g @railway/cli
          railway login --token ${{ secrets.RAILWAY_TOKEN }}
          railway up --service jarvis-pm-api
```

### 质量门禁

```yaml
Pipeline Stages:
  Stage 1 - 静态分析:
    - ESLint / Ruff 检查
    - Prettier / Ruff format 检查
    - TypeScript / mypy 类型检查
    - SonarQube 扫描
    
  Stage 2 - 单元测试:
    - 前端 Jest 测试
    - 后端 pytest 测试
    - 覆盖率 >= 80%
    
  Stage 3 - 集成测试:
    - API 集成测试
    - 数据库迁移测试
    - AI 服务 Mock 测试
    
  Stage 4 - E2E 测试:
    - Playwright 核心流程测试
    - 跨浏览器测试
    
  Stage 5 - 安全扫描:
    - 依赖漏洞扫描 (npm audit / pip-audit)
    - 容器镜像扫描
    - 密钥泄露检测
```

---

## Git 工作流规范

### 分支策略: GitHub Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    main     │────→│  feature/*  │────→│    main     │
│   (生产)     │     │  (开发分支)  │     │   (生产)     │
└─────────────┘     └─────────────┘     └─────────────┘
       ↑                                       │
       └───────────────────────────────────────┘
                    PR + Code Review
```

### 分支命名规范

| 类型 | 命名格式 | 示例 |
|------|----------|------|
| 功能 | `feature/[issue-id]-描述` | `feature/123-add-auth` |
| 修复 | `fix/[issue-id]-描述` | `fix/456-login-bug` |
| 热修复 | `hotfix/描述` | `hotfix/critical-security` |
| 重构 | `refactor/描述` | `refactor/api-structure` |
| 文档 | `docs/描述` | `docs/api-guide` |

### Commit 规范 (Conventional Commits)

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型:**

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式调整 |
| `refactor` | 重构 |
| `test` | 测试相关 |
| `chore` | 构建/工具相关 |
| `perf` | 性能优化 |

**示例:**
```bash
feat(auth): add JWT authentication

- Implement login endpoint
- Add token refresh mechanism
- Add auth middleware

Closes #123

fix(api): resolve PRD creation error

test(prd): add unit tests for PRD service
docs(readme): update setup instructions
```

### Git Worktree 使用规范

**开发新功能前必须创建隔离工作区:**

```bash
# 1. 创建 worktree (使用 skill: using-git-worktrees)
git worktree add .worktrees/feature-auth -b feature/123-add-auth
cd .worktrees/feature-auth

# 2. 安装依赖并验证基线
npm install  # 或 pip install -r requirements.txt
npm test     # 验证测试通过

# 3. 开始开发
# ... 开发代码 ...

# 4. 提交代码
git add .
git commit -m "feat(auth): add JWT authentication"

# 5. 推送并创建 PR
git push origin feature/123-add-auth
gh pr create --title "feat: add JWT authentication" --body "..."

# 6. 合并后清理
cd ../..
git worktree remove .worktrees/feature-auth
git branch -d feature/123-add-auth
```

### .gitignore 配置

**根目录 `.gitignore`:**
```gitignore
# Dependencies
node_modules/
__pycache__/
*.pyc
venv/
.env

# Build outputs
.next/
dist/
build/
*.egg-info/

# Testing
coverage/
.nyc_output/
.pytest_cache/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Worktrees
.worktrees/
worktrees/

# Logs
*.log
logs/

# Database
*.db
*.sqlite

# Temporary files
*.tmp
.temp/
```

---

## Code Review 指南

### 审查清单

#### 1. 功能正确性
- [ ] 代码实现了需求描述的功能
- [ ] 边界条件处理正确
- [ ] 错误处理完善
- [ ] 无明显的逻辑错误

#### 2. 代码质量
- [ ] 遵循项目代码规范
- [ ] 命名清晰有意义
- [ ] 函数/组件职责单一
- [ ] 无重复代码 (DRY)
- [ ] 无死代码

#### 3. 测试
- [ ] 新增功能有对应的单元测试
- [ ] 测试覆盖关键路径
- [ ] 测试用例有意义
- [ ] 所有测试通过

#### 4. 安全性
- [ ] 无硬编码密钥
- [ ] 输入验证完善
- [ ] 无 SQL 注入风险
- [ ] 无 XSS 风险
- [ ] 敏感数据正确处理

#### 5. 性能
- [ ] 无明显的性能问题
- [ ] 大数据量处理考虑
- [ ] 不必要的重渲染避免 (React)

#### 6. 文档
- [ ] 复杂逻辑有注释
- [ ] 公共 API 有文档
- [ ] README 更新 (如需要)

### 审查流程 (使用 Skill: requesting-code-review)

```
┌─────────────────────────────────────────────────────────────┐
│                     Code Review 流程                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 准备阶段                                                 │
│     ├── 确保所有测试通过                                     │
│     ├── 自我审查 (使用 checklist)                            │
│     └── 准备审查说明                                         │
│                                                             │
│  2. 发起审查                                                 │
│     ├── 使用 Skill: requesting-code-review                   │
│     ├── 提供上下文: 做了什么、为什么                         │
│     └── 指定审查重点                                         │
│                                                             │
│  3. 处理反馈                                                 │
│     ├── 使用 Skill: receiving-code-review                    │
│     ├── 分类: Critical / Important / Minor                   │
│     ├── Critical: 必须修复                                   │
│     ├── Important: 建议修复                                  │
│     └── Minor: 可选                                          │
│                                                             │
│  4. 修复验证                                                 │
│     ├── 修复问题                                             │
│     ├── 重新测试                                             │
│     └── 更新 PR                                              │
│                                                             │
│  5. 合并                                                     │
│     ├── 获得批准                                             │
│     ├── 合并到 main                                          │
│     └── 清理工作区                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 审查反馈分类

| 级别 | 说明 | 处理方式 |
|------|------|----------|
| **Critical** | 阻塞性问题 (安全漏洞、功能错误) | 必须修复 |
| **Important** | 重要问题 (性能、可维护性) | 建议修复 |
| **Minor** | 小问题 (命名、格式) | 可选修复 |
| **Nit** | 个人偏好 | 可讨论 |

### 审查模板

```markdown
## Code Review

### 总结
[简要总结 PR 内容]

### 发现的问题

#### Critical
- [ ] [问题描述] - [位置]

#### Important
- [ ] [问题描述] - [位置]

#### Minor
- [ ] [问题描述] - [位置]

### 建议
[可选改进建议]

### 批准状态
- [ ] 批准 (Approved)
- [ ] 需要修改 (Request Changes)
- [ ] 评论 (Comment)
```

---

## 实施路线图

### Phase 1: 基础搭建 (第 1-2 周)

| 任务 | 优先级 | 负责人 | 状态 |
|------|--------|--------|------|
| 配置前端测试环境 (Jest + RTL) | P0 | - | 待开始 |
| 配置后端测试环境增强 | P0 | - | 待开始 |
| 配置 ESLint + Prettier | P0 | - | 待开始 |
| 配置 Ruff + mypy | P0 | - | 待开始 |
| 创建测试基线 | P1 | - | 待开始 |

### Phase 2: CI/CD 搭建 (第 2-3 周)

| 任务 | 优先级 | 负责人 | 状态 |
|------|--------|--------|------|
| 配置 GitHub Actions PR 检查 | P0 | - | 待开始 |
| 配置代码覆盖率报告 | P1 | - | 待开始 |
| 配置 E2E 测试流水线 | P1 | - | 待开始 |
| 配置自动部署 | P2 | - | 待开始 |

### Phase 3: 流程落地 (第 3-4 周)

| 任务 | 优先级 | 负责人 | 状态 |
|------|--------|--------|------|
| 团队培训 (Skills 使用) | P0 | - | 待开始 |
| Code Review 指南落地 | P0 | - | 待开始 |
| Git Worktree 流程推广 | P1 | - | 待开始 |
| 文档完善 | P1 | - | 待开始 |

### Phase 4: 持续优化 (持续)

| 任务 | 优先级 | 频率 |
|------|--------|------|
| 测试覆盖率监控 | P1 | 每周 |
| 代码质量报告 | P1 | 每周 |
| 流程回顾改进 | P2 | 每月 |
| Skill 更新维护 | P2 | 每季度 |

---

## 附录

### A. 推荐的 VS Code 配置

**`.vscode/settings.json`:**
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit"
  },
  "typescript.preferences.importModuleSpecifier": "non-relative",
  "python.formatting.provider": "ruff",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
}
```

**`.vscode/extensions.json`:**
```json
{
  "recommendations": [
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "bradlc.vscode-tailwindcss",
    "ms-playwright.playwright"
  ]
}
```

### B. 常用命令速查

```bash
# 前端
npm run dev          # 开发服务器
npm run build        # 生产构建
npm run test         # 运行测试
npm run test:watch   # 监听模式测试
npm run lint         # 代码检查
npm run lint:fix     # 自动修复
npm run format       # 格式化代码

# 后端
python main.py       # 启动服务
pytest               # 运行测试
pytest --cov=app     # 带覆盖率测试
ruff check .         # 代码检查
ruff format .        # 格式化
mypy app             # 类型检查

# Git
git worktree add .worktrees/feat-name -b feature/name
git worktree remove .worktrees/feat-name
```

### C. 参考资源

- [Testing Skill](https://github.com/affaan-m/everything-claude-code) - 测试标准
- [Claude Skills](https://github.com/jessezhang/awesome-claude-skills) - Skills 集合
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/) - FastAPI 测试指南
- [Next.js Testing](https://nextjs.org/docs/app/building-your-application/testing) - Next.js 测试文档
- [Playwright](https://playwright.dev/) - E2E 测试框架

---

*文档版本: 1.0*  
*生成日期: 2026-04-10*  
*维护者: Jarvis PM Team*
