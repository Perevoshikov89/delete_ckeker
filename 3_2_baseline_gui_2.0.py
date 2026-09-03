import json
import re
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import html


# ============================================================
# DLL
# ============================================================

_DLL_DIR_HANDLES = []


def setup_db2_dll_path():

    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

    dll_paths = [
        os.path.join(base_dir, "clidriver", "bin"),
        os.path.join(base_dir, "bin"),
    ]

    for path in dll_paths:

        if os.path.isdir(path):

            _DLL_DIR_HANDLES.append(
                os.add_dll_directory(path)
            )


setup_db2_dll_path()

import ibm_db


# ============================================================
# КОНСТАНТЫ
# ============================================================

HOST = "10.230.227.100"
PORT = "2668"
DATABASE = "cprosd22"
SCHEMA = "INDIC"
USER = "yperevos"


TABLES = [
    "ru_collatrepay",
    "ru_legalrecord",
    "ru_obligtermination",
    "ru_funddate",
    "ru_account_amt",
    "ru_coborrower",
    "ru_sourcenonmonetoblig",
    "ru_contract_terms_changes",
    "ru_all_arrears",
    "ru_trade",
    "ru_acquirerlegal",
    "ru_provision_payment_offset",
    "ru_subjectnonmonetoblig",
    "ru_serviceco",
    "ru_guarantor",
    "ru_paymt_condition",
    "ru_submithold",
    "ru_prevorgacquirer",
    "ru_collatinsured",
    "ru_amendment",
]


# ============================================================
# ПРИЛОЖЕНИЕ
# ============================================================

class BaselineApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "3.2 Regression Checker — DB Baseline"
        )

        self.root.geometry(
            "1100x850"
        )

        self.root.minsize(
            900,
            700
        )

        self.baseline = None

        self.before_baseline = None
        self.after_baseline = None

        self.loader_info = None

        # ====================================================
        # HTML REPORT STATE
        # ====================================================

        self.report_data = None
        self.log_entries = []
        self.report_ready = False
        self.report_file = None

        self.create_ui()

    # ========================================================
    # UI
    # ========================================================

    def create_ui(self):

        main = ttk.Frame(
            self.root,
            padding=15
        )

        main.pack(
            fill="both",
            expand=True
        )

        title = ttk.Label(
            main,
            text="3.2 Regression Checker",
            font=("Segoe UI", 18, "bold")
        )

        title.pack(
            anchor="w"
        )

        subtitle = ttk.Label(
            main,
            text=(
                "READ ONLY: BEFORE → loader 3.2 → AFTER. "
                "Сравнение удаления записей и контрольного UID."
            )
        )

        subtitle.pack(
            anchor="w",
            pady=(0, 15)
        )

        # ----------------------------------------------------
        # DB
        # ----------------------------------------------------

        db_frame = ttk.LabelFrame(
            main,
            text="Подключение к Db2",
            padding=10
        )

        db_frame.pack(
            fill="x"
        )

        self.host = self.add_field(
            db_frame,
            "Host:",
            HOST,
            0
        )

        self.port = self.add_field(
            db_frame,
            "Port:",
            PORT,
            1
        )

        self.database = self.add_field(
            db_frame,
            "Database:",
            DATABASE,
            2
        )

        self.schema = self.add_field(
            db_frame,
            "Schema:",
            SCHEMA,
            3
        )

        self.user = self.add_field(
            db_frame,
            "User:",
            USER,
            4
        )

        self.password = self.add_field(
            db_frame,
            "Password:",
            "",
            5,
            show="*"
        )

        # ----------------------------------------------------
        # Параметры 3.2
        # ----------------------------------------------------

        param_frame = ttk.LabelFrame(
            main,
            text="Параметры проверки 3.2",
            padding=10
        )

        param_frame.pack(
            fill="x",
            pady=(10, 0)
        )

        ttk.Label(
            param_frame,
            text="FID:"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.fid = ttk.Entry(
            param_frame,
            width=35
        )

        self.fid.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(10, 20)
        )

        ttk.Label(
            param_frame,
            text="TARGET UID / SN:"
        ).grid(
            row=0,
            column=2,
            sticky="w"
        )

        self.target_uid = ttk.Entry(
            param_frame,
            width=35
        )

        self.target_uid.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=(10, 0)
        )

        param_frame.columnconfigure(
            1,
            weight=1
        )

        param_frame.columnconfigure(
            3,
            weight=1
        )

        # ----------------------------------------------------
        # BEFORE / AFTER
        # ----------------------------------------------------

        snapshot_frame = ttk.LabelFrame(
            main,
            text="BEFORE / AFTER baseline",
            padding=10
        )

        snapshot_frame.pack(
            fill="x",
            pady=(10, 0)
        )

        self.before_label = ttk.Label(
            snapshot_frame,
            text="BEFORE: не загружен"
        )

        self.before_label.grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.load_before_button = ttk.Button(
            snapshot_frame,
            text="Загрузить BEFORE",
            command=self.load_before
        )

        self.load_before_button.grid(
            row=0,
            column=1,
            padx=10
        )

        self.after_label = ttk.Label(
            snapshot_frame,
            text="AFTER: не загружен"
        )

        self.after_label.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(7, 0)
        )

        self.load_after_button = ttk.Button(
            snapshot_frame,
            text="Загрузить AFTER",
            command=self.load_after
        )

        self.load_after_button.grid(
            row=1,
            column=1,
            padx=10,
            pady=(7, 0)
        )

        snapshot_frame.columnconfigure(
            0,
            weight=1
        )

        # ----------------------------------------------------
        # Кнопки
        # ----------------------------------------------------

        buttons = ttk.Frame(
            main
        )

        buttons.pack(
            fill="x",
            pady=12
        )

        self.test_button = ttk.Button(
            buttons,
            text="Проверить подключение",
            command=self.test_connection
        )

        self.test_button.pack(
            side="left"
        )

        self.baseline_button = ttk.Button(
            buttons,
            text="Снять BASELINE",
            command=self.start_baseline
        )

        self.baseline_button.pack(
            side="left",
            padx=10
        )

        self.save_button = ttk.Button(
            buttons,
            text="Сохранить текущий BASELINE",
            command=self.save_baseline,
            state="disabled"
        )

        self.save_button.pack(
            side="left"
        )

        self.use_before_button = ttk.Button(
            buttons,
            text="Текущий → BEFORE",
            command=self.use_current_as_before,
            state="disabled"
        )

        self.use_before_button.pack(
            side="left",
            padx=(10, 0)
        )

        self.use_after_button = ttk.Button(
            buttons,
            text="Текущий → AFTER",
            command=self.use_current_as_after,
            state="disabled"
        )

        self.use_after_button.pack(
            side="left",
            padx=5
        )

        # ----------------------------------------------------
        # Loader
        # ----------------------------------------------------

        loader_frame = ttk.LabelFrame(
            main,
            text="Сообщение loader для события 3.2",
            padding=8
        )

        loader_frame.pack(
            fill="both",
            expand=False,
            pady=(5, 0)
        )

        loader_hint = ttk.Label(
            loader_frame,
            text=(
                "Вставь блок строк Deleting ... for 3_2. "
                "Если есть строка Correcting uid..., "
                "FID/TARGET/startDateTime определятся автоматически."
            )
        )

        loader_hint.pack(
            anchor="w",
            pady=(0, 5)
        )

        loader_text_frame = ttk.Frame(
            loader_frame
        )

        loader_text_frame.pack(
            fill="both",
            expand=True
        )

        self.loader_text = tk.Text(
            loader_text_frame,
            height=10,
            wrap="none",
            font=("Consolas", 9)
        )

        self.loader_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        loader_scroll_y = ttk.Scrollbar(
            loader_text_frame,
            orient="vertical",
            command=self.loader_text.yview
        )

        loader_scroll_y.pack(
            side="right",
            fill="y"
        )

        self.loader_text.configure(
            yscrollcommand=loader_scroll_y.set
        )

        # ----------------------------------------------------
        # Проверка
        # ----------------------------------------------------

        check_frame = ttk.Frame(
            main
        )

        check_frame.pack(
            fill="x",
            pady=10
        )

        self.check_button = ttk.Button(
            check_frame,
            text="ПРОВЕРИТЬ EVENT 3.2",
            command=self.check_event_3_2
        )

        self.check_button.pack(
            side="left"
        )

        # ====================================================
        # НОВАЯ КНОПКА HTML
        # ====================================================

        self.save_report_button = ttk.Button(
            check_frame,
            text="СОХРАНИТЬ HTML-ОТЧЁТ",
            command=self.save_html_report,
            state="disabled"
        )

        self.save_report_button.pack(
            side="left",
            padx=10
        )

        self.clear_loader_button = ttk.Button(
            check_frame,
            text="Очистить сообщение loader",
            command=self.clear_loader
        )

        self.clear_loader_button.pack(
            side="left"
        )

        # ----------------------------------------------------
        # Прогресс
        # ----------------------------------------------------

        progress_frame = ttk.Frame(
            main
        )

        progress_frame.pack(
            fill="x"
        )

        self.progress = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=len(TABLES)
        )

        self.progress.pack(
            fill="x"
        )

        self.progress_label = ttk.Label(
            progress_frame,
            text="Готово к работе"
        )

        self.progress_label.pack(
            anchor="w",
            pady=(5, 0)
        )

        # ----------------------------------------------------
        # Журнал
        # ----------------------------------------------------

        log_frame = ttk.LabelFrame(
            main,
            text="Журнал",
            padding=5
        )

        log_frame.pack(
            fill="both",
            expand=True,
            pady=(10, 0)
        )

        self.log = tk.Text(
            log_frame,
            wrap="none",
            font=("Consolas", 10)
        )

        self.log.pack(
            side="left",
            fill="both",
            expand=True
        )

        log_scroll = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log.yview
        )

        log_scroll.pack(
            side="right",
            fill="y"
        )

        self.log.configure(
            yscrollcommand=log_scroll.set
        )

        self.write_log(
            "Программа запущена."
        )

        self.write_log(
            "Режим БД: READ ONLY — используются только SELECT."
        )

        self.write_log(
            "Для проверки нужны BEFORE и AFTER baseline."
        )

    # ========================================================
    # Поле
    # ========================================================

    def add_field(
        self,
        parent,
        label,
        value,
        row,
        show=None
    ):

        ttk.Label(
            parent,
            text=label,
            width=16
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=3
        )

        entry = ttk.Entry(
            parent,
            width=50,
            show=show
        )

        entry.insert(
            0,
            value
        )

        entry.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=(5, 0),
            pady=3
        )

        parent.columnconfigure(
            1,
            weight=1
        )

        return entry

    # ========================================================
    # Очистка loader
    # ========================================================

    def clear_loader(self):

        self.loader_text.delete(
            "1.0",
            "end"
        )

        self.write_log(
            "Поле сообщения loader очищено."
        )

    # ========================================================
    # Лог
    # ========================================================

    def write_log(
        self,
        text
    ):

        timestamp = datetime.now().strftime(
            "%H:%M:%S"
        )

        text = str(text)

        # Сохраняем запись для HTML-отчёта
        self.log_entries.append({
            "time": timestamp,
            "text": text
        })

        def append():

            self.log.insert(
                "end",
                f"[{timestamp}] {text}\n"
            )

            self.log.see(
                "end"
            )

        self.root.after(
            0,
            append
        )

    # ========================================================
    # DB CONNECTION
    # ========================================================

    def get_connection(self):

        host = self.host.get().strip()
        port = self.port.get().strip()
        database = self.database.get().strip()
        user = self.user.get().strip()
        password = self.password.get()

        conn_str = (
            f"DATABASE={database};"
            f"HOSTNAME={host};"
            f"PORT={port};"
            f"PROTOCOL=TCPIP;"
            f"UID={user};"
            f"PWD={password};"
        )

        return ibm_db.connect(
            conn_str,
            "",
            ""
        )

    # ========================================================
    # Проверка подключения
    # ========================================================

    def test_connection(self):

        self.test_button.config(
            state="disabled"
        )

        self.write_log(
            "Проверяем подключение к Db2..."
        )

        thread = threading.Thread(
            target=self.test_connection_thread,
            daemon=True
        )

        thread.start()

    def test_connection_thread(self):

        conn = None

        try:

            conn = self.get_connection()

            sql = """
                SELECT
                    CURRENT SERVER,
                    CURRENT SCHEMA
                FROM SYSIBM.SYSDUMMY1
            """

            stmt = ibm_db.exec_immediate(
                conn,
                sql
            )

            row = ibm_db.fetch_assoc(
                stmt
            )

            server = row["CURRENT SERVER"]
            schema = row["CURRENT SCHEMA"]

            self.write_log(
                f"✓ Подключение успешно. "
                f"SERVER={server}, SCHEMA={schema}"
            )

            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Подключение",
                    f"Подключение успешно!\n\n"
                    f"Server: {server}\n"
                    f"Schema: {schema}"
                )
            )

        except Exception as e:

            self.write_log(
                f"✗ Ошибка подключения: {e}"
            )

            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Ошибка подключения",
                    str(e)
                )
            )

        finally:

            if conn is not None:

                try:
                    ibm_db.close(conn)
                except Exception:
                    pass

            self.root.after(
                0,
                lambda: self.test_button.config(
                    state="normal"
                )
            )

    # ========================================================
    # START BASELINE
    # ========================================================

    def start_baseline(self):

        fid = self.fid.get().strip()

        if not fid:

            messagebox.showwarning(
                "FID",
                "Укажи FID тестового субъекта."
            )

            return

        self.baseline_button.config(
            state="disabled"
        )

        self.test_button.config(
            state="disabled"
        )

        self.save_button.config(
            state="disabled"
        )

        self.use_before_button.config(
            state="disabled"
        )

        self.use_after_button.config(
            state="disabled"
        )

        self.progress["value"] = 0

        self.progress_label.config(
            text="Начинаем..."
        )

        self.log.delete(
            "1.0",
            "end"
        )

        # Новый запуск baseline — старый журнал отчёта не нужен
        self.log_entries = []

        # Сбрасываем старый отчёт
        self.report_data = None
        self.report_ready = False
        self.report_file = None

        self.save_report_button.config(
            state="disabled"
        )

        self.write_log(
            f"Начинаем снятие BASELINE для FID={fid}"
        )

        thread = threading.Thread(
            target=self.baseline_thread,
            args=(fid,),
            daemon=True
        )

        thread.start()

    # ========================================================
    # BASELINE
    # ========================================================

    def baseline_thread(
        self,
        fid
    ):

        conn = None

        try:

            self.write_log(
                "Подключение к Db2..."
            )

            conn = self.get_connection()

            self.write_log(
                "✓ Подключение установлено."
            )

            result = {
                "created_at": datetime.now().isoformat(
                    timespec="seconds"
                ),
                "database": self.database.get().strip(),
                "schema": self.schema.get().strip(),
                "fid": fid,
                "tables": {}
            }

            total = 0

            for index, table in enumerate(
                TABLES,
                start=1
            ):

                self.update_progress(
                    index,
                    table
                )

                self.write_log(
                    f"[{index:02d}/{len(TABLES)}] "
                    f"{table}"
                )

                rows = self.read_table(
                    conn,
                    table,
                    fid
                )

                result["tables"][table] = rows

                if isinstance(
                    rows,
                    dict
                ):

                    self.write_log(
                        f"    ✗ ERROR: "
                        f"{rows['error']}"
                    )

                else:

                    table_total = sum(
                        row["count"]
                        for row in rows
                    )

                    total += table_total

                    self.write_log(
                        f"    записей: "
                        f"{table_total}"
                    )

                    for row in rows:

                        self.write_log(
                            f"      "
                            f"{row['acc_serial_num']} | "
                            f"{row['reported_dt']} | "
                            f"{row['count']}"
                        )

            result["total_records"] = total

            self.baseline = result

            self.write_log("")
            self.write_log(
                "=========================================="
            )
            self.write_log(
                "BASELINE ГОТОВ"
            )
            self.write_log(
                f"Всего записей: {total}"
            )
            self.write_log(
                "=========================================="
            )

            self.root.after(
                0,
                lambda: self.save_button.config(
                    state="normal"
                )
            )

            self.root.after(
                0,
                lambda: self.use_before_button.config(
                    state="normal"
                )
            )

            self.root.after(
                0,
                lambda: self.use_after_button.config(
                    state="normal"
                )
            )

            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "BASELINE",
                    f"Baseline успешно снят.\n\n"
                    f"FID: {fid}\n"
                    f"Таблиц: {len(TABLES)}\n"
                    f"Записей: {total}"
                )
            )

        except Exception as e:

            self.write_log(
                f"✗ КРИТИЧЕСКАЯ ОШИБКА: {e}"
            )

            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Ошибка",
                    str(e)
                )
            )

        finally:

            if conn is not None:

                try:
                    ibm_db.close(conn)
                except Exception:
                    pass

            self.root.after(
                0,
                lambda: self.baseline_button.config(
                    state="normal"
                )
            )

            self.root.after(
                0,
                lambda: self.test_button.config(
                    state="normal"
                )
            )

    # ========================================================
    # Чтение таблицы
    # ========================================================

    def read_table(
        self,
        conn,
        table,
        fid
    ):

        sql = f"""
            SELECT
                fid,
                acc_serial_num,
                reported_dt,
                COUNT(*) AS cnt
            FROM {SCHEMA}.{table}
            WHERE fid = ?
            GROUP BY
                fid,
                acc_serial_num,
                reported_dt
            ORDER BY
                acc_serial_num,
                reported_dt
        """

        try:

            stmt = ibm_db.prepare(
                conn,
                sql
            )

            ibm_db.bind_param(
                stmt,
                1,
                fid
            )

            ibm_db.execute(
                stmt
            )

            rows = []

            while True:

                row = ibm_db.fetch_assoc(
                    stmt
                )

                if not row:
                    break

                rows.append({
                    "fid": str(
                        row["FID"]
                    ),
                    "acc_serial_num": str(
                        row["ACC_SERIAL_NUM"]
                    ),
                    "reported_dt": (
                        str(
                            row["REPORTED_DT"]
                        )
                        if row["REPORTED_DT"] is not None
                        else None
                    ),
                    "count": int(
                        row["CNT"]
                    )
                })

            return rows

        except Exception as e:

            return {
                "error": str(e)
            }

    # ========================================================
    # Прогресс
    # ========================================================

    def update_progress(
        self,
        value,
        table
    ):

        def update():

            self.progress["value"] = value

            self.progress_label.config(
                text=(
                    f"Обработка: "
                    f"{value}/{len(TABLES)} — "
                    f"{table}"
                )
            )

        self.root.after(
            0,
            update
        )

    # ========================================================
    # Сохранение BASELINE
    # ========================================================

    def save_baseline(self):

        if not self.baseline:
            return

        default_name = (
            "3_2_baseline_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".json"
        )

        filename = filedialog.asksaveasfilename(
            title="Сохранить BASELINE",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )

        if not filename:
            return

        try:

            with open(
                filename,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    self.baseline,
                    file,
                    ensure_ascii=False,
                    indent=4
                )

            self.write_log(
                f"✓ BASELINE сохранён: {filename}"
            )

            messagebox.showinfo(
                "Сохранение",
                f"Baseline сохранён:\n\n{filename}"
            )

        except Exception as e:

            messagebox.showerror(
                "Ошибка сохранения",
                str(e)
            )

    # ========================================================
    # BEFORE / AFTER
    # ========================================================

    def use_current_as_before(self):

        if not self.baseline:
            return

        self.before_baseline = self.baseline

        self.before_label.config(
            text=(
                f"BEFORE: "
                f"FID={self.baseline.get('fid')} | "
                f"{self.baseline.get('created_at')} | "
                f"записей="
                f"{self.baseline.get('total_records')}"
            )
        )

        self.write_log(
            "✓ Текущий BASELINE назначен как BEFORE."
        )

    def use_current_as_after(self):

        if not self.baseline:
            return

        self.after_baseline = self.baseline

        self.after_label.config(
            text=(
                f"AFTER: "
                f"FID={self.baseline.get('fid')} | "
                f"{self.baseline.get('created_at')} | "
                f"записей="
                f"{self.baseline.get('total_records')}"
            )
        )

        self.write_log(
            "✓ Текущий BASELINE назначен как AFTER."
        )

    # ========================================================
    # Загрузка BEFORE
    # ========================================================

    def load_before(self):

        filename = filedialog.askopenfilename(
            title="Выбрать BEFORE baseline",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )

        if not filename:
            return

        try:

            data = self.load_baseline_file(
                filename
            )

            self.validate_baseline(
                data
            )

            self.before_baseline = data

            self.before_label.config(
                text=(
                    f"BEFORE: "
                    f"{os.path.basename(filename)} | "
                    f"FID={data.get('fid')} | "
                    f"записей="
                    f"{data.get('total_records')}"
                )
            )

            if data.get("fid"):

                self.fid.delete(
                    0,
                    "end"
                )

                self.fid.insert(
                    0,
                    str(data["fid"])
                )

            self.write_log(
                f"✓ BEFORE загружен: {filename}"
            )

        except Exception as e:

            messagebox.showerror(
                "Ошибка BEFORE",
                str(e)
            )

    # ========================================================
    # Загрузка AFTER
    # ========================================================

    def load_after(self):

        filename = filedialog.askopenfilename(
            title="Выбрать AFTER baseline",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )

        if not filename:
            return

        try:

            data = self.load_baseline_file(
                filename
            )

            self.validate_baseline(
                data
            )

            self.after_baseline = data

            self.after_label.config(
                text=(
                    f"AFTER: "
                    f"{os.path.basename(filename)} | "
                    f"FID={data.get('fid')} | "
                    f"записей="
                    f"{data.get('total_records')}"
                )
            )

            if data.get("fid"):

                self.fid.delete(
                    0,
                    "end"
                )

                self.fid.insert(
                    0,
                    str(data["fid"])
                )

            self.write_log(
                f"✓ AFTER загружен: {filename}"
            )

        except Exception as e:

            messagebox.showerror(
                "Ошибка AFTER",
                str(e)
            )

    # ========================================================
    # Работа с JSON
    # ========================================================

    def load_baseline_file(
        self,
        filename
    ):

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(
                file
            )

    def validate_baseline(
        self,
        data
    ):

        if not isinstance(
            data,
            dict
        ):

            raise ValueError(
                "Файл baseline должен "
                "содержать JSON-объект."
            )

        if "fid" not in data:

            raise ValueError(
                "В baseline отсутствует поле fid."
            )

        if "tables" not in data:

            raise ValueError(
                "В baseline отсутствует поле tables."
            )

        if not isinstance(
            data["tables"],
            dict
        ):

            raise ValueError(
                "Поле tables имеет неправильный формат."
            )

    # ========================================================
    # PARSE LOADER
    # ========================================================

    def parse_loader_message(
        self,
        text
    ):

        if not text.strip():

            raise ValueError(
                "Поле сообщения loader пустое."
            )

        deletions = {}

        deletion_pattern = re.compile(
            r"Deleting\s+(\d+)\s+records\s+in\s+"
            r"([A-Za-z0-9_]+)\s+for\s+3_2",
            re.IGNORECASE
        )

        for match in deletion_pattern.finditer(
            text
        ):

            count = int(
                match.group(1)
            )

            table = match.group(2).lower()

            if table not in TABLES:
                continue

            deletions[table] = count

        if not deletions:

            raise ValueError(
                "Не найдено ни одной строки:\n\n"
                "Deleting N records in TABLE for 3_2"
            )

        fid = None
        target_uid = None
        start_datetime = None

        correcting_pattern = re.compile(
            r"Correcting\s+uid\s+in\s+3_2\s+mode:\s*"
            r"fid\s+([^,\s]+),\s*"
            r"sn\s+([^,\s]+),\s*"
            r"startDateTime\s+(.+?)(?:\r?\n|$)",
            re.IGNORECASE
        )

        correcting_match = correcting_pattern.search(
            text
        )

        if correcting_match:

            fid = correcting_match.group(
                1
            ).strip()

            target_uid = correcting_match.group(
                2
            ).strip()

            start_datetime = correcting_match.group(
                3
            ).strip()

        return {
            "fid": fid,
            "target_uid": target_uid,
            "start_datetime": start_datetime,
            "deletions": deletions
        }

    # ========================================================
    # Вспомогательные функции
    # ========================================================

    def table_rows(
        self,
        baseline,
        table
    ):

        if not baseline:
            return []

        rows = baseline.get(
            "tables",
            {}
        ).get(
            table,
            []
        )

        if isinstance(
            rows,
            dict
        ):
            return []

        return rows

    def total_for_uid(
        self,
        baseline,
        table,
        uid
    ):

        total = 0

        for row in self.table_rows(
            baseline,
            table
        ):

            if str(
                row.get("acc_serial_num")
            ) == str(uid):

                total += int(
                    row.get("count", 0)
                )

        return total

    def all_uids(
        self,
        baseline
    ):

        result = set()

        if not baseline:
            return result

        for table in TABLES:

            for row in self.table_rows(
                baseline,
                table
            ):

                uid = row.get(
                    "acc_serial_num"
                )

                if uid is not None:

                    result.add(
                        str(uid)
                    )

        return result

    def get_table_total(
        self,
        baseline,
        table
    ):

        return sum(
            int(
                row.get(
                    "count",
                    0
                )
            )
            for row in self.table_rows(
                baseline,
                table
            )
        )

    # ========================================================
    # Детализация UID + reported_dt
    # ========================================================

    def get_uid_details(
        self,
        baseline,
        table,
        uid
    ):

        result = {}

        for row in self.table_rows(
            baseline,
            table
        ):

            if str(
                row.get("acc_serial_num")
            ) != str(uid):

                continue

            reported_dt = row.get(
                "reported_dt"
            )

            key = (
                str(reported_dt)
                if reported_dt is not None
                else "NULL"
            )

            result[key] = (
                result.get(key, 0)
                +
                int(
                    row.get(
                        "count",
                        0
                    )
                )
            )

        return result

    def write_uid_details(
        self,
        table,
        uid,
        before,
        after
    ):

        before_details = self.get_uid_details(
            before,
            table,
            uid
        )

        after_details = self.get_uid_details(
            after,
            table,
            uid
        )

        dates = (
            set(before_details.keys())
            |
            set(after_details.keys())
        )

        details_result = []

        if not dates:
            return details_result

        for reported_dt in sorted(
            dates
        ):

            before_count = before_details.get(
                reported_dt,
                0
            )

            after_count = after_details.get(
                reported_dt,
                0
            )

            deleted = (
                before_count -
                after_count
            )

            details_result.append({
                "uid": str(uid),
                "reported_dt": reported_dt,
                "before": before_count,
                "after": after_count,
                "deleted": deleted
            })

            self.write_log(
                f"    {uid:<12} | "
                f"{reported_dt:<25} | "
                f"{before_count:>6} | "
                f"{after_count:>5} | "
                f"{deleted:>7}"
            )

        return details_result

    # ========================================================
    # CHECK EVENT 3.2
    # ========================================================

    def check_event_3_2(self):

        # Сбрасываем предыдущий HTML-отчёт.
        self.report_ready = False
        self.report_data = None
        self.report_file = None

        self.save_report_button.config(
            state="disabled"
        )

        try:

            if not self.before_baseline:

                raise ValueError(
                    "Не загружен BEFORE baseline."
                )

            if not self.after_baseline:

                raise ValueError(
                    "Не загружен AFTER baseline."
                )

            before_fid = str(
                self.before_baseline.get(
                    "fid",
                    ""
                )
            )

            after_fid = str(
                self.after_baseline.get(
                    "fid",
                    ""
                )
            )

            if before_fid != after_fid:

                raise ValueError(
                    "BEFORE и AFTER относятся "
                    "к разным FID:\n\n"
                    f"BEFORE = {before_fid}\n"
                    f"AFTER  = {after_fid}"
                )

            loader_text = self.loader_text.get(
                "1.0",
                "end"
            )

            parsed = self.parse_loader_message(
                loader_text
            )

            fid = (
                parsed.get("fid")
                or self.fid.get().strip()
            )

            if not fid:

                raise ValueError(
                    "Не указан FID."
                )

            if fid != before_fid:

                raise ValueError(
                    "FID loader/поля не совпадает "
                    "с baseline:\n\n"
                    f"Loader/поле = {fid}\n"
                    f"Baseline    = {before_fid}"
                )

            target_uid = (
                parsed.get("target_uid")
                or self.target_uid.get().strip()
            )

            if not target_uid:

                raise ValueError(
                    "Не удалось определить TARGET UID / SN.\n\n"
                    "Вставь строку:\n"
                    "Correcting uid in 3_2 mode: ...\n\n"
                    "или укажи TARGET UID / SN вручную."
                )

            self.fid.delete(
                0,
                "end"
            )

            self.fid.insert(
                0,
                fid
            )

            self.target_uid.delete(
                0,
                "end"
            )

            self.target_uid.insert(
                0,
                target_uid
            )

            self.loader_info = parsed

            self.run_comparison(
                fid=fid,
                target_uid=target_uid,
                start_datetime=parsed.get(
                    "start_datetime"
                ),
                deletions=parsed["deletions"]
            )

        except Exception as e:

            self.write_log(
                f"✗ Проверка не выполнена: {e}"
            )

            messagebox.showerror(
                "Ошибка проверки 3.2",
                str(e)
            )

    # ========================================================
    # ОСНОВНОЕ СРАВНЕНИЕ
    # ========================================================

    def run_comparison(
        self,
        fid,
        target_uid,
        start_datetime,
        deletions
    ):

        before = self.before_baseline
        after = self.after_baseline

        control_uids = (
            self.all_uids(before)
            |
            self.all_uids(after)
        )

        control_uids.discard(
            str(target_uid)
        )

        # ----------------------------------------------------
        # Новый журнал именно для итоговой проверки
        # ----------------------------------------------------

        self.log.delete(
            "1.0",
            "end"
        )

        self.log_entries = []

        self.report_data = None
        self.report_ready = False
        self.report_file = None

        self.save_report_button.config(
            state="disabled"
        )

        # ----------------------------------------------------
        # Структуры HTML отчёта
        # ----------------------------------------------------

        loader_db_report = []
        target_report = []
        target_detail_report = {}
        control_report = []
        unexpected_increase_report = []

        # ====================================================
        # HEADER
        # ====================================================

        self.write_log(
            "══════════════════════════════════════════"
        )

        self.write_log(
            "EVENT 3.2 REGRESSION CHECK"
        )

        self.write_log(
            "══════════════════════════════════════════"
        )

        self.write_log(
            f"FID:        {fid}"
        )

        self.write_log(
            f"TARGET UID: {target_uid}"
        )

        if start_datetime:

            self.write_log(
                f"START DATE: {start_datetime}"
            )

        else:

            self.write_log(
                "START DATE: не указан"
            )

        # ----------------------------------------------------
        # LOADER
        # ----------------------------------------------------

        self.write_log("")
        self.write_log(
            "LOADER → ожидаемое количество удалений:"
        )

        loader_total = 0

        for table in TABLES:

            count = int(
                deletions.get(
                    table,
                    0
                )
            )

            if count > 0:

                self.write_log(
                    f"  {table}: {count}"
                )

            loader_total += count

        self.write_log(
            f"  ИТОГО: {loader_total}"
        )

        # ====================================================
        # CHECK 1
        # LOADER ↔ DB
        # ====================================================

        self.write_log("")
        self.write_log(
            "LOADER ↔ DB"
        )

        self.write_log(
            "TABLE                         "
            "BEFORE  LOADER  AFTER  УДАЛЕНО  CHECK"
        )

        self.write_log(
            "------------------------------------------------"
        )

        overall_pass = True

        for table in TABLES:

            before_total = self.get_table_total(
                before,
                table
            )

            after_total = self.get_table_total(
                after,
                table
            )

            loader_count = int(
                deletions.get(
                    table,
                    0
                )
            )

            deleted = (
                before_total -
                after_total
            )

            passed = (
                deleted ==
                loader_count
            )

            if not passed:

                overall_pass = False

            status = (
                "PASS"
                if passed
                else "FAIL"
            )

            loader_db_report.append({
                "table": table,
                "before": before_total,
                "loader": loader_count,
                "after": after_total,
                "deleted": deleted,
                "passed": passed
            })

            self.write_log(
                f"{table:<30}"
                f"{before_total:>7} "
                f"{loader_count:>7} "
                f"{after_total:>6} "
                f"{deleted:>8}  "
                f"{status}"
            )

        # ====================================================
        # CHECK 2
        # TARGET UID
        # ====================================================

        self.write_log("")
        self.write_log(
            f"TARGET UID CHECK: {target_uid}"
        )

        self.write_log(
            "TABLE                         "
            "BEFORE  LOADER  AFTER  УДАЛЕНО  CHECK"
        )

        self.write_log(
            "------------------------------------------------"
        )

        target_pass = True

        for table in TABLES:

            before_uid = self.total_for_uid(
                before,
                table,
                target_uid
            )

            after_uid = self.total_for_uid(
                after,
                table,
                target_uid
            )

            loader_count = int(
                deletions.get(
                    table,
                    0
                )
            )

            deleted = (
                before_uid -
                after_uid
            )

            passed = (
                deleted ==
                loader_count
                and
                deleted >= 0
            )

            if not passed:

                target_pass = False

            status = (
                "PASS"
                if passed
                else "FAIL"
            )

            target_report.append({
                "table": table,
                "before": before_uid,
                "loader": loader_count,
                "after": after_uid,
                "deleted": deleted,
                "passed": passed
            })

            self.write_log(
                f"{table:<30}"
                f"{before_uid:>7} "
                f"{loader_count:>7} "
                f"{after_uid:>6} "
                f"{deleted:>8}  "
                f"{status}"
            )

        # ====================================================
        # CHECK 2.1
        # TARGET UID DETAIL
        # ====================================================

        self.write_log("")
        self.write_log(
            "TARGET UID DETAIL: UID + reported_dt"
        )

        self.write_log(
            "TABLE"
        )

        self.write_log(
            "  UID          reported_dt               "
            "BEFORE  AFTER  УДАЛЕНО"
        )

        self.write_log(
            "------------------------------------------------"
        )

        for table in TABLES:

            before_uid = self.total_for_uid(
                before,
                table,
                target_uid
            )

            after_uid = self.total_for_uid(
                after,
                table,
                target_uid
            )

            if (
                before_uid == 0
                and
                after_uid == 0
            ):

                continue

            self.write_log(
                f"{table}:"
            )

            details = self.write_uid_details(
                table,
                target_uid,
                before,
                after
            )

            target_detail_report[table] = details

        # ====================================================
        # CHECK 3
        # CONTROL UID
        # ====================================================

        self.write_log("")
        self.write_log(
            "CONTROL UID CHECK"
        )

        control_pass = True

        if not control_uids:

            self.write_log(
                "Контрольных UID не найдено."
            )

        else:

            for control_uid in sorted(
                control_uids
            ):

                uid_has_problem = False
                control_problems = []

                self.write_log("")
                self.write_log(
                    f"CONTROL UID: {control_uid}"
                )

                for table in TABLES:

                    before_uid = self.total_for_uid(
                        before,
                        table,
                        control_uid
                    )

                    after_uid = self.total_for_uid(
                        after,
                        table,
                        control_uid
                    )

                    deleted = (
                        before_uid -
                        after_uid
                    )

                    if deleted != 0:

                        uid_has_problem = True
                        control_pass = False

                        self.write_log(
                            f"  FAIL {table}: "
                            f"{before_uid} → "
                            f"{after_uid} "
                            f"(удалено {deleted})"
                        )

                        # Детализация проблемного UID
                        self.write_log(
                            "    Детализация:"
                        )

                        self.write_log(
                            "    UID          reported_dt               "
                            "BEFORE  AFTER  УДАЛЕНО"
                        )

                        details = self.write_uid_details(
                            table,
                            control_uid,
                            before,
                            after
                        )

                        control_problems.append({
                            "table": table,
                            "before": before_uid,
                            "after": after_uid,
                            "deleted": deleted,
                            "details": details
                        })

                if not uid_has_problem:

                    self.write_log(
                        "  PASS — изменений удаления "
                        "не обнаружено."
                    )

                control_report.append({
                    "uid": control_uid,
                    "passed": not uid_has_problem,
                    "problems": control_problems
                })

        # ====================================================
        # CHECK 4
        # Неожиданный рост
        # ====================================================

        unexpected_increase = []

        for table in TABLES:

            before_total = self.get_table_total(
                before,
                table
            )

            after_total = self.get_table_total(
                after,
                table
            )

            if after_total > before_total:

                item = {
                    "table": table,
                    "before": before_total,
                    "after": after_total,
                    "increase": (
                        after_total -
                        before_total
                    )
                }

                unexpected_increase.append(
                    item
                )

                unexpected_increase_report.append(
                    item
                )

        if unexpected_increase:

            overall_pass = False

            self.write_log("")
            self.write_log(
                "WARNING/FAIL: AFTER содержит "
                "увеличение количества записей:"
            )

            for item in unexpected_increase:

                self.write_log(
                    f"  {item['table']}: "
                    f"{item['before']} → "
                    f"{item['after']} "
                    f"(+{item['increase']})"
                )

        # ====================================================
        # ИТОГ
        # ====================================================

        final_pass = (
            overall_pass
            and
            target_pass
            and
            control_pass
        )

        self.write_log("")
        self.write_log(
            "══════════════════════════════════════════"
        )

        self.write_log(
            f"LOADER ↔ DB:       "
            f"{'PASS' if overall_pass else 'FAIL'}"
        )

        self.write_log(
            f"TARGET UID:        "
            f"{'PASS' if target_pass else 'FAIL'}"
        )

        self.write_log(
            f"CONTROL UID:       "
            f"{'PASS' if control_pass else 'FAIL'}"
        )

        self.write_log(
            "------------------------------------------"
        )

        self.write_log(
            f"RESULT:            "
            f"{'PASS' if final_pass else 'FAIL'}"
        )

        self.write_log(
            "══════════════════════════════════════════"
        )

        # ====================================================
        # Сохраняем структуру отчёта
        # ====================================================

        self.report_data = {
            "generated_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "fid": str(fid),
            "target_uid": str(target_uid),
            "start_datetime": (
                str(start_datetime)
                if start_datetime
                else "не указан"
            ),

            "loader_total": loader_total,
            "loader_deletions": dict(
                deletions
            ),

            "loader_db": loader_db_report,
            "target": target_report,
            "target_detail": target_detail_report,
            "control": control_report,
            "unexpected_increase": (
                unexpected_increase_report
            ),

            "overall_pass": overall_pass,
            "target_pass": target_pass,
            "control_pass": control_pass,
            "final_pass": final_pass
        }

        # Отчёт доступен даже при FAIL
        self.report_ready = True

        self.save_report_button.config(
            state="normal"
        )

        # ====================================================
        # MESSAGEBOX
        # ====================================================

        if final_pass:

            messagebox.showinfo(
                "EVENT 3.2 — PASS",
                "Проверка события 3.2 пройдена.\n\n"
                f"FID: {fid}\n"
                f"TARGET UID: {target_uid}\n\n"
                "✓ Loader соответствует DB\n"
                "✓ TARGET UID соответствует удалениям\n"
                "✓ CONTROL UID не изменён\n\n"
                "HTML-отчёт можно сохранить кнопкой\n"
                "«СОХРАНИТЬ HTML-ОТЧЁТ»."
            )

        else:

            messagebox.showerror(
                "EVENT 3.2 — FAIL",
                "Обнаружено расхождение.\n\n"
                f"FID: {fid}\n"
                f"TARGET UID: {target_uid}\n\n"
                "Подробности находятся в журнале.\n\n"
                "HTML-отчёт можно сохранить кнопкой\n"
                "«СОХРАНИТЬ HTML-ОТЧЁТ»."
            )

    # ========================================================
    # HTML REPORT
    # ========================================================

    def generate_html_report(self):

        if not self.report_data:
            return ""

        data = self.report_data

        def esc(value):

            if value is None:
                return ""

            return html.escape(
                str(value)
            )

        def result_class(value):

            return (
                "pass"
                if value
                else "fail"
            )

        def result_text(value):

            return (
                "PASS"
                if value
                else "FAIL"
            )

        parts = []

        # ====================================================
        # HTML HEADER
        # ====================================================

        parts.append(
            """<!DOCTYPE html>
<html lang="ru">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>
Event 3.2 Regression Report
</title>

<style>

body {
    font-family:
        "Segoe UI",
        Arial,
        Helvetica,
        sans-serif;

    margin: 0;
    padding: 30px;

    background: #f3f5f7;
    color: #222;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
}

h1 {
    margin-bottom: 5px;
}

h2 {
    margin-top: 35px;
    padding-bottom: 8px;
    border-bottom: 2px solid #555;
}

h3 {
    margin-top: 25px;
}

.header {
    background: white;
    border: 1px solid #d5d9dd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
}

.meta {
    width: 100%;
    border-collapse: collapse;
}

.meta td {
    padding: 8px 10px;
    border-bottom: 1px solid #e5e5e5;
}

.meta td:first-child {
    width: 230px;
    font-weight: bold;
}

.result {
    margin-top: 18px;
    padding: 15px;
    border-radius: 7px;
    font-size: 20px;
    font-weight: bold;
}

.pass {
    color: #176b32;
    background: #e9f7ed;
    border: 1px solid #a9d9b5;
}

.fail {
    color: #a51d2d;
    background: #fdecee;
    border: 1px solid #e5aeb5;
}

.warn {
    color: #795700;
    background: #fff6d8;
    border: 1px solid #e6cd7a;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    margin-top: 10px;
}

th {
    background: #e8ebee;
    font-weight: bold;
}

th,
td {
    border: 1px solid #cfd3d7;
    padding: 7px 9px;
    vertical-align: top;
}

.pass-row {
    background: #f4fbf6;
}

.fail-row {
    background: #fff1f2;
}

.badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 12px;
    font-weight: bold;
}

pre {
    background: #171717;
    color: #eeeeee;
    padding: 15px;
    border-radius: 8px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: Consolas, "Courier New", monospace;
    font-size: 12px;
}

.summary-table td:first-child {
    font-weight: bold;
}

.footer {
    margin-top: 35px;
    color: #777;
    font-size: 12px;
    text-align: center;
}

@media print {

    body {
        background: white;
        padding: 10px;
    }

    .header {
        border: 1px solid #999;
    }

    h2 {
        page-break-after: avoid;
    }

    table {
        page-break-inside: auto;
    }

    tr {
        page-break-inside: avoid;
    }

}

</style>

</head>

<body>

<div class="container">
"""
        )

        # ====================================================
        # HEADER
        # ====================================================

        parts.append(
            f"""
<div class="header">

<h1>
EVENT 3.2 REGRESSION CHECK
</h1>

<table class="meta">

<tr>
<td>Дата формирования отчёта</td>
<td>{esc(data["generated_at"])}</td>
</tr>

<tr>
<td>FID</td>
<td>{esc(data["fid"])}</td>
</tr>

<tr>
<td>TARGET UID</td>
<td>{esc(data["target_uid"])}</td>
</tr>

<tr>
<td>START DATE</td>
<td>{esc(data["start_datetime"])}</td>
</tr>

</table>

<div class="result {result_class(data["final_pass"])}">

FINAL RESULT:
{result_text(data["final_pass"])}

</div>

</div>
"""
        )

        # ====================================================
        # LOADER EXPECTED
        # ====================================================

        parts.append(
            """
<h2>
LOADER → EXPECTED DELETIONS
</h2>

<table>

<tr>
<th>TABLE</th>
<th>EXPECTED DELETIONS</th>
</tr>
"""
        )

        for table, count in data[
            "loader_deletions"
        ].items():

            parts.append(
                f"""
<tr>
<td>{esc(table)}</td>
<td>{esc(count)}</td>
</tr>
"""
            )

        parts.append(
            f"""
<tr>
<th>TOTAL</th>
<th>{esc(data["loader_total"])}</th>
</tr>

</table>
"""
        )

        # ====================================================
        # LOADER ↔ DB
        # ====================================================

        parts.append(
            """
<h2>
LOADER ↔ DB
</h2>

<table>

<tr>
<th>TABLE</th>
<th>BEFORE</th>
<th>LOADER</th>
<th>AFTER</th>
<th>DELETED</th>
<th>RESULT</th>
</tr>
"""
        )

        for row in data["loader_db"]:

            row_class = (
                "pass-row"
                if row["passed"]
                else "fail-row"
            )

            parts.append(
                f"""
<tr class="{row_class}">

<td>{esc(row["table"])}</td>
<td>{esc(row["before"])}</td>
<td>{esc(row["loader"])}</td>
<td>{esc(row["after"])}</td>
<td>{esc(row["deleted"])}</td>

<td>

<span class="badge {result_class(row["passed"])}">

{result_text(row["passed"])}

</span>

</td>

</tr>
"""
            )

        parts.append(
            """
</table>
"""
        )

        # ====================================================
        # TARGET UID
        # ====================================================

        parts.append(
            f"""
<h2>
TARGET UID: {esc(data["target_uid"])}
</h2>

<table>

<tr>
<th>TABLE</th>
<th>BEFORE</th>
<th>LOADER</th>
<th>AFTER</th>
<th>DELETED</th>
<th>RESULT</th>
</tr>
"""
        )

        for row in data["target"]:

            row_class = (
                "pass-row"
                if row["passed"]
                else "fail-row"
            )

            parts.append(
                f"""
<tr class="{row_class}">

<td>{esc(row["table"])}</td>
<td>{esc(row["before"])}</td>
<td>{esc(row["loader"])}</td>
<td>{esc(row["after"])}</td>
<td>{esc(row["deleted"])}</td>

<td>

<span class="badge {result_class(row["passed"])}">

{result_text(row["passed"])}

</span>

</td>

</tr>
"""
            )

        parts.append(
            """
</table>
"""
        )

        # ====================================================
        # TARGET UID DETAIL
        # ====================================================

        parts.append(
            """
<h2>
TARGET UID DETAIL
</h2>
"""
        )

        if not data["target_detail"]:

            parts.append(
                """
<p>
Нет детальных записей для TARGET UID.
</p>
"""
            )

        else:

            for table, details in data[
                "target_detail"
            ].items():

                parts.append(
                    f"""
<h3>
{esc(table)}
</h3>

<table>

<tr>
<th>UID</th>
<th>REPORTED_DT</th>
<th>BEFORE</th>
<th>AFTER</th>
<th>DELETED</th>
</tr>
"""
                )

                if not details:

                    parts.append(
                        """
<tr>
<td colspan="5">
Нет записей.
</td>
</tr>
"""
                    )

                for row in details:

                    row_class = (
                        "pass-row"
                        if row["deleted"] >= 0
                        else "fail-row"
                    )

                    parts.append(
                        f"""
<tr class="{row_class}">

<td>{esc(row["uid"])}</td>
<td>{esc(row["reported_dt"])}</td>
<td>{esc(row["before"])}</td>
<td>{esc(row["after"])}</td>
<td>{esc(row["deleted"])}</td>

</tr>
"""
                    )

                parts.append(
                    """
</table>
"""
                )

        # ====================================================
        # CONTROL UID
        # ====================================================

        parts.append(
            """
<h2>
CONTROL UID CHECK
</h2>
"""
        )

        if not data["control"]:

            parts.append(
                """
<div class="result warn">
Контрольных UID не найдено.
</div>
"""
            )

        else:

            for control in data[
                "control"
            ]:

                passed = control["passed"]

                parts.append(
                    f"""
<div class="result {result_class(passed)}">

CONTROL UID {esc(control["uid"])}
—
{result_text(passed)}

</div>
"""
                )

                problems = control[
                    "problems"
                ]

                if problems:

                    parts.append(
                        """
<table>

<tr>
<th>TABLE</th>
<th>BEFORE</th>
<th>AFTER</th>
<th>DELETED</th>
</tr>
"""
                    )

                    for problem in problems:

                        parts.append(
                            f"""
<tr class="fail-row">

<td>{esc(problem["table"])}</td>
<td>{esc(problem["before"])}</td>
<td>{esc(problem["after"])}</td>
<td>{esc(problem["deleted"])}</td>

</tr>
"""
                        )

                    parts.append(
                        """
</table>
"""
                    )

                    # Детализация control UID
                    for problem in problems:

                        details = problem.get(
                            "details",
                            []
                        )

                        if not details:
                            continue

                        parts.append(
                            f"""
<h3>
CONTROL UID {esc(control["uid"])}
—
{esc(problem["table"])}
DETAIL
</h3>

<table>

<tr>
<th>UID</th>
<th>REPORTED_DT</th>
<th>BEFORE</th>
<th>AFTER</th>
<th>DELETED</th>
</tr>
"""
                        )

                        for detail in details:

                            row_class = (
                                "pass-row"
                                if detail["deleted"] == 0
                                else "fail-row"
                            )

                            parts.append(
                                f"""
<tr class="{row_class}">

<td>{esc(detail["uid"])}</td>
<td>{esc(detail["reported_dt"])}</td>
<td>{esc(detail["before"])}</td>
<td>{esc(detail["after"])}</td>
<td>{esc(detail["deleted"])}</td>

</tr>
"""
                            )

                        parts.append(
                            """
</table>
"""
                        )

                else:

                    parts.append(
                        """
<p>
Удалений контрольного UID не обнаружено.
</p>
"""
                    )

        # ====================================================
        # UNEXPECTED INCREASE
        # ====================================================

        parts.append(
            """
<h2>
UNEXPECTED INCREASE
</h2>
"""
        )

        if data[
            "unexpected_increase"
        ]:

            parts.append(
                """
<table>

<tr>
<th>TABLE</th>
<th>BEFORE</th>
<th>AFTER</th>
<th>INCREASE</th>
</tr>
"""
            )

            for row in data[
                "unexpected_increase"
            ]:

                parts.append(
                    f"""
<tr class="fail-row">

<td>{esc(row["table"])}</td>
<td>{esc(row["before"])}</td>
<td>{esc(row["after"])}</td>
<td>{esc(row["increase"])}</td>

</tr>
"""
                )

            parts.append(
                """
</table>
"""
            )

        else:

            parts.append(
                """
<div class="result pass">

Неожиданного увеличения количества
записей не обнаружено.

</div>
"""
            )

        # ====================================================
        # SUMMARY
        # ====================================================

        parts.append(
            f"""
<h2>
CHECK SUMMARY
</h2>

<table class="summary-table">

<tr>

<td>
LOADER ↔ DB
</td>

<td>

<span class="badge {result_class(data["overall_pass"])}">

{result_text(data["overall_pass"])}

</span>

</td>

</tr>

<tr>

<td>
TARGET UID
</td>

<td>

<span class="badge {result_class(data["target_pass"])}">

{result_text(data["target_pass"])}

</span>

</td>

</tr>

<tr>

<td>
CONTROL UID
</td>

<td>

<span class="badge {result_class(data["control_pass"])}">

{result_text(data["control_pass"])}

</span>

</td>

</tr>

<tr>

<td>
FINAL
</td>

<td>

<span class="badge {result_class(data["final_pass"])}">

{result_text(data["final_pass"])}

</span>

</td>

</tr>

</table>
"""
        )

        # ====================================================
        # FULL JOURNAL
        # ====================================================

        parts.append(
            """
<h2>
FULL JOURNAL
</h2>

<pre>
"""
        )

        for entry in self.log_entries:

            parts.append(
                f"[{esc(entry['time'])}] "
                f"{esc(entry['text'])}\n"
            )

        parts.append(
            """
</pre>
"""
        )

        # ====================================================
        # FOOTER
        # ====================================================

        parts.append(
            """
<div class="footer">

Event 3.2 Regression Checker<br>
READ ONLY DB CHECK

</div>

</div>

</body>

</html>
"""
        )

        return "".join(
            parts
        )

    # ========================================================
    # СОХРАНЕНИЕ HTML-ОТЧЁТА
    # ========================================================

    def save_html_report(self):

        if (
            not self.report_ready
            or
            not self.report_data
        ):

            messagebox.showwarning(
                "HTML-отчёт",
                "Сначала необходимо выполнить "
                "окончательную проверку EVENT 3.2."
            )

            return

        data = self.report_data

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        default_name = (
            "3_2_regression_report_"
            f"{data['fid']}_"
            f"{timestamp}.html"
        )

        filename = filedialog.asksaveasfilename(
            title="Сохранить HTML-отчёт",
            defaultextension=".html",
            initialfile=default_name,
            filetypes=[
                (
                    "HTML files",
                    "*.html"
                ),
                (
                    "All files",
                    "*.*"
                )
            ]
        )

        if not filename:
            return

        try:

            report_html = (
                self.generate_html_report()
            )

            with open(
                filename,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(
                    report_html
                )

            self.report_file = filename

            self.write_log(
                f"✓ HTML-отчёт сохранён: "
                f"{filename}"
            )

            messagebox.showinfo(
                "HTML-отчёт",
                "HTML-отчёт успешно сохранён.\n\n"
                f"{filename}"
            )

        except Exception as e:

            self.write_log(
                f"✗ Ошибка сохранения HTML-отчёта: "
                f"{e}"
            )

            messagebox.showerror(
                "Ошибка сохранения HTML-отчёта",
                str(e)
            )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = BaselineApp(
        root
    )

    root.mainloop()