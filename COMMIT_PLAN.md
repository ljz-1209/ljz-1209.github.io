# Git 提交计划（≥ 3 次 commit，证明作品是一步步做出来的）

> ✅ **本计划已于 2026-10-04 执行完毕**：4 个里程碑提交已推送到
> `ljz-1209.github.io`，仓库连同此前的历史共 15 个提交（满足"不少于 3 次"）。
> 以下保留执行过程，作为"一步步做出来"的记录。

你的 GitHub 上已经有 `ljz-1209.github.io` 仓库（11 个提交，Pages 已开启）。
**本计划把本次考核的全部作品推进这个已有仓库**——不用新建仓库，网址就是
`https://ljz-1209.github.io/`，推送后 Pages 会自动更新。

> 注意：本地这个文件夹是全新的 git 仓库，而远端已有自己的提交历史，
> 直接 push 会被拒绝。按下面第 0 步把远端历史"接"过来即可。

## 推送步骤（在仓库根目录依次执行）

```bash
# 0) 接上远端仓库并借用它的历史（工作区文件不会被动）
git remote add origin https://github.com/ljz-1209/ljz-1209.github.io.git
git fetch origin
git reset --soft origin/main
# 此时 origin 的 11 个提交成为本地历史，你的新文件全部是"待提交"状态

# 1) 里程碑一：作品集骨架（README / LICENSE / 提交计划 / .gitignore）
git add LICENSE .gitignore README.md COMMIT_PLAN.md
git commit -m "docs: 考核作品集 README——素养说明、提示词记录、手算vs仿真对比"

# 2) 里程碑二：个人主页 + 个人简介 PDF（同时覆盖线上带冲突标记的旧主页）
git add index.html style.css 个人简介/
git commit -m "feat: 个人主页改版（作品展示区+深色模式）与修正后的个人简介 PDF"

# 3) 里程碑三：贪吃蛇（阶段一+阶段二 AI）与验证截图
git add games/ assets/
git commit -m "feat: 贪吃蛇 AI 版——BFS+安全模拟自动演示，计分/主题/战绩三功能"

# 4) 里程碑四：PySpice 三个电路
git add pyspice/
git commit -m "feat: PySpice 三个电路仿真——RC滤波/戴维南验证/NMOS共源放大"

# 5) 推送（浏览器会弹出 GitHub 登录/授权，本人完成）
git push -u origin main
```

推完等一两分钟，刷新 https://ljz-1209.github.io/ —— 看到带"我的作品"的新主页
就成功了；贪吃蛇在 `/games/snake.html`。

## 说明

- 每次 commit 前可以用 `git status` 查看将提交的文件，用 `git log --oneline` 回顾历史。
- `pyspice/plots/`、`pyspice/circuits/`、`pyspice/results/` 是仿真生成的图片和数据，
  一并提交，评审点开网页就能看到。
- 如果你更想单独建一个新仓库（如 freshman-2026）：把上面第 0 步换成
  在 GitHub 网页新建空仓库，再 `git remote add origin <新仓库地址>` 后直接 push，
  然后到该仓库 Settings → Pages 里开启（main 分支 /root），
  并把 README 和主页里两处链接改回新仓库地址。
