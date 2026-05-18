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
    # SAVE DNS
    # ======================================================

    def save_dns(self, hosts, cnames):

        try:

            payload = {
                "config": {
                    "dns": {
                        "hosts": hosts,
                        "cnameRecords": cnames
                    }
                }
            }

            response = self.session.patch(
                f"{self.url}/api/config",
                json=payload,
                timeout=10,
                verify=False
            )

            if response.status_code not in [200, 201]:

                print("\n❌ Помилка збереження")
                print(response.text)

                log_action(
                    "SAVE_CONFIG",
                    "ERROR",
                    response.text
                )

                return False

            log_action(
                "SAVE_CONFIG",
                "OK",
                f"hosts={len(hosts)} cnames={len(cnames)}"
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
    # GET HOSTS
    # ======================================================

    def get_hosts(self):

        config = self.get_config()

        if not config:
            return []

        dns = config.get("dns", {})
        hosts = dns.get("hosts", [])

        records = []

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
                    "address": ip,
                    "type": "A"
                })

            except Exception:
                pass

        return records

    # ======================================================
    # GET CNAMES
    # ======================================================

    def get_cnames(self):

        config = self.get_config()

        if not config:
            return []

        dns = config.get("dns", {})
        cnames = dns.get("cnameRecords", [])

        records = []

        if not isinstance(cnames, list):
            return []

        for item in cnames:

            try:

                parts = item.strip().split(",")

                if len(parts) < 2:
                    continue

                alias = parts[0].strip()
                target = parts[1].strip()

                records.append({
                    "alias": alias,
                    "target": target,
                    "type": "CNAME"
                })

            except Exception:
                pass

        return records

    # ======================================================
    # PRINT RECORDS
    # ======================================================

    def print_records(self):

        hosts = self.get_hosts()
        cnames = self.get_cnames()

        print("\n================================================")
        print(" DNS RECORDS")
        print("================================================")

        print("\n--- HOST RECORDS ---")

        if not hosts:
            print("Немає host записів")

        for idx, record in enumerate(hosts, start=1):

            print(
                f"{idx}. [A] "
                f"{record['domain']} -> "
                f"{record['address']}"
            )

        print("\n--- CNAME RECORDS ---")

        if not cnames:
            print("Немає CNAME записів")

        for idx, record in enumerate(cnames, start=1):

            print(
                f"{idx}. [CNAME] "
                f"{record['alias']} -> "
                f"{record['target']}"
            )

        print("================================================\n")

    # ======================================================
    # ADD HOST RECORD
    # ======================================================

    def add_host_record(self):

        host = input("Hostname: ").strip()
        ip = input("IP Address: ").strip()

        new_record = f"{ip} {host}"

        print(f"\nДодати HOST запис: {new_record}")

        confirm = input("Підтвердити? (yes/no): ").lower()

        if confirm != "yes":
            return

        config = self.get_config()

        dns = config.get("dns", {})

        hosts = dns.get("hosts", [])
        cnames = dns.get("cnameRecords", [])

        if new_record in hosts:
            print("\n⚠️ Запис вже існує")
            return

        hosts.append(new_record)

        if self.save_dns(hosts, cnames):

            print("\n✅ HOST запис додано")

            log_action(
                "ADD_HOST",
                "OK",
                new_record
            )

    # ======================================================
    # DELETE HOST RECORD
    # ======================================================

    def delete_host_record(self):

        hosts = self.get_hosts()

        if not hosts:
            print("Немає HOST записів")
            return

        print("--- HOST RECORDS ---")

        for idx, record in enumerate(hosts, start=1):

            print(
                f"{idx}. "
                f"{record['domain']} -> "
                f"{record['address']}"
            )

        try:

            index = int(input("Номер запису: ")) - 1

            if index < 0 or index >= len(hosts):
                print("Невірний номер")
                return

            record = hosts[index]

            record_string = (
                f"{record['address']} "
                f"{record['domain']}"
            )

            confirm = input(
                f"Видалити {record_string}? (yes/no): "
            ).lower()

            if confirm != "yes":
                return

            config = self.get_config()

            dns = config.get("dns", {})

            host_records = dns.get("hosts", [])
            cnames = dns.get("cnameRecords", [])

            host_records = [
                x for x in host_records
                if x != record_string
            ]

            if self.save_dns(host_records, cnames):

                print("✅ HOST запис видалено")

                log_action(
                    "DELETE_HOST",
                    "OK",
                    record_string
                )

        except Exception as e:

            print(f"❌ Помилка: {e}")

            log_action(
                "DELETE_HOST",
                "ERROR",
                str(e)
            )

    # ======================================================
    # ADD CNAME RECORD
    # ======================================================

    def add_cname_record(self):

        alias = input("Alias: ").strip()
        target = input("Target hostname: ").strip()

        new_record = f"{alias},{target}"

        print(f"\nДодати CNAME запис: {alias} -> {target}")

        confirm = input("Підтвердити? (yes/no): ").lower()

        if confirm != "yes":
            return

        config = self.get_config()

        dns = config.get("dns", {})

        hosts = dns.get("hosts", [])
        cnames = dns.get("cnameRecords", [])

        if new_record in cnames:
            print("\n⚠️ Запис вже існує")
            return

        cnames.append(new_record)

        if self.save_dns(hosts, cnames):

            print("\n✅ CNAME запис додано")

            log_action(
                "ADD_CNAME",
                "OK",
                new_record
            )

    # ======================================================
    # DELETE CNAME
    # ======================================================

    def delete_cname_record(self):

        cnames = self.get_cnames()

        if not cnames:
            print("Немає CNAME записів")
            return

        print("\n--- CNAME RECORDS ---")

        for idx, record in enumerate(cnames, start=1):

            print(
                f"{idx}. "
                f"{record['alias']} -> "
                f"{record['target']}"
            )

        index = int(input("Номер запису: ")) - 1

        if index < 0 or index >= len(cnames):
            print("Невірний номер")
            return

        record = cnames[index]

        record_string = (
            f"{record['alias']},"
            f"{record['target']}"
        )

        confirm = input(
            f"Видалити {record_string}? (yes/no): "
        ).lower()

        if confirm != "yes":
            return

        config = self.get_config()

        dns = config.get("dns", {})

        hosts = dns.get("hosts", [])
        cname_records = dns.get("cnameRecords", [])

        cname_records = [
            x for x in cname_records
            if x != record_string
        ]

        if self.save_dns(hosts, cname_records):

            print("\n✅ CNAME запис видалено")

            log_action(
                "DELETE_CNAME",
                "OK",
                record_string
            )

    # ======================================================
    # MENU
    # ======================================================

    def menu(self):

        while True:

            self.print_records()

            print("1. Додати HOST запис")
            print("2. Видалити HOST запис")
            print("3. Додати CNAME запис")
            print("4. Видалити CNAME запис")
            print("5. Оновити список")
            print("6. Вийти")

            choice = input("\nВаш вибір: ").strip()

            if choice == "1":
                self.add_host_record()

            elif choice == "2":
                self.delete_host_record()

            elif choice == "3":
                self.add_cname_record()

            elif choice == "4":
                self.delete_cname_record()

            elif choice == "5":
                continue

            elif choice == "6":

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