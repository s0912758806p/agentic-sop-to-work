# agentic-sop-to-work — Claude Code plugin marketplace

一個 **Claude Code plugin marketplace**，透過 GitHub 發佈 `agentic-sop-kit` plugin，讓任何人用 `/plugin install` 一鍵安裝。

## 安裝（任何人，從 GitHub）
在 Claude Code（含 Claude Desktop 的 **Code 分頁**）執行：
```
/plugin marketplace add s0912758806p/agentic-sop-to-work
/plugin install agentic-sop-kit@agentic-sop-to-work
/reload-plugins      # 或重開 session
```
> 也可用完整網址：`/plugin marketplace add https://github.com/s0912758806p/agentic-sop-to-work`

驗證：`/help` 應看到 `/agentic-sop-kit:sop-flow`；兩支 skill（`agentic-sop`、`agentic-workflow-audit`）會依描述自動觸發。

## 內含 plugin
| Plugin | 說明 |
|--------|------|
| `agentic-sop-kit` | 方法論 skills（agentic-sop、agentic-workflow-audit）＋ `/sop-flow` 指令＋專案範圍 Stop-hook 回歸閘門＋可攜 kit。詳見 [`plugins/agentic-sop-kit/README.md`](plugins/agentic-sop-kit/README.md)。 |

## 結構
```
agentic-sop-to-work/
├── .claude-plugin/marketplace.json     # 目錄清單（marketplace 名稱 = agentic-sop-to-work）
└── plugins/
    └── agentic-sop-kit/                 # plugin（source: "./plugins/agentic-sop-kit"）
        ├── .claude-plugin/plugin.json
        ├── skills/{agentic-sop,agentic-workflow-audit}/SKILL.md
        ├── commands/sop-flow.md
        ├── hooks/{hooks.json,stop_gate.py,session_check.py}
        └── kit/                         # 內附的 agentic-sop-kit 副本
```

## 更新
改完 plugin 內容後 `git push`；使用者端執行 `/plugin marketplace update agentic-sop-to-work` 取得最新版（或移除後重加）。記得在每次有意義的變更時調高 `plugins/agentic-sop-kit/.claude-plugin/plugin.json` 的 `version`。
