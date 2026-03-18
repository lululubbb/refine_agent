# RefineTestGen — 完整目录结构与数据流说明

## 一、完整目录结构（与 ChatUniTest 完全兼容）

```
RefineTestGen/
│
├── config/
│   └── config.ini               ← 全局配置（路径、LLM 参数、数据库连接）
│
├── src/                         ← 所有 Python 源码
│   ├── run.py                   ← 一键运行入口（parse → export → generate → test）
│   ├── scope_test_refine.py     ← 替换 scope_test.py，启动 Refine pipeline
│   ├── askGPT_refine.py         ← 替换 askGPT.py 的 fix 逻辑（Suite 级迭代）
│   ├── refine_agent.py          ← Refine Agent（工具调用 + LLM 指令生成）
│   ├── llm_client.py            ← 统一 LLM 客户端（Generator + Refiner）
│   ├── suite_io.py              ← Suite 级 I/O（提取方法、rebuild、写文件）
│   ├── config.py                ← 配置读取
│   ├── tools.py                 ← 工具函数（直接复用 ChatUniTest）
│   │
│   │── ── 以下直接复用 ChatUniTest ──
│   ├── database.py              ← MySQL 数据库封装
│   ├── parse_data.py            ← JSON → MySQL（解析后入库）
│   ├── export_data.py           ← MySQL → dataset JSON 文件（direction_1/3/raw）
│   ├── task.py                  ← Task.parse / Task.test / Task.all_test
│   ├── test_runner.py           ← 编译/执行/JaCoCo 覆盖率
│   ├── aggregate_scores.py      ← 综合评分
│   ├── score_dataset.py         ← 批量评分入口
│   └── scripts/
│       ├── bug_revealing.py     ← buggy vs fixed 检测
│       ├── code_to_ast.py       ← Java → AST token
│       └── measure_similarity.py ← pairwise 相似度计算
│
├── prompt/                      ← Jinja2 prompt 模板
│   ├── d1_4.jinja2              ← 初始生成（无依赖）
│   ├── d1_4_system.jinja2
│   ├── d3_4.jinja2              ← 初始生成（有依赖）
│   ├── d3_4_system.jinja2
│   ├── refine_agent_system.jinja2 ← Refine Agent 系统 prompt
│   ├── refine_agent.jinja2        ← Refine Agent 用户 prompt
│   └── refine_fix.jinja2          ← Generator 精修 prompt
│
├── class_info/                  ← Task.parse 产出的 JSON（Java 类解析结果）
│   └── Csv_1_b/
│       └── Token.java.json
│
├── dataset_batch/               ← export_data 导出的待测方法上下文
│   └── Csv_1_b/                 ← 每个项目一个子目录（由 config.dataset_dir 指定）
│       ├── direction_1/
│       │   └── 1%Csv_1_b%Token%reset%d1.json
│       ├── direction_3/
│       │   └── 1%Csv_1_b%Token%reset%d3.json
│       └── raw_data/
│           └── 1%Csv_1_b%Token%reset%raw.json
│
├── defect4j_projects/           ← Defects4J checkout 的 Java 项目
│   ├── Csv_1_b/                 ← buggy 版本
│   │   ├── pom.xml
│   │   ├── src/
│   │   ├── target/classes/
│   │   └── tests%YYYYMMDDHHMMSS/   ← TestRunner.start_all_test 生成
│   │       ├── test_cases/         ← TestRunner 从 results_batch 复制过来的 .java
│   │       ├── compiler_output/
│   │       ├── test_output/
│   │       ├── report/
│   │       ├── logs/
│   │       │   ├── diagnosis.log
│   │       │   ├── compile.log
│   │       │   └── ...
│   │       ├── Csv_1_b_*_coveragedetail.csv
│   │       ├── Csv_1_b_*_final_scores.csv
│   │       └── Similarity/
│   │           └── Csv_1_b_*_bigSims.csv
│   └── Csv_1_f/                 ← fixed 版本（用于 bug_revealing）
│
└── results_batch/               ← LLM 生成的测试用例及迭代记录
    └── Csv_1_b/                 ← 每项目一个目录（与 ChatUniTest 完全相同）
        └── scope_test%YYYYMMDDHHMMSS%/   ← start_generation 创建的时间戳目录
            ├── record.txt
            ├── global_stats.json
            └── 1%Csv_1_b%Token%reset%d3/  ← 每个 focal method 一个目录
                │   (命名：methodId%proj%class%method%dir)
                │
                ├── test_cases/            ← ★ TestRunner 读取的最终 .java 文件
                │   └── Token_1_1Test.java
                │
                └── 1/                    ← test_num=1 的迭代过程记录
                    ├── 1_GEN_0.json      ← Generator 初始生成 LLM 原始输出
                    ├── 2_SUITE_0.java    ← 初始 suite 源码快照
                    ├── 3_tool_diag_1.json ← Round 1: 工具调用诊断结果
                    ├── 4_REFINE_1.json   ← Round 1: Refiner LLM 输出 + token
                    ├── 5_GEN_1.json      ← Round 1: Generator 精修 LLM 输出
                    ├── 6_SUITE_1.java    ← Round 1 精修后 suite 快照
                    ├── ...（Round 2, 3...）
                    ├── time_stats.json
                    └── token_stats.json
```

## 二、数据流：从上传项目到生成测试用例

```
Step 0: 上传 Java 项目
  defect4j_projects/Csv_1_b/   (pom.xml + src/)
  defect4j_projects/Csv_1_f/   (fixed 版本，可选)
  config.ini: project_dir = ../defect4j_projects/Csv_1_b

Step 1: Task.parse(project_dir)
  → 解析所有 .java 文件
  → 输出到 class_info/Csv_1_b/*.json
  → 格式: [{"class_name":..., "methods":[...], "imports":..., ...}]

Step 2: parse_data(class_info 路径)
  → 读取 class_info JSON → 入库 MySQL
  → 表: method(id, project_name, class_name, method_name, source_code, ...)
  → 表: class(project_name, class_name, package, imports, fields, ...)

Step 3: export_data()
  → 查询 MySQL → 生成 dataset_batch/Csv_1_b/
  → direction_1/  1%Csv_1_b%Token%reset%d1.json  {"focal_method", "class_name", "information"}
  → direction_3/  1%Csv_1_b%Token%reset%d3.json  {"full_fm", "c_deps", "m_deps", "focal_method", "class_name"}
  → raw_data/     1%Csv_1_b%Token%reset%raw.json  {"source_code", "package", "imports", ...}

Step 4: scope_test_refine.start_generation(sql_query)
  → 创建 results_batch/Csv_1_b/scope_test%YYYYMMDDHHMMSS%/
  → 遍历 dataset_batch/Csv_1_b/direction_1/ 下所有 .json
  → 对每个 focal method 调用 suite_refine_process()

Step 5: suite_refine_process(test_num, ...)
  Round 0:
    Generator LLM → 1_GEN_0.json → 提取 Java 代码
    → 写入 test_cases/Token_1_1Test.java  ← 与 ChatUniTest 完全相同！
  Round 1..max_rounds:
    Refine Agent:
      [Tool 1] TestRunner(test_cases/, project_dir).start_all_test()
               → defect4j_projects/Csv_1_b/tests%YYYYMMDDHHMMSS/
               → 读 diagnosis.log / coveragedetail.csv
      [Tool 2] 覆盖率解析 → focal_line_rate, focal_branch_rate
      [Tool 3] bug_revealing.py → bugrevealing.csv
      [Tool 4] code_to_ast + measure_similarity → bigSims.csv
      → 3_tool_diag_1.json (汇总所有工具结果)
      Refiner LLM → 4_REFINE_1.json (per-test 指令)
    Generator LLM 精修 → 5_GEN_1.json
    → 更新 test_cases/Token_1_1Test.java

Step 6: Task.all_test(result_path, project_path)
  → 对所有生成的 test_cases/ 运行最终测试 + 覆盖率报告
```

## 三、关键：test_cases/ 路径与 TestRunner 的关系

TestRunner 读取的路径：
```python
# TestRunner.__init__(test_path, target_path)
# test_path = results_batch/.../scope_test%T%/1%Csv_1_b%Token%reset%d3/
# TestRunner 会从 test_path/test_cases/ 读取所有 *Test.java

# start_all_test() 会在 target_path (defect4j_projects/Csv_1_b) 下创建：
# defect4j_projects/Csv_1_b/tests%T2/
#   test_cases/   ← 从 results_batch 复制过来
#   compiler_output/
#   test_output/
#   report/
#   logs/
#   *.csv         ← 覆盖率、bug_revealing、相似度结果
```

suite_refine_process 中的 tests_dir 就是：
```
results_batch/Csv_1_b/scope_test%T%/1%Csv_1_b%Token%reset%d3/
```

Refine Agent 中调用：
```python
runner = TestRunner(
    test_path=focal_method_result_dir,   # results_batch/.../1%Csv_1_b%Token%reset%d3/
    target_path=project_dir              # defect4j_projects/Csv_1_b
)
runner.start_all_test()
# 生成：defect4j_projects/Csv_1_b/tests%T2/ 下的所有诊断数据
```
