将 JSONL（每行一个 JSON 对象）转换为 CSV，核心思路是：**逐行读取 JSONL 中的每个 JSON 对象 → 提取所有字段作为 CSV 表头 → 逐行将 JSON 数据映射为 CSV 行数据**。

推荐 3 种实用方法（覆盖不同场景：小白友好、编程灵活、批量高效），你可根据自身情况选择：


### 一、方法1：在线工具（小白首选，无需编程）
适合 JSONL 文件小（<100MB）、字段简单的场景，无需安装任何软件。

#### 推荐工具：
1. **Convertio**（https://convertio.co/jsonl-csv/）
2. **JSON Lines to CSV Converter**（https://jsonlines-csv-converter.herokuapp.com/）
3. **AnyConv**（https://anyconv.com/jsonl-to-csv-converter/）

#### 操作步骤（以 Convertio 为例）：
1. 打开网站，点击「选择文件」，上传你的 JSONL 文件；
2. 确认目标格式为「CSV」，无需额外设置（工具会自动识别 JSON 字段）；
3. 点击「转换」，完成后下载 CSV 文件即可。

⚠️ 注意：敏感数据（如隐私、涉密信息）不建议用在线工具，优先选择本地方法。


### 二、方法2：Python 脚本（灵活可控，支持大文件/自定义字段）
适合需要自定义 CSV 表头、处理复杂 JSON 结构（如嵌套字段）、或处理大文件的场景。

#### 前提：
已安装 Python（3.6+），无需额外装库（用内置 `json` 和 `csv` 模块）。

#### 脚本1：基础版（自动识别所有字段，适合平级 JSON）
假设你的 JSONL 文件（`data.jsonl`）内容如下（平级字段，无嵌套）：
```json
{"id": 1, "name": "张三", "age": 25, "city": "北京"}
{"id": 2, "name": "李四", "age": 30, "city": "上海"}
{"id": 3, "name": "王五", "age": 28}  // 部分字段缺失也能兼容
```

运行以下脚本，会生成 `output.csv`：
```python
import json
import csv

# 1. 读取 JSONL 文件，收集所有字段（避免部分行缺失字段）
jsonl_file = "data.jsonl"  # 你的 JSONL 文件路径
csv_file = "output.csv"    # 输出 CSV 路径
all_fields = set()
data_list = []

# 第一次读取：收集所有可能的字段
with open(jsonl_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        data_list.append(data)
        all_fields.update(data.keys())  # 收集字段名

# 2. 字段排序（可选，让表头顺序固定）
header = sorted(all_fields)

# 3. 写入 CSV 文件
with open(csv_file, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=header)
    writer.writeheader()  # 写入表头
    writer.writerows(data_list)  # 写入所有数据

print(f"转换完成！CSV 文件已保存到：{csv_file}")
```

#### 脚本2：进阶版（处理嵌套 JSON 字段）
如果 JSONL 有嵌套结构（如下），需要手动指定字段提取规则：
```json
{"id": 1, "name": "张三", "info": {"age": 25, "city": "北京"}}
{"id": 2, "name": "李四", "info": {"age": 30, "city": "上海"}}
```

修改脚本，提取嵌套字段（如 `info.age` → 转为 CSV 列 `age`）：
```python
import json
import csv

jsonl_file = "data.jsonl"
csv_file = "output.csv"
header = ["id", "name", "age", "city"]  # 自定义 CSV 表头
data_list = []

with open(jsonl_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        # 提取嵌套字段，缺失字段填空字符串
        csv_row = {
            "id": data.get("id", ""),
            "name": data.get("name", ""),
            "age": data.get("info", {}).get("age", ""),  # 嵌套提取
            "city": data.get("info", {}).get("city", "")
        }
        data_list.append(csv_row)

# 写入 CSV
with open(csv_file, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=header)
    writer.writeheader()
    writer.writerows(data_list)

print("嵌套 JSONL 转换完成！")
```

#### 运行方式：
1. 把脚本保存为 `jsonl_to_csv.py`；
2. 把 JSONL 文件和脚本放在同一文件夹；
3. 打开终端，进入该文件夹，执行：
   ```bash
   python jsonl_to_csv.py
   ```


### 三、方法3：用 `pandas` 库（批量处理，适合数据分析场景）
如果经常处理数据，可安装 `pandas` 库，一行代码完成转换，效率更高。

#### 步骤：
1. 安装 `pandas`：
   ```bash
   pip install pandas
   ```

2. 运行代码：
   ```python
   import pandas as pd

   # 读取 JSONL 文件（自动解析每行 JSON）
   df = pd.read_json("data.jsonl", lines=True)  # lines=True 表示按行读取 JSONL

   # 写入 CSV（index=False 去掉默认的行号列）
   df.to_csv("output.csv", index=False, encoding="utf-8")

   print("转换完成！")
   ```

⚠️ 注意：`pandas` 会将嵌套 JSON 字段转为字典格式，若需展开嵌套字段，需额外处理（参考方法2的嵌套字段提取逻辑）。


### 四、常见问题解决
1. **中文乱码**：确保脚本中 `encoding="utf-8"`（CSV 用 UTF-8 编码），用 Excel 打开时选择「数据 → 自文本」，编码选 UTF-8。
2. **字段缺失**：脚本1和 `pandas` 会自动为缺失字段填 `NaN`（CSV 中显示为空），不影响整体转换。
3. **大文件处理**：方法2的基础版（逐行读取）适合大文件（GB 级），不会占用过多内存；`pandas` 可能需要调整内存参数。

根据你的需求选择对应的方法即可，小文件用在线工具，复杂场景用 Python 脚本~