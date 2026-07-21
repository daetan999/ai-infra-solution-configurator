```markdown
# ai-infra-solution-configurator Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns, coding conventions, and collaborative workflows used in the `ai-infra-solution-configurator` Python codebase. You'll learn how to implement, test, document, and maintain features in a structured, team-friendly way, following conventions that support clarity, reliability, and traceability.

## Coding Conventions

**File Naming**
- Use `camelCase` for file names (e.g., `engineCore.py`, `configuratorEngine.py`).

**Imports**
- Prefer **relative imports** within the package.
  ```python
  from .rules import RuleEngine
  from .engine import Engine
  ```

**Exports**
- Use **named exports** (explicitly define what is exported from a module).
  ```python
  # In app/exports.py
  __all__ = ["Engine", "RuleEngine"]
  ```

**Commit Messages**
- Follow **Conventional Commits**:
  - Prefixes: `feat`, `fix`, `test`, `docs`, `style`, `refactor`, `chore`
  - Example: `feat(engine): add support for custom rule sets`

## Workflows

### Implement or Update Core Feature with Tests
**Trigger:** When adding or modifying a core feature (engine, rules, API, diagram, etc.), ensuring it is tested.  
**Command:** `/implement-feature-with-tests`

1. Edit or create feature files in `app/` (e.g., `engine.py`, `rules.py`, `architecture.py`, `diagram.py`).
2. Edit or create corresponding test files in `tests/` (e.g., `test_engine.py`, `test_rules.py`).
3. Ensure new or updated features are covered by tests.
4. Commit with a descriptive message:
   ```
   feat(engine): add new dependency resolution logic
   ```
5. Run tests to verify correctness.

**Example:**
```python
# app/engine.py
class Engine:
    def run(self):
        pass

# tests/test_engine.py
from app.engine import Engine

def test_engine_runs():
    engine = Engine()
    assert engine.run() is None
```

---

### Document Feature or Verification Evidence
**Trigger:** When documenting a new feature, test evidence, or architectural change.  
**Command:** `/add-doc-evidence`

1. Edit or create markdown docs in `docs/` (e.g., `docs/testing/*.md`, `docs/architecture.md`).
2. Optionally add/update assets in `docs/assets/`.
3. Optionally update `README.md`.
4. Commit with a message like:
   ```
   docs(architecture): update diagram for new workflow
   ```

**Example:**
```markdown
# docs/architecture.md

## New Workflow Diagram
![Workflow](assets/configuration-workflow.svg)
```

---

### Fix or Harden Existing Feature
**Trigger:** When fixing a bug, closing an audit gap, or improving robustness.  
**Command:** `/fix-feature`

1. Edit files in `app/` (e.g., `rules.py`, `engine.py`).
2. Optionally update related test files in `tests/`.
3. Optionally update UI files in `static/` or `templates/`.
4. Commit with a message like:
   ```
   fix(rules): handle edge case for empty input
   ```

**Example:**
```python
# app/rules.py
def validate_rule(rule):
    if not rule:
        return False
    # existing logic...
```

---

### Update or Add Interface Assets and Contract Tests
**Trigger:** When changing the frontend interface or its contract.  
**Command:** `/update-interface`

1. Edit or add files in `static/` (e.g., `app.js`, `styles.css`).
2. Edit or add files in `templates/` (e.g., `index.html`).
3. Edit or add interface contract tests in `tests/test_interface_contract.py`.
4. Optionally update UI diagrams in `docs/assets/`.
5. Commit with a message like:
   ```
   feat(ui): update workflow CSS for new steps
   ```

**Example:**
```javascript
// static/app.js
document.getElementById('run-btn').onclick = () => {
    // trigger backend
};
```
```python
# tests/test_interface_contract.py
def test_ui_contract():
    # test frontend-backend contract
    pass
```

---

### Add or Update End-to-End Browser Tests
**Trigger:** When automating browser journeys or updating E2E test coverage.  
**Command:** `/add-e2e-tests`

1. Edit or add tests in `tests/e2e/` (e.g., `configurator.spec.mjs`).
2. Edit or add Playwright config (`playwright.config.mjs`).
3. Update `package.json` and `package-lock.json` if dependencies change.
4. Optionally update CI workflow (`.github/workflows/ci.yml`), `Makefile`, or `.gitignore`.
5. Optionally update documentation (`docs/testing/browser-qa.md`).
6. Commit with a message like:
   ```
   test(e2e): add test for multi-step configuration
   ```

**Example:**
```js
// tests/e2e/configurator.spec.mjs
import { test, expect } from '@playwright/test';

test('can complete configuration', async ({ page }) => {
    await page.goto('/');
    await page.click('#start-btn');
    expect(await page.textContent('#status')).toBe('Complete');
});
```

## Testing Patterns

- **Test files** are named as `test_*.py` and placed in the `tests/` directory.
- Tests cover both unit and integration scenarios.
- E2E/browser tests are placed in `tests/e2e/` using Playwright (`*.spec.mjs`).
- Test assertions use standard Python `assert` or the testing framework's facilities.

**Example:**
```python
# tests/test_rules.py
from app.rules import validate_rule

def test_validate_rule_empty():
    assert not validate_rule(None)
```

## Commands

| Command                    | Purpose                                                        |
|----------------------------|----------------------------------------------------------------|
| /implement-feature-with-tests | Implement or update a core feature with corresponding tests     |
| /add-doc-evidence          | Add or update documentation and verification evidence           |
| /fix-feature               | Fix or harden an existing feature, with optional test updates   |
| /update-interface          | Update or add UI assets and interface contract tests            |
| /add-e2e-tests             | Add or update end-to-end browser tests and supporting configs   |
```
