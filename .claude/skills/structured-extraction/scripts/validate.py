#!/usr/bin/env python3
"""抽出結果(JSON)をスキーマ(JSON Schema のサブセット)で検証し、必要なら CSV に書き出す。

Python 標準ライブラリのみで動作する。対応キーワード:
  type (単一 or 配列, "null" 可), required, properties, items, enum, format: date

使い方:
  python validate.py --schema schema.json --data output.json
  python validate.py --schema schema.json --data output.json --csv output.csv
  python validate.py --schema schema.json --data output.json --csv output.csv --labels  # 日本語見出し

data はオブジェクト1件、またはオブジェクトの配列(複数ファイル分)を受け付ける。
終了コード: 0 = 問題なし / 1 = 検証エラーあり / 2 = 入力ファイルの読み込み失敗
"""
import argparse
import csv
import json
import re
import sys

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def validate(value, schema, path, errors):
    types = schema.get("type")
    if types is not None:
        types = types if isinstance(types, list) else [types]
        if not any(TYPE_CHECKS.get(t, lambda v: True)(value) for t in types):
            hint = ""
            if isinstance(value, str) and "number" in types:
                hint = "（数値は文字列ではなく数値型で。カンマ・円記号を外す）"
            errors.append(f"{path}: 型が {'/'.join(types)} ではありません: {value!r}{hint}")
            return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: 許可されていない値 {value!r}（候補: {schema['enum']}）")
    if schema.get("format") == "date" and isinstance(value, str) and not DATE_RE.match(value):
        errors.append(f"{path}: 日付は YYYY-MM-DD 形式にしてください: {value!r}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: 必須項目 '{key}' がありません（不明なら null を入れる）")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                validate(value[key], sub, f"{path}.{key}", errors)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{i}]", errors)


def table_keys(records):
    """オブジェクトの配列になっている項目（=明細表）を列挙する。"""
    keys = []
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v) and k not in keys:
                keys.append(k)
    return keys


def cell(v):
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        if isinstance(v, list) and all(not isinstance(x, (dict, list)) for x in v):
            return "; ".join("" if x is None else str(x) for x in v)
        return json.dumps(v, ensure_ascii=False)
    return v


def rows_for(records, tables, expand):
    """共通項目 + 明細表1つ分の行を作る。expand が None なら共通項目のみ1レコード1行。"""
    rows = []
    for rec in records:
        base = {}
        for k, v in rec.items():
            # 明細表・注記(_notes 等)は行ごとに繰り返すと読みにくいので CSV には入れない（注記は会話で報告する）
            if k in tables or k.startswith("_"):
                continue
            # 明細を展開するときは、出席者などのリスト項目も全行に重複するため省く
            if expand and isinstance(v, list):
                continue
            if isinstance(v, dict):
                for sk, sv in v.items():
                    base[f"{k}.{sk}"] = cell(sv)
            else:
                base[k] = cell(v)
        items = rec.get(expand) if expand else None
        if not items:
            rows.append(base)
            continue
        for item in items:
            row = dict(base)
            for sk, sv in item.items():
                row[f"{expand}.{sk}"] = cell(sv)
            rows.append(row)
    return rows


def schema_labels(schema, prefix=""):
    """スキーマの description 先頭語を列見出しの日本語ラベルにする（例: '開催日 YYYY-MM-DD' -> '開催日'）。"""
    labels = {}
    for k, sub in schema.get("properties", {}).items():
        key = f"{prefix}{k}"
        desc = sub.get("description")
        if desc:
            labels[key] = desc.split()[0]
        if "items" in sub and isinstance(sub["items"], dict):
            labels.update(schema_labels(sub["items"], f"{key}."))
        if sub.get("properties"):
            labels.update(schema_labels(sub, f"{key}."))
    return labels


def write_rows(rows, path, labels=None):
    headers = []
    for r in rows:
        for k in r:
            if k not in headers:
                headers.append(k)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # BOM付き: Excelで文字化けしない
        w = csv.writer(f)
        w.writerow([(labels or {}).get(h, h) for h in headers])
        for r in rows:
            w.writerow([r.get(k, "") for k in headers])


def write_csv(records, path, labels=None):
    """明細表が0〜1個なら1ファイル。2個以上なら表ごとに <名前>_<表名>.csv に分ける。"""
    tables = table_keys(records)
    if len(tables) <= 1:
        rows = rows_for(records, tables, tables[0] if tables else None)
        write_rows(rows, path, labels)
        return [(path, len(rows))]
    stem = path[:-4] if path.lower().endswith(".csv") else path
    out = []
    for t in tables:
        rows = rows_for(records, tables, t)
        p = f"{stem}_{t}.csv"
        write_rows(rows, p, labels)
        out.append((p, len(rows)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--csv", help="CSV の出力先（任意）")
    ap.add_argument("--labels", action="store_true", help="CSV の列見出しをスキーマの description による日本語ラベルにする")
    args = ap.parse_args()
    try:
        with open(args.schema, encoding="utf-8") as f:
            schema = json.load(f)
        with open(args.data, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"読み込みエラー: {e}", file=sys.stderr)
        return 2

    records = data if isinstance(data, list) else [data]
    errors = []
    for i, rec in enumerate(records):
        validate(rec, schema, f"$[{i}]" if isinstance(data, list) else "$", errors)

    null_fields = sorted({k for rec in records if isinstance(rec, dict) for k, v in rec.items() if v is None})
    if errors:
        print(f"NG: {len(errors)} 件のエラー")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"OK: {len(records)} 件のレコードがスキーマに適合")
    if null_fields:
        print(f"null の項目（記載なし/判読不可）: {', '.join(null_fields)}")
    if args.csv and not errors:
        for p, n in write_csv(records, args.csv, schema_labels(schema) if args.labels else None):
            print(f"CSV 出力: {p}（{n} 行）")
    elif args.csv:
        print("エラーがあるため CSV は出力していません")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
