# GitHub 推送文件指南

## 1. 推送原则

本项目推送到 GitHub 时，只提交项目运行所需的核心代码和必要配置文件，不提交个人环境文件、虚拟环境、临时文件、技能文件、计划文档或实验过程文档。

GitHub 仓库应主要包含：

* 后端核心代码
* 前端核心代码
* 必要的配置文件
* 必要的依赖说明文件
* 必要的 README 说明
* 示例配置文件

不应包含：

* Python 虚拟环境
* Node.js 依赖目录
* agent skill 文件
* 临时计划文档
* 本地测试输出
* 大型仿真结果文件
* 日志文件
* API key、token、账号密码等敏感信息

## 2. 建议提交的核心文件

通常可以提交以下内容：

```text
autosim/
frontend/
model_registry/
requirements.txt
pyproject.toml
package.json
package-lock.json
README.md
.gitignore
```

如果项目中有后端和前端分离结构，应提交：

```text
backend source code
frontend source code
API schema
model registry descriptors
必要的 mock data
必要的示例配置文件
```

如果需要提供环境变量示例，可以提交：

```text
.env.example
```

但不要提交真实的：

```text
.env
```

## 3. 不要提交的文件

以下内容不要 push 到 GitHub：

```text
.venv/
venv/
env/
__pycache__/
.pytest_cache/
node_modules/
dist/
build/
.DS_Store
*.log
*.tmp
*.cache
.env
```

同时不要提交以下项目辅助文件：

```text
skills/
agent-skills/
docs/agent-skills/
*_plan.md
*_draft.md
project_plan.md
agent_native_simulation_plan.md
```

如果这些文件只是用于和 AI agent 沟通、项目规划、临时设计说明或个人实验记录，不应作为核心代码提交。

## 4. 推荐的 `.gitignore`

可以在项目根目录创建或更新 `.gitignore`：

```gitignore
# Python virtual environments
.venv/
venv/
env/

# Python cache
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node dependencies
node_modules/

# Frontend build outputs
dist/
build/

# Environment variables and secrets
.env
.env.local
.env.*.local

# Logs and temporary files
*.log
*.tmp
*.cache

# OS files
.DS_Store
Thumbs.db

# IDE files
.vscode/
.idea/

# Agent / skill files
skills/
agent-skills/
docs/agent-skills/

# Planning and temporary markdown files
*_plan.md
*_draft.md
project_plan.md
agent_native_simulation_plan.md

# Simulation outputs
outputs/
results/
runs/
checkpoints/
```

如果某些 markdown 文件是正式文档，例如 `README.md`、`API.md`、`CONTRIBUTING.md`，可以保留提交。

## 5. 首次推送流程

在项目根目录执行：

```bash
git init
git status
```

先检查当前有哪些文件会被 Git 追踪。

添加核心代码：

```bash
git add autosim frontend model_registry README.md .gitignore
```

如果有依赖文件，也一起添加：

```bash
git add requirements.txt pyproject.toml package.json package-lock.json
```

提交：

```bash
git commit -m "Initial commit: core simulation platform"
```

关联远程仓库：

```bash
git remote add origin <your-github-repo-url>
```

推送到 GitHub：

```bash
git branch -M main
git push -u origin main
```

## 6. 每次推送前检查

每次 push 前都建议执行：

```bash
git status
```

确认没有误提交以下内容：

```text
.venv/
node_modules/
skills/
*.log
.env
计划文档
临时 markdown
大型仿真结果
```

可以使用：

```bash
git diff --staged
```

检查已经加入暂存区的内容是否正确。

如果误添加了不该提交的文件，可以取消暂存：

```bash
git restore --staged <file_or_folder>
```

例如：

```bash
git restore --staged skills/
git restore --staged .venv/
git restore --staged agent_native_simulation_plan.md
```

## 7. 已经误提交怎么办

如果只是加入暂存区，还没 commit：

```bash
git restore --staged <file_or_folder>
```

如果已经 commit，但还没 push，可以从 Git 中移除但保留本地文件：

```bash
git rm --cached -r <file_or_folder>
git commit -m "Remove non-core files from repository"
```

例如：

```bash
git rm --cached -r .venv
git rm --cached -r skills
git rm --cached agent_native_simulation_plan.md
git commit
```
