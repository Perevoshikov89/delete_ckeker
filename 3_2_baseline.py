import json
import getpass
from datetime import datetime

import ibm_db


# ============================================================
# Настройки подключения
# ============================================================

HOST = "10.230.227.100"
PORT = "2668"
DATABASE = "cprosd22"
USER = "yperevos"
SCHEMA = "INDIC"


# ============================================================
# Таблицы для проверки
# ============================================================

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
# Подключение
# ============================================================

def connect_to_db():

    password = getpass.getpass("Пароль Db2: ")

    conn_str = (
        f"DATABASE={DATABASE};"
        f"HOSTNAME={HOST};"
        f"PORT={PORT};"
        f"PROTOCOL=TCPIP;"
        f"UID={USER};"
        f"PWD={password};"
    )

    try:
        conn = ibm_db.connect(conn_str, "", "")

        print()
        print("Подключение к Db2 успешно.")
        print(f"Server : {DATABASE}")
        print(f"Schema : {SCHEMA}")
        print()

        return conn

    except Exception as e:
        print()
        print("ОШИБКА ПОДКЛЮЧЕНИЯ:")
        print(e)
        raise SystemExit(1)


# ============================================================
# Проверка одной таблицы
# ============================================================

def check_table(conn, table_name, fid):

    sql = f"""
        SELECT
            fid,
            acc_serial_num,
            reported_dt,
            COUNT(*) AS cnt
        FROM {SCHEMA}.{table_name}
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

        stmt = ibm_db.prepare(conn, sql)

        ibm_db.bind_param(stmt, 1, fid)

        ibm_db.execute(stmt)

        rows = []

        while True:

            row = ibm_db.fetch_assoc(stmt)

            if not row:
                break

            rows.append({
                "fid": str(row["FID"]),
                "acc_serial_num": str(row["ACC_SERIAL_NUM"]),
                "reported_dt": (
                    str(row["REPORTED_DT"])
                    if row["REPORTED_DT"] is not None
                    else None
                ),
                "count": int(row["CNT"])
            })

        return rows

    except Exception as e:

        print(f"  ERROR: {e}")

        return {
            "error": str(e)
        }


# ============================================================
# Основная функция
# ============================================================

def main():

    print("=" * 70)
    print("3.2 REGRESSION — DB BASELINE")
    print("=" * 70)

    fid = input("Введите FID: ").strip()

    if not fid:
        print("FID не указан.")
        return

    print()
    print(f"FID: {fid}")
    print()
    print("Начинаем снятие baseline...")
    print()

    conn = connect_to_db()

    baseline = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "database": DATABASE,
        "schema": SCHEMA,
        "fid": fid,
        "tables": {}
    }

    total_records = 0

    for index, table in enumerate(TABLES, start=1):

        print(f"[{index:02d}/{len(TABLES)}] {table} ...", end=" ")

        result = check_table(conn, table, fid)

        baseline["tables"][table] = result

        if isinstance(result, dict) and "error" in result:

            print("ERROR")

        else:

            table_count = sum(
                row["count"]
                for row in result
            )

            total_records += table_count

            print(f"OK ({table_count} записей)")

            for row in result:

                print(
                    f"      {row['acc_serial_num']} | "
                    f"{row['reported_dt']} | "
                    f"{row['count']}"
                )

    ibm_db.close(conn)

    # ========================================================
    # Сохраняем baseline
    # ========================================================

    filename = (
        "baseline_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".json"
    )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            baseline,
            file,
            ensure_ascii=False,
            indent=4
        )

    print()
    print("=" * 70)
    print("BASELINE ГОТОВ")
    print("=" * 70)

    print(f"FID:              {fid}")
    print(f"Таблиц проверено: {len(TABLES)}")
    print(f"Всего записей:    {total_records}")
    print(f"Файл:             {filename}")
    print("=" * 70)


# ============================================================
# Запуск
# ============================================================

if __name__ == "__main__":
    main()