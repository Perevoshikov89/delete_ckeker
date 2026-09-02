import getpass
import ibm_db


HOST = "10.230.227.100"
PORT = "2668"
DATABASE = "cprosd22"
USER = "yperevos"


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

    print("Подключение к Db2 успешно!")

    stmt = ibm_db.exec_immediate(
        conn,
        "SELECT CURRENT SERVER, CURRENT SCHEMA FROM SYSIBM.SYSDUMMY1"
    )

    row = ibm_db.fetch_assoc(stmt)

    print(f"CURRENT SERVER: {row['CURRENT SERVER']}")
    print(f"CURRENT SCHEMA: {row['CURRENT SCHEMA']}")

    ibm_db.close(conn)

except Exception as e:
    print("Ошибка подключения:")
    print(e)