import glob
import os
import subprocess
import re
import shutil
import sys
import tempfile
import csv
from datetime import datetime

# ── sys.path 配置（在 src/ 目录下运行）──────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from config import *
from scoring_ablation import global_ablation_config, compute_final_score_ablation
import xml.etree.ElementTree as ET


# ════════════════════════════════════════════════════════════════════
# Bug-Coverage-1 修复：统一的 JaCoCo class 匹配辅助函数
# ════════════════════════════════════════════════════════════════════

def _jacoco_outer_class(jacoco_class_name: str) -> str:
    """
    从 JaCoCo class name（如 org/foo/Bar$Inner）提取外部类简单名（Bar）。
    这是修复 Bug-Coverage-1 的核心：内部类也应属于外部类的覆盖统计。
    """
    last = jacoco_class_name.split('/')[-1]  # Bar$Inner
    return last.split('$')[0]               # Bar


def _jacoco_class_matches(jacoco_class_name: str, target_simple: str) -> bool:
    """
    判断 JaCoCo <class name="..."> 是否属于 target_simple（含内部类）。

    例：
      "org/.../PolygonsSet$Edge", "PolygonsSet" → True  ✓ (内部类)
      "org/.../PolygonsSet",      "PolygonsSet" → True  ✓ (外部类)
      "org/.../CSVRecord",        "PolygonsSet" → False ✓
    """
    return _jacoco_outer_class(jacoco_class_name) == target_simple


class TestRunner:

    def __init__(self, test_path, target_path, tool="jacoco"):
        """
        :param tool: coverage tool (Only support cobertura or jacoco)
        :param test_path: test cases directory path e.g.:
        /data/share/TestGPT_ASE/result/scope_test%20230414210243%d3_1/ (all test)
        /data/share/TestGPT_ASE/result/scope_test%20230414210243%d3_1/1460%lang_1_f%ToStringBuilder%append%d3/5 (single test)
        :param target_path: target project path
        """
        self.coverage_tool = tool
        self.test_path = test_path
        self.target_path = target_path

        # Preprocess
        self.dependencies = self.make_dependency()
        self.build_dir_name = "target/classes"
        self.build_dir = self.process_single_repo()

        self.COMPILE_ERROR = 0
        self.TEST_RUN_ERROR = 0
        self.SYNTAX_TOTAL = 0
        self.SYNTAX_ERROR = 0
        # 可选：指定当前运行时的 jacoco exec 输出路径（用于单个用例覆盖）
        self.jacoco_destfile = None

    def start_single_test(self):
        temp_dir = os.path.join(self.test_path, "temp")
        compiled_test_dir = os.path.join(self.test_path, "runtemp")
        os.makedirs(compiled_test_dir, exist_ok=True)
        try:
            self.instrument(compiled_test_dir, compiled_test_dir)
            test_file = os.path.abspath(glob.glob(temp_dir + '/*.java')[0])
            compiler_output = os.path.join(temp_dir, 'compile_error')
            test_output = os.path.join(temp_dir, 'runtime_error')
            if not self.run_single_test(test_file, compiled_test_dir, compiler_output, test_output):
                return False
            else:
                self.report(compiled_test_dir, temp_dir)
        except Exception as e:
            print(e)
            return False
        return True

    def start_all_test(self):
        """
        Initialize configurations and run all tests
        """
        
        if os.path.isdir(self.test_path) and os.path.isdir(os.path.join(self.test_path, 'test_cases')):
            tests_dir = self.test_path
            compiler_output_dir = os.path.join(tests_dir, "compiler_output")
            test_output_dir = os.path.join(tests_dir, "test_output")
            report_dir = os.path.join(tests_dir, "report")
 
            compiler_output = os.path.join(compiler_output_dir, "CompilerOutput")
            test_output = os.path.join(test_output_dir, "TestOutput")
            compiled_test_dir = os.path.join(tests_dir, "tests_ChatGPT")
 
            os.makedirs(compiler_output_dir, exist_ok=True)
            os.makedirs(test_output_dir, exist_ok=True)
            os.makedirs(report_dir, exist_ok=True)
            os.makedirs(compiled_test_dir, exist_ok=True)
 
            logs_dir = os.path.join(tests_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            logs = self._make_logs(logs_dir)
 
            return self.run_all_tests(tests_dir, compiled_test_dir, compiler_output, test_output, report_dir, logs)
        
        date = datetime.now().strftime("%Y%m%d%H%M%S")
        tests_dir = os.path.join(self.target_path, f"tests%{date}")
        compiler_output_dir = os.path.join(tests_dir, "compiler_output")
        test_output_dir = os.path.join(tests_dir, "test_output")
        report_dir = os.path.join(tests_dir, "report")

        compiler_output = os.path.join(compiler_output_dir, "CompilerOutput")
        test_output = os.path.join(test_output_dir, "TestOutput")
        compiled_test_dir = os.path.join(tests_dir, "tests_ChatGPT")

        self.copy_tests(tests_dir)

        logs_dir = os.path.join(tests_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        logs = self._make_logs(logs_dir)

        return self.run_all_tests(tests_dir, compiled_test_dir, compiler_output, test_output, report_dir, logs)

    @staticmethod
    def _make_logs(logs_dir):
        """创建并初始化 logs 字典"""
        paths = {
            "syntax":          os.path.join(logs_dir, "syntax.log"),
            "compile":         os.path.join(logs_dir, "compile.log"),
            "exec":            os.path.join(logs_dir, "test_exec.log"),
            "coverage":        os.path.join(logs_dir, "coverage.log"),
            "execution_stats": os.path.join(logs_dir, "execution_stats.log"),
            "compile_failed":  os.path.join(logs_dir, "compile_failed.txt"),
            "diagnosis":       os.path.join(logs_dir, "diagnosis.log"),
        }
        
        for p in paths.values():
            open(p, 'w').close()
        with open(paths["diagnosis"], 'w', encoding='utf-8') as f:
            f.write("# diagnosis.log — 测试用例问题诊断\n")
            f.write("# 每个 [DIAGNOSIS] 块对应一个测试类，供优化指令生成使用\n")
            f.write("# status 取值: compile_fail | exec_fail | exec_timeout | exec_ok\n")
            f.write("# =============================================================\n\n")
        return paths

    @staticmethod
    def _extract_missed_coverage(jacoco_xml_path: str, target_class: str):
        import xml.etree.ElementTree as ET
        import re as _re

        missed_methods: list = []
        partial_methods: list = []

        if not jacoco_xml_path or not os.path.exists(jacoco_xml_path):
            return missed_methods, partial_methods

        try:
            with open(jacoco_xml_path, 'r', encoding='utf-8', errors='replace') as _f:
                raw = _f.read()

            _report_start = raw.find('<report')
            if _report_start < 0:
                return missed_methods, partial_methods
            raw = raw[_report_start:]

            root = ET.fromstring(raw)
            simple = target_class.split('.')[-1] if target_class else ''
            all_classes = list(root.iter('class'))

            # ★ Bug-Coverage-2 修复：收集所有匹配的 class 元素（含内部类）
            # 原来只取第一个，导致内部类的方法覆盖信息丢失
            target_class_elems = [
                cls for cls in all_classes
                if _jacoco_outer_class(cls.get('name', '')) == simple
            ]

            if not target_class_elems:
                return missed_methods, partial_methods

            # 遍历所有匹配的 class 元素（含内部类）
            for target_class_elem in target_class_elems:
                for method_elem in target_class_elem.findall('method'):
                    mname = method_elem.get('name', '')
                    mline = method_elem.get('line', '?')
                    # 将 <init> 显示为类名（构造函数），<clinit> 仍跳过（静态初始化块）
                    if mname == '<clinit>':
                        continue
                    display_name = f"{simple}()" if mname == '<init>' else mname

                    line_missed = line_covered = branch_missed = branch_covered = 0
                    for counter in method_elem.findall('counter'):
                        ctype = counter.get('type', '')
                        if ctype == 'LINE':
                            line_missed  = int(counter.get('missed',  0))
                            line_covered = int(counter.get('covered', 0))
                        elif ctype == 'BRANCH':
                            branch_missed  = int(counter.get('missed',  0))
                            branch_covered = int(counter.get('covered', 0))

                    if line_covered == 0 and line_missed > 0:
                        missed_methods.append(f"line {mline}: {display_name}() — completely uncovered")
                    elif branch_missed > 0:
                        total_br = branch_missed + branch_covered
                        partial_methods.append(
                            f"line {mline}: {display_name}() — {branch_missed}/{total_br} branches missed"
                        )

        except Exception as _e:
            print(f"[WARN] _extract_missed_coverage failed: {_e}")

        return missed_methods, partial_methods

    # ------------------------------------------------------------------
    # 辅助：从 test_cases 目录文件名推断 target_class（modified_class）
    # 优先级: modified_classes.src > defects4j.build.properties > 文件名前缀
    # ------------------------------------------------------------------
    def _resolve_all_target_classes(self) -> list:
        """返回所有 modified class 的简单类名列表（支持多个）。"""
        from test_runner_focal_fix import resolve_all_target_classes
        return resolve_all_target_classes(self.target_path)

    def _resolve_target_class(self, tests_dir):
        """返回主要 target_class 简单类名（如 CSVRecord），失败返回空字符串
        [PATCHED] 内部使用 _resolve_all_target_classes，返回第一个"""
        all_classes = self._resolve_all_target_classes()
        if all_classes:
            return all_classes[0]

        project_root = self.target_path
        meta_file = os.path.join(project_root, 'modified_classes.src')
        if os.path.exists(meta_file):
            try:
                with open(meta_file) as f:
                    line = f.readline().strip()
                if line:
                    return line.split('.')[-1]
            except Exception:
                pass

        # 优先2：defects4j.build.properties
        prop_file = os.path.join(project_root, 'defects4j.build.properties')
        if os.path.exists(prop_file):
            try:
                with open(prop_file) as f:
                    for l in f:
                        if 'd4j.classes.modified' in l and '=' in l:
                            val = l.split('=', 1)[1].strip()
                            first_class = val.split(',')[0].strip()
                            if first_class:
                                return first_class.split('.')[-1]
            except Exception:
                pass

        # 优先3：从 test_cases 文件名前缀推断
        tc_dir = os.path.join(tests_dir, 'test_cases')
        if os.path.isdir(tc_dir):
            for fname in os.listdir(tc_dir):
                if fname.endswith('Test.java'):
                    # 匹配 ClassName_数字_数字Test.java，兼容类名含下划线
                    # 兼容 focal method 名为字符串或数字的命名: Class_<mid>_<seq>Test.java
                    m = re.match(r'^(.+?)_[^_]+_\d+Test\.java$', fname)
                    if m:
                        return m.group(1)
                    return fname.split('_')[0]

        return ''

    def _resolve_focal_method(self, tests_dir):
        """
        按优先级从多个来源解析 focal method 名称：

        优先1：向上遍历路径，找含 % 分隔元信息的目录名。
               格式：<method_id>%<proj>%<class>%<method>%...
               例：1%Csv_1%Token%reset%d1  → 第4段 reset 即为 focal method 名。
               注意：tests%xxx 这类目录名也含 %，但格式不符（段数<4 或第4段为时间戳），
               因此需要验证第4段不是纯数字且不为空。

        优先2：扫描 raw_data 目录下的 JSON 文件名（无需读取内容）。
               文件名格式：<method_id>%<proj>%<class>%<method>%raw.json
               例：1%Csv_1_b%ExtendedBufferedReader%getLineNumber%raw.json → getLineNumber

        优先3：从 test_cases 目录的文件名中提取 mid，若非数字则直接作为方法名。

        优先4：通过 mid（数字）在 raw_data JSON 内容中查找 method_name 字段。
        """

        # ── 优先2：扫描 raw_data 目录下 JSON 文件名 ───────────────────────
        # 文件名格式：<id>%<proj>%<class>%<method>%raw.json
        # 先从当前 tests_dir 向上找 raw_data 目录；再尝试 dataset_batch / dataset 路径
        try:
            raw_data_dir = os.path.join(dataset_dir, "raw_data")
            if raw_data_dir and os.path.isdir(raw_data_dir):
                for fname in sorted(os.listdir(raw_data_dir)):
                    if fname.endswith('.json') and '%' in fname:
                        parts = fname.split('%')
                        # 期望至少4段，第4段为方法名
                        if len(parts) >= 4:
                            method_candidate = parts[3].strip()
                            if method_candidate and not method_candidate.isdigit():
                                # 只取第一个匹配（同目录下所有文件应属于同一 focal method）
                                return method_candidate
        except Exception:
            pass

        # ── 优先3：从 test_cases 文件名的 mid 推断（非数字直接用） ─────────
        try:
            tc_dir = os.path.join(tests_dir, 'test_cases')
            if os.path.isdir(tc_dir):
                for fname in sorted(os.listdir(tc_dir)):
                    if fname.endswith('Test.java'):
                        m = re.match(r'^.+?_([^_]+)_\d+Test\.java$', fname)
                        if m:
                            mid = m.group(1)
                            if not mid.isdigit():
                                return mid
                            # mid 是数字，进入优先4
                            mid_map = self._build_mid_to_method_map(tests_dir)
                            name = mid_map.get(mid, '')
                            if name:
                                return name
                            return ''  # 数字 mid 但查不到，返回空由后续按组查找
        except Exception:
            pass

        return ''

    def _find_raw_data_dir(self, tests_dir: str) -> str:
        raw_data_dir = os.path.join(dataset_dir, "raw_data")
        return raw_data_dir

    def _parse_test_name(self, tc_name: str):
        """Parse test class name like: <class>_<methodIdOrName>_<seq>Test
        Returns (class_prefix, mid, seq) or (tc_name, '', '') on failure.
        This is robust to class names containing underscores.
        """
        try:
            m = re.match(r'^(?P<class>.*)_(?P<mid>[^_]+)_(?P<seq>\d+)Test$', tc_name)
            if m:
                return m.group('class'), m.group('mid'), m.group('seq')
        except Exception:
            pass
        return tc_name, '', ''

    def _group_from_test_class(self, tc_name: str):
        """Return a stable focal-group key for a test class.
        Example: org.apache...CSVRecord_getRecordNumber  (class + '_' + method-id-or-name)
        Falls back to the raw test class name when parsing fails.
        """
        cls, mid, seq = self._parse_test_name(tc_name)
        if mid:
            return f"{cls}_{mid}"
        m = re.match(r'^(.*?_)(\d+)_\d+Test$', tc_name)
        if m:
            return m.group(1).rstrip('_')
        parts = tc_name.rsplit('_', 2)
        if len(parts) >= 3:
            return parts[0] + '_' + parts[1]
        return tc_name

    def _focal_method_from_group(self, grp: str, mid_to_name: dict = None,
                                  global_focal: str = '') -> str:
        """从 group key（形如 pkg.ClassName_mid）提取 focal method 名称（向后兼容）。"""
        name, _ = self._focal_info_from_group(grp, mid_to_name, global_focal)
        return name

    def _focal_info_from_group(self, grp: str, mid_to_name: dict = None,
                                global_focal: str = '',
                                mid_to_focal_map: dict = None) -> tuple:
        """从 group key 提取 (focal_method_name, jvm_descriptor_prefix)。

        descriptor 用于精确匹配重载方法：
          - 非空时：匹配 JaCoCo XML <method desc="..."> 的 startswith
          - None 时：退化为按方法名匹配所有重载（旧行为）

        mid_to_focal_map 优先于 mid_to_name（包含 descriptor 信息）。
        """
        if '_' not in grp:
            return global_focal or '', None

        mid = grp.split('_')[-1]

        if not mid.isdigit():
            # mid 直接是方法名（无 descriptor 可用）
            return mid, None

        # 优先查 mid_to_focal_map（含 descriptor）
        if mid_to_focal_map:
            info = mid_to_focal_map.get(mid)
            if info:
                return info.get('name', ''), info.get('descriptor')

        # 回退到 mid_to_name（仅方法名）
        if mid_to_name:
            name = mid_to_name.get(mid)
            if name:
                return name, None

        return global_focal or '', None

    def _is_focal_method_match(self, method_name: str, focal_name: str,
                               modified_class_name: str,
                               focal_descriptor: str = None,
                               method_desc: str = None) -> bool:
        """判断 JaCoCo XML 中的 method 元素是否对应 focal method（包括构造函数、重载方法）。

        参数：
            method_name        JaCoCo XML <method name="...">
            focal_name         期望的 focal method 名称
            modified_class_name  被测类简单类名（用于构造函数识别）
            focal_descriptor   从 raw_data JSON 解析的 JVM descriptor 参数前缀，
                               如 '(I' 或 '(ILjava/lang/String;'。
                               非 None 时用于重载方法的精确匹配。
            method_desc        JaCoCo XML <method desc="...">（完整 JVM descriptor）
        """
        if not focal_name:
            return False

        # ── 构造函数识别 ──────────────────────────────────────────────────
        # JaCoCo 中构造函数 name="<init>"，focal_name 为 Java 类名
        if method_name == '<init>' and modified_class_name:
            simple_class = modified_class_name.split('.')[-1].split('$')[0]
            if focal_name in (modified_class_name, simple_class):
                # 有 descriptor 时进一步验证参数签名
                if focal_descriptor and method_desc:
                    return method_desc.startswith(focal_descriptor)
                return True

        # ── 方法名不匹配，直接排除 ────────────────────────────────────────
        if method_name != focal_name:
            return False

        # ── 方法名匹配：有重载 descriptor 时精确匹配，否则接受所有重载 ────
        if focal_descriptor and method_desc:
            # ★ PATCH: 完整参数部分匹配（提取括号内内容），而非 startswith
            # 这修复了 getOrder() descriptor="()" 无法匹配 desc="()I" 的问题
            if focal_descriptor.endswith(')'):
                method_params = method_desc[:method_desc.find(')') + 1] if ')' in method_desc else method_desc
                return method_params == focal_descriptor
            else:
                # 前缀匹配（部分 descriptor）
                return method_desc.startswith(focal_descriptor)

        return True

    def _merge_jacoco_execs(self, exec_paths: list, out_exec: str) -> bool:
        """使用 jacococli merge 将多个 exec 文件合并为一个（用于按 focal group 生成 coverage）。"""
        valid_execs = [p for p in exec_paths if p and os.path.exists(p) and os.path.getsize(p) > 0]
        if not valid_execs:
            return False

        # 单个 exec 时直接拷贝
        if len(valid_execs) == 1:
            try:
                os.makedirs(os.path.dirname(out_exec), exist_ok=True)
                shutil.copy2(valid_execs[0], out_exec)
                return os.path.exists(out_exec) and os.path.getsize(out_exec) > 0
            except Exception:
                return False

        cmd = [
            "java", "-jar", JACOCO_CLI,
            "merge",
            *valid_execs,
            "--destfile", out_exec,
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return os.path.exists(out_exec) and os.path.getsize(out_exec) > 0
        except Exception:
            return False

    def _compute_focal_totals_from_merged_jacoco(self, groups: dict, modified_class_name: str,
                                                 mid_to_name: dict, focal_method: str,
                                                 mid_to_focal_map: dict = None) -> dict:
        """针对每个 focal group：
        1. 合并该组所有 test 的 jacoco.exec；
        2. 生成该组的 jacoco.xml；
        3. 从该 xml 中提取 focal method 覆盖率（支持重载方法精确匹配）。
        """
        result = {}
        exec_base_dir = os.path.join(self.test_path, 'group_exec')
        report_base_dir = os.path.join(self.test_path, 'group_report')

        for grp_k, members_k in groups.items():
            focal_name_k, focal_desc_k = self._focal_info_from_group(
                grp_k, mid_to_name, focal_method, mid_to_focal_map)
            if not focal_name_k:
                result[grp_k] = {
                    'f_line_total': None, 'f_line_cov': None,
                    'f_branch_total': None, 'f_branch_cov': None,
                }
                continue

            # 合并该组的 jacoco.exec
            exec_paths = [m.get('exec_file') for m in members_k]
            grp_exec = os.path.join(exec_base_dir, f"{grp_k}.exec")
            os.makedirs(os.path.dirname(grp_exec), exist_ok=True)
            merged_ok = self._merge_jacoco_execs(exec_paths, grp_exec)

            if not merged_ok:
                result[grp_k] = {
                    'f_line_total': None, 'f_line_cov': None,
                    'f_branch_total': None, 'f_branch_cov': None,
                }
                continue

            # 生成该组的 jacoco report
            grp_report_dir = os.path.join(report_base_dir, grp_k)
            try:
                os.makedirs(grp_report_dir, exist_ok=True)
                self.report(grp_report_dir, grp_report_dir, jacoco_exec_override=grp_exec)

                # 复制全局生成的 jacoco.xml 为 group 专用文件
                global_xml = os.path.join(self.target_path, 'target', 'site', 'jacoco', 'jacoco.xml')
                grp_xml = os.path.join(grp_report_dir, 'jacoco.xml')
                if os.path.exists(global_xml):
                    try:
                        shutil.copy2(global_xml, grp_xml)
                    except Exception:
                        pass
            except Exception:
                pass

            # 若 report 未生成，再尝试读取全局 xml
            grp_xml = os.path.join(grp_report_dir, 'jacoco.xml')
            if not os.path.exists(grp_xml):
                grp_xml = os.path.join(self.target_path, 'target', 'site', 'jacoco', 'jacoco.xml')

            flc = flt = fbc = fbt = 0
            found = False

            try:
                tree = ET.parse(grp_xml)
                root = tree.getroot()
            except Exception:
                result[grp_k] = {
                    'f_line_total': None, 'f_line_cov': None,
                    'f_branch_total': None, 'f_branch_cov': None,
                }
                continue

            for cls_elem in root.findall('.//class'):
                cname_k = cls_elem.attrib.get('name', '')
                # ★ 修复：使用 _jacoco_outer_class 正确匹配含内部类的情况
                simple_k = _jacoco_outer_class(cname_k)
                if modified_class_name and simple_k != modified_class_name:
                    continue

                for meth_elem in cls_elem.findall('method'):
                    mn = meth_elem.get('name', '')
                    md = meth_elem.get('desc', '')
                    if not self._is_focal_method_match(
                            mn, focal_name_k, modified_class_name,
                            focal_descriptor=focal_desc_k,
                            method_desc=md):
                        continue
                    found = True
                    for cnt in meth_elem.findall('counter'):
                        ct = cnt.attrib.get('type', '')
                        cov = int(cnt.attrib.get('covered', 0))
                        mis = int(cnt.attrib.get('missed', 0))
                        if ct == 'LINE':
                            flc += cov
                            flt += cov + mis
                        elif ct == 'BRANCH':
                            fbc += cov
                            fbt += cov + mis

            result[grp_k] = {
                'f_line_total': flt if found else None,
                'f_line_cov': flc if found else None,
                'f_branch_total': fbt if found else None,
                'f_branch_cov': fbc if found else None,
            }

        return result

    # ------------------------------------------------------------------
    # JVM descriptor 工具：将 Java 参数类型列表转为 JVM descriptor 前缀
    # 用于精确匹配 JaCoCo XML 中重载方法的 desc 属性
    # ------------------------------------------------------------------
    _JAVA_PRIMITIVE_MAP = {
        'int':     'I', 'long':    'J', 'double':  'D', 'float':   'F',
        'boolean': 'Z', 'byte':    'B', 'char':    'C', 'short':   'S',
        'void':    'V',
    }

    @classmethod
    def _java_type_to_jvm(cls, java_type: str) -> str:
        """将单个 Java 类型字符串转换为 JVM 类型描述符。
        例：'int' → 'I'，'String' → 'Ljava/lang/String;'，'int[]' → '[I'
        支持多维数组。
        """
        java_type = java_type.strip()
        # 去掉泛型部分，如 List<String> → List
        java_type = re.sub(r'<.*>', '', java_type).strip()

        # 处理数组，每一个 [] 对应一个 [
        array_prefix = ''
        while java_type.endswith('[]'):
            array_prefix += '['
            java_type = java_type[:-2].strip()

        if java_type in cls._JAVA_PRIMITIVE_MAP:
            return array_prefix + cls._JAVA_PRIMITIVE_MAP[java_type]

        # 对象类型：转为 Lxxx/yyy; 格式
        # 如果已经是全限定名（含 .）则转换分隔符；否则保留原样（无法确定包名）
        jvm_class = java_type.replace('.', '/')
        return array_prefix + 'L' + jvm_class + ';'

    @classmethod
    def _params_to_jvm_descriptor_prefix(cls, params: list) -> str:
        """将参数类型列表转为 JVM descriptor 参数部分（不含返回值）。
        例：['int', 'String'] → '(ILjava/lang/String;'
        返回值部分用 ')' 结尾前的前缀，便于 startswith 匹配。
        """
        if not params:
            return '('
        return '(' + ''.join(cls._java_type_to_jvm(p) for p in params)

    def _build_mid_to_method_map(self, tests_dir: str) -> dict:
        """
        向后兼容的简单映射：{method_id -> method_name}
        实际上是 _build_mid_to_focal_map 的 name-only 视图。
        """
        return {mid: info['name']
                for mid, info in self._build_mid_to_focal_map(tests_dir).items()}

    def _build_mid_to_focal_map(self, tests_dir: str) -> dict:
        """
        建立 {method_id -> {name, descriptor, params}} 映射，用于精确匹配重载方法。

        数据来源（优先级递减）：
          1. raw_data JSON 文件内容，按以下子优先级尝试：
             a. 直接 JVM descriptor 字段（method_descriptor 等）
             b. 参数类型列表字段（method_params 等，必须是 list 类型）
             c. 完整方法签名字符串（focal_method_signature / method_signature），
                形如 "methodName(Type1, Type2)" 或 "methodName(Type param1, Type param2)"
          2. raw_data 文件名（仅方法名，descriptor=None）

        descriptor 为 None 时退化为按方法名匹配所有重载（兼容旧行为）。

        重要：对象类型如 String / Reader 无完整包名时，JVM descriptor 无法精确生成。
        这种情况下 descriptor 置为 None，避免错误匹配。只有当参数全为基本类型或
        基本类型数组时，才能生成可靠的 descriptor。
        """
        import json as _json

        result: dict = {}

        try:
            raw_data_dir = os.path.join(dataset_dir, "raw_data")
            if not os.path.isdir(raw_data_dir):
                print(f"[WARN] raw_data_dir not found: {raw_data_dir}")
                return result

            for fname in sorted(os.listdir(raw_data_dir)):
                if not fname.endswith(".json") or "%" not in fname:
                    continue

                parts = fname.split("%")
                # 格式：<mid>%<proj>%<class>%<method>%raw.json
                if len(parts) < 4:
                    continue

                mid = parts[0].strip()
                name_from_fname = parts[3].strip()
                if not mid.isdigit() or not name_from_fname or name_from_fname.isdigit():
                    continue

                # 默认值：仅靠文件名，descriptor=None（退化为按名匹配）
                entry = {'name': name_from_fname, 'descriptor': None, 'params': None}

                json_path = os.path.join(raw_data_dir, fname)
                try:
                    with open(json_path, 'r', encoding='utf-8', errors='replace') as _jf:
                        raw_json = _jf.read(65536)
                    data = _json.loads(raw_json)

                    # ── 解析方法名 ──────────────────────────────────────────
                    method_name = (data.get('method_name') or
                                   data.get('focal_method') or
                                   name_from_fname)
                    entry['name'] = method_name

                    # ── 子优先级 a：直接 JVM descriptor ────────────────────
                    jvm_desc = (data.get('method_descriptor') or
                                data.get('focal_method_descriptor') or
                                data.get('descriptor'))
                    if jvm_desc and isinstance(jvm_desc, str) and jvm_desc.startswith('('):
                        paren_close = jvm_desc.find(')')
                        desc_prefix = jvm_desc[:paren_close + 1] if paren_close >= 0 else jvm_desc
                        entry['descriptor'] = desc_prefix
                        result[mid] = entry
                        continue

                    # ── 子优先级 b：参数类型 list 字段 ─────────────────────
                    # 只接受 list 类型，拒绝字符串（字符串可能是完整签名，走优先级c）
                    for params_key in ('method_params', 'param_types', 'focal_method_params'):
                        params_raw = data.get(params_key)
                        if isinstance(params_raw, list):
                            param_types = []
                            for p in params_raw:
                                if isinstance(p, dict):
                                    t = (p.get('type') or p.get('param_type') or '')
                                    # 去掉参数名，只保留类型（如 "int count" → "int"）
                                    t = t.strip().split()[0] if t.strip() else ''
                                    param_types.append(t)
                                elif isinstance(p, str):
                                    # 去掉参数名（如 "int count" → "int"）
                                    param_types.append(p.strip().split()[0] if p.strip() else '')
                            param_types = [t for t in param_types if t]
                            desc = self._safe_params_to_descriptor(param_types)
                            if desc is not None:
                                entry['params'] = param_types
                                entry['descriptor'] = desc
                                break

                    # ── 子优先级 c：完整方法签名字符串 ─────────────────────
                    # 形如 "read(char[], int, int)" 或 "append(int count, String s)"
                    if entry['descriptor'] is None:
                        for sig_key in ('focal_method_signature', 'method_signature',
                                        'signature', 'focal_method'):
                            sig_raw = data.get(sig_key)
                            if not sig_raw or not isinstance(sig_raw, str):
                                continue
                            sig_raw = sig_raw.strip()
                            # 必须含括号才当签名处理（排除纯方法名字符串）
                            if '(' not in sig_raw:
                                continue
                            # 提取括号内参数部分，支持 read(char[], int, int)
                            # 用 rfind 找最后一个 ) 前的内容（避免泛型干扰）
                            paren_open = sig_raw.index('(')
                            paren_close = sig_raw.rfind(')')
                            if paren_close <= paren_open:
                                continue
                            raw_params_str = sig_raw[paren_open + 1:paren_close].strip()
                            if not raw_params_str:
                                # 无参数方法：descriptor = "()"
                                entry['params'] = []
                                entry['descriptor'] = '()'
                                break
                            # 按逗号分割，每段取第一个 token 作为类型（去掉参数名）
                            param_types = []
                            for seg in raw_params_str.split(','):
                                seg = seg.strip()
                                if not seg:
                                    continue
                                # 取第一个空白前的部分（类型），忽略参数名
                                # 如 "int count" → "int"，"char[] buf" → "char[]"
                                tokens = seg.split()
                                param_types.append(tokens[0])
                            desc = self._safe_params_to_descriptor(param_types)
                            if desc is not None:
                                entry['params'] = param_types
                                entry['descriptor'] = desc
                                break

                except Exception as _je:
                    pass  # JSON 解析失败，保持 descriptor=None

                result[mid] = entry

        except Exception as e:
            print("[WARN] _build_mid_to_focal_map failed:", e)

        return result

    def _safe_params_to_descriptor(self, param_types: list):
        """将参数类型列表转为 JVM descriptor 参数前缀，失败或含不可靠类型时返回 None。

        只有当所有参数都是基本类型或基本类型数组时，才能生成可靠的 descriptor。
        对象类型（如 String、Reader）因无包名信息无法准确转换，返回 None 以避免误匹配。
        这样设计确保：有 descriptor → 精确匹配；无 descriptor → 退化为按名匹配所有重载。

        [PATCHED] 无参方法返回 "()" 而非 None，修复 getOrder() 等无参方法无法匹配的问题。
        """
        primitives = set(self._JAVA_PRIMITIVE_MAP.keys())
        if not param_types:
            return "()"
        result_parts = []
        for t in param_types:
            t = t.strip()
            base = t
            array_prefix = ''
            while base.endswith('[]'):
                array_prefix += '['
                base = base[:-2].strip()
            if base in primitives:
                result_parts.append(array_prefix + self._JAVA_PRIMITIVE_MAP[base])
            else:
                return None
        return '(' + ''.join(result_parts)


    def run_all_tests(self, tests_dir, compiled_test_dir, compiler_output, test_output, report_dir, logs=None):
        """
        Run all test cases in a project.
        """
        tests = os.path.join(tests_dir, "test_cases")
        self.instrument(compiled_test_dir, compiled_test_dir)
        start_time = datetime.now()

        total_compile = 0
        total_test_run = 0
        total_tests = 0
        syntax_errors = 0
        compile_failed_list = []

        # ── 推断 target_class ──────────────────────────────────────────
        target_class = self._resolve_target_class(tests_dir)
        from test_runner_focal_fix import (
            resolve_all_target_classes as _resolve_all_tcs,
            resolve_target_class_for_test as _resolve_tc_for_test,
        )
        all_target_classes = _resolve_all_tcs(self.target_path)
        if not all_target_classes:
            all_target_classes = [target_class] if target_class else []
        project_name = os.path.basename(self.target_path.rstrip('/'))
        global_csv_parent_dir = os.path.abspath(tests_dir)
        os.makedirs(global_csv_parent_dir, exist_ok=True)

        # ── per_test_status 内存字典（key=full_class_name）─────────────
        # 结构: { full_class_name: {compile_status, exec_status, exec_timeout,
        #                           jacoco_exec_size, compile_score, exec_score} }
        per_test_status_map = {}
        per_test_records = []

        # ── 推断 focal method ────────────────────────────────────────
        focal_method = self._resolve_focal_method(tests_dir)
        # 预建 mid_to_focal_map（含 descriptor，用于精确匹配重载方法）
        # 同时保留 mid_to_name（向后兼容）
        mid_to_focal_map = self._build_mid_to_focal_map(tests_dir)
        mid_to_name = {mid: info['name'] for mid, info in mid_to_focal_map.items()}
        if not focal_method:
            # 最后兜底：从 test_cases 文件名的数字 mid 查映射表
            try:
                tc_dir = os.path.join(tests_dir, 'test_cases')
                if os.path.isdir(tc_dir):
                    for fname in sorted(os.listdir(tc_dir)):
                        if fname.endswith('Test.java'):
                            m2 = re.match(r'^.+?_([^_]+)_\d+Test\.java$', fname)
                            if m2:
                                mid_cand = m2.group(1)
                                if mid_cand.isdigit() and mid_to_name:
                                    focal_method = mid_to_name.get(mid_cand, '')
                                elif not mid_cand.isdigit():
                                    focal_method = mid_cand
                            break
            except Exception:
                pass

        for t in range(1, 1 + test_number):
            print("Processing attempt: ", str(t))
            for test_case_file in os.listdir(tests):
                if str(t) != test_case_file.split('_')[-1].replace('Test.java', ''):
                    continue

                total_compile += 1
                total_tests += 1
                test_file = os.path.join(tests, test_case_file)
                full_name = self.get_full_name(test_file)
                # ★ 多 modified class 修复：为当前测试推断正确的 target_class
                per_test_target_class = _resolve_tc_for_test(
                    test_class_name=test_case_file.replace('.java', ''),
                    all_modified_classes=all_target_classes,
                    fallback=target_class,
                )

                # ── 1) Syntax check ───────────────────────────────────
                syntax_tmp = tempfile.mkdtemp()
                try:
                    syntax_cmd = self.javac_cmd(syntax_tmp, test_file)
                    syntax_cmd.insert(1, '-Xlint:all')
                    proc = subprocess.run(syntax_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stderr = proc.stderr or ""
                    self.SYNTAX_TOTAL += 1

                    syntax_pattern = re.compile(
                        r"(illegal start of expression|';' expected|unclosed string literal|"
                        r"unterminated string literal|unclosed comment|illegal character|"
                        r"identifier expected|expected '\}'|expected '\)'|expected '\]'|"
                        r"missing ';'|syntax error)",
                        re.IGNORECASE
                    )
                    if proc.returncode != 0:
                        if syntax_pattern.search(stderr):
                            self.SYNTAX_ERROR += 1
                            syntax_errors += 1
                            if logs:
                                with open(logs['syntax'], 'a') as f:
                                    f.write(f"[SYNTAX_ERROR] {test_case_file}: {stderr.splitlines()[0] if stderr else 'syntax error'}\n")
                        else:
                            if logs:
                                with open(logs['syntax'], 'a') as f:
                                    f.write(f"[SYNTAX_SEMANTIC] {test_case_file}: {stderr.splitlines()[0] if stderr else 'compile error'}\n")
                    else:
                        if logs:
                            with open(logs['syntax'], 'a') as f:
                                f.write(f"[SYNTAX_OK] {test_case_file}\n")
                finally:
                    if os.path.exists(syntax_tmp):
                        shutil.rmtree(syntax_tmp)

                # ── 2) Compile ────────────────────────────────────────
                os.makedirs(compiled_test_dir, exist_ok=True)
                cmd = self.javac_cmd(compiled_test_dir, test_file)
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                compiled_ok = (result.returncode == 0)

                if not compiled_ok:
                    self.COMPILE_ERROR += 1
                    compile_failed_list.append(test_case_file)

                    if logs:
                        with open(logs['compile'], 'a') as f:
                            f.write(f"[COMPILE_FAILED] {full_name}:\n")
                            if result.stderr:
                                for line in result.stderr.splitlines():
                                    f.write(f"    {line}\n")
                            else:
                                f.write("    compile error\n")
                            f.write("=" * 80 + "\n")
                        with open(logs['compile_failed'], 'a') as f:
                            f.write(f"{full_name}\t{test_case_file}\n")

                    if os.path.basename(compiler_output) == 'compile_error':
                        compiler_output_file = f"{compiler_output}.txt"
                    else:
                        compiler_output_file = f"{compiler_output}-{os.path.basename(test_file)}.txt"
                    with open(compiler_output_file, "w") as f:
                        f.write(result.stdout)
                        f.write(result.stderr)

                    per_test_status_map[full_name] = {
                        'compile_status':  'fail',
                        'exec_status':     'skip',
                        'exec_timeout':    False,
                        'jacoco_exec_size': 0,
                        'compile_score':   0.0,
                        'exec_score':      0.0,
                    }

                    if logs and 'diagnosis' in logs:
                        _stderr_cf = result.stderr or ''
                        _lines_cf  = _stderr_cf.strip().splitlines()
                        _core_cf   = [l.strip() for l in _lines_cf if ': error:' in l][:10]
                        if not _core_cf:
                            _core_cf = [_lines_cf[0].strip()] if _lines_cf else ['unknown compile error']
                        try:
                            with open(logs['diagnosis'], 'a', encoding='utf-8') as _df:
                                _df.write(f"[DIAGNOSIS] test_class={full_name}\n")
                                _df.write(f"  project={project_name}  target_class={target_class}\n")
                                _df.write(f"  status=compile_fail\n")
                                _df.write(f"  error_type=compile_error\n")
                                _df.write(f"  core_errors ({len(_core_cf)}):\n")
                                for _ce in _core_cf:
                                    _df.write(f"    - {_ce}\n")
                                _show_n = min(len(_lines_cf), 100)
                                _df.write(f"  full_stderr ({_show_n}/{len(_lines_cf)} lines):\n")
                                for _ll in _lines_cf[:100]:
                                    _df.write(f"    {_ll}\n")
                                if len(_lines_cf) > 100:
                                    _df.write(f"    ... [{len(_lines_cf)-100} more lines truncated]\n")
                                _df.write("---\n")
                        except Exception:
                            pass

                    # 编译失败的用例也追加到 per_test_records（覆盖率全 None）
                    per_test_records.append({
                        'test_class': full_name, 'exec_file': None,
                        'exec_note': 'compile_fail',
                        'per_test_target_class': per_test_target_class,
                        'm_per_line_cov': None, 'm_per_line_total': None,
                        'm_per_branch_cov': None, 'm_per_branch_total': None,
                        'f_per_line_cov': None, 'f_per_line_total': None,
                        'f_per_branch_cov': None, 'f_per_branch_total': None,
                        'per_test_jacoco_xml': None,
                    })
                    continue

                else:
                    if logs:
                        with open(logs['compile'], 'a') as f:
                            f.write(f"[COMPILE_OK] {full_name}\n")

                    # ★ 初始化编译成功状态（exec 待填）
                    per_test_status_map[full_name] = {
                        'compile_status':  'pass',
                        'exec_status':     'pending',
                        'exec_timeout':    False,
                        'jacoco_exec_size': 0,
                        'compile_score':   1.0,
                        'exec_score':      0.0,
                    }

                # ── 3) Run test ───────────────────────────────────────
                test_basename = os.path.splitext(test_case_file)[0]
                per_test_exec = os.path.join(compiled_test_dir, f"jacoco_{test_basename}.exec")
                try:
                    if os.path.exists(per_test_exec):
                        os.remove(per_test_exec)
                except Exception:
                    pass

                self.jacoco_destfile = per_test_exec
                exec_ok, is_timeout = self.run_test_only_with_reason(test_file, compiled_test_dir, test_output, logs)
                self.jacoco_destfile = None

                try:
                    exec_size = os.path.getsize(per_test_exec) if os.path.exists(per_test_exec) else 0
                except Exception:
                    exec_size = 0

                # ★ 更新执行状态
                per_test_status_map[full_name]['exec_status']     = 'pass' if exec_ok else 'fail'
                per_test_status_map[full_name]['exec_timeout']    = is_timeout
                per_test_status_map[full_name]['jacoco_exec_size'] = exec_size
                per_test_status_map[full_name]['exec_score']      = 1.0 if exec_ok else 0.0

                if logs:
                    try:
                        with open(logs['execution_stats'], 'a') as f:
                            f.write(f"[PER_TEST_RUN] {test_case_file} exec_ok={exec_ok} exec_size={exec_size}\n")
                    except Exception:
                        pass

                if logs and 'diagnosis' in logs and not exec_ok:
                    try:
                        with open(logs['diagnosis'], 'a', encoding='utf-8') as _df:
                            _df.write(f"[DIAGNOSIS] test_class={full_name}\n")
                            _df.write(f"  project={project_name}  target_class={target_class}\n")
                            if is_timeout:
                                _df.write(f"  status=exec_timeout\n")
                                _df.write(f"  error_type=timeout\n")
                                _df.write(f"  core_errors:\n")
                                _df.write(f"    - Exceeded TIMEOUT limit\n")
                            else:
                                _df.write(f"  status=exec_fail\n")
                                _df.write(f"  error_type=runtime_error\n")
                                _rt_file = f"{test_output}-{test_case_file}.txt"
                                _exc_lines = []
                                if os.path.exists(_rt_file):
                                    try:
                                        _rt_all = open(_rt_file, errors='ignore').read()
                                        _exc_lines = []
                                        for _line in _rt_all.splitlines():
                                            if re.search(r'(?:AssertionFailedError|expected:|but was:|Exception|Error|FAILED)', _line):
                                                _clean = _line.strip()
                                                if _clean and not _clean.startswith('at '):
                                                    _exc_lines.append(_clean[:300])
                                            if len(_exc_lines) >= 8:
                                                break
                                    except Exception:
                                        pass
                                if not _exc_lines:
                                    _exc_lines = ['runtime error (no details captured)']
                                _df.write(f"  core_errors:\n")
                                for _ec in _exc_lines:
                                    _df.write(f"    - {_ec.strip()}\n")
                            _df.write("---\n")
                    except Exception:
                        pass

                # ── 4) 单测覆盖率（针对 modified_class 和 focal_method） ──────
                exec_note = 'ok' if exec_ok else ('timeout' if is_timeout else 'fail')
                m_per_line_cov = m_per_line_total = None
                m_per_branch_cov = m_per_branch_total = None
                # ★ focal method 的 per-test 覆盖数据初始化
                f_per_line_cov = f_per_line_total = None
                f_per_branch_cov = f_per_branch_total = None
                per_test_jacoco_xml = None

                if exec_size > 0:
                    per_test_report_dir = os.path.join(report_dir, "per_test_reports", test_basename)
                    self.report(compiled_test_dir, per_test_report_dir, jacoco_exec_override=per_test_exec)

                    # FIX: jacococli-based report() writes jacoco.xml directly
                    # into per_test_report_dir — check that path first
                    _per_xml = os.path.join(per_test_report_dir, "jacoco.xml")
                    if os.path.exists(_per_xml):
                        per_test_jacoco_xml = _per_xml
                    else:
                        _global_xml = os.path.join(
                            self.target_path, "target", "site", "jacoco", "jacoco.xml")
                        if os.path.exists(_global_xml):
                            os.makedirs(per_test_report_dir, exist_ok=True)
                            try:
                                shutil.copy2(_global_xml, _per_xml)
                                per_test_jacoco_xml = _per_xml
                            except Exception:
                                per_test_jacoco_xml = _global_xml

                    # ── 提取 target_class 和 focal_method 的覆盖数据 ──────────
                    try:
                        jacoco_xml_path = per_test_jacoco_xml
                        # ★ 多 modified class 修复：使用 per_test_target_class 替代固定的 target_class
                        _eff_target_class = per_test_target_class if per_test_target_class else target_class
                        if jacoco_xml_path and os.path.exists(jacoco_xml_path) and _eff_target_class:
                            tree_p = ET.parse(jacoco_xml_path)
                            root_p = tree_p.getroot()
 
                            # 确定本测试类对应的 focal method 名称及 descriptor
                            grp_for_this = self._group_from_test_class(full_name)
                            focal_for_this, focal_desc_for_this = self._focal_info_from_group(
                                grp_for_this, mid_to_name, focal_method, mid_to_focal_map)
 
                            for class_elem in root_p.findall('.//class'):
                                cname = class_elem.attrib.get('name', '')
                                # ★ Bug-Coverage-1 修复：使用 _jacoco_outer_class 匹配（含内部类）
                                simple = _jacoco_outer_class(cname)
                                if simple != _eff_target_class:
                                    continue
 
                                # target_class 级别覆盖（class-level counter）
                                for c in class_elem.findall('counter'):
                                    ctype = c.attrib.get('type', '')
                                    covered = int(c.attrib.get('covered', 0))
                                    missed  = int(c.attrib.get('missed', 0))
                                    if ctype == 'LINE':
                                        m_per_line_cov = (m_per_line_cov or 0) + covered
                                        m_per_line_total = (m_per_line_total or 0) + covered + missed
                                    elif ctype == 'BRANCH':
                                        m_per_branch_cov = (m_per_branch_cov or 0) + covered
                                        m_per_branch_total = (m_per_branch_total or 0) + covered + missed
 
                                # focal method 级别覆盖
                                if focal_for_this:
                                    matched_methods = [
                                        me for me in class_elem.findall('method')
                                        if self._is_focal_method_match(
                                            me.get('name', ''), focal_for_this, _eff_target_class,
                                            focal_descriptor=focal_desc_for_this,
                                            method_desc=me.get('desc', ''),
                                        )
                                    ]
                                    
                                    if matched_methods:
                                        fl_cov = fl_tot = fb_cov = fb_tot = 0
                                        for me in matched_methods:
                                            for cc in me.findall('counter'):
                                                ct2 = cc.get('type', '')
                                                cov2 = int(cc.get('covered', 0))
                                                mis2 = int(cc.get('missed', 0))
                                                if ct2 == 'LINE':
                                                    fl_cov += cov2
                                                    fl_tot += cov2 + mis2
                                                elif ct2 == 'BRANCH':
                                                    fb_cov += cov2
                                                    fb_tot += cov2 + mis2
                                        if fl_tot > 0:
                                            f_per_line_cov = fl_cov
                                            f_per_line_total = fl_tot
                                        if fb_tot > 0:
                                            f_per_branch_cov = fb_cov
                                            f_per_branch_total = fb_tot
                                    else:
                                        print(f"[WARN] focal method '{focal_for_this}'"
                                              f"(desc={focal_desc_for_this}) not found in "
                                              f"class '{simple}' for test '{test_basename}'")
                                # ★ 不再 break —— 继续遍历该类的内部类（$Edge 等）

                    except Exception as _xml_err:
                        if logs:
                            with open(logs.get('coverage', os.devnull), 'a') as _f:
                                _f.write(f"[PER_TEST_XML_ERR] {test_case_file}: {_xml_err}\n")

                per_test_records.append({
                    'test_class':          full_name,
                    'exec_file':           per_test_exec,
                    'exec_note':           exec_note,
                    'per_test_target_class': per_test_target_class,
                    'm_per_line_cov':      m_per_line_cov,
                    'm_per_line_total':    m_per_line_total,
                    'm_per_branch_cov':    m_per_branch_cov,
                    'm_per_branch_total':  m_per_branch_total,
                    'f_per_line_cov':      f_per_line_cov,
                    'f_per_line_total':    f_per_line_total,
                    'f_per_branch_cov':    f_per_branch_cov,
                    'f_per_branch_total':  f_per_branch_total,
                    'per_test_jacoco_xml': per_test_jacoco_xml,
                })

        # ── 写出 per_test_status.csv ─────────────────────────────────
        self._write_per_test_status(
            global_csv_parent_dir, project_name, target_class, per_test_status_map, logs)

        # ── 合并所有 exec，生成全项目覆盖报告 ───────────────────────
        report_target = os.path.join(report_dir, "final")
        line_cov = branch_cov = line_total = branch_total = line_rate = branch_rate = None
        m_line_cov = m_branch_cov = m_line_total = m_branch_total = m_line_rate = m_branch_rate = None
        modified_class_name = target_class or None

        merged_exec = os.path.join(compiled_test_dir, "jacoco_merged.exec")
        exec_files = [r['exec_file'] for r in per_test_records
                      if r.get('exec_file')
                      and os.path.exists(r.get('exec_file'))
                      and os.path.getsize(r.get('exec_file')) > 0]  # FIX Bug-B: skip 0-byte exec files

        # 参考 step_9_global_test_eval：merge 和统计 should include all local exec files
        for ef in sorted(glob.glob(os.path.join(compiled_test_dir, "jacoco_*.exec")) +
                         glob.glob(os.path.join(compiled_test_dir, "jacoco.exec"))):
            if ef and os.path.exists(ef) and os.path.getsize(ef) > 0 and ef not in exec_files:
                exec_files.append(ef)

        exec_files = list(dict.fromkeys(exec_files))  # remove duplicates, keep order

        res = None
        if exec_files:
            if JACOCO_CLI and os.path.exists(JACOCO_CLI):
                merge_cmd = ["java", "-jar", JACOCO_CLI, "merge"] + exec_files + ["--destfile", merged_exec]
                try:
                    subprocess.run(merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                except Exception:
                    pass
                res = self.report(compiled_test_dir, report_target, jacoco_exec_override=merged_exec)
            else:
                res = self.report(compiled_test_dir, report_target, jacoco_exec_override=exec_files[0])
        else:
            default_exec = os.path.join(compiled_test_dir, "jacoco.exec")
            if os.path.exists(default_exec):
                res = self.report(compiled_test_dir, report_target, jacoco_exec_override=default_exec)
            else:
                res = self.report(compiled_test_dir, report_target)

        if logs and res is not None:
            try:
                out = res.stdout.decode() if isinstance(res.stdout, bytes) else (res.stdout or "")
                err = res.stderr.decode() if isinstance(res.stderr, bytes) else (res.stderr or "")
                with open(logs['coverage'], 'a') as f:
                    f.write("===== Coverage report (all attempts) =====\n")
                    if out: f.write("--- STDOUT ---\n" + out + "\n")
                    if err: f.write("--- STDERR ---\n" + err + "\n")
            except Exception:
                pass

        jacoco_xml_path = os.path.join(self.target_path, "target", "site", "jacoco", "jacoco.xml")
        fallback_jacoco_xml = os.path.join(report_target, "jacoco.xml")
        if not os.path.exists(jacoco_xml_path) and os.path.exists(fallback_jacoco_xml):
            print(f"⚠️ 主要 jacoco.xml 未找到，回退到 {fallback_jacoco_xml}")
            jacoco_xml_path = fallback_jacoco_xml

        # ★ Bug-Coverage-1 修复：使用修复后的函数计算 per_class_coverage（含内部类）
        per_class_coverage: dict = {}
        if os.path.exists(jacoco_xml_path):
            tree = ET.parse(jacoco_xml_path)
            root_elem = tree.getroot()
            counters = root_elem.findall('.//counter')
            line_counters   = [c for c in counters if c.attrib.get('type') == 'LINE']
            branch_counters = [c for c in counters if c.attrib.get('type') == 'BRANCH']
            if line_counters:
                lc = line_counters[-1]
                line_cov   = int(lc.attrib.get('covered', 0))
                line_total = line_cov + int(lc.attrib.get('missed', 0))
                line_rate  = round(100 * line_cov / line_total, 2) if line_total else 0.0
            if branch_counters:
                bc = branch_counters[-1]
                branch_cov   = int(bc.attrib.get('covered', 0))
                branch_total = branch_cov + int(bc.attrib.get('missed', 0))
                branch_rate  = round(100 * branch_cov / branch_total, 2) if branch_total else 0.0
 
            # ★ Bug-Coverage-1 修复：对每个 modified class，汇总所有内部类的覆盖行数
            # 原来只匹配 cname.endswith('/' + _tc_simple)，对内部类（Bar$Inner）失效
            # 修复后使用 _jacoco_outer_class(cname) == _tc_simple，正确匹配内部类
            for _tc in all_target_classes:
                _tc_simple = _tc.split('.')[-1].split('$')[0]
                _lc = _lm = _bc = _bm = 0
                # 遍历所有 class 元素，汇总属于 _tc_simple（含内部类）的覆盖数据
                for class_elem in root_elem.findall('.//class'):
                    _cname = class_elem.attrib.get('name', '')
                    # ★ 关键修复：使用 _jacoco_outer_class 而非 endswith
                    if _jacoco_outer_class(_cname) != _tc_simple:
                        continue
                    for c in class_elem.findall('counter'):
                        if c.attrib.get('type') == 'LINE':
                            _lc += int(c.attrib.get('covered', 0))
                            _lm += int(c.attrib.get('missed', 0))
                        if c.attrib.get('type') == 'BRANCH':
                            _bc += int(c.attrib.get('covered', 0))
                            _bm += int(c.attrib.get('missed', 0))
                _lt = _lc + _lm; _bt = _bc + _bm
                per_class_coverage[_tc_simple] = {
                    'line_cov': _lc, 'line_total': _lt,
                    'line_rate': round(100 * _lc / _lt, 2) if _lt else 0.0,
                    'branch_cov': _bc, 'branch_total': _bt,
                    'branch_rate': round(100 * _bc / _bt, 2) if _bt else 0.0,
                }
 
            # 向后兼容：m_line_*/m_branch_* 使用第一个（主） modified class 的值
            if modified_class_name:
                _pc = per_class_coverage.get(modified_class_name, {})
                m_line_cov     = _pc.get('line_cov')
                m_line_total   = _pc.get('line_total')
                m_line_rate    = _pc.get('line_rate')
                m_branch_cov   = _pc.get('branch_cov')
                m_branch_total = _pc.get('branch_total')
                m_branch_rate  = _pc.get('branch_rate')

            # 回退策略：如果 per_class_coverage 未能计算到目标类，尝试使用 per_test_records 的单测覆盖数据
            if all_target_classes:
                need_fallback = any(
                    per_class_coverage.get(_tc.split('.')[-1].split('$')[0], {}).get('line_total', 0) == 0
                    for _tc in all_target_classes
                )
            else:
                need_fallback = (m_line_total is None or m_line_total == 0)

            if need_fallback and per_test_records:
                fallback_per_class = {}
                for rec in per_test_records:
                    rec_target = rec.get('per_test_target_class') or modified_class_name or ''
                    rec_simple = rec_target.split('.')[-1].split('$')[0] if rec_target else None
                    if not rec_simple:
                        continue

                    if all_target_classes and rec_simple not in [c.split('.')[-1].split('$')[0] for c in all_target_classes]:
                        continue

                    if rec.get('m_per_line_total') is None and rec.get('m_per_branch_total') is None:
                        continue

                    fc = fallback_per_class.setdefault(rec_simple, {
                        'line_cov': 0, 'line_total': 0, 'line_rate': 0.0,
                        'branch_cov': 0, 'branch_total': 0, 'branch_rate': 0.0,
                    })

                    # 采用 max 策略避免重复累加或覆盖错位（近似高度）
                    fc['line_cov'] = max(fc['line_cov'], rec.get('m_per_line_cov') or 0)
                    fc['line_total'] = max(fc['line_total'], rec.get('m_per_line_total') or 0)
                    fc['branch_cov'] = max(fc['branch_cov'], rec.get('m_per_branch_cov') or 0)
                    fc['branch_total'] = max(fc['branch_total'], rec.get('m_per_branch_total') or 0)

                for k, v in fallback_per_class.items():
                    if v['line_total'] > 0:
                        v['line_rate'] = round(100.0 * v['line_cov'] / v['line_total'], 2)
                    if v['branch_total'] > 0:
                        v['branch_rate'] = round(100.0 * v['branch_cov'] / v['branch_total'], 2)

                if fallback_per_class:
                    # 仅当主路径完全没命中时，才采用回退逻辑
                    if all_target_classes:
                        missing_keys = [c.split('.')[-1].split('$')[0] for c in all_target_classes
                                        if per_class_coverage.get(c.split('.')[-1].split('$')[0], {}).get('line_total', 0) == 0]
                        for k in missing_keys:
                            if k in fallback_per_class:
                                per_class_coverage[k] = fallback_per_class[k]
                    else:
                        if modified_class_name:
                            key = modified_class_name.split('.')[-1].split('$')[0]
                            if key in fallback_per_class:
                                per_class_coverage[key] = fallback_per_class[key]
                                m_line_cov = fallback_per_class[key]['line_cov']
                                m_line_total = fallback_per_class[key]['line_total']
                                m_line_rate = fallback_per_class[key]['line_rate']
                                m_branch_cov = fallback_per_class[key]['branch_cov']
                                m_branch_total = fallback_per_class[key]['branch_total']
                                m_branch_rate = fallback_per_class[key]['branch_rate']

                    if m_line_total in (None, 0) and modified_class_name:
                        key = modified_class_name.split('.')[-1].split('$')[0]
                        _pc = per_class_coverage.get(key, {})
                        if _pc.get('line_total'):
                            m_line_cov = _pc.get('line_cov')
                            m_line_total = _pc.get('line_total')
                            m_line_rate = _pc.get('line_rate')
                        if _pc.get('branch_total'):
                            m_branch_cov = _pc.get('branch_cov')
                            m_branch_total = _pc.get('branch_total')
                            m_branch_rate = _pc.get('branch_rate')

                    if line_rate is None or line_rate == 0:
                        global_cov = sum(v.get('line_cov', 0) for v in per_class_coverage.values())
                        global_tot = sum(v.get('line_total', 0) for v in per_class_coverage.values())
                        if global_tot > 0:
                            line_cov = global_cov
                            line_total = global_tot
                            line_rate = round(100.0 * global_cov / global_tot, 2)
                    if branch_rate is None or branch_rate == 0:
                        global_bcov = sum(v.get('branch_cov', 0) for v in per_class_coverage.values())
                        global_btot = sum(v.get('branch_total', 0) for v in per_class_coverage.values())
                        if global_btot > 0:
                            branch_cov = global_bcov
                            branch_total = global_btot
                            branch_rate = round(100.0 * global_bcov / global_btot, 2)

        # ── coveragedetail.csv ────────────────────────────────────────
        try:
            tc_slug = (target_class or 'unknown').replace('.', '')
            pn_slug = project_name.replace('.', '')
            detail_csv = os.path.join(global_csv_parent_dir,
                                      f'{pn_slug}_{tc_slug}_coveragedetail.csv')
            header = [
                'project', 'target_class', 'test_class', 'focal_method', 'exec_status',
                'm_per_line_cov', 'm_per_line_total', 'm_per_line_rate',
                'm_per_branch_cov', 'm_per_branch_total', 'm_per_branch_rate',
                'm_line_contrib_pct', 'm_branch_contrib_pct', 'm_coverage_score',
            ]
            file_exists = os.path.exists(detail_csv)

            # 按 focal 组聚合（用于计算 per-test 对 focal 的 f_contrib_pct）
            groups_cd: dict = {}
            for rec in per_test_records:
                tc_r = rec.get('test_class', '')
                grp_r = self._group_from_test_class(tc_r)
                groups_cd.setdefault(grp_r, []).append(rec)

            # Compute group totals for modified class coverage (sum of per-test coverage)
            # 每组 focal totals（优先基于合并后的 jacoco.xml，避免同一行/分支被多次计入）
            focal_totals_cd: dict = self._compute_focal_totals_from_merged_jacoco(
                groups_cd, modified_class_name, mid_to_name, focal_method,
                mid_to_focal_map=mid_to_focal_map)
            
            group_modified_totals = {}
            for grp_k, members_k in groups_cd.items():
                total_m_line_cov = sum(m.get('m_per_line_cov', 0) or 0 for m in members_k)
                total_m_branch_cov = sum(m.get('m_per_branch_cov', 0) or 0 for m in members_k)
                group_modified_totals[grp_k] = {
                    'm_line_cov': total_m_line_cov,
                    'm_branch_cov': total_m_branch_cov
                }

            # 若合并 jacoco 未命中 focal method，则回退到 per-test 覆盖率的上确界（取 max，避免重复累加）
            # 注意：不能用 sum，因为同一行被多个 test 覆盖时 total 不变，只有 covered 可能更高。
            # 这里用 max(f_per_line_total) 作为方法总行数，max(f_per_line_cov) 作为最佳单测覆盖数。
            for grp_r, members_r in groups_cd.items():
                gtot = focal_totals_cd.get(grp_r, {})
                if not gtot or gtot.get('f_line_total') is None:
                    valid_members = [m for m in members_r
                                     if (m.get('f_per_line_total') or 0) > 0]
                    if valid_members:
                        focal_totals_cd[grp_r] = {
                            'f_line_total':   max(m.get('f_per_line_total')   or 0 for m in valid_members),
                            'f_line_cov':     max(m.get('f_per_line_cov')     or 0 for m in valid_members),
                            'f_branch_total': max(m.get('f_per_branch_total') or 0 for m in valid_members),
                            'f_branch_cov':   max(m.get('f_per_branch_cov')   or 0 for m in valid_members),
                        }
                    else:
                        focal_totals_cd[grp_r] = {
                            'f_line_total': 0, 'f_line_cov': 0,
                            'f_branch_total': 0, 'f_branch_cov': 0,
                        }

            with open(detail_csv, 'a', newline='', encoding='utf-8') as csvf:
                writer = csv.writer(csvf)
                if not file_exists:
                    header_ext = header + [
                        'f_per_line_cov', 'f_per_line_total', 'f_per_line_rate',
                        'f_per_branch_cov', 'f_per_branch_total', 'f_per_branch_rate',
                        'f_line_contrib_pct', 'f_branch_contrib_pct', 'f_coverage_score',
                    ]
                    writer.writerow(header_ext)

                for rec in per_test_records:
                    mlc = rec.get('m_per_line_cov') or 0
                    mlt = rec.get('m_per_line_total') or 0
                    mlr = round(100.0 * mlc / mlt, 4) if mlt else 0.0
                    mbc = rec.get('m_per_branch_cov') or 0
                    mbt = rec.get('m_per_branch_total') or 0
                    mbr = round(100.0 * mbc / mbt, 4) if mbt else 0.0

                    # line_contrib_pct / branch_contrib_pct：
                    # 单测在 modified class 上的覆盖行(分支)数 /
                    # 该 focal 组合并后在 modified class 上的总覆盖行(分支)数
                    # 分母来自 group_modified_totals 中 modified class 级别的组覆盖数
                    tc_r = rec.get('test_class', '')
                    grp_r = self._group_from_test_class(tc_r)
                    fm_r = self._focal_method_from_group(grp_r, mid_to_name, focal_method)
                    gtot = focal_totals_cd.get(grp_r, {})
                    gmod_tot = group_modified_totals.get(grp_r, {})

                    # focal 组在 modified class 上的合并覆盖数（coverage table 的 m_line_cov/m_branch_cov 之和）
                    grp_m_line_cov   = gmod_tot.get('m_line_cov')   or 0
                    grp_m_branch_cov = gmod_tot.get('m_branch_cov') or 0

                    # 贡献度 = 单测覆盖数 / 组合并覆盖数（分母为0时置0，避免除零）
                    line_contrib_pct   = round(100.0 * mlc / grp_m_line_cov,   4) if grp_m_line_cov   and mlc else 0.0
                    branch_contrib_pct = round(100.0 * mbc / grp_m_branch_cov, 4) if grp_m_branch_cov and mbc else 0.0

                    coverage_score = round(
                        0.25 * (mlr / 100.0) + 0.25 * (mbr / 100.0) +
                        0.25 * (line_contrib_pct / 100.0) + 0.25 * (branch_contrib_pct / 100.0), 6)
                    rec['coverage_score'] = coverage_score

                    # focal 字段（focal method 维度）
                    ffc = rec.get('f_per_line_cov')   or 0
                    fft = rec.get('f_per_line_total')  or 0
                    ffr = round(100.0 * ffc / fft, 4)  if fft else 0.0
                    fbc2 = rec.get('f_per_branch_cov')  or 0
                    fbt2 = rec.get('f_per_branch_total') or 0
                    fbr2 = round(100.0 * fbc2 / fbt2, 4) if fbt2 else 0.0

                    # f_line_contrib_pct / f_branch_contrib_pct：
                    # 单测在 focal method 上的覆盖行(分支)数 /
                    # 该 focal 组合并后在 focal method 上的总覆盖行(分支)数
                    # 分母使用 f_line_cov（组覆盖数），即 coveragemethod 里记录的值
                    gf_line_cov   = gtot.get('f_line_cov')   or 0
                    gf_branch_cov = gtot.get('f_branch_cov') or 0
                    f_line_contrib_pct   = round(100.0 * ffc  / gf_line_cov,   4) if gf_line_cov   and ffc  else 0.0
                    f_branch_contrib_pct = round(100.0 * fbc2 / gf_branch_cov, 4) if gf_branch_cov and fbc2 else 0.0
                    f_coverage_score = round(
                        0.25 * (ffr / 100.0) + 0.25 * (fbr2 / 100.0) +
                        0.25 * (f_line_contrib_pct / 100.0) + 0.25 * (f_branch_contrib_pct / 100.0), 6)

                    writer.writerow([
                        project_name, target_class,
                        rec.get('test_class', ''), fm_r, rec.get('exec_note', 'ok'),
                        mlc if mlt else '', mlt if mlt else '', mlr if mlt else '',
                        mbc if mbt else '', mbt if mbt else '', mbr if mbt else '',
                        line_contrib_pct, branch_contrib_pct, coverage_score,
                        ffc if fft else '',  fft if fft else '',  ffr if fft else '',
                        fbc2 if fbt2 else '', fbt2 if fbt2 else '', fbr2 if fbt2 else '',
                        f_line_contrib_pct, f_branch_contrib_pct, f_coverage_score,
                    ])

                    # diagnosis
                    if logs and 'diagnosis' in logs and rec.get('exec_note', '') == 'ok':
                        try:
                            _snap = rec.get('per_test_jacoco_xml')
                            _global_xml2 = os.path.join(
                                self.target_path, "target", "site", "jacoco", "jacoco.xml")
                            _jxml = _snap if (_snap and os.path.isfile(_snap) and
                                              os.path.getsize(_snap) > 200) else _global_xml2
                            _missed_methods, _partial_methods = self._extract_missed_coverage(
                                _jxml, target_class)
                            _tc_name = rec.get('test_class', '')
                            _br_hint = 'N/A'
                            _sim_hint = None
                            try:
                                import glob as _glob, csv as _csv
                                _br_files = sorted(_glob.glob(
                                    os.path.join(global_csv_parent_dir, '*bugrevealing*.csv')))
                                for _br_file in _br_files:
                                    with open(_br_file, newline='', encoding='utf-8') as _bf:
                                        for _brow in _csv.DictReader(_bf):
                                            if _brow.get('test_class', '').strip() == _tc_name:
                                                _v = str(_brow.get('bug_revealing', '')).lower()
                                                _br_hint = 'true' if _v == 'true' else 'false'
                                                break
                                    if _br_hint == 'true':
                                        break
                                _sim_dir2 = os.path.join(global_csv_parent_dir, 'Similarity')
                                for _sf in sorted(_glob.glob(os.path.join(_sim_dir2, '*_bigSims.csv'))):
                                    with open(_sf, newline='', encoding='utf-8') as _sf_f:
                                        for _srow in _csv.DictReader(_sf_f):
                                            if _srow.get('test_case_1', '').strip() == _tc_name:
                                                _sim_hint = _srow.get('redundancy_score', '').strip()
                                                break
                                    if _sim_hint is not None:
                                        break
                            except Exception:
                                pass
                            with open(logs['diagnosis'], 'a', encoding='utf-8') as _df:
                                _df.write(f"[DIAGNOSIS] test_class={_tc_name}\n")
                                _df.write(f"  project={project_name}  target_class={target_class}  focal_method={fm_r}\n")
                                _df.write(f"  status=exec_ok\n")
                                _df.write(f"  error_type=coverage_gap\n")
                                _df.write(f"  line_rate={mlr:.4f}%  ({mlc}/{mlt})\n")
                                _df.write(f"  branch_rate={mbr:.4f}%  ({mbc}/{mbt if mbt else 0})\n")
                                _df.write(f"  coverage_score={coverage_score}\n")
                                # ── 未覆盖方法 ──
                                if _missed_methods:
                                    _df.write(f"  uncovered_methods ({len(_missed_methods)}):\n")
                                    for _mm in _missed_methods[:20]:
                                        _df.write(f"    - {_mm}\n")
                                    if len(_missed_methods) > 20:
                                        _df.write(f"    ... [{len(_missed_methods)-20} more]\n")
                                else:
                                    _df.write(f"  uncovered_methods: none\n")
                                # ── 分支未完全覆盖方法 ──
                                if _partial_methods:
                                    _df.write(f"  partial_branch_methods ({len(_partial_methods)}):\n")
                                    for _pm in _partial_methods[:20]:
                                        _df.write(f"    - {_pm}\n")
                                    if len(_partial_methods) > 20:
                                        _df.write(f"    ... [{len(_partial_methods)-20} more]\n")
                                else:
                                    _df.write(f"  partial_branch_methods: none\n")
                                _df.write("---\n")
                        except Exception as _diag_err:
                            import traceback
                            print(f"[WARN] diagnosis write error: {_diag_err}")
                            traceback.print_exc()

        except Exception as e:
            print('Failed to write coveragedetail.csv:', e)
            import traceback; traceback.print_exc()

        # ─── 生成 coveragemethod.csv / final_scores.csv / final_scores2.csv ──────
        try:
            # 重建 groups
            groups: dict = {}
            for rec in per_test_records:
                tc_r = rec.get('test_class', '')
                grp_r = self._group_from_test_class(tc_r)
                groups.setdefault(grp_r, []).append(rec)

            # ── focal totals（优先 merged jacoco XML） ──────────────────────────
            focal_totals: dict = self._compute_focal_totals_from_merged_jacoco(
                groups, modified_class_name, mid_to_name, focal_method,
                mid_to_focal_map=mid_to_focal_map)

            # 合并 jacoco 未命中 focal method 时，回退到 per-test 覆盖率的上确界（取 max，避免重复累加）
            for grp_k, members_k in groups.items():
                gtot = focal_totals.get(grp_k, {})
                if not gtot or gtot.get('f_line_total') is None:
                    valid_mk = [m for m in members_k
                                if (m.get('f_per_line_total') or 0) > 0]
                    if valid_mk:
                        focal_totals[grp_k] = {
                            'f_line_total':   max(m.get('f_per_line_total')   or 0 for m in valid_mk),
                            'f_line_cov':     max(m.get('f_per_line_cov')     or 0 for m in valid_mk),
                            'f_branch_total': max(m.get('f_per_branch_total') or 0 for m in valid_mk),
                            'f_branch_cov':   max(m.get('f_per_branch_cov')   or 0 for m in valid_mk),
                        }
                    else:
                        focal_totals[grp_k] = {
                            'f_line_total': 0, 'f_line_cov': 0,
                            'f_branch_total': 0, 'f_branch_cov': 0,
                        }

            tc_slug = (target_class or 'unknown').replace('.', '')
            pn_slug = project_name.replace('.', '')

            # ── coveragemethod.csv ──────────────────────────────────────────────
            coveragemethod_csv = os.path.join(
                global_csv_parent_dir, f'{pn_slug}_{tc_slug}_coveragemethod.csv')
            cm_is_new = not (os.path.exists(coveragemethod_csv) and
                             os.path.getsize(coveragemethod_csv) > 0)
            with open(coveragemethod_csv, 'a', newline='', encoding='utf-8') as cmf:
                w_cm = csv.writer(cmf)
                if cm_is_new:
                    w_cm.writerow([
                        'project', 'target_class', 'focal_method', 'exec_status',
                        'f_per_line_cov', 'f_per_line_total', 'f_per_line_rate',
                        'f_per_branch_cov', 'f_per_branch_total', 'f_per_branch_rate',
                        'line_contrib_pct', 'branch_contrib_pct', 'coverage_score',
                    ])
                for grp_k, members_k in groups.items():
                    ft_k = focal_totals.get(grp_k, {})
                    flc_k = ft_k.get('f_line_cov') or 0
                    flt_k = ft_k.get('f_line_total') or 0
                    flr_k = round(100.0 * flc_k / flt_k, 4) if flt_k else 0.0
                    fbc_k = ft_k.get('f_branch_cov') or 0
                    fbt_k = ft_k.get('f_branch_total') or 0
                    fbr_k = round(100.0 * fbc_k / fbt_k, 4) if fbt_k else 0.0
                    lcp_k = flr_k
                    bcp_k = fbr_k
                    cov_s_k = round(
                        0.25 * (flr_k / 100.0) + 0.25 * (fbr_k / 100.0) +
                        0.25 * (lcp_k / 100.0) + 0.25 * (bcp_k / 100.0), 6)
                    fm_k = self._focal_method_from_group(grp_k, mid_to_name, focal_method)
                    en_k = [m.get('exec_note', '') for m in members_k]
                    es_k = 'ok' if 'ok' in en_k else (en_k[0] if en_k else '')
                    w_cm.writerow([project_name, target_class, fm_k, es_k,
                                   flc_k, flt_k, flr_k, fbc_k, fbt_k, fbr_k,
                                   lcp_k, bcp_k, cov_s_k])

            # ── 加载 bug_revealing 和 similarity ───────────────────────────────
            br_map: dict = {}
            try:
                import glob as _glob, csv as _csv
                for _f in sorted(_glob.glob(
                        os.path.join(global_csv_parent_dir, '*bugrevealing*.csv'))):
                    with open(_f, newline='', encoding='utf-8') as _bf:
                        for _r in _csv.DictReader(_bf):
                            _tc2 = _r.get('test_class', '').strip()
                            br_map[_tc2] = (1.0 if str(_r.get('bug_revealing', '')).strip().lower() == 'true'
                                            else 0.0)
            except Exception:
                pass

            sim_map: dict = {}
            try:
                import glob as _glob, csv as _csv
                _sim_dir = os.path.join(global_csv_parent_dir, 'Similarity')
                if os.path.isdir(_sim_dir):
                    for _f in sorted(_glob.glob(os.path.join(_sim_dir, '*_bigSims.csv'))):
                        with open(_f, newline='', encoding='utf-8') as _sf:
                            for _r in _csv.DictReader(_sf):
                                try:
                                    sim_map[_r.get('test_case_1', '').strip()] = \
                                        float(_r.get('redundancy_score', ''))
                                except Exception:
                                    pass
            except Exception:
                pass



            # ── final_scores.csv（per-test） ────────────────────────────────────
            per_test_final = os.path.join(
                global_csv_parent_dir, f'{pn_slug}_{tc_slug}_final_scores.csv')
            pf_is_new = not (os.path.exists(per_test_final) and
                             os.path.getsize(per_test_final) > 0)
            with open(per_test_final, 'a', newline='', encoding='utf-8') as pf:
                pfw = csv.writer(pf)
                if pf_is_new:
                    pfw.writerow([
                        'test_class', 'focal_method', 'compile_score', 'exec_score',
                        'coverage_score', 'bug_revealing_score', 'redundancy_score',
                        'final_score', 'valid_weight_pct',
                    ])
                for grp_k, members_k in groups.items():
                    fm_k = self._focal_method_from_group(grp_k, mid_to_name, focal_method)
                    for mrec in members_k:
                        tc_n = mrec.get('test_class', '')
                        cs_p = 1.0 if mrec.get('exec_note') != 'compile_fail' else 0.0
                        es_p = 1.0 if mrec.get('exec_note') == 'ok' else 0.0
                        cv_p = mrec.get('m_coverage_score', '')
                        br_p = br_map.get(tc_n)
                        br_p = br_p if br_p is not None else ''
                        sm_p = sim_map.get(tc_n)
                        sm_p = sm_p if sm_p is not None else ''
                        _abl_cfg = global_ablation_config()
                        fs_p, vw_p = compute_final_score_ablation(cs_p, es_p, cv_p, br_p, sm_p, _abl_cfg)
                        pfw.writerow([tc_n, fm_k, cs_p, es_p, cv_p,
                                      br_p, sm_p, fs_p, round(vw_p, 4)])

            # ── final_scores2.csv（per-focalmethod 组聚合） ────────────────────
            final_csv = os.path.join(
                global_csv_parent_dir, f'{pn_slug}_{tc_slug}_final_scores2.csv')
            fs2_is_new = not (os.path.exists(final_csv) and
                              os.path.getsize(final_csv) > 0)
            with open(final_csv, 'a', newline='', encoding='utf-8') as f2:
                w2 = csv.writer(f2)
                if fs2_is_new:
                    w2.writerow([
                        'test_class', 'focal_method', 'compile_score', 'exec_score',
                        'coverage_score', 'bug_revealing_score', 'redundancy_score',
                        'final_score', 'valid_weight_pct',
                    ])
                for grp_k, members_k in groups.items():
                    tot_k = len(members_k) or 1
                    cs_g = round(
                        sum(1.0 if m.get('exec_note') != 'compile_fail' else 0.0
                            for m in members_k) / tot_k, 6)
                    es_g = round(
                        sum(1.0 if m.get('exec_note') == 'ok' else 0.0
                            for m in members_k) / tot_k, 6)
                    # coverage_score: focal method 覆盖率（与 coveragemethod 一致）
                    ft_g = focal_totals.get(grp_k, {})
                    flc_g = ft_g.get('f_line_cov') or 0; flt_g = ft_g.get('f_line_total') or 0
                    fbc_g = ft_g.get('f_branch_cov') or 0; fbt_g = ft_g.get('f_branch_total') or 0
                    flr_g = round(100.0 * flc_g / flt_g, 4) if flt_g else 0.0
                    fbr_g = round(100.0 * fbc_g / fbt_g, 4) if fbt_g else 0.0
                    cv_g = round(
                        0.25 * (flr_g / 100.0) + 0.25 * (fbr_g / 100.0) +
                        0.25 * (flr_g / 100.0) + 0.25 * (fbr_g / 100.0), 6
                    ) if (flt_g or fbt_g) else ''
                    # bug_revealing / redundancy: 组内均值
                    brv_g = [br_map.get(m.get('test_class', '')) for m in members_k]
                    brv_g = [v for v in brv_g if v is not None]
                    br_g  = round(sum(brv_g) / len(brv_g), 6) if brv_g else ''
                    smv_g = [sim_map.get(m.get('test_class', '')) for m in members_k]
                    smv_g = [v for v in smv_g if isinstance(v, (int, float))]
                    sm_g  = round(sum(smv_g) / len(smv_g), 6) if smv_g else ''
                    # final_score: 按权重加权
                    _abl_cfg = global_ablation_config()
                    fs_g, vw_g = compute_final_score_ablation(cs_g, es_g, cv_g, br_g, sm_g, _abl_cfg)
                    fm_g = self._focal_method_from_group(grp_k, mid_to_name, focal_method)
                    w2.writerow([grp_k, fm_g, cs_g, es_g, cv_g,
                                 br_g, sm_g, fs_g, round(vw_g, 4)])

            # ── 控制台：focal method 覆盖率 ──────────────────────────────────
            print("-" * 50)
            print("FOCAL METHOD COVERAGE (per group):")
            if focal_totals:
                any_data = False
                for grp_k, ft_p in focal_totals.items():
                    fm_p  = self._focal_method_from_group(grp_k, mid_to_name, focal_method)
                    flc_p = ft_p.get('f_line_cov') or 0
                    flt_p = ft_p.get('f_line_total') or 0
                    fbc_p = ft_p.get('f_branch_cov') or 0
                    fbt_p = ft_p.get('f_branch_total') or 0
                    flr_p = round(100.0 * flc_p / flt_p, 4) if flt_p else None
                    fbr_p = round(100.0 * fbc_p / fbt_p, 4) if fbt_p else None
                    print(f"  group={grp_k}  focal_method={fm_p or '(unknown)'}")
                    if flr_p is not None:
                        print(f"    行覆盖率: {flr_p}% ({flc_p}/{flt_p})")
                        any_data = True
                    else:
                        print(f"    行覆盖率: N/A")
                    if fbr_p is not None:
                        print(f"    分支覆盖率: {fbr_p}% ({fbc_p}/{fbt_p})")
                    else:
                        print(f"    分支覆盖率: N/A")
                if not any_data:
                    print("  [注意] focal method 名称未解析到，无法从 jacoco.xml 提取数据。")
                    print(f"  [调试] focal_method='{fm_p}'  mid_to_name={mid_to_name}")
            else:
                print("  未获取到 focal method 覆盖率数据")
            print("-" * 50)

        except Exception as _e:
            import traceback
            print('[WARN] per-focal/final csv generation failed:', _e)
            traceback.print_exc()

        # ── execution_stats log ──────────────────────────────────────
        if logs:
            with open(logs['execution_stats'], 'a') as f:
                f.write(f"[ALL ATTEMPTS]\n")
                f.write(f"  total_tests={total_tests}\n")
                f.write(f"  syntax_errors={syntax_errors}\n")
                f.write(f"  compile_errors={self.COMPILE_ERROR}\n")
                f.write(f"  test_run_errors={self.TEST_RUN_ERROR}\n")
                if line_rate is not None:
                    f.write(f"  全项目行覆盖率: {line_rate}% ({line_cov}/{line_total})\n")
                if branch_rate is not None:
                    f.write(f"  全项目分支覆盖率: {branch_rate}% ({branch_cov}/{branch_total})\n")
                if all_target_classes:
                    f.write(f"  target_classes: {all_target_classes}\n")
                    for _tc_name in all_target_classes:
                        _tc_simple = _tc_name.split('.')[-1].split('$')[0]
                        _pc = per_class_coverage.get(_tc_simple, {})
                        f.write(f"  target_class: {_tc_simple}\n")
                        if _pc.get('line_total'):
                            f.write(f"    行覆盖率: {_pc['line_rate']}% ({_pc['line_cov']}/{_pc['line_total']})\n")
                        if _pc.get('branch_total'):
                            f.write(f"    分支覆盖率: {_pc['branch_rate']}% ({_pc['branch_cov']}/{_pc['branch_total']})\n")

        # ── project_test_summary.csv ─────────────────────────────────
        try:
            run_time_seconds = round((datetime.now() - start_time).total_seconds(), 2)
            Attempts    = total_tests
            Aborted     = max(0, Attempts - total_compile)
            SyntaxError = self.SYNTAX_ERROR
            CompileError = self.COMPILE_ERROR
            RuntimeError = self.TEST_RUN_ERROR
            denom     = Attempts - Aborted if (Attempts - Aborted) > 0 else None
            run_denom = (Attempts - Aborted - CompileError) if denom else None

            SyntaxRate  = (1.0 - SyntaxError  / denom)       if denom else None
            CompileRate = (1.0 - CompileError  / denom)       if denom else None
            RunRate     = (1.0 - RuntimeError  / run_denom)   if run_denom and run_denom > 0 else None
            Passed      = max(0, Attempts - Aborted - CompileError - RuntimeError)
            PassRate    = (Passed / denom) if denom else None

            summary_headers = [
                'project', 'modified_class',
                'Attempts', 'Aborted', 'SyntaxError', 'SyntaxRate',
                'CompileError', 'CompileRate', 'RuntimeError', 'RunRate', 'Passed', 'PassRate',
                'line_cov', 'line_total', 'line_rate',
                'branch_cov', 'branch_total', 'branch_rate',
                'm_line_cov', 'm_line_total', 'm_line_rate',
                'm_branch_cov', 'm_branch_total', 'm_branch_rate', 'run_time',
            ]
            tc_slug = (target_class or 'unknown').replace('.', '')
            pn_slug = project_name.replace('.', '')
            summary_fname = os.path.join(global_csv_parent_dir, f'{pn_slug}_{tc_slug}_coverage.csv')
            file_exists = os.path.exists(summary_fname)
            with open(summary_fname, 'a', newline='', encoding='utf-8') as sf:
                w = csv.writer(sf)
                if not file_exists:
                    w.writerow(summary_headers)
                w.writerow([
                    project_name, modified_class_name or "",
                    Attempts, Aborted, SyntaxError,
                    round(SyntaxRate,  4) if SyntaxRate  is not None else '',
                    CompileError,
                    round(CompileRate, 4) if CompileRate is not None else '',
                    RuntimeError,
                    round(RunRate,     4) if RunRate     is not None else '',
                    Passed,
                    round(PassRate,    4) if PassRate    is not None else '',
                    line_cov   if line_cov   is not None else '',
                    line_total if line_total is not None else '',
                    line_rate  if line_rate  is not None else '',
                    branch_cov   if branch_cov   is not None else '',
                    branch_total if branch_total is not None else '',
                    branch_rate  if branch_rate  is not None else '',
                    m_line_cov   if m_line_cov   is not None else '',
                    m_line_total if m_line_total is not None else '',
                    m_line_rate  if m_line_rate  is not None else '',
                    m_branch_cov   if m_branch_cov   is not None else '',
                    m_branch_total if m_branch_total is not None else '',
                    m_branch_rate  if m_branch_rate  is not None else '',
                    run_time_seconds,
                ])
        except Exception as e:
            print('Failed to write project_test_summary.csv:', e)

        total_test_run = total_compile - self.COMPILE_ERROR
        print("SYNTAX TOTAL COUNT:", self.SYNTAX_TOTAL)
        print("SYNTAX ERROR COUNT:", self.SYNTAX_ERROR)
        print("COMPILE TOTAL COUNT:", total_compile)
        print("COMPILE ERROR COUNT:", self.COMPILE_ERROR)
        print("TEST RUN TOTAL COUNT:", total_test_run)
        print("TEST RUN ERROR COUNT:", self.TEST_RUN_ERROR)
        print("-" * 50)
        print("COVERAGE STATISTICS (ALL ATTEMPTS):")
        if line_rate is not None:
            print(f"  全项目 行覆盖率: {line_rate}% ({line_cov}/{line_total})")
        if branch_rate is not None:
            print(f"  全项目 分支覆盖率: {branch_rate}% ({branch_cov}/{branch_total})")
        if all_target_classes:
            for _tc_name in all_target_classes:
                _tc_simple = _tc_name.split('.')[-1].split('$')[0]
                _pc = per_class_coverage.get(_tc_simple, {})
                print(f"  target_class: {_tc_simple}")
                # FIX Bug-A: use 'is not None' — int 0 is falsy, hid 0/0 results
                if _pc.get('line_total') is not None:
                    lt = _pc['line_total']
                    if lt == 0:
                        print(f"    行覆盖率: N/A (0行被JVM加载 — 测试未执行到被测类，或jacoco.xml陈旧)")
                    else:
                        print(f"    行覆盖率: {_pc['line_rate']}% ({_pc['line_cov']}/{lt})")
                else:
                    print(f"    行覆盖率: N/A (jacoco.xml中未找到该类)")
                if _pc.get('branch_total') is not None:
                    bt = _pc['branch_total']
                    if bt > 0:
                        print(f"    分支覆盖率: {_pc['branch_rate']}% ({_pc['branch_cov']}/{bt})")
                    else:
                        print(f"    分支覆盖率: N/A (无分支数据)")
        elif modified_class_name:
            print(f"  target_class: {modified_class_name}")
            if m_line_rate is not None:
                print(f"    行覆盖率: {m_line_rate}% ({m_line_cov}/{m_line_total})")
            if m_branch_rate is not None:
                print(f"    分支覆盖率: {m_branch_rate}% ({m_branch_cov}/{m_branch_total})")
        # FIX Bug-C: always show diagnostic when coverage is 0, even if all_target_classes is set
        _has_any_coverage = any(
            v.get('line_total', 0) > 0 for v in per_class_coverage.values()
        ) if per_class_coverage else (m_line_total is not None and m_line_total > 0)
        if not _has_any_coverage:
            print("  ⚠ 未获取到有效覆盖率数据 — 可能原因:")
            print("      1. 测试在执行被测类前抛出异常 (构造参数错误、Mock配置缺失等)")
            print("      2. jacoco.xml不存在或为上次运行的陈旧文件 (检查target/site/jacoco/)")
            print("      3. 所有测试超时被SIGTERM终止，jacoco agent shutdown hook未执行")
        print("-" * 50)

        return total_compile, total_test_run

    def _write_per_test_status(self, output_dir, project_name, target_class,
                                status_map, logs=None):
        if not status_map:
            return
        try:
            tc_slug = (target_class or 'unknown').replace('.', '')
            pn_slug = (project_name or 'project').replace('.', '')
            csv_path = os.path.join(output_dir, f'{pn_slug}_{tc_slug}_status.csv')
            header = [
                'project', 'target_class', 'test_class',
                'compile_status', 'exec_status', 'exec_timeout',
                'jacoco_exec_size', 'compile_score', 'exec_score',
            ]
            file_exists = os.path.exists(csv_path)
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(header)
                for full_name, s in status_map.items():
                    writer.writerow([
                        project_name, target_class, full_name,
                        s['compile_status'], s['exec_status'], s['exec_timeout'],
                        s['jacoco_exec_size'], s['compile_score'], s['exec_score'],
                    ])
        except Exception as e:
            print('Failed to write per_test_status.csv:', e)

    def run_test_only_with_reason(self, test_file, compiled_test_dir, test_output, logs=None):
        if os.path.basename(test_output) == 'runtime_error':
            test_output_file = f"{test_output}.txt"
        else:
            test_output_file = f"{test_output}-{os.path.basename(test_file)}.txt"

        cmd = self.java_cmd(compiled_test_dir, test_file)
        try:
            result = subprocess.run(cmd, timeout=TIMEOUT,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                self.TEST_RUN_ERROR += 1
                self.export_runtime_output(result, test_output_file)
                if logs:
                    stderr_content = result.stderr or ""
                    core_exception = "未提取到明确异常信息"
                    for pat in [
                        re.compile(r"=>\s*([\w\.]+Exception):\s*(.*?)(?=\n\s+at|$)", re.DOTALL),
                        re.compile(r"([\w\.]+Exception):\s*(.*?)(?=\n\s+at|$)", re.DOTALL),
                        re.compile(r"([\w\.]+Error):\s*(.*?)(?=\n\s+at|$)", re.DOTALL),
                        re.compile(r"([\w\.]+Exception)$", re.MULTILINE),
                        re.compile(r"([\w\.]+Error)$", re.MULTILINE),
                    ]:
                        m = pat.search(stderr_content)
                        if m:
                            if len(m.groups()) > 1 and m.group(2):
                                core_exception = f"{m.group(1)}：{m.group(2).strip()}"
                            else:
                                core_exception = m.group(1)
                            break
                    with open(logs['exec'], 'a') as f:
                        f.write(f"[EXEC_FAILED] {test_file}:\n")
                        f.write(f"[EXEC_CORE_ERROR] {core_exception}\n")
                        f.write("[EXEC_STDERR]\n")
                        for line in stderr_content.splitlines():
                            f.write(f"    {line}\n")
                        f.write("=" * 80 + "\n")
                return False, False
            else:
                if logs:
                    with open(logs['exec'], 'a') as f:
                        f.write(f"[EXEC_OK] {test_file}\n")
                return True, False
        except subprocess.TimeoutExpired:
            self.TEST_RUN_ERROR += 1
            if logs:
                with open(logs['exec'], 'a') as f:
                    f.write(f"[EXEC_TIMEOUT] {test_file}\n")
            return False, True
        except Exception as e:
            self.TEST_RUN_ERROR += 1
            if logs:
                with open(logs['exec'], 'a') as f:
                    f.write(f"[EXEC_ERROR] {test_file}: {e}\n")
            return False, False

    def run_single_test(self, test_file, compiled_test_dir, compiler_output, test_output):
        if not self.compile(test_file, compiled_test_dir, compiler_output):
            return False
        if os.path.basename(test_output) == 'runtime_error':
            test_output_file = f"{test_output}.txt"
        else:
            test_output_file = f"{test_output}-{os.path.basename(test_file)}.txt"
        cmd = self.java_cmd(compiled_test_dir, test_file)
        try:
            result = subprocess.run(cmd, timeout=TIMEOUT,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                self.TEST_RUN_ERROR += 1
                self.export_runtime_output(result, test_output_file)
                return False
        except subprocess.TimeoutExpired:
            return False
        return True

    @staticmethod
    def export_runtime_output(result, test_output_file):
        with open(test_output_file, "w") as f:
            f.write(result.stdout)
            error_msg = re.sub(r'log4j:WARN.*\n?', '', result.stderr)
            if error_msg:
                f.write(error_msg)

    def compile(self, test_file, compiled_test_dir, compiler_output):
        os.makedirs(compiled_test_dir, exist_ok=True)
        cmd = self.javac_cmd(compiled_test_dir, test_file)
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            self.COMPILE_ERROR += 1
            if os.path.basename(compiler_output) == 'compile_error':
                compiler_output_file = f"{compiler_output}.txt"
            else:
                compiler_output_file = f"{compiler_output}-{os.path.basename(test_file)}.txt"
            with open(compiler_output_file, "w") as f:
                f.write(result.stdout)
                f.write(result.stderr)
            return False
        return True

    def process_single_repo(self):
        if self.has_submodule(self.target_path):
            modules = self.get_submodule(self.target_path)
            postfixed_modules = [f'{self.target_path}/{module}/{self.build_dir_name}' for module in modules]
            build_dir = ':'.join(postfixed_modules)
        else:
            build_dir = os.path.join(self.target_path, self.build_dir_name)
        return build_dir

    @staticmethod
    def get_package(test_file):
        pkg = ''
        try:
            with open(test_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('package '):
                        pkg = line.replace('package ', '').replace(';', '').strip()
                        break
        except Exception:
            pass
        return pkg

    @staticmethod
    def is_module(project_path):
        if not os.path.isdir(project_path):
            return False
        if 'pom.xml' in os.listdir(project_path) and 'target' in os.listdir(project_path):
            return True
        return False

    def get_submodule(self, project_path):
        return [d for d in os.listdir(project_path) if self.is_module(os.path.join(project_path, d))]

    def has_submodule(self, project_path):
        for d in os.listdir(project_path):
            if self.is_module(os.path.join(project_path, d)):
                return True
        return False

    def javac_cmd(self, compiled_test_dir, test_file):
        classpath = f"{JUNIT_JAR}:{MOCKITO_JAR}:{LOG4J_JAR}:{self.dependencies}:{self.build_dir}:."
        classpath_file = os.path.join(compiled_test_dir, 'classpath.txt')
        self.export_classpath(classpath_file, classpath)
        return ["javac", "-d", compiled_test_dir, f"@{classpath_file}", test_file]

    def java_cmd(self, compiled_test_dir, test_file):
        full_test_name = self.get_full_name(test_file)
        classpath = (
            f"{COBERTURA_DIR}/cobertura-2.1.1.jar:{compiled_test_dir}/instrumented:{compiled_test_dir}:"
            f"{JUNIT_JAR}:{MOCKITO_JAR}:{LOG4J_JAR}:{self.dependencies}:{self.build_dir}:."
        )
        classpath_file = os.path.join(compiled_test_dir, 'classpath.txt')
        self.export_classpath(classpath_file, classpath)
        if self.coverage_tool == "cobertura":
            return ["java", f"@{classpath_file}",
                    f"-Dnet.sourceforge.cobertura.datafile={compiled_test_dir}/cobertura.ser",
                    "org.junit.platform.console.ConsoleLauncher", "--disable-banner",
                    "--disable-ansi-colors", "--fail-if-no-tests", "--details=none",
                    "--select-class", full_test_name]
        else:
            jacoco_dest = self.jacoco_destfile if self.jacoco_destfile else os.path.join(compiled_test_dir, 'jacoco.exec')
            javaagent = f"-javaagent:{JACOCO_AGENT}=destfile={jacoco_dest},append=true"
            return ["java", javaagent, f"@{classpath_file}",
                    "org.junit.platform.console.ConsoleLauncher", "--disable-banner",
                    "--disable-ansi-colors", "--fail-if-no-tests", "--details=none",
                    "--select-class", full_test_name]

    @staticmethod
    def export_classpath(classpath_file, classpath):
        with open(classpath_file, 'w') as f:
            f.write("-cp " + classpath)

    def get_full_name(self, test_file):
        package = self.get_package(test_file)
        test_case = os.path.splitext(os.path.basename(test_file))[0]
        return f"{package}.{test_case}" if package else test_case

    def instrument(self, instrument_dir, datafile_dir):
        if self.coverage_tool == "jacoco":
            return
        os.makedirs(instrument_dir, exist_ok=True)
        os.makedirs(datafile_dir, exist_ok=True)
        if 'instrumented' in os.listdir(instrument_dir):
            return
        if self.has_submodule(self.target_path):
            target_classes = os.path.join(self.target_path, '**/target/classes')
        else:
            target_classes = os.path.join(self.target_path, 'target/classes')
        subprocess.run(["bash", os.path.join(COBERTURA_DIR, "cobertura-instrument.sh"),
                        "--basedir", self.target_path,
                        "--destination", f"{instrument_dir}/instrumented",
                        "--datafile", f"{datafile_dir}/cobertura.ser",
                        target_classes], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


    def _collect_class_dirs(self) -> list:
        """
        Collect all target/classes directories in the project.
        For single-module projects: [target_path/target/classes]
        For multi-module projects:  each module's target/classes
        
        ★ 修复：如果 target/classes 为空或不存在 .class 文件，尝试编译或查找备选位置。
        Used by the jacococli-based report() to set --classfiles.
        """
        class_dirs = []
        
        # 1. 尝试多模块项目
        if self.has_submodule(self.target_path):
            for module in self.get_submodule(self.target_path):
                d = os.path.join(self.target_path, module, "target", "classes")
                if os.path.isdir(d) and self._has_class_files(d):
                    class_dirs.append(d)
        
        # 2. 尝试单模块项目
        if not class_dirs:
            d = os.path.join(self.target_path, "target", "classes")
            if os.path.isdir(d):
                if self._has_class_files(d):
                    class_dirs.append(d)
                else:
                    # ★ 修复：如果 classes 目录为空，尝试编译
                    print(f"  [WARN] target/classes 中没有 .class 文件，尝试编译...")
                    self._try_compile_project()
                    if self._has_class_files(d):
                        class_dirs.append(d)
            else:
                # ★ 修复：目录不存在时尝试编译
                print(f"  [WARN] target/classes 目录不存在，尝试编译项目...")
                self._try_compile_project()
                if os.path.isdir(d) and self._has_class_files(d):
                    class_dirs.append(d)
        
        return class_dirs
    
    def _has_class_files(self, class_dir: str) -> bool:
        """检查目录中是否包含 .class 文件"""
        if not os.path.isdir(class_dir):
            return False
        for root, dirs, files in os.walk(class_dir):
            for f in files:
                if f.endswith('.class'):
                    return True
        return False
    
    def _xml_has_coverage_data(self, xml_path: str) -> bool:
        """
        ★ 新增方法：检查 jacoco.xml 是否包含实际的覆盖率数据。
        返回 True 如果 XML 中有 <class> 元素，False 否则。
        """
        if not os.path.exists(xml_path):
            return False
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            # 查找是否有任何 <class> 元素（表示有实际的覆盖率数据）
            classes = root.findall('.//class')
            return len(classes) > 0
        except Exception as e:
            print(f"  [WARN] 检查 XML 数据失败: {e}")
            return False
    
    def _try_compile_project(self) -> bool:
        """
        ★ 新增方法：尝试编译项目以生成 .class 文件。
        返回 True 如果编译成功，False 否则。
        """
        try:
            pom_path = os.path.join(self.target_path, "pom.xml")
            if not os.path.exists(pom_path):
                print(f"    ❌ pom.xml 不存在于 {self.target_path}")
                return False
            
            print(f"    运行 mvn clean compile ...")
            result = subprocess.run(
                ["mvn", "clean", "compile", "-q"],
                cwd=self.target_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300
            )
            if result.returncode == 0:
                print(f"    ✅ 编译成功")
                return True
            else:
                print(f"    ❌ 编译失败 (rc={result.returncode})")
                if result.stderr:
                    print(f"       错误信息: {result.stderr[:200]}")
                return False
        except Exception as e:
            print(f"    ❌ 编译异常: {e}")
            return False

    def report(self, datafile_dir, report_dir, jacoco_exec_override=None):
        """
        Generate a JaCoCo XML coverage report.

        Uses jacococli report (CLI jar) instead of mvn jacoco:report because:
          1. jacococli writes to an explicit --xml path (no shared-path collision).
          2. jacococli reads --classfiles directly from target/classes, bypassing
             Maven lifecycle — this fixes the 0/0 coverage bug on defects4j projects
             like Math_32_f where mvn jacoco:report fails to locate classfiles.
          3. Mirrors the approach used in HITS run_pipeline.py step_9.
        
        ★ 修复：添加检查以确保 XML 中有实际的覆盖率数据，而不是空文件。
        """
        os.makedirs(report_dir, exist_ok=True)
        result = None

        if self.coverage_tool == "cobertura":
            result = subprocess.run(
                ["bash", os.path.join(COBERTURA_DIR, "cobertura-report.sh"),
                 "--format", REPORT_FORMAT,
                 "--datafile", f"{datafile_dir}/cobertura.ser",
                 "--destination", report_dir],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result

        jacoco_exec_path = (jacoco_exec_override
                            or os.path.join(datafile_dir, "jacoco.exec"))
        if not os.path.exists(jacoco_exec_path) or os.path.getsize(jacoco_exec_path) == 0:
            print(f"⚠️  jacoco.exec 无效或不存在：{jacoco_exec_path}")
            return None

        # XML output: per-run specific path inside report_dir (no collision between runs)
        xml_out = os.path.join(report_dir, "jacoco.xml")

        # ── Primary: jacococli report (mirrors HITS pipeline approach) ────────
        if JACOCO_CLI and os.path.exists(JACOCO_CLI):
            class_dirs = self._collect_class_dirs()
            if class_dirs:
                cmd = ["java", "-jar", JACOCO_CLI, "report", jacoco_exec_path]
                for d in class_dirs:
                    cmd += ["--classfiles", d]
                cmd += ["--xml", xml_out, "--html", report_dir]
                # Source dirs improve line-level reporting (optional)
                for suffix in ["src/main/java", "src/main"]:
                    sd = os.path.join(self.target_path, suffix)
                    if os.path.isdir(sd):
                        cmd += ["--sourcefiles", sd]
                        break
                if self.has_submodule(self.target_path):
                    for module in self.get_submodule(self.target_path):
                        for suffix in ["src/main/java", "src/main"]:
                            sd = os.path.join(self.target_path, module, suffix)
                            if os.path.isdir(sd):
                                cmd += ["--sourcefiles", sd]
                                break

                result = subprocess.run(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
                if result.returncode == 0 and os.path.exists(xml_out):
                    print(f"  [JaCoCo-Fix] ✅ Report generated: {xml_out}")
                    
                    # ★ 新增：检查生成的 XML 是否有实际数据
                    if self._xml_has_coverage_data(xml_out):
                        print(f"  [JaCoCo-Fix] ✅ XML 包含覆盖率数据")
                    else:
                        print(f"  [JaCoCo-Fix] ⚠️ XML 为空（没有覆盖率数据）")
                        print(f"  [JaCoCo-Fix] 可能原因：")
                        print(f"    1. .exec 文件中没有覆盖率记录")
                        print(f"    2. 类文件与 .exec 中的记录不匹配")
                        print(f"    3. JaCoCo agent 未正确注入到测试中")
                    
                    # Copy to legacy shared path for any code still reading it
                    legacy_xml = os.path.join(
                        self.target_path, "target", "site", "jacoco", "jacoco.xml")
                    try:
                        os.makedirs(os.path.dirname(legacy_xml), exist_ok=True)
                        shutil.copy2(xml_out, legacy_xml)
                    except Exception:
                        pass
                    return result
                print(f"  [JaCoCo-Fix] ⚠️ jacococli rc={result.returncode}: "
                      f"{(result.stderr or '')[:300]}")
                # fall through to mvn fallback

        # ── Fallback: mvn jacoco:report ────────────────────────────────────────
        print(f"  [JaCoCo] Falling back to mvn jacoco:report ...")
        mvn_cmd = [
            "mvn", "jacoco:report",
            f"-Djacoco.dataFile={jacoco_exec_path}",
            "-Dmaven.bundle.skip=true",
            "-f", os.path.join(self.target_path, "pom.xml"),
        ]
        result = subprocess.run(mvn_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=self.target_path, text=True)
        jacoco_xml_mvn = os.path.join(
            self.target_path, "target", "site", "jacoco", "jacoco.xml")
        if os.path.exists(jacoco_xml_mvn):
            print(f"✅ Jacoco 报告生成成功：{os.path.dirname(jacoco_xml)}")
            try:
                shutil.copy2(jacoco_xml_mvn, xml_out)
            except Exception:
                pass
        else:
            print(f"⚠️  Jacoco 报告生成失败")
        return result

    def make_dependency(self):
        mvn_dependency_dir = 'target/dependency'
        if not self.has_made():
            subprocess.run(
                f"mvn dependency:copy-dependencies -DoutputDirectory={mvn_dependency_dir} -f {self.target_path}/pom.xml",
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(
                f"mvn install -DskipTests -f {self.target_path}/pom.xml",
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        dep_jars = glob.glob(self.target_path + "/**/*.jar", recursive=True)
        return ':'.join(list(set(dep_jars)))

    def has_made(self):
        for dirpath, dirnames, filenames in os.walk(self.target_path):
            if 'pom.xml' in filenames and 'target' in dirnames:
                if 'dependency' in os.listdir(os.path.join(dirpath, 'target')):
                    return True
        return False

    def copy_tests(self, target_dir):
        tests = glob.glob(self.test_path + "/**/*Test.java", recursive=True)
        target_project = os.path.basename(self.target_path.rstrip('/'))
        for dir_name in ("test_cases", "compiler_output", "test_output", "report"):
            os.makedirs(os.path.join(target_dir, dir_name), exist_ok=True)
        print("Copying tests to", target_project, '...')
        for tc in tests:
            tc_norm = os.path.normpath(tc)
            parts = tc_norm.split(os.sep)
            tc_project = None
            for part in reversed(parts[:-1]):
                if '%' in part:
                    tokens = part.split('%')
                    if len(tokens) >= 2 and tokens[1]:
                        tc_project = tokens[1]
                        break
            if not tc_project and target_project in parts:
                tc_project = target_project
            if not tc_project:
                print(f"Skipping test with unexpected path: {tc}")
                continue
            if tc_project != target_project or not os.path.exists(self.target_path):
                continue
            os.system(f"cp {tc} {os.path.join(target_dir, 'test_cases')}")