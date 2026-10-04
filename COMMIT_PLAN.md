# Git 提交计划（≥ 3 次 commit，证明作品是一步步做出来的）

> 已于 2026-10-04 执行完毕，本次作品分 6 批提交，连同更早的仓库历史全部保留在提交记录里。

作品提交到 `ljz-1209.github.io` 仓库——它同时就是 GitHub Pages 的来源，推送后网站自动更新。

## 实际步骤

```bash
# 0) 本地是新建的仓库，先接上远端历史（不然 push 会被拒绝）
git remote add origin https://github.com/ljz-1209/ljz-1209.github.io.git
git fetch origin
git reset --soft origin/main

# 1) README、LICENSE、提交计划
git add LICENSE .gitignore README.md COMMIT_PLAN.md
git commit -m "添加 README、LICENSE 和提交计划"

# 2) 个人主页改版 + 修正用户名后的简介 PDF
git add index.html style.css 个人简介/
git commit -m "改版个人主页，修正简介 PDF 里的用户名"

# 3) 贪吃蛇（AI 自动演示）和验证截图
git add games/ assets/
git commit -m "贪吃蛇加上 AI 自动演示、计分、主题和战绩"

# 4) PySpice 三个电路
git add pyspice/
git commit -m "PySpice 仿真三个电路：RC 滤波、戴维南、NMOS 放大"

# 5) 推送
git push -u origin main
```

## 说明

- 提交前用 `git status` 看要提交什么，用 `git log --oneline` 回顾历史。
- pyspice 的图片和数据一起提交，评审在网页上就能直接看到。
- 这台电脑的 git 全局配了代理（127.0.0.1:7890），代理软件没开时 push 会失败，
  可以临时用 `git -c http.proxy= -c https.proxy= push` 绕开。
