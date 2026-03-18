import mysql.connector
from mysql.connector import Error, errors  
import warnings
import time
from config import config

class database(object):
    def __init__(self):
        self.user = config.get("database", "user")
        self.password = config.get("database", "password")
        self.database = config.get("database", "database")
        self.unix_socket = config.get("database", "unix_socket")
        # 读取3307端口（仅作为备用，核心用socket）
        self.port = config.getint("database", "port") if config.has_option("database", "port") else 3307
        
        
        self.db = None  
        self.cursor = None
        
        # ========== 核心修改：关闭连接池，简化配置 ==========
        self.connect_config = {
            'user': self.user,
            'password': self.password,
            'database': self.database,
            'unix_socket': self.unix_socket,
            'port': self.port,
            'charset': 'utf8mb4',
            'connection_timeout': 300,
            'autocommit': True,
            'auth_plugin': 'mysql_native_password',
        }
        self.connect()

    def connect(self):
        """重构连接逻辑：关闭连接池，手动设置SESSION参数"""
        retry_count = 3
        while retry_count > 0:
            try:
                # 清理无效连接
                if self.db:
                    try:
                        self.db.close()
                    except:
                        pass
                self.db = None
                self.cursor = None

                # ========== 1. 建立基础连接（无池化、无初始化命令） ==========
                self.db = mysql.connector.connect(**self.connect_config)
                self.cursor = self.db.cursor(dictionary=True)
                print(f"✅ 数据库连接成功（socket：{self.unix_socket}，端口：{self.port}）")

                # ========== 2. 手动执行SESSION配置（连接建立后执行，避免初始化时断开） ==========
                try:
                    self.cursor.execute("SET SESSION wait_timeout=86400;")
                    self.cursor.execute("SET SESSION interactive_timeout=86400;")
                    print("✅ 数据库SESSION配置生效")
                except Exception as e:
                    print(f"⚠️ SESSION配置执行失败（不影响核心连接）：{e}")

                print("✅ 数据库连接完全成功")
                return
            
            except errors.OperationalError as e:
                retry_count -= 1
                print(f"❌ 数据库连接失败：{e}，剩余重试次数：{retry_count}")
                time.sleep(5)
            except Exception as e:
                retry_count -= 1
                print(f"❌ 数据库连接未知错误：{e}，剩余重试次数：{retry_count}")
                time.sleep(5)
        
        raise Exception("数据库连接失败，重试3次后仍无法连接")

    def ping(self):
        """简化保活逻辑：只ping，不重连（避免嵌套重连）"""
        try:
            if self.db and self.db.is_connected():
                self.db.ping(reconnect=False)  # 关闭自动重连，手动控制
            else:
                self.connect()
        except Exception as e:
            print(f"⚠️ MySQL ping失败，重新建立连接：{e}")
            self.connect()

    def execute(self, script, values=None):
        """简化执行逻辑：避免过度重连"""
        try:
            if not self.db or not self.db.is_connected():
                self.connect()

            self.cursor = self.db.cursor(buffered=True, dictionary=True)
            if values:
                self.cursor.execute(script, values)
            else:
                self.cursor.execute(script)
            return self.cursor
        
        except errors.OperationalError as e:
            if "Lost connection" in str(e):
                print(f"⚠️ 数据库连接断开，重新建立连接：{e}")
                self.connect()
                self.cursor = self.db.cursor(buffered=True, dictionary=True)
                if values:
                    self.cursor.execute(script, values)
                else:
                    self.cursor.execute(script)
                return self.cursor
            else:
                raise e

    # ========== 保留你原有select/insert/delete/update/create_table/drop_table方法 ==========
    def select(self, table_name: str = "", conditions=None, result_cols="*", script=None):
        if self.db is None or not self.db.is_connected():
            self.connect()
        self.ping()
        self.cursor = self.db.cursor(buffered=True)
        if script is None:
            if table_name == "":
                raise RuntimeError("if script is not provided, table_name is required.")
            if isinstance(result_cols, list):
                result_cols = ", ".join(result_cols)
            script = f"SELECT {result_cols} FROM {table_name}"
            values = []
            if conditions:
                where_clauses = []
                for key, value in conditions.items():
                    if value is None:
                        where_clauses.append(f"{key} IS %s")
                    else:
                        where_clauses.append(f"{key} = %s")
                    values.append(value)
                script += " WHERE " + " AND ".join(where_clauses)
            self.cursor.execute(script, values)
        else:
            self.cursor.execute(script)
        result = self.cursor.fetchall()
        return result

    def insert(self, table_name, row: dict):
        column_names = ", ".join(row.keys())
        column_values = tuple(x for x in row.values())
        script = r"""INSERT INTO {} ({}) VALUES {}""".format(table_name, column_names, column_values)
        if self.db is None:
            self.connect()
        try:
            self.cursor.execute(script)
        except Exception as e:
            warnings.warn("Error mes:{} \nScript: {}".format(e, script), Warning)
            return
        self.db.commit()

    def delete(self, table_name, conditions: dict):
        script = "DELETE FROM {} WHERE".format(table_name)
        if self.db is None:
            self.connect()
        for key, value in conditions.items():
            script += " {} = %s AND".format(key)
        script = script[:-4]
        self.cursor.execute(script, list(conditions.values()))
        self.db.commit()

    def update(self, table_name, conditions: dict, new_cols: dict):
        if self.db is None:
            self.connect()
        set_pairs = [f"{column}=%s" for column, value in new_cols.items()]
        where_pairs = [f"{column}=%s" for column, value in conditions.items()]
        set_clause = ", ".join(set_pairs)
        where_clause = " AND ".join(where_pairs)
        all_values = list(new_cols.values()) + list(conditions.values())
        script = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        self.cursor.execute(script, all_values)
        self.db.commit()

def create_table():
    db = database()
    sql_script = """
        CREATE TABLE IF NOT EXISTS `class` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `project_name` VARCHAR(255) NOT NULL,
        `class_name` VARCHAR(255) NOT NULL,
        `class_path` VARCHAR(255) NOT NULL,
        `signature` TEXT NOT NULL,
        `super_class` TEXT NULL,
        `package` TEXT NULL,
        `imports` TEXT NULL,
        `fields` LONGTEXT NULL,
        `has_constructor` TINYINT(1) NOT NULL,
        `dependencies` TEXT NULL,
        CONSTRAINT `project_name` UNIQUE (`project_name`, `class_name`)
    );
        CREATE TABLE IF NOT EXISTS `method` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `project_name` VARCHAR(255) NOT NULL,
        `signature` TEXT NOT NULL,
        `method_name` VARCHAR(255) NOT NULL,
        `parameters` TEXT NOT NULL,
        `source_code` LONGTEXT NOT NULL,
        `class_name` VARCHAR(255) NOT NULL,
        `dependencies` LONGTEXT NULL,
        `use_field` TINYINT(1) NOT NULL,
        `is_constructor` TINYINT(1) NOT NULL,
        `is_get_set` TINYINT(1) NOT NULL,
        `is_public` TINYINT(1) NOT NULL
    );
    """
    db.execute(sql_script)

def drop_table():
    db = database()
    sql_script = """
        DROP TABLE IF EXISTS chatunitest.class;
        DROP TABLE IF EXISTS chatunitest.method;
    """
    db.execute(sql_script)