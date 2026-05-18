#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import logging
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(
    filename="pihole_dns_manager.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def log_action(action, status="OK", details=""):
    logging.info(
        f"{action} | STATUS={status} | DETAILS={details}"
    )


# ==========================================================
# PIHOLE MANAGER
# ==========================================================

class PiHoleManager:

    def __init__(self, url, password):

        self.url = url.rstrip("/")
        self.password = password

        self.session = requests.Session()

    # ======================================================
    # AUTH
    # ======================================================

    def authenticate(self):

        try:

            response = self.session.post(
                f"{self.url}/api/auth",
                json={
                    "password": self.password
                },
                timeout=10,
                verify=False
            )

            if response.status_code != 200:

                print("\n❌ Помилка авторизації")
                print(response.text)

                log_action(
                    "AUTH",
                    "ERROR",
                    response.text
                )

                return False

            data = response.json()

            sid = data.get("session", {}).get("sid")

            if not sid:

                print("\n❌ SID не отримано")

                log_action(
                    "AUTH",
                    "ERROR",
                    str(data)
                )

                return False

            self.session.headers.update({
                "X-FTL-SID": sid
            })

            print("\n✅ Авторизація успішна")

            log_action(
                "AUTH",
                "OK",
                self.url
            )

            return True

        except Exception as e:

            print(f"\n❌ Помилка: {e}")

            log_action(
                "AUTH",
                "ERROR",
                str(e)
            )

            return False

    # ======================================================
    # GET CONFIG
    # ======================================================

    def get_config(self):

        try:

            response = self.session.get(
                f"{self.url}/api/config",
                timeout=10,
                verify=False
            )

            if response.status_code != 200:

                print("\n❌ Помилка отримання config")
                print(response.text)

                log_action(
                    "GET_CONFIG",
                    "ERROR",
                    response.text
                )

                return None

            data = response.json()

            return data.get("config", {})

        except Exception as e:

            print(f"\n❌ Помилка: {e}")

            log_action(
                "GET_CONFIG",
                "ERROR",
                str(e)
            )

            return None

    # ======================================================
    # SAVE HOSTS
    # ======================================================

    def save_hosts(self, hosts):

        try:

            payload = {
                "config": {
                    "dns": {
                        "hosts": hosts
                    }
                }
            }

            print("\nDEBUG SAVE PAYLOAD:")
            print(payload)

            response = self.session.patch(
                f"{self.url}/api/config",
                json=payload,
                timeout=10,
                verify=False
            )

            print("\nDEBUG RESPONSE:")
            print(response.status_code)
            print(response.text)

            if response.status_code not in [200, 201]:

                print("\n❌ Помилка збереження")

                log_action(
                    "SAVE_CONFIG",
                    "ERROR",
                    response.text
                )

                return False

            log_action(
                "SAVE_CONFIG",
                "OK",
                f"records={len(hosts)}"
            )

            return True

        except Exception as e:

            print(f"\n❌ Помилка: {e}")

            log_action(
                "SAVE_CONFIG",
                "ERROR",
                str(e)
            )

            return False

    # ======================================================
    # GET RECORDS
    # ======================================================

    def get_records(self):

        config = self.get_config()

        if not config:
            return []

        dns = config.get("dns", {})
        hosts = dns.get("hosts", [])

        records = []

        print("\nDEBUG HOSTS:")
        print(hosts)

        if not isinstance(hosts, list):
            return []

        for item in hosts:

            try:

                parts = item.strip().split()

                if len(parts) < 2:
                    continue

                ip = parts[0]
                domain = parts[1]

                records.append({
                    "domain": domain,
                    "address": ip
                })

            except Exception:
                pass

        return records

    # ======================================================
    # PRINT RECORDS
    # ======================================================

    def print_records(self):

        records = self.get_records()

        print("\n================================================")
        print(" LOCAL DNS RECORDS")
        print("================================================")

        if not records:

            print("Немає записів")
            print("================================================\n")

            return records

        for idx, record in enumerate(records, start=1):

            print(
                f"{idx}. "
                f"{record['domain']} -> "
                f"{record['address']}"
            )

        print("================================================\n")

        return records

    # ======================================================
    # ADD RECORD
    # ======================================================

    def add_record(self):

        host = input("Hostname: ").strip()
        ip = input("IP Address: ").strip()

        new_record = f"{ip} {host}"

        print("\nНовий запис:")
        print(new_record)

        confirm = input("\nПідтвердити? (yes/no): ").lower()

        if confirm != "yes":

            print("Скасовано")

            log_action(
                "ADD_RECORD",
                "CANCELLED",
                new_record
            )

            return

        config = self.get_config()

        if not config:
            return

        dns = config.get("dns", {})
        hosts = dns.get("hosts", [])

        if not isinstance(hosts, list):
            hosts = []

        if new_record in hosts:

            print("\n⚠️ Запис вже існує")
            return

        hosts.append(new_record)

        if self.save_hosts(hosts):

            print("\n✅ Запис додано")

            log_action(
                "ADD_RECORD",
                "OK",
                new_record
            )

    # ======================================================
    # DELETE RECORD
    # ======================================================

    def delete_record(self):

        records = self.print_records()

        if not records:
            return

        try:

            index = int(
                input("Номер запису для видалення: ")
            ) - 1

            if index < 0 or index >= len(records):

                print("Невірний номер")
                return

            record = records[index]

            record_string = (
                f"{record['address']} "
                f"{record['domain']}"
            )

            print("\nВидалити запис:")
            print(record_string)

            confirm = input("\nПідтвердити? (yes/no): ").lower()

            if confirm != "yes":

                print("Скасовано")

                log_action(
                    "DELETE_RECORD",
                    "CANCELLED",
                    record_string
                )

                return

            config = self.get_config()

            if not config:
                return

            dns = config.get("dns", {})
            hosts = dns.get("hosts", [])

            if not isinstance(hosts, list):
                hosts = []

            hosts = [
                x for x in hosts
                if x != record_string
            ]

            if self.save_hosts(hosts):

                print("\n✅ Запис видалено")

                log_action(
                    "DELETE_RECORD",
                    "OK",
                    record_string
                )

        except Exception as e:

            print(f"\n❌ Помилка: {e}")

            log_action(
                "DELETE_RECORD",
                "ERROR",
                str(e)
            )

    # ======================================================
    # EDIT RECORD
    # ======================================================

    def edit_record(self):

        records = self.print_records()

        if not records:
            return

        try:

            index = int(
                input("Номер запису для редагування: ")
            ) - 1

            if index < 0 or index >= len(records):

                print("Невірний номер")
                return

            record = records[index]

            old_record = (
                f"{record['address']} "
                f"{record['domain']}"
            )

            print("\nПоточний запис:")
            print(old_record)

            new_host = input(
                f"Hostname [{record['domain']}]: "
            ).strip()

            new_ip = input(
                f"IP [{record['address']}]: "
            ).strip()

            if not new_host:
                new_host = record["domain"]

            if not new_ip:
                new_ip = record["address"]

            new_record = f"{new_ip} {new_host}"

            print("\nНовий запис:")
            print(new_record)

            confirm = input("\nПідтвердити? (yes/no): ").lower()

            if confirm != "yes":

                print("Скасовано")

                log_action(
                    "EDIT_RECORD",
                    "CANCELLED",
                    old_record
                )

                return

            config = self.get_config()

            if not config:
                return

            dns = config.get("dns", {})
            hosts = dns.get("hosts", [])

            if not isinstance(hosts, list):
                hosts = []

            # Видалити старий
            hosts = [
                x for x in hosts
                if x != old_record
            ]

            # Додати новий
            hosts.append(new_record)

            if self.save_hosts(hosts):

                print("\n✅ Запис оновлено")

                log_action(
                    "EDIT_RECORD",
                    "OK",
                    f"{old_record} -> {new_record}"
                )

        except Exception as e:

            print(f"\n❌ Помилка: {e}")

            log_action(
                "EDIT_RECORD",
                "ERROR",
                str(e)
            )

    # ======================================================
    # MENU
    # ======================================================

    def menu(self):

        while True:

            self.print_records()

            print("1. Додати запис")
            print("2. Редагувати запис")
            print("3. Видалити запис")
            print("4. Оновити список")
            print("5. Вийти")

            choice = input("\nВаш вибір: ").strip()

            if choice == "1":
                self.add_record()

            elif choice == "2":
                self.edit_record()

            elif choice == "3":
                self.delete_record()

            elif choice == "4":
                continue

            elif choice == "5":

                print("\nВихід...")

                log_action(
                    "EXIT",
                    "OK",
                    self.url
                )

                break

            else:
                print("\n❌ Невірний вибір")


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("========================================")
    print(" Pi-hole DNS Manager")
    print("========================================\n")

    pihole_url = input(
        "Pi-hole URL (https://192.168.1.2): "
    ).strip()

    password = input(
        "Pi-hole Password: "
    ).strip()

    manager = PiHoleManager(
        pihole_url,
        password
    )

    if not manager.authenticate():
        sys.exit(1)

    manager.menu()


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":
    main()