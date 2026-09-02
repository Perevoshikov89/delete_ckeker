import json
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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

        self.root.title("3.2 Regression Checker — DB Baseline")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        self.conn = None
        self.baseline = None

        self.create_ui()

    # ========================================================
    # UI
    # ========================================================

    def create_ui(self):

        main = ttk.Frame(self.root, padding=15)
        main.pack(fill="both", expand=True)

        title = ttk.Label(
            main,
            text="3.2 Regression Checker",
            font=("Segoe UI", 18, "bold")
        )
        title.pack(anchor="w")

        subtitle = ttk.Label(
            main,
            text="Снятие read-only BASELINE перед проверкой события 3.2"
        )
        subtitle.pack(anchor="w", pady=(0, 15))

        # ----------------------------------------------------
        # Подключение
        # ----------------------------------------------------

        db_frame = ttk.LabelFrame(
            main,
            text="Подключение к Db2",
            padding=10
        )
        db_frame.pack(fill="x")

        self.host = self.add_field(
            db_frame, "Host:", HOST, 0
        )

        self.port = self.add_field(
            db_frame, "Port:", PORT, 1
        )

        self.database = self.add_field(
            db_frame, "Database:", DATABASE, 2
        )

        self.schema = self.add_field(
            db_frame, "Schema:", SCHEMA, 3
        )

        self.user = self.add_field(
            db_frame, "User:", USER, 4
        )

        self.password = self.add_field(
            db_frame, "Password:", "", 5, show="*"
        )

        # ----------------------------------------------------
        # FID
        # ----------------------------------------------------

        fid_frame = ttk.LabelFrame(
            main,
            text="Тестовый субъект",
            padding=10
        )
        fid_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(
            fid_frame,
            text="FID:"
        ).grid(row=0, column=0, sticky="w")

        self.fid = ttk.Entry(fid_frame, width=55)
        self.fid.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(10, 0)
        )

        fid_frame.columnconfigure(1, weight=1)

        # ----------------------------------------------------
        # Кнопки
        # ----------------------------------------------------

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=12)

        self.test_button = ttk.Button(
            buttons,
            text="Проверить подключение",
            command=self.test_connection
        )
        self.test_button.pack(side="left")

        self.baseline_button = ttk.Button(
            buttons,
            text="Снять BASELINE",
            command=self.start_baseline
        )
        self.baseline_button.pack(side="left", padx=10)

        self.save_button = ttk.Button(
            buttons,
            text="Сохранить результат",
            command=self.save_baseline,
            state="disabled"
        )
        self.save_button.pack(side="left")

        # ----------------------------------------------------
        # Прогресс
        # ----------------------------------------------------

        progress_frame = ttk.Frame(main)
        progress_frame.pack(fill="x")

        self.progress = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=len(TABLES)
        )
        self.progress.pack(fill="x")

        self.progress_label = ttk.Label(
            progress_frame,
            text="Готово к работе"
        )
        self.progress_label.pack(anchor="w", pady=(5, 0))

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

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log.yview
        )
        scrollbar.pack(side="right", fill="y")

        self.log.configure(
            yscrollcommand=scrollbar.set
        )

        self.write_log("Программа запущена.")
        self.write_log("Режим БД: READ ONLY — используются только SELECT.")

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
            width=12
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

        entry.insert(0, value)

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
    # Лог
    # ========================================================

    def write_log(self, text):

        def append():

            timestamp = datetime.now().strftime("%H:%M:%S")

            self.log.insert(
                "end",
                f"[{timestamp}] {text}\n"
            )

            self.log.see("end")

        self.root.after(0, append)

    # ========================================================
    # Подключение
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

            row = ibm_db.fetch_assoc(stmt)

            server = row["CURRENT SERVER"]
            schema = row["CURRENT SCHEMA"]

            ibm_db.close(conn)

            self.write_log(
                f"✓ Подключение успешно. SERVER={server}, SCHEMA={schema}"
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

        self.progress["value"] = 0

        self.log.delete(
            "1.0",
            "end"
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

    def baseline_thread(self, fid):

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

                if isinstance(rows, dict):

                    self.write_log(
                        f"    ✗ ERROR: {rows['error']}"
                    )

                else:

                    table_total = sum(
                        row["count"]
                        for row in rows
                    )

                    total += table_total

                    self.write_log(
                        f"    записей: {table_total}"
                    )

                    for row in rows:

                        self.write_log(
                            f"      "
                            f"{row['acc_serial_num']} | "
                            f"{row['reported_dt']} | "
                            f"{row['count']}"
                        )

            ibm_db.close(conn)

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

            ibm_db.execute(stmt)

            rows = []

            while True:

                row = ibm_db.fetch_assoc(
                    stmt
                )

                if not row:
                    break

                rows.append({
                    "fid": str(row["FID"]),
                    "acc_serial_num": str(
                        row["ACC_SERIAL_NUM"]
                    ),
                    "reported_dt": (
                        str(row["REPORTED_DT"])
                        if row["REPORTED_DT"] is not None
                        else None
                    ),
                    "count": int(row["CNT"])
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
                    f"Обработка: {value}/{len(TABLES)} — "
                    f"{table}"
                )
            )

        self.root.after(
            0,
            update
        )

    # ========================================================
    # Сохранение
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


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = BaselineApp(root)

    root.mainloop()