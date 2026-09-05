# 从“看懂 GitHub”到“完成第一次协作”

完成这篇教程后，你会理解 Git 和 GitHub 的区别，并只用网页完成一次“创建分支 → 修改文件 → 发起 Pull Request → 合并”的协作流程。

## 一、初步认知

### 1、GitHub 是干什么的？

一句话解释：

GitHub 是一个用于保存项目、查看修改历史、多人协作和分享成果的平台。

可以把它理解为：

```text
网盘 + 版本历史 + 项目管理 + 团队协作 + 技术社区
```

### 2、Git、GitHub 和仓库有什么区别？

| 名称 | 简单理解 |
| --- | --- |
| Git | 记录文件修改历史的工具 |
| GitHub | 在线保存和协作的平台 |
| Repository | 一个带版本历史的项目文件夹 |

## 二、四个常见操作

```text
Star = 收藏
Fork = 在线复制一份
Clone = 完整下载到电脑
Download ZIP = 下载当前文件
```

如果只是收藏项目，用 Star；只想拿到当前文件，用 Download ZIP；准备长期修改或同步更新时，再使用 Clone。

## 三、只用网页完成第一次协作

### 1、创建仓库

登录 GitHub，选择 `New repository`，仓库名填写 `hello-world`，勾选创建 `README.md`。

完成后，你会看到仓库首页和 README 内容。

### 2、创建分支

打开分支菜单，以 `main` 为基础创建 `readme-edits`。

分支可以理解为一条独立修改路线。此时 `main` 仍保持原样。

### 3、修改并提交

在 `readme-edits` 分支编辑 `README.md`，加入一句自我介绍，然后填写提交说明：

```text
Add personal introduction
```

点击提交后，修改只存在于 `readme-edits` 分支。

### 4、创建 Pull Request

进入 `Pull requests`，比较：

```text
base: main ← compare: readme-edits
```

确认差异只包含刚才的 README 修改，再创建 Pull Request。Pull Request 可以理解为：“我已经完成修改，请检查后决定是否合并。”

### 5、合并

检查无误后选择 `Merge pull request` 并确认。回到 `main`，应该能看到刚才新增的自我介绍。

如果看不到，先检查当前显示的分支是不是 `main`，以及 Pull Request 是否已经显示为 `Merged`。

## 四、让 AI 帮你准备项目

```text
帮我创建一个 GitHub 新手项目：

名称：my-first-project
用途：记录学习笔记
包含：README.md、notes 文件夹

先创建本地内容，不要上传。发布前检查密码、Token 和隐私信息，并等我确认。
```

AI 可以帮你准备文件、解释差异和检查风险，但公开仓库、合并修改、删除内容等动作仍应由你确认。

## 五、最终记住四句话

1. Git 管理版本，GitHub 保存和协作。
2. README 是了解项目的第一入口。
3. Star 是收藏，Fork 是在线复制，Clone 是完整下载。
4. 分支负责隔离修改，Pull Request 负责检查和合并修改。
