# GitHub Workspace Guide

このリポジトリは、案件別リポジトリ運用の共通入口です。案件本体は格納しません。

## 基本方針

- 1案件 = 1リポジトリ
- 通常作業は ChatGPT Chat を基本とする
- Codex は大規模コード実装・横断修正など、ChatGPT Chat では非効率な場合に利用する
- Claude Code は Windows / ローカル実行 / 環境依存検証 / 大量実行など、実機作業が必要な場合に利用する
- AI間の連携は GitHub 上の要求、設計、差分、Pull Request、検証結果を介して行う
- 会話全文をAI間で引き継がない
- 案件リポジトリは main を正本、work/<task> を作業ブランチとする

詳細ルールは `docs/AI_WORKFLOW.md` を参照してください。
